#!/usr/bin/env python3
"""
arXiv论文批量转换工具
将PDF和TeX压缩包转换为结构化的Markdown文件
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from arxiv_parser.config import (
    ensure_directories, 
    SOURCE_DIR, 
    OUTPUT_DIR, 
    FAILED_DIR, 
    TEMP_DIR,
    SUPPORTED_PDF_EXTENSIONS,
    SUPPORTED_TEX_EXTENSIONS
)
from arxiv_parser.utils.logger import setup_logger
from arxiv_parser.utils.file_system import safe_move_to_failed
from arxiv_parser.processors import tex_processor

logger = setup_logger("main")

def get_file_type(file_path: Path) -> str:
    """
    确定文件类型
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件类型：'pdf', 'tex', 或 'unknown'
    """
    suffix = file_path.suffix.lower()
    
    if suffix in SUPPORTED_PDF_EXTENSIONS:
        return 'pdf'
    elif suffix in SUPPORTED_TEX_EXTENSIONS or file_path.name.endswith('.tar.gz'):
        return 'tex'
    else:
        return 'unknown'

def process_single_file(file_path: Path) -> Tuple[bool, str]:
    """
    处理单个文件（不包含失败文件移动逻辑）
    
    Args:
        file_path: 文件路径
        
    Returns:
        (处理是否成功, 错误信息)
    """
    logger.info(f"开始处理文件: {file_path.name}")
    
    file_type = get_file_type(file_path)
    
    try:
        if file_type == 'pdf':
            logger.info(f"🚫 跳过PDF文件: {file_path.name} (仅处理TeX压缩包)")
            return False, "跳过PDF文件 (仅处理TeX压缩包)"
        elif file_type == 'tex':
            success, error_msg = tex_processor.process(file_path, OUTPUT_DIR, TEMP_DIR)
            if success:
                logger.info(f"成功处理文件: {file_path.name}")
                return True, ""
            else:
                logger.error(f"处理文件失败: {file_path.name}")
                return False, error_msg
        else:
            error_msg = f"不支持的文件类型: {file_path.suffix}"
            logger.warning(f"跳过不支持的文件类型: {file_path.name}")
            return False, error_msg
            
    except Exception as e:
        error_msg = f"处理异常: {str(e)}"
        logger.error(f"处理文件 {file_path.name} 时发生异常: {e}")
        return False, error_msg

def process_single_file_with_failover(file_path: Path) -> bool:
    """
    处理单个文件并在失败时移动到failed目录
    
    Args:
        file_path: 文件路径
        
    Returns:
        处理是否成功
    """
    success, error_msg = process_single_file(file_path)
    
    if not success:
        # 立即将失败的文件移动到失败目录，并记录错误信息
        logger.warning(f"文件处理失败，立即移动到失败目录: {file_path.name}")
        
        # 清理可能已创建的输出目录
        cleanup_failed_output_directory(file_path)
        
        if safe_move_to_failed(file_path, FAILED_DIR, error_msg):
            logger.info(f"✅ 已移动失败文件: {file_path.name} -> failed/")
        else:
            logger.error(f"❌ 移动失败文件时出错: {file_path.name}")
    
    return success

def cleanup_failed_output_directory(file_path: Path):
    """
    清理失败文件可能已创建的输出目录
    
    Args:
        file_path: 原始文件路径
    """
    try:
        from .utils.file_system import get_base_name
        base_name = get_base_name(file_path)
        potential_output_dir = OUTPUT_DIR / base_name
        
        if potential_output_dir.exists():
            import shutil
            shutil.rmtree(potential_output_dir)
            logger.debug(f"已清理失败文件的输出目录: {potential_output_dir}")
    except Exception as e:
        logger.warning(f"清理失败文件的输出目录时出错: {e}")

def get_processing_statistics(source_dir: Path) -> Tuple[int, int, int]:
    """
    获取处理统计信息
    
    Args:
        source_dir: 源目录
        
    Returns:
        (总文件数, PDF文件数, TeX文件数)
    """
    all_files = list(source_dir.glob("*"))
    all_files = [f for f in all_files if f.is_file() and not f.name.startswith('.')]
    
    pdf_count = sum(1 for f in all_files if get_file_type(f) == 'pdf')
    tex_count = sum(1 for f in all_files if get_file_type(f) == 'tex')
    
    return len(all_files), pdf_count, tex_count

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("开始arXiv论文批量转换")
    logger.info("=" * 60)
    
    # 确保所有必要目录存在
    ensure_directories()
    
    # 获取源目录中的所有文件
    if not SOURCE_DIR.exists():
        logger.error(f"源目录不存在: {SOURCE_DIR}")
        return 1
    
    all_files = list(SOURCE_DIR.glob("*"))
    # 过滤掉目录和隐藏文件
    files_to_process = [f for f in all_files if f.is_file() and not f.name.startswith('.')]
    
    if not files_to_process:
        logger.warning(f"在源目录 {SOURCE_DIR} 中未找到任何文件")
        return 0
    
    # 显示统计信息
    total_files, pdf_count, tex_count = get_processing_statistics(SOURCE_DIR)
    logger.info(f"发现文件统计:")
    logger.info(f"  总文件数: {total_files}")
    logger.info(f"  PDF文件: {pdf_count} (将被跳过)")
    logger.info(f"  TeX文件: {tex_count} (将被处理)")
    logger.info(f"  其他文件: {total_files - pdf_count - tex_count}")
    
    # 处理文件
    successful_count = 0
    failed_count = 0
    skipped_count = 0
    pdf_skipped_count = 0
    
    for i, file_path in enumerate(files_to_process, 1):
        logger.info(f"\n进度: {i}/{len(files_to_process)}")
        
        file_type = get_file_type(file_path)
        if file_type == 'unknown':
            logger.info(f"跳过不支持的文件: {file_path.name}")
            skipped_count += 1
            continue
        elif file_type == 'pdf':
            logger.info(f"🚫 跳过PDF文件: {file_path.name}")
            pdf_skipped_count += 1
            continue
        
        # 处理文件（现在只处理TeX文件）
        success = process_single_file_with_failover(file_path)
        
        if success:
            successful_count += 1
        else:
            failed_count += 1
    
    # 显示最终统计
    logger.info("\n" + "=" * 60)
    logger.info("处理完成！最终统计:")
    logger.info("=" * 60)
    logger.info(f"成功处理: {successful_count} 个TeX文件")
    logger.info(f"处理失败: {failed_count} 个TeX文件")
    logger.info(f"跳过PDF文件: {pdf_skipped_count} 个文件")
    logger.info(f"跳过其他文件: {skipped_count} 个文件")
    
    if successful_count > 0:
        logger.info(f"\n成功处理的文件输出到: {OUTPUT_DIR}")
    
    if failed_count > 0:
        logger.info("您可以检查failed/目录中的失败文件并尝试手动处理")
    
    # 清理临时目录
    if TEMP_DIR.exists():
        import shutil
        for item in TEMP_DIR.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        logger.info("已清理临时目录")
    
    logger.info("\n转换任务完成！")
    
    return 0 if failed_count == 0 else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 