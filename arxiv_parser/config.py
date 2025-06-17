import os
from pathlib import Path

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 关键目录路径
SOURCE_DIR = PROJECT_ROOT / "Arxiv"  # arXiv文件的源目录
OUTPUT_DIR = PROJECT_ROOT / "output"  # 成功处理后的输出目录
FAILED_DIR = PROJECT_ROOT / "failed"  # 处理失败的文件存放目录
TEMP_DIR = PROJECT_ROOT / "temp"      # 临时目录，用于解压等操作

# 日志配置
LOG_FILE = PROJECT_ROOT / "logs/arxiv_parser.log"
LOG_LEVEL = "DEBUG"

# Pandoc配置
PANDOC_PATH = "/opt/homebrew/bin/pandoc"  # macOS Homebrew安装的Pandoc路径

# 文件类型支持
SUPPORTED_PDF_EXTENSIONS = ['.pdf']
SUPPORTED_TEX_EXTENSIONS = ['.gz', '.tar.gz']

# TeX源码中常见的主文件名
COMMON_MAIN_TEX_NAMES = [
    'main.tex', 
    'root.tex', 
    'ms.tex',
    'paper.tex',
    'manuscript.tex'
]

# TeX相关文件扩展名（处理附件时需要排除）
TEX_RELATED_EXTENSIONS = [
    '.tex', '.bib', '.bbl', '.blg', '.aux', '.log', 
    '.cls', '.sty', '.fdb_latexmk', '.fls', '.out',
    '.toc', '.lof', '.lot', '.nav', '.snm', '.vrb'
]

# 图片文件扩展名
IMAGE_EXTENSIONS = [
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', 
    '.eps', '.pdf', '.tiff', '.tif'
]

# 源代码文件扩展名
SOURCE_CODE_EXTENSIONS = [
    '.py', '.m', '.cpp', '.c', '.h', '.hpp', '.java', 
    '.js', '.html', '.css', '.r', '.sh', '.pl', '.rb',
    '.zip', '.tar', '.dat', '.txt', '.csv', '.json', '.xml'
]

# 文件筛选配置
FILE_FILTERING_CONFIG = {
    "enable_ai_filtering": False,  # 是否启用AI智能筛选（默认关闭）
    "strategy": "extension_based",  # 筛选策略: "extension_based" 或 "ai_based"
    
    # 基于扩展名的筛选配置
    "valuable_extensions": {
        # 源代码文件
        '.py', '.java', '.cpp', '.c', '.h', '.hpp', '.js', '.ts', '.go', '.rs', '.rb', '.php',
        '.r', '.m', '.scala', '.kt', '.swift', '.sh', '.bat', '.ps1',
        
        # 数据文件
        '.csv', 
        '.xls', '.xlsx',
        
        # 配置和文档文件
        '.cfg', '.conf', '.ini', '.toml', '.properties',
        '.md', '.rst', '.txt', '.log',
        
        # 数据科学相关
        '.ipynb', '.rmd', '.mat', '.dat', '.hdf5', '.h5', '.npz', '.pkl', '.pickle',
        
        # 其他有价值的文件
        '.bib', '.bibtex', '.endnote', '.ris',

        # 图片文件
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', 
        '.eps', '.pdf', '.tiff', '.tif',
    }
}

# AI服务配置
AI_CONFIG = {
    "provider": "deepseek",  # 支持: "deepseek", "openai", "ollama"
    "deepseek": {
        "api_key": "sk-a8525bd7b5974be1b9f1e966e798d7e9",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "temperature": 0.1,
        "max_tokens": 100,
        "timeout": 30
    },
    "openai": {
        "api_key": "your-openai-api-key",
        "base_url": "https://api.openai.com/v1", 
        "model": "gpt-3.5-turbo",
        "temperature": 0.1,
        "max_tokens": 100,
        "timeout": 30
    },
    "ollama": {
        "base_url": "http://192.168.31.4:11434",
        "model": "gemma3:4b",
        "temperature": 0.1,
        "timeout": 30
    }
}

def ensure_directories():
    """确保所有必要的目录存在"""
    for directory in [OUTPUT_DIR, FAILED_DIR, TEMP_DIR]:
        directory.mkdir(parents=True, exist_ok=True) 