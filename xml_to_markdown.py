#!/usr/bin/env python3
"""
XML到Markdown转换工具
支持LaTeXML生成的XML文档转换为Markdown格式
"""
import subprocess
import sys
from pathlib import Path
import re
import argparse

def run_pandoc_conversion(xml_file, output_file):
    """使用Pandoc将XML转换为Markdown"""
    try:
        cmd = [
            "pandoc",
            str(xml_file),
            "-f", "xml",
            "-t", "gfm", 
            "--mathjax",
            "--wrap=none",
            "-o", str(output_file)
        ]
        
        print(f"📝 正在转换 {xml_file.name} → {output_file.name}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✅ Pandoc转换成功")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Pandoc转换失败: {e}")
        return False
    except FileNotFoundError:
        print(f"❌ 未找到Pandoc，请先安装：brew install pandoc")
        return False

def post_process_markdown(md_file, xml_dir):
    """后处理Markdown文件"""
    try:
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"🔧 正在后处理Markdown文件...")
        
        # 修复图片路径
        content = re.sub(r'!\[([^\]]*)\]\(x(\d+)\.png\)', r'![\1](x\2.png)', content)
        
        # 清理多余空行
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # 添加文档头部
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            title = title_match.group(1)
            header = f'---\ntitle: "{title}"\nsource: "LaTeXML XML转换"\n---\n\n'
            content = header + content
        
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ 后处理完成")
        
    except Exception as e:
        print(f"⚠️  后处理错误: {e}")

def convert_xml_to_markdown(xml_file, output_dir=None):
    """完整转换流程"""
    xml_file = Path(xml_file)
    if not xml_file.exists():
        print(f"❌ XML文件不存在: {xml_file}")
        return False
    
    if output_dir is None:
        output_dir = xml_file.parent
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"{xml_file.stem}.md"
    
    if run_pandoc_conversion(xml_file, output_file):
        post_process_markdown(output_file, xml_file.parent)
        
        xml_size = xml_file.stat().st_size / 1024
        md_size = output_file.stat().st_size / 1024
        
        print(f"""
📊 转换完成:
   输入: {xml_file.name} ({xml_size:.1f} KB)
   输出: {output_file.name} ({md_size:.1f} KB)
   路径: {output_file}
""")
        return True
    
    return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python xml_to_markdown.py <xml_file> [output_dir]")
        sys.exit(1)
    
    xml_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = convert_xml_to_markdown(xml_file, output_dir)
    sys.exit(0 if success else 1) 