import tarfile
import subprocess
import shutil
import re
import os
import platform
from pathlib import Path
from typing import List, Optional, Tuple
from ..utils.logger import setup_logger
from ..utils.file_system import (
    get_base_name, 
    create_unique_temp_dir, 
    categorize_files, 
    safe_copy_file
)
from ..utils.ai_service import ai_service
from ..config import (
    COMMON_MAIN_TEX_NAMES, 
    TEX_RELATED_EXTENSIONS,
    SOURCE_CODE_EXTENSIONS,
    FILE_FILTERING_CONFIG
)


logger = setup_logger("tex_processor")

def process(gz_path: Path, output_base_dir: Path, temp_base_dir: Path) -> Tuple[bool, str]:
    """
    处理TeX压缩包，解压并转换为HTML
    
    Args:
        gz_path: 压缩包路径
        output_base_dir: 输出基础目录
        temp_base_dir: 临时目录
        
    Returns:
        (处理是否成功, 错误信息)
    """
    base_name = get_base_name(gz_path)
    final_output_dir = output_base_dir / base_name
    temp_extract_dir = None
    temp_output_dir = None
    
    try:
        logger.info(f"开始处理TeX压缩包: {gz_path}")
        
        # 创建临时目录
        temp_extract_dir = create_unique_temp_dir(temp_base_dir, f"extract_{base_name}_")
        temp_output_dir = create_unique_temp_dir(temp_base_dir, f"output_{base_name}_")
        
        # 准备临时输出路径
        temp_assets_dir = temp_output_dir / 'assets'
        temp_assets_dir.mkdir(parents=True, exist_ok=True)
        
        # 解压文件
        try:
            extract_archive(gz_path, temp_extract_dir)
        except Exception as e:
            error_msg = f"解压失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        
        # 查找主TeX文件
        main_tex_path = find_main_tex_file(temp_extract_dir)
        if not main_tex_path:
            error_msg = f"无法找到主TeX文件 (搜索了常见的主文件名和包含\\documentclass的文件)"
            logger.error(error_msg)
            return False, error_msg
        
        logger.info(f"找到主TeX文件: {main_tex_path}")
        
        # 智能处理其他附件 - 根据配置选择筛选策略
        try:
            process_additional_files(temp_extract_dir, temp_assets_dir)
        except Exception as e:
            logger.warning(f"处理附件时出错: {e}")
            # 附件处理失败不影响主要功能
        
        # 使用LaTeXML转换到临时目录（改回HTML格式）
        temp_html_path = temp_output_dir / f"{base_name}.html"
        success, latexml_error = convert_with_latexml_html(main_tex_path, temp_html_path, temp_extract_dir)
        
        if not success:
            error_msg = f"LaTeXML转换失败: {latexml_error}"
            logger.error(error_msg)
            return False, error_msg
        
        # HTML格式支持附件链接，将附件信息添加到HTML文件中
        append_asset_links_to_html(temp_html_path, temp_assets_dir)
        logger.info(f"HTML转换完成，附件文件已保存在assets目录: {temp_assets_dir}")
        
        # 新增: 将HTML转换为Markdown
        logger.info("尝试将HTML转换为Markdown...")
        md_success, md_message = convert_html_to_markdown(temp_html_path)
        if md_success:
            logger.info(f"成功创建Markdown文件: {md_message}")
        else:
            logger.warning(f"HTML到Markdown转换失败 (此步骤为可选，不影响主流程): {md_message}")
        
        # 所有处理成功，将临时输出目录移动到最终位置
        if final_output_dir.exists():
            shutil.rmtree(final_output_dir)
            logger.debug(f"清理已存在的输出目录: {final_output_dir}")
        
        shutil.move(str(temp_output_dir), str(final_output_dir))
        temp_output_dir = None  # 标记为已移动，避免在finally中删除
        
        logger.info(f"TeX处理完成: {gz_path} -> {final_output_dir}")
        return True, ""
        
    except Exception as e:
        error_msg = f"未知错误: {str(e)}"
        logger.error(f"处理TeX文件 {gz_path} 时出错: {e}")
        return False, error_msg
        
    finally:
        # 清理临时目录
        if temp_extract_dir and temp_extract_dir.exists():
            try:
                shutil.rmtree(temp_extract_dir)
                logger.debug(f"已清理解压临时目录: {temp_extract_dir}")
            except Exception as e:
                logger.warning(f"清理解压临时目录时出错: {e}")
        
        # 如果temp_output_dir不为None，说明移动失败或处理失败，需要清理
        if temp_output_dir and temp_output_dir.exists():
            try:
                shutil.rmtree(temp_output_dir)
                logger.debug(f"已清理输出临时目录: {temp_output_dir}")
            except Exception as e:
                logger.warning(f"清理输出临时目录时出错: {e}")

