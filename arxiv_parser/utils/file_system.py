import os
import shutil
import tempfile
from pathlib import Path
import time
import datetime
from typing import List, Optional
from ..config import TEX_RELATED_EXTENSIONS, IMAGE_EXTENSIONS, SOURCE_CODE_EXTENSIONS
from .logger import setup_logger

logger = setup_logger("file_system")

def safe_move_to_failed(file_path: Path, failed_dir: Path, error_info: str = None) -> bool:
    """
    安全地将文件移动到失败目录，并记录失败日志
    
    Args:
        file_path: 源文件路径
        failed_dir: 失败目录
        error_info: 错误信息
        
    Returns:
        是否移动成功
    """
    try:
        # 确保失败目录存在
        failed_dir.mkdir(parents=True, exist_ok=True)
        
        # 移动文件
        target_path = failed_dir / file_path.name
        
        # 如果目标文件已存在，添加时间戳避免冲突
        if target_path.exists():
            timestamp = int(time.time())
            stem = target_path.stem
            suffix = target_path.suffix
            target_path = failed_dir / f"{stem}_{timestamp}{suffix}"
        
        shutil.move(str(file_path), str(target_path))
        
        # 记录失败日志
        if error_info:
            write_failure_log(failed_dir, file_path.name, error_info)
        
        return True
        
    except Exception as e:
        logger.error(f"移动文件到失败目录时出错: {e}")
        return False

def write_failure_log(failed_dir: Path, filename: str, error_info: str):
    """
    写入失败日志
    
    Args:
        failed_dir: 失败目录
        filename: 失败的文件名
        error_info: 错误信息
    """
    try:
        log_file = failed_dir / "fail.log"
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 添加日志条目
        log_entry = f"[{timestamp}] {filename}: {error_info}\n"
        
        # 追加写入日志文件
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
            
        logger.debug(f"失败日志已记录: {filename}")
        
    except Exception as e:
        logger.error(f"写入失败日志时出错: {e}")

def get_base_name(file_path: Path) -> str:
    """
    从文件路径获取基础名称（不包含扩展名）
    
    Args:
        file_path: 文件路径
        
    Returns:
        基础文件名
    """
    name = file_path.name
    # 处理.tar.gz这样的双扩展名
    if name.endswith('.tar.gz'):
        return name[:-7]
    else:
        return file_path.stem

def create_unique_temp_dir(base_dir: Path, prefix: str = "temp_") -> Path:
    """
    创建唯一的临时目录
    
    Args:
        base_dir: 基础目录
        prefix: 目录名前缀
        
    Returns:
        临时目录路径
    """
    base_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = tempfile.mkdtemp(dir=base_dir, prefix=prefix)
    return Path(temp_dir)

def categorize_files(directory: Path) -> dict:
    """
    对目录中的文件进行分类
    
    Args:
        directory: 要分类的目录
        
    Returns:
        分类结果字典
    """
    result = {
        'tex_files': [],
        'image_files': [],
        'source_code_files': [],
        'other_files': []
    }
    
    for file_path in directory.rglob('*'):
        if file_path.is_file():
            suffix = file_path.suffix.lower()
            
            if suffix in TEX_RELATED_EXTENSIONS:
                result['tex_files'].append(file_path)
            elif suffix in IMAGE_EXTENSIONS:
                result['image_files'].append(file_path)
            elif suffix in SOURCE_CODE_EXTENSIONS:
                result['source_code_files'].append(file_path)
            else:
                result['other_files'].append(file_path)
    
    return result

def safe_copy_file(src: Path, dst: Path) -> bool:
    """
    安全地复制文件
    
    Args:
        src: 源文件路径
        dst: 目标文件路径
        
    Returns:
        复制是否成功
    """
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return True
    except Exception as e:
        print(f"复制文件 {src} 到 {dst} 时出错: {e}")
        return False 