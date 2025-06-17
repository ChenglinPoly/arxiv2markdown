import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Tuple
from ..utils.logger import setup_logger
from ..utils.file_system import get_base_name, safe_copy_file

logger = setup_logger("pdf_processor")

def process(pdf_path: Path, output_base_dir: Path) -> bool:
    """
    处理PDF文件，提取文本和图片，生成Markdown
    
    Args:
        pdf_path: PDF文件路径
        output_base_dir: 输出基础目录
        
    Returns:
        处理是否成功
    """
    try:
        logger.info(f"开始处理PDF文件: {pdf_path}")
        
        # 准备输出路径
        base_name = get_base_name(pdf_path)
        output_dir = output_base_dir / base_name
        assets_dir = output_dir / 'assets'
        
        # 创建输出目录
        output_dir.mkdir(parents=True, exist_ok=True)
        assets_dir.mkdir(parents=True, exist_ok=True)
        
        # 打开PDF文档
        doc = fitz.open(str(pdf_path))
        
        # 提取文本和图片，直接在原位置插入图片
        full_text = extract_text_with_inline_images(doc, assets_dir)
        
        # 生成简洁的Markdown文件
        markdown_path = output_dir / f"{base_name}.md"
        generate_clean_markdown(full_text, markdown_path, base_name)
        
        # 关闭文档
        doc.close()
        
        logger.info(f"PDF处理完成: {pdf_path} -> {output_dir}")
        return True
        
    except Exception as e:
        logger.error(f"处理PDF文件 {pdf_path} 时出错: {e}")
        return False

def extract_text_with_inline_images(doc: fitz.Document, assets_dir: Path) -> str:
    """
    从PDF文档中提取文本，并在原位置插入图片链接
    
    Args:
        doc: PyMuPDF文档对象
        assets_dir: 图片保存目录
        
    Returns:
        包含内联图片的完整文本
    """
    full_text = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # 获取页面的文本块和图片信息
        page_dict = page.get_text("dict")
        
        # 获取页面图片列表
        image_list = page.get_images()
        page_images = {}
        
        # 提取并保存图片，记录图片位置信息
        for img_index, img in enumerate(image_list):
            try:
                # 获取图片数据
                xref = img[0]
                pix = fitz.Pixmap(doc, xref)
                
                # 确定图片格式和文件名
                if pix.n - pix.alpha < 4:  # 不是CMYK
                    if pix.alpha:
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    
                    img_filename = f"image-p{page_num + 1}-i{img_index + 1}.png"
                    img_path = assets_dir / img_filename
                    
                    # 保存图片
                    pix.save(str(img_path))
                    
                    # 获取图片在页面中的位置
                    # img是一个元组，包含(xref, smask, width, height, bpc, colorspace, alt, name, filter, bbox)
                    try:
                        # 尝试从image信息中获取bbox，如果没有则使用默认位置
                        if len(img) > 9 and img[9]:
                            img_bbox = fitz.Rect(img[9])
                        else:
                            # 如果没有bbox信息，使用页面中心位置
                            page_rect = page.rect
                            img_bbox = fitz.Rect(page_rect.width * 0.1, 
                                               page_rect.height * 0.1 + img_index * 50,
                                               page_rect.width * 0.9, 
                                               page_rect.height * 0.1 + img_index * 50 + 100)
                        
                        page_images[img_index] = {
                            'filename': img_filename,
                            'rect': img_bbox,
                            'y_position': img_bbox.y0  # 使用顶部y坐标作为排序依据
                        }
                    except Exception as bbox_error:
                        # 如果获取bbox失败，使用默认位置
                        page_rect = page.rect
                        default_y = page_rect.height * 0.5 + img_index * 100
                        page_images[img_index] = {
                            'filename': img_filename,
                            'rect': None,
                            'y_position': default_y
                        }
                    
                    logger.debug(f"提取图片: {img_filename} at position {img_rect}")
                
                pix = None  # 释放内存
                
            except Exception as e:
                logger.warning(f"提取第 {page_num + 1} 页第 {img_index + 1} 张图片时出错: {e}")
                continue
        
        # 提取页面文本并插入图片
        page_text = extract_page_text_with_images(page, page_images)
        
        if page_text.strip():  # 只添加非空页面
            full_text.append(page_text)
    
    return "\n\n".join(full_text)

def extract_page_text_with_images(page: fitz.Page, page_images: dict) -> str:
    """
    提取页面文本并在适当位置插入图片
    
    Args:
        page: PyMuPDF页面对象
        page_images: 页面图片信息字典
        
    Returns:
        包含图片的页面文本
    """
    # 获取文本块
    blocks = page.get_text("dict")["blocks"]
    
    # 创建文本块和图片的混合列表，按y坐标排序
    content_items = []
    
    # 添加文本块
    for block in blocks:
        if "lines" in block:  # 文本块
            block_text = []
            for line in block["lines"]:
                line_text = ""
                for span in line["spans"]:
                    line_text += span["text"]
                if line_text.strip():
                    block_text.append(line_text)
            
            if block_text:
                content_items.append({
                    'type': 'text',
                    'content': "\n".join(block_text),
                    'y_position': block["bbox"][1]  # 使用bbox的顶部y坐标
                })
    
    # 添加图片
    for img_index, img_info in page_images.items():
        content_items.append({
            'type': 'image',
            'content': f"![Image](./assets/{img_info['filename']})",
            'y_position': img_info['y_position']
        })
    
    # 按y坐标排序（从上到下）
    content_items.sort(key=lambda x: x['y_position'])
    
    # 组合内容
    page_content = []
    for item in content_items:
        page_content.append(item['content'])
    
    return "\n\n".join(page_content)

def generate_clean_markdown(text: str, output_path: Path, title: str):
    """
    生成简洁的Markdown文件，适合LLM预训练
    
    Args:
        text: 提取的文本
        output_path: 输出文件路径
        title: 文档标题
    """
    # 直接输出标题和内容，不添加任何自定义文字
    markdown_content = f"# {title}\n\n{text}"
    
    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    logger.info(f"Markdown文件已生成: {output_path}") 