def extract_archive(archive_path: Path, extract_dir: Path) -> None:
    """
    解压压缩文件
    
    Args:
        archive_path: 压缩文件路径
        extract_dir: 解压目录
    """
    logger.debug(f"解压 {archive_path} 到 {extract_dir}")
    
    try:
        with tarfile.open(archive_path, 'r:gz') as tar:
            tar.extractall(path=extract_dir)
    except Exception as e:
        logger.error(f"解压文件 {archive_path} 失败: {e}")
        raise

def find_main_tex_file(directory: Path) -> Optional[Path]:
    """
    在目录中查找主TeX文件
    
    Args:
        directory: 要搜索的目录
        
    Returns:
        主TeX文件路径，如果未找到则返回None
    """
    logger.debug(f"在目录 {directory} 中查找主TeX文件")
    
    # 策略1: 查找常见的主文件名
    for main_name in COMMON_MAIN_TEX_NAMES:
        main_path = directory / main_name
        if main_path.exists():
            logger.debug(f"通过文件名找到主TeX文件: {main_path}")
            return main_path
    
    # 策略2: 查找包含\documentclass的文件
    tex_files = list(directory.rglob("*.tex"))
    main_candidates = []
    
    for tex_file in tex_files:
        try:
            with open(tex_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                if re.search(r'\\documentclass', content):
                    main_candidates.append(tex_file)
                    logger.debug(f"找到包含\\documentclass的文件: {tex_file}")
        except Exception as e:
            logger.warning(f"读取文件 {tex_file} 时出错: {e}")
            continue
    
    if len(main_candidates) == 1:
        return main_candidates[0]
    elif len(main_candidates) > 1:
        # 如果有多个候选文件，选择路径最短的（通常是根目录）
        main_file = min(main_candidates, key=lambda x: len(str(x)))
        logger.warning(f"找到多个主TeX文件候选，选择: {main_file}")
        return main_file
    
    # 策略3: 如果还没找到，选择根目录下的第一个.tex文件
    root_tex_files = [f for f in directory.glob("*.tex")]
    if root_tex_files:
        main_file = root_tex_files[0]
        logger.warning(f"使用根目录下的第一个TeX文件: {main_file}")
        return main_file
    
    logger.error(f"在 {directory} 中未找到任何主TeX文件")
    return None

def convert_with_latexml_html(main_tex_path: Path, output_html_path: Path, extract_dir: Path) -> Tuple[bool, str]:
    """
    使用LaTeXML将TeX转换为HTML，自适应Windows和Linux环境
    
    Args:
        main_tex_path: 主TeX文件路径
        output_html_path: 输出HTML文件路径
        extract_dir: 解压目录
        
    Returns:
        (转换是否成功, 错误信息)
    """
    logger.debug(f"使用LaTeXML转换 {main_tex_path} -> {output_html_path}")
    
    try:
        # 准备目录
        output_dir = output_html_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 自适应环境处理路径
        is_windows = platform.system().lower() == 'windows'
        
        # 获取相对于extract_dir的main_tex_path
        rel_main_tex_path = main_tex_path.relative_to(extract_dir)
        
        # 构建路径字符串
        if is_windows:
            extract_dir_str = str(extract_dir).replace('\\', '/')
            output_dir_str = str(output_dir).replace('\\', '/')
        else:
            extract_dir_str = str(extract_dir)
            output_dir_str = str(output_dir)
        
        # 构建Docker命令
        docker_cmd = [
            "docker", "run", "--rm",
            "-v", f"{extract_dir_str}:/data",
            "-v", f"{output_dir_str}:/output",
            "latexml/ar5ivist", "ar5iv",
            f"--source=/data/{rel_main_tex_path}",
            f"--dest=/output/{output_html_path.name}",
            "--format=html5"
        ]
        
        # 执行Docker命令
        logger.info(f"开始LaTeXML转换，这可能需要一些时间...")
        logger.debug(f"LaTeXML命令: {' '.join(docker_cmd)}")
        
        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        
        if result.returncode == 0 and output_html_path.exists():
            logger.info(f"LaTeXML转换成功: {output_html_path}")
            return True, ""
        else:
            error_msg = f"LaTeXML转换失败，返回码: {result.returncode}, stderr: {result.stderr}"
            logger.error(error_msg)
            return False, error_msg
            
    except subprocess.TimeoutExpired:
        error_msg = "LaTeXML转换超时（300秒）"
        logger.warning(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"执行LaTeXML时出错: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def should_skip_file(file_path: Path) -> bool:
    """
    判断是否应该跳过某个文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        是否应该跳过
    """
    # 跳过隐藏文件
    if file_path.name.startswith('.'):
        return True
    
    # 跳过LaTeX编译相关的临时文件和辅助文件
    skip_extensions = {
        '.log', '.aux', '.bbl', '.blg', '.fdb_latexmk', '.fls', '.out', '.toc',
        '.lof', '.lot', '.nav', '.snm', '.vrb', '.spl', '.fls', '.synctex.gz'
    }
    if file_path.suffix.lower() in skip_extensions:
        return True
    
    # 跳过LaTeX系统文件
    skip_files = {
        'elsarticle.dtx', 'elsarticle.ins', 'elsarticle.cls',
        'model1-num-names.bst', 'model2-names.bst', 'model3-num-names.bst',
        'model4-names.bst', 'model5-names.bst', 'model6-num-names.bst',
        'natbib.sty', 'harvard.sty', 'apalike.sty',
        'README', 'readme.txt', 'README.txt'
    }
    if file_path.name.lower() in skip_files:
        return True
    
    # 跳过明显的模板和样式文件
    if any(pattern in file_path.name.lower() for pattern in [
        'template', 'sample', 'example', 'demo',
        'elsarticle', 'ieeetran', 'llncs', 'lipics'
    ]):
        return True
    
    # 跳过空文件
    try:
        if file_path.stat().st_size == 0:
            return True
    except:
        return True
    
    return False

def append_asset_links_to_html(html_path: Path, assets_dir: Path) -> None:
    """
    在HTML文件末尾添加资源文件链接
    
    Args:
        html_path: HTML文件路径
        assets_dir: 资源目录
    """
    try:
        # 收集文件信息（现在所有文件都在assets目录的根目录下）
        asset_files = []
        if assets_dir.exists():
            for file_path in assets_dir.glob('*'):  # 只扫描一层，不用rglob
                if file_path.is_file():
                    rel_path = file_path.relative_to(assets_dir.parent)
                    size_kb = file_path.stat().st_size / 1024
                    asset_files.append((str(rel_path), file_path.name, size_kb))
        
        # 如果没有附加文件，直接返回
        if not asset_files:
            logger.debug("没有发现附加文件，跳过附件部分")
            return
        else:
            logger.info(f"发现 {len(asset_files)} 个主tex未使用的附加文件")
            return
        
        
        # 读取HTML内容
        with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # 创建附件HTML内容
        attachment_html = "\n\n<div class='additional-files' style='margin-top: 2em; padding: 1em; border-top: 1px solid #ccc;'>\n"
        attachment_html += "<h2>研究相关附加文件</h2>\n"
        attachment_html += "<p>以下是筛选出的与研究相关的附加文件：</p>\n"
        
        # 添加资源文件
        attachment_html += "<h3>附加研究资源</h3>\n<ul>\n"
        for rel_path, name, size_kb in sorted(asset_files):
            size_str = f" ({size_kb:.1f} KB)" if size_kb > 0 else ""
            attachment_html += f"<li><a href='{rel_path}'>{name}</a>{size_str}</li>\n"
        attachment_html += "</ul>\n"
        
        attachment_html += "</div>\n"
        
        # 插入HTML内容
        body_end_pos = content.rfind('</body>')
        if body_end_pos == -1:
            # 如果没有</body>标签，直接添加到末尾
            content += attachment_html
        else:
            # 如果有</body>标签，在标签前插入
            content = content[:body_end_pos] + attachment_html + content[body_end_pos:]
        
        # 写回文件
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"已在HTML中添加 {len(asset_files)} 个筛选的附加文件链接")
        
    except Exception as e:
        logger.error(f"添加附件链接到XML时出错: {e}")

def judge_file_by_extension(file_path: Path) -> bool:
    """
    基于文件扩展名判断文件是否应该保留
    
    Args:
        file_path: 文件路径
        
    Returns:
        是否应该保留文件
    """
    extension = file_path.suffix.lower()
    valuable_extensions = FILE_FILTERING_CONFIG['valuable_extensions']
    
    if extension in valuable_extensions:
        logger.debug(f"基于扩展名保留文件: {file_path.name}")
        return True
    else:
        logger.debug(f"基于扩展名跳过文件: {file_path.name}")
        return False

def extract_file_content_preview(file_path: Path, max_lines: int = 200) -> str:
    """
    提取文件的前N行内容用于AI判断
    
    Args:
        file_path: 文件路径
        max_lines: 最大行数
        
    Returns:
        文件内容预览
    """
    try:
        # 尝试不同的编码
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= max_lines:
                            break
                        lines.append(line.rstrip())
                    return '\n'.join(lines)
            except UnicodeDecodeError:
                continue
        
        # 如果所有编码都失败，返回空字符串
        logger.warning(f"无法读取文件内容: {file_path}")
        return ""
        
    except Exception as e:
        logger.warning(f"提取文件内容时出错 {file_path}: {e}")
        return ""

def is_text_file(file_path: Path) -> bool:
    """
    判断文件是否为文本文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        是否为文本文件
    """
    # 明确的文本文件扩展名
    text_extensions = {
        '.txt', '.py', '.r', '.m', '.cpp', '.c', '.h', '.hpp', '.java', '.js', 
        '.html', '.css', '.xml', '.json', '.yaml', '.yml', '.csv', '.tsv',
        '.md', '.rst', '.tex', '.bib', '.sh', '.bat', '.sql', '.ini', '.cfg',
        '.conf', '.log', '.dat', '.pl', '.rb', '.php', '.go', '.rs', '.kt'
    }
    
    # 明确的二进制文件扩展名
    binary_extensions = {
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.pdf', '.eps', '.tiff',
        '.zip', '.tar', '.gz', '.bz2', '.xz', '.rar', '.7z',
        '.exe', '.dll', '.so', '.dylib', '.bin',
        '.mp3', '.mp4', '.avi', '.mov', '.wav',
        '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'
    }
    
    extension = file_path.suffix.lower()
    
    if extension in text_extensions:
        return True
    elif extension in binary_extensions:
        return False
    
    # 对于未知扩展名，尝试读取文件开头判断
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            # 检查是否包含大量null字节（通常表示二进制文件）
            if b'\x00' in chunk[:512]:
                return False
            # 尝试解码为文本
            try:
                chunk.decode('utf-8')
                return True
            except UnicodeDecodeError:
                try:
                    chunk.decode('latin-1')
                    return True
                except UnicodeDecodeError:
                    return False
    except Exception:
        return False

def process_additional_files(extract_dir: Path, assets_dir: Path) -> None:
    """
    处理额外文件，根据配置选择筛选策略
    
    Args:
        extract_dir: 解压目录
        assets_dir: 资源输出目录
    """
    enable_ai_filtering = FILE_FILTERING_CONFIG.get('enable_ai_filtering', False)
    
    if enable_ai_filtering:
        logger.info(f"开始AI智能筛选附加文件: {extract_dir}")
        filter_method = "AI"
    else:
        logger.info(f"开始基于扩展名筛选附加文件: {extract_dir}")
        filter_method = "扩展名"
    
    # 分类文件
    file_categories = categorize_files(extract_dir)
    
    kept_files = 0
    discarded_files = 0
    
    # 处理所有潜在的附加文件（包括图片文件）
    all_potential_files = (
        file_categories.get('image_files', []) +
        file_categories.get('source_code_files', []) +
        file_categories.get('other_files', [])
    )
    
    for file_path in all_potential_files:
        if should_skip_file(file_path):
            continue
        
        try:
            should_keep = False
            
            if enable_ai_filtering:
                # AI筛选策略
                # 图片文件直接基于扩展名判断，其他文件需要是文本文件才能AI判断
                if file_path.suffix.lower() in {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.pdf', '.eps', '.tiff', '.tif'}:
                    # 图片文件直接基于扩展名判断
                    should_keep = judge_file_by_extension(file_path)
                elif not is_text_file(file_path):
                    logger.debug(f"跳过二进制文件: {file_path.name}")
                    discarded_files += 1
                    continue
                
                # 提取文件内容预览
                content_preview = extract_file_content_preview(file_path)
                
                if not content_preview.strip():
                    logger.debug(f"跳过空文件或无法读取的文件: {file_path.name}")
                    discarded_files += 1
                    continue
                
                # 调用AI判断文件价值
                should_keep = ai_service.judge_file_relevance(
                    content_preview, 
                    file_path.name, 
                    file_path.suffix
                )
            else:
                # 基于扩展名的筛选策略
                should_keep = judge_file_by_extension(file_path)
            
            if should_keep:
                # 保留文件 - 直接放在assets根目录下（单层结构）
                file_name = file_path.name
                dest_path = assets_dir / file_name
                
                # 处理同名文件冲突
                counter = 1
                original_stem = file_path.stem
                original_suffix = file_path.suffix
                while dest_path.exists():
                    new_name = f"{original_stem}_{counter}{original_suffix}"
                    dest_path = assets_dir / new_name
                    counter += 1
                    if counter > 100:  # 防止无限循环
                        logger.warning(f"同名文件过多，跳过: {file_path.name}")
                        discarded_files += 1
                        break
                else:
                    # 确保目标目录存在
                    assets_dir.mkdir(parents=True, exist_ok=True)
                    
                    if safe_copy_file(file_path, dest_path):
                        relative_path = file_path.relative_to(extract_dir)
                        logger.debug(f"{filter_method}判断保留文件: {relative_path} -> {dest_path.name}")
                        kept_files += 1
                    else:
                        discarded_files += 1
            else:
                logger.debug(f"{filter_method}判断丢弃文件: {file_path.name}")
                discarded_files += 1
                
        except Exception as e:
            logger.warning(f"处理文件 {file_path.name} 时出错: {e}")
            discarded_files += 1
    
    logger.info(f"{filter_method}筛选完成 - 保留: {kept_files} 个文件, 丢弃: {discarded_files} 个文件") 

def convert_html_to_markdown(html_path: Path) -> Tuple[bool, str]:
    """
    使用pandoc将HTML文件转换为Markdown (GFM)文件，并进行后处理。
    
    Args:
        html_path: 输入的HTML文件路径
        
    Returns:
        (转换是否成功, 错误或成功信息)
    """
    md_path = html_path.with_suffix('.md')
    logger.debug(f"使用pandoc转换 {html_path} -> {md_path}")
    
    pandoc_cmd = [
        "pandoc",
        str(html_path),
        "-f", "html",
        "-t", "gfm+tex_math_dollars",
        "--wrap=none",
        "-o", str(md_path)
    ]
    
    try:
        result = subprocess.run(
            pandoc_cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0 and md_path.exists():
            try:
                # 1. 读取Markdown文件内容
                with open(md_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 2. 删除 LaTeXML 生成的页脚
                # 正则表达式匹配 "Generated on" 开始，直到 "by" 和一个完整的<a>标签结束
                footer_pattern = r'Generated on .*? by <a href="http://dlmf.nist.gov/LaTeXML/".*?</a>'
                # 使用 re.DOTALL 使 '.' 可以匹配换行符
                cleaned_content = re.sub(footer_pattern, '', content, flags=re.DOTALL).strip()
                
                # 3. 执行数学公式括号的替换: \[ -> [ 和 \] -> ]
                final_content = cleaned_content.replace('\\[', '[').replace('\\]', ']')
                
                # 4. 写回清理后的文件
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(final_content)
                
                logger.debug(f"已清理页脚并对 {md_path.name} 执行了特殊字符替换")
                
            except Exception as e:
                logger.warning(f"后处理Markdown文件 {md_path.name} 时出错: {e}")
                # 后处理失败不影响主流程，只记录警告

            return True, f"{md_path.name}"
        else:
            error_msg = f"Pandoc返回码: {result.returncode}, stderr: {result.stderr.strip()}"
            return False, error_msg
            
    except FileNotFoundError:
        error_msg = "Pandoc命令未找到。请确保pandoc已安装并处于系统的PATH中。"
        return False, error_msg
    except subprocess.TimeoutExpired:
        error_msg = f"Pandoc转换超时（120秒）"
        return False, error_msg
    except Exception as e:
        error_msg = f"执行Pandoc时出错: {str(e)}"
        return False, error_msg