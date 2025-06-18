import os
import argparse
import shutil
import tarfile
import json
import re
import time
from pathlib import Path
import threading
from datetime import datetime

from arxiv_parser.parallel_processor import run_parallel_processing
from arxiv_parser.utils.logger import setup_logger

# 设置日志记录器
logger = setup_logger("batch_processor")

# 定义项目内的关键目录
PROJECT_ROOT = Path(__file__).resolve().parent
ARXIV_DIR = PROJECT_ROOT / "Arxiv"
TEMP_TAR_DIR = PROJECT_ROOT / "temp_tar"
STATE_FILE = PROJECT_ROOT / "processing_state.json"
SPEED_LOG = PROJECT_ROOT / "logs" / "speed.log"
OUTPUT_DIR = PROJECT_ROOT / "output"

def get_priority_from_filename(filename: str) -> int:
    """从文件名中提取优先级数字 (例如: arXiv_src_2208_071.tar -> 2208071)"""
    match = re.search(r'src_(\d+)_(\d+)\.tar', filename)
    if match:
        # 将 "2208" 和 "071" 拼接为 "2208071" 并转换为整数
        return int(f"{match.group(1)}{match.group(2)}")
    return 0

def initialize_state(source_dir: Path) -> list:
    """扫描源目录，初始化或更新状态文件，并返回待处理任务列表"""
    logger.info(f"正在扫描源目录: {source_dir}")
    
    # 读取现有状态
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            state_data = json.load(f)
    else:
        state_data = {"files": {}}

    # 扫描源目录下的所有 .tar 文件
    found_files = {p.name: str(p) for p in source_dir.glob("*.tar")}
    
    # 更新状态字典，添加新文件
    for filename, filepath in found_files.items():
        if filename not in state_data["files"]:
            state_data["files"][filename] = {
                "path": filepath,
                "status": "pending",
                "priority": get_priority_from_filename(filename)
            }
            logger.info(f"发现新文件: {filename}")

    # 保存更新后的状态
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state_data, f, indent=4)
        
    # 筛选出待处理任务并按优先级排序
    pending_tasks = [
        (name, info) for name, info in state_data["files"].items() 
        if info["status"] == "pending"
    ]
    
    # 按优先级降序排序 (数字大的优先)
    pending_tasks.sort(key=lambda item: item[1]["priority"], reverse=True)
    
    return pending_tasks

def clear_directory(directory: Path):
    """清空指定目录下的所有文件和子目录"""
    if not directory.exists():
        return
    for item in directory.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()
    logger.debug(f"已清空目录: {directory}")

# 统计线程函数
def speed_monitor(start_time, stop_event):
    last_count = 0
    while not stop_event.is_set():
        time.sleep(60)
        try:
            if not OUTPUT_DIR.exists():
                count = 0
            else:
                # 只统计 output 目录下的文件夹数量
                count = sum(1 for x in OUTPUT_DIR.iterdir() if x.is_dir())
            elapsed = (datetime.now() - start_time).total_seconds() / 60  # 分钟
            speed = count / elapsed if elapsed > 0 else 0
            log_line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, count={count}, elapsed(min)={elapsed:.2f}, speed(per min)={speed:.4f}\n"
            with open(SPEED_LOG, 'a', encoding='utf-8') as f:
                f.write(log_line)
        except Exception as e:
            with open(SPEED_LOG, 'a', encoding='utf-8') as f:
                f.write(f"[ERROR] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {e}\n")

