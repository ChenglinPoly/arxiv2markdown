#!/usr/bin/env python3
"""
测试LaTeXML功能的脚本
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from arxiv_parser.config import OUTPUT_DIR, FAILED_DIR, TEMP_DIR, ensure_directories
from arxiv_parser.utils.logger import setup_logger
from arxiv_parser.processors import tex_processor
import shutil

# 设置日志
logger = setup_logger("test_latexml")

def test_file(file_path: Path, test_name: str):
    """测试单个文件"""
    logger.info(f"\n{'='*60}")
    logger.info(f"开始测试: {test_name}")
    logger.info(f"文件: {file_path}")
    logger.info(f"大小: {file_path.stat().st_size / 1024:.1f} KB")
    logger.info(f"{'='*60}")
    
    try:
        success, error_msg = tex_processor.process(file_path, OUTPUT_DIR, TEMP_DIR)
        
        if success:
            logger.info(f"✅ {test_name} - 处理成功！")
            
            # 检查输出文件
            base_name = file_path.stem  # 获取不含扩展名的文件名
            output_dir = OUTPUT_DIR / base_name
            if output_dir.exists():
                html_file = output_dir / f"{base_name}.html"
                source_dir = output_dir / "source_code"
                assets_dir = output_dir / "assets" 
                other_assets_dir = output_dir / "other_assets"
                
                logger.info(f"输出目录: {output_dir}")
                if html_file.exists():
                    logger.info(f"✅ HTML文件已生成: {html_file} ({html_file.stat().st_size / 1024:.1f} KB)")
                if source_dir.exists():
                    source_files = list(source_dir.rglob('*'))
                    source_files = [f for f in source_files if f.is_file()]
                    logger.info(f"📁 源代码文件: {len(source_files)} 个")
                if assets_dir.exists():
                    asset_files = list(assets_dir.rglob('*'))
                    asset_files = [f for f in asset_files if f.is_file()]
                    logger.info(f"🖼️ 资源文件: {len(asset_files)} 个")
                if other_assets_dir.exists():
                    other_files = list(other_assets_dir.rglob('*'))
                    other_files = [f for f in other_files if f.is_file()]
                    logger.info(f"📊 其他资源: {len(other_files)} 个")
            
        else:
            logger.error(f"❌ {test_name} - 处理失败: {error_msg}")
            
    except Exception as e:
        logger.error(f"❌ {test_name} - 异常: {e}")
    
    return success

def main():
    """主测试函数"""
    logger.info("开始LaTeXML功能测试")
    
    # 确保目录存在
    ensure_directories()
    
    # 测试文件列表
    test_files = [
        ("test_arxiv/2403.16500.gz", "小文件测试 (16KB)"),
        ("test_arxiv/2403.16493.gz", "小文件测试 (25KB)"),
        ("test_arxiv/2403.16410.gz", "大文件测试 (13MB)"),
    ]
    
    successful_tests = 0
    total_tests = len(test_files)
    
    for file_path_str, test_name in test_files:
        file_path = Path(file_path_str)
        if not file_path.exists():
            logger.error(f"❌ 测试文件不存在: {file_path}")
            continue
            
        if test_file(file_path, test_name):
            successful_tests += 1
    
    # 测试总结
    logger.info(f"\n{'='*60}")
    logger.info("测试总结")
    logger.info(f"{'='*60}")
    logger.info(f"总测试数: {total_tests}")
    logger.info(f"成功: {successful_tests}")
    logger.info(f"失败: {total_tests - successful_tests}")
    
    if successful_tests == total_tests:
        logger.info("🎉 所有测试通过！")
    else:
        logger.warning("⚠️  部分测试失败，请检查日志")
    
    # 清理临时目录
    if TEMP_DIR.exists():
        try:
            for item in TEMP_DIR.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
            logger.info("🧹 已清理临时目录")
        except Exception as e:
            logger.warning(f"清理临时目录时出错: {e}")

if __name__ == "__main__":
    main() 