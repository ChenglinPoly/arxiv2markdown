#!/usr/bin/env python3
"""
并行处理模块
使用队列和多个worker来并行处理arXiv文件 (多进程版)
"""

import time
import csv
import numpy as np
import multiprocessing
from pathlib import Path
from queue import Empty
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, field

from .main import process_single_file_with_failover, get_file_type
from .utils.logger import setup_logger
from .config import SOURCE_DIR, OUTPUT_DIR, FAILED_DIR, TEMP_DIR

logger = setup_logger("parallel_processor")

@dataclass
class ProcessingStats:
    """处理统计信息"""
    total_files: int = 0
    processed_files: int = 0
    successful_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0
    start_time: float = field(default_factory=time.time)
    end_time: float = 0.0
    processing_times: List[float] = field(default_factory=list)
    
    @property
    def total_time(self) -> float:
        """总处理时间"""
        if self.end_time == 0:
            return time.time() - self.start_time
        return self.end_time - self.start_time
    
    @property
    def average_time(self) -> float:
        """平均处理时间"""
        if not self.processing_times:
            return 0.0
        return sum(self.processing_times) / len(self.processing_times)
    
    @property
    def median_time(self) -> float:
        """中位数处理时间"""
        if not self.processing_times:
            return 0.0
        return float(np.median(self.processing_times))

    @property
    def max_time(self) -> float:
        """最长处理时间"""
        return max(self.processing_times) if self.processing_times else 0.0
    
    @property
    def min_time(self) -> float:
        """最短处理时间"""
        return min(self.processing_times) if self.processing_times else 0.0

    @property
    def success_rate(self) -> float:
        """成功率"""
        if (self.successful_files + self.failed_files) == 0:
            return 0.0
        return (self.successful_files / (self.successful_files + self.failed_files)) * 100

    @property
    def middle_80_percent_time_range(self) -> Tuple[float, float]:
        """中部80%的处理时长范围 (P10 to P90)"""
        if len(self.processing_times) < 2:
            return 0.0, 0.0
        p10 = float(np.percentile(self.processing_times, 10))
        p90 = float(np.percentile(self.processing_times, 90))
        return p10, p90

    def generate_csv_report(self, output_path: str) -> None:
        """生成CSV格式的性能报告"""
        logger.info(f"正在生成性能报告到: {output_path}")

        p10, p90 = self.middle_80_percent_time_range
        report_data = {
            "总耗时 (s)": f"{self.total_time:.2f}",
            "文件总数": self.total_files,
            "已处理文件数 (成功+失败)": self.successful_files + self.failed_files,
            "成功文件数": self.successful_files,
            "失败文件数": self.failed_files,
            "跳过文件数": self.skipped_files,
            "成功率 (%)": f"{self.success_rate:.2f}",
            "平均处理时长 (s)": f"{self.average_time:.2f}",
            "中位数处理时长 (s)": f"{self.median_time:.2f}",
            "最高处理时长 (s)": f"{self.max_time:.2f}",
            "最低处理时长 (s)": f"{self.min_time:.2f}",
            "中部80%处理时长范围 (s)": f"{p10:.2f} - {p90:.2f}",
        }

        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Metric', 'Value'])
                for key, value in report_data.items():
                    writer.writerow([key, str(value)])
            logger.info(f"性能报告生成成功: {output_path}")
        except IOError as e:
            logger.error(f"无法写入CSV报告: {e}")
            
    def print_summary(self):
        """打印处理结果摘要到日志"""
        logger.info("------------- 处理完成 -------------")
        logger.info(f" 总耗时: {self.total_time:.2f} 秒")
        logger.info(f" 文件总数: {self.total_files}, 已处理: {self.processed_files}")
        logger.info(f"   - 成功: {self.successful_files}")
        logger.info(f"   - 失败: {self.failed_files}")
        logger.info(f"   - 跳过: {self.skipped_files}")
        if self.processing_times:
            logger.info(f" 成功率: {self.success_rate:.2f}%")
            logger.info(f" 平均处理时长: {self.average_time:.2f} s")
            logger.info(f" 时长 (min/median/max): {self.min_time:.2f}s / {self.median_time:.2f}s / {self.max_time:.2f}s")
            p10, p90 = self.middle_80_percent_time_range
            logger.info(f" 中部80%处理时长: {p10:.2f}s - {p90:.2f}s")
        logger.info("------------------------------------")


