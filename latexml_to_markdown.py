#!/usr/bin/env python3
"""
LaTeXML XML到Markdown转换器
专门处理LaTeXML生成的XML文档
"""
import xml.etree.ElementTree as ET
import re
import sys
from pathlib import Path
from typing import List, Optional

class LaTeXMLToMarkdown:
    def __init__(self):
        self.namespaces = {
            '': 'http://dlmf.nist.gov/LaTeXML',
            'm': 'http://www.w3.org/1998/Math/MathML'
        }
        
    def convert_file(self, xml_file: Path, output_file: Path) -> bool:
        """转换XML文件到Markdown"""
        try:
            print(f"📝 解析LaTeXML文件: {xml_file.name}")
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            markdown_content = self.convert_document(root)
            
            # 写入Markdown文件
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            xml_size = xml_file.stat().st_size / 1024
            md_size = output_file.stat().st_size / 1024
            
            print(f"""
📊 转换完成:
   输入: {xml_file.name} ({xml_size:.1f} KB)
   输出: {output_file.name} ({md_size:.1f} KB)
   路径: {output_file}
""")
            return True
            
        except Exception as e:
            print(f"❌ 转换失败: {e}")
            return False
    
    def convert_document(self, root) -> str:
        """转换整个文档"""
        lines = []
        
        # 添加文档头部
        title_elem = root.find('.//{http://dlmf.nist.gov/LaTeXML}title')
        if title_elem is not None:
            title = self.extract_text(title_elem)
            lines.append("---")
            lines.append(f'title: "{title}"')
            lines.append('source: "LaTeXML XML转换"')
            lines.append("---")
            lines.append("")
            lines.append(f"# {title}")
            lines.append("")
        
        # 添加作者
        creator_elem = root.find('.//{http://dlmf.nist.gov/LaTeXML}creator')
        if creator_elem is not None:
            author = self.extract_text(creator_elem)
            lines.append(f"**Author**: {author}")
            lines.append("")
        
        # 添加摘要
        abstract_elem = root.find('.//{http://dlmf.nist.gov/LaTeXML}abstract')
        if abstract_elem is not None:
            lines.append("## Abstract")
            lines.append("")
            abstract_text = self.extract_text(abstract_elem)
            lines.append(abstract_text)
            lines.append("")
        
        # 添加关键词
        keywords_elem = root.find('.//{http://dlmf.nist.gov/LaTeXML}keywords')
        if keywords_elem is not None:
            keywords = self.extract_text(keywords_elem)
            lines.append(f"**关键词**: {keywords}")
            lines.append("")
        
        # 处理章节
        sections = root.findall('.//{http://dlmf.nist.gov/LaTeXML}section')
        for section in sections:
            section_md = self.convert_section(section, level=2)
            lines.append(section_md)
            lines.append("")
        
        return "\n".join(lines)
    
    def convert_section(self, section, level: int = 2) -> str:
        """转换章节"""
        lines = []
        
        # 章节标题
        title_elem = section.find('.//{http://dlmf.nist.gov/LaTeXML}title')
        if title_elem is not None:
            title = self.extract_text(title_elem)
            lines.append("#" * level + f" {title}")
            lines.append("")
        
        # 章节内容
        for child in section:
            if child.tag.endswith('title'):
                continue  # 标题已处理
            elif child.tag.endswith('para'):
                para_text = self.convert_paragraph(child)
                if para_text.strip():
                    lines.append(para_text)
                    lines.append("")
            elif child.tag.endswith('subsection'):
                subsection_md = self.convert_section(child, level + 1)
                lines.append(subsection_md)
                lines.append("")
            elif child.tag.endswith('figure'):
                figure_md = self.convert_figure(child)
                lines.append(figure_md)
                lines.append("")
            elif child.tag.endswith('equation') or child.tag.endswith('equationgroup'):
                eq_md = self.convert_equation(child)
                lines.append(eq_md)
                lines.append("")
            elif child.tag.endswith('itemize'):
                list_md = self.convert_list(child)
                lines.append(list_md)
                lines.append("")
        
        return "\n".join(lines)
    
    def convert_paragraph(self, para) -> str:
        """转换段落"""
        return self.extract_text(para)
    
    def convert_figure(self, figure) -> str:
        """转换图片"""
        lines = []
        
        # 查找图片元素
        graphics = figure.find('.//{http://dlmf.nist.gov/LaTeXML}graphics')
        if graphics is not None:
            img_src = graphics.get('imagesrc', '')
            alt_text = "图片"
            
            # 查找图片标题
            caption = figure.find('.//{http://dlmf.nist.gov/LaTeXML}caption')
            if caption is not None:
                alt_text = self.extract_text(caption)
            
            if img_src:
                lines.append(f"![{alt_text}]({img_src})")
            
            # 添加图片说明
            if caption is not None:
                caption_text = self.extract_text(caption)
                lines.append("")
                lines.append(f"*{caption_text}*")
        
        return "\n".join(lines)
    
    def convert_equation(self, equation) -> str:
        """转换数学公式"""
        # 查找LaTeX注释
        for elem in equation.iter():
            if elem.tag.endswith('annotation') and elem.get('encoding') == 'application/x-tex':
                latex = elem.text
                if latex:
                    # 块级公式
                    return f"$$\n{latex}\n$$"
        
        # 如果找不到LaTeX，尝试提取MathML
        math_elem = equation.find('.//{http://www.w3.org/1998/Math/MathML}math')
        if math_elem is not None:
            # 简单的MathML到LaTeX转换（这里只是示例）
            return "$$[数学公式]$$"
        
        return ""
    
    def convert_list(self, itemize) -> str:
        """转换列表"""
        lines = []
        items = itemize.findall('.//{http://dlmf.nist.gov/LaTeXML}item')
        
        for item in items:
            item_text = self.extract_text(item)
            lines.append(f"- {item_text}")
        
        return "\n".join(lines)
    
    def extract_text(self, element) -> str:
        """提取元素中的所有文本内容"""
        if element is None:
            return ""
        
        # 获取所有文本内容
        text_parts = []
        
        def collect_text(elem):
            if elem.text:
                text_parts.append(elem.text)
            
            for child in elem:
                # 处理特殊元素
                if child.tag.endswith('Math'):
                    # 查找LaTeX公式
                    annotation = child.find('.//{http://www.w3.org/1998/Math/MathML}annotation[@encoding="application/x-tex"]')
                    if annotation is not None and annotation.text:
                        text_parts.append(f"${annotation.text}$")
                    else:
                        text_parts.append("[数学公式]")
                elif child.tag.endswith('cite'):
                    # 处理引用
                    refs = child.findall('.//{http://dlmf.nist.gov/LaTeXML}ref')
                    ref_nums = [ref.text for ref in refs if ref.text]
                    if ref_nums:
                        text_parts.append(f"[{', '.join(ref_nums)}]")
                elif child.tag.endswith('ref'):
                    # 处理交叉引用
                    ref_text = child.get('title', child.text or '[引用]')
                    text_parts.append(ref_text)
                else:
                    collect_text(child)
                
                if child.tail:
                    text_parts.append(child.tail)
        
        collect_text(element)
        
        # 清理文本
        text = "".join(text_parts)
        text = re.sub(r'\s+', ' ', text)  # 合并空白字符
        text = text.strip()
        
        return text

def main():
    if len(sys.argv) < 2:
        print("用法: python latexml_to_markdown.py <xml_file> [output_file]")
        sys.exit(1)
    
    xml_file = Path(sys.argv[1])
    
    if len(sys.argv) > 2:
        output_file = Path(sys.argv[2])
    else:
        output_file = xml_file.parent / f"{xml_file.stem}.md"
    
    converter = LaTeXMLToMarkdown()
    success = converter.convert_file(xml_file, output_file)
    
    if success:
        print(f"✅ 转换成功！Markdown文件已保存到: {output_file}")
    else:
        print("❌ 转换失败")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 