def main(source_dir_path: str, num_workers: int):
    """主编排函数"""
    source_dir = Path(source_dir_path)
    if not source_dir.is_dir():
        logger.error(f"错误：源目录不存在或不是一个目录 -> {source_dir_path}")
        return

    # 确保所需目录存在
    ARXIV_DIR.mkdir(exist_ok=True)
    TEMP_TAR_DIR.mkdir(exist_ok=True)
    (PROJECT_ROOT / "logs").mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    # 1. 初始化状态，获取任务列表
    pending_tasks = initialize_state(source_dir)

    if not pending_tasks:
        logger.info("所有文件均已处理完毕，没有待处理的任务。")
        return

    logger.info(f"发现 {len(pending_tasks)} 个待处理的.tar压缩包。开始处理...")

    # 启动统计线程
    start_time = datetime.now()
    stop_event = threading.Event()
    monitor_thread = threading.Thread(target=speed_monitor, args=(start_time, stop_event), daemon=True)
    monitor_thread.start()

    try:
        # 2. 循环处理任务
        for filename, info in pending_tasks:
            logger.info(f"======== 开始处理压缩包: {filename} (优先级: {info['priority']}) ========")
            
            local_tar_path = TEMP_TAR_DIR / filename

            try:
                # a. 清理工作区
                logger.info("步骤 1/6: 清理工作目录...")
                clear_directory(ARXIV_DIR)
                clear_directory(TEMP_TAR_DIR)

                # b. 复制.tar文件到临时目录
                logger.info(f"步骤 2/6: 复制 {filename} 到临时目录...")
                shutil.copy(info["path"], local_tar_path)

                # c. 解压.tar文件
                logger.info(f"步骤 3/6: 解压 {local_tar_path}...")
                with tarfile.open(local_tar_path, 'r') as tar:
                    tar.extractall(path=TEMP_TAR_DIR)
                
                # d. 将解压后的文件移动到Arxiv目录
                logger.info(f"步骤 4/6: 移动解压文件到 {ARXIV_DIR}...")
                
                # 解压后，文件通常在 TEMP_TAR_DIR 下的某个子目录中
                # 需要找到包含实际文件的目录
                for item in TEMP_TAR_DIR.iterdir():
                    if item.is_dir() and item.name != filename:  # 跳过 tar 文件本身
                        # 这应该是解压出来的目录（如 "1" 或其他名称）
                        logger.debug(f"找到解压目录: {item.name}")
                        # 移动该目录下的所有文件到 Arxiv
                        for file_item in item.iterdir():
                            if file_item.is_file() and not file_item.name.startswith('.'):
                                shutil.move(str(file_item), str(ARXIV_DIR / file_item.name))
                                logger.debug(f"移动文件: {file_item.name}")
                
                # e. 运行核心解析逻辑
                logger.info(f"步骤 5/6: 启动核心解析器 (Workers: {num_workers})...")
                report_path = f"report_{filename.replace('.tar','')}_{int(time.time())}.csv"
                run_parallel_processing(num_workers=num_workers, report_path=report_path)

                # f. 更新状态为 'completed'
                logger.info(f"步骤 6/6: 更新状态为 'completed'...")
                with open(STATE_FILE, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                state_data["files"][filename]["status"] = "completed"
                with open(STATE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(state_data, f, indent=4)
                
                logger.info(f"======== 成功处理压缩包: {filename} ========")

            except Exception as e:
                logger.error(f"处理 {filename} 时发生严重错误: {e}", exc_info=True)
                # 更新状态为 'failed'
                with open(STATE_FILE, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                state_data["files"][filename]["status"] = "failed"
                with open(STATE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(state_data, f, indent=4)
            finally:
                # 清理临时文件，为下一次循环做准备
                clear_directory(TEMP_TAR_DIR)
                clear_directory(ARXIV_DIR)
        
        logger.info("所有待处理任务均已完成。")
    finally:
        stop_event.set()
        monitor_thread.join(timeout=2)

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2 and sys.argv[1] == "--test-speed":
        OUTPUT_DIR = PROJECT_ROOT / "output"
        start_time = datetime.now()
        if not OUTPUT_DIR.exists():
            count = 0
        else:
            count = sum(1 for x in OUTPUT_DIR.iterdir() if x.is_dir())
        elapsed = (datetime.now() - start_time).total_seconds() / 60  # 分钟
        speed = count / elapsed if elapsed > 0 else 0
        print(f"output文件夹下的文件夹数量: {count}")
        print(f"耗时(分钟): {elapsed:.4f}")
        print(f"平均速度(每分钟): {speed:.4f}")
        sys.exit(0)

    parser = argparse.ArgumentParser(description="arXiv批处理编排器")
    parser.add_argument(
        '--source-dir', 
        type=str, 
        required=True, 
        help='存放.tar压缩包的源文件夹的绝对路径'
    )
    parser.add_argument(
        '--workers', 
        type=int, 
        default=max(1, os.cpu_count() // 2), 
        help='并行处理时使用的worker数量'
    )
    args = parser.parse_args()

    # 确保在多进程环境中，子进程不会重新执行此部分代码
    # multiprocessing.freeze_support() 是给Windows用的，在main guard里调用
    main(source_dir_path=args.source_dir, num_workers=args.workers) 