def worker_process(worker_id: int, file_queue: multiprocessing.Queue, result_queue: multiprocessing.Queue):
    """工作进程函数"""
    logger.info(f"Worker {worker_id} 启动 (PID: {multiprocessing.current_process().pid})")
    
    while True:
        try:
            file_path_str = file_queue.get()
            if file_path_str is None:
                break
            
            file_path = Path(file_path_str)
            logger.info(f"Worker {worker_id} 开始处理: {file_path.name}")
            start_time = time.time()
            
            result = {'file_name': file_path.name, 'status': 'failure', 'time': 0}

            try:
                file_type = get_file_type(file_path)
                
                if file_type == 'pdf':
                    logger.info(f"Worker {worker_id} 跳过PDF文件: {file_path.name}")
                    result['status'] = 'skipped'
                elif file_type == 'tex':
                    success = process_single_file_with_failover(file_path)
                    processing_time = time.time() - start_time
                    result['time'] = processing_time
                    if success:
                        logger.info(f"Worker {worker_id} 成功处理: {file_path.name} ({processing_time:.2f}s)")
                        result['status'] = 'success'
                    else:
                        logger.warning(f"Worker {worker_id} 处理失败: {file_path.name} ({processing_time:.2f}s)")
                        result['status'] = 'failure'
                else:
                    logger.info(f"Worker {worker_id} 跳过不支持的文件: {file_path.name}")
                    result['status'] = 'skipped'
            except Exception as e:
                logger.error(f"Worker {worker_id} 在处理 {file_path.name} 时出现异常: {e}")
                result['status'] = 'failure'
                result['time'] = time.time() - start_time
            
            result_queue.put(result)
            
        except (KeyboardInterrupt, SystemExit):
            break
        except Exception as e:
            logger.error(f"Worker {worker_id} 出现严重错误: {e}")

    logger.info(f"Worker {worker_id} 结束")


class ParallelProcessor:
    """并行处理器 (多进程版)"""
    
    def __init__(self, num_workers: int):
        self.num_workers = num_workers
        self.stats = ProcessingStats()
        self.file_queue = multiprocessing.Queue()
        self.result_queue = multiprocessing.Queue()
        self.workers = []
        
    def process_files(self, file_list: List[Path]) -> ProcessingStats:
        """并行处理文件列表"""
        logger.info(f"开始并行处理 {len(file_list)} 个文件，使用 {self.num_workers} 个worker")
        
        self.stats = ProcessingStats(total_files=len(file_list))
        
        # 将文件路径字符串放入队列
        for file_path in file_list:
            self.file_queue.put(str(file_path))
        
        # 启动工作进程
        for i in range(self.num_workers):
            process = multiprocessing.Process(target=worker_process, args=(i + 1, self.file_queue, self.result_queue))
            process.start()
            self.workers.append(process)
        
        # 收集结果并更新统计
        for _ in range(len(file_list)):
            try:
                result = self.result_queue.get()
                self.stats.processed_files += 1
                status = result.get('status', 'failure')
                
                if status == 'success':
                    self.stats.successful_files += 1
                    self.stats.processing_times.append(result['time'])
                elif status == 'failure':
                    self.stats.failed_files += 1
                    if result['time'] > 0:
                        self.stats.processing_times.append(result['time'])
                elif status == 'skipped':
                    self.stats.skipped_files += 1
            except (KeyboardInterrupt, SystemExit):
                logger.warning("收到中断信号，正在终止处理...")
                break
        
        # 发送停止信号
        for _ in range(self.num_workers):
            self.file_queue.put(None)
        
        # 等待所有worker结束
        for worker in self.workers:
            worker.join(timeout=10)
            if worker.is_alive():
                logger.warning(f"Worker {worker.pid} 未能在10秒内正常结束，将强制终止。")
                worker.terminate()
        
        self.stats.end_time = time.time()
        self.stats.print_summary()
        return self.stats


def run_parallel_processing(num_workers: int, report_path: str = 'processing_report.csv'):
    """
    运行并行处理并生成报告的测试函数
    
    Args:
        num_workers: worker数量
        report_path: CSV报告的输出路径
    """
    if not SOURCE_DIR.exists():
        logger.error(f"源目录不存在: {SOURCE_DIR}")
        return
    
    all_files = list(SOURCE_DIR.glob("*"))
    files_to_process = [f for f in all_files if f.is_file() and not f.name.startswith('.')]
    
    if not files_to_process:
        logger.warning(f"在源目录 {SOURCE_DIR} 中未找到任何文件")
        return
        
    processor = ParallelProcessor(num_workers)
    stats = processor.process_files(files_to_process)
    
    stats.generate_csv_report(report_path)

# 将旧函数重命名并标记为弃用
def parallel_process_arxiv(num_workers: int = 4) -> ProcessingStats:
    logger.warning("`parallel_process_arxiv` 已被 `run_parallel_processing` 替代，请更新调用。")
    report_path = f"report_{int(time.time())}.csv"
    run_parallel_processing(num_workers, report_path)
    # 返回一个空的stats对象以保持向后兼容性
    return ProcessingStats() 