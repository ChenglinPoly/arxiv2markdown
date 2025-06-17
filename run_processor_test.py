import multiprocessing
import time
from arxiv_parser.parallel_processor import run_parallel_processing
from arxiv_parser.utils.logger import setup_logger

logger = setup_logger("test_runner")

def main():
    """
    主测试函数，用于启动并行处理器。
    """
    logger.info("=============================================")
    logger.info("===      开始运行并行处理测试      ===")
    logger.info("=============================================")

    # --- 配置参数 ---
    # 设置要使用的CPU核心数。默认使用系统核心数的一半，可以根据需要调整。
    # 例如，对于一个12核的机器，这里会使用6个worker。
    try:
        cpu_cores = multiprocessing.cpu_count()
        num_workers = max(1, cpu_cores // 2)
    except NotImplementedError:
        # 如果无法检测到CPU核心数，默认使用4个worker
        num_workers = 4
        
    # 您可以手动覆盖worker数量，例如：
    # num_workers = 8 

    # 设置性能报告的输出文件名
    report_filename = f"performance_report_{int(time.time())}.csv"

    logger.info(f"检测到 {cpu_cores} 个CPU核心，将使用 {num_workers} 个worker进程进行处理。")
    logger.info(f"性能报告将保存为: {report_filename}")
    
    # 记录开始时间
    start_time = time.time()

    # --- 启动并行处理 ---
    try:
        run_parallel_processing(num_workers=num_workers, report_path=report_filename)
    except Exception as e:
        logger.error(f"测试过程中发生未捕获的异常: {e}", exc_info=True)
    finally:
        # 记录结束时间并打印总耗时
        end_time = time.time()
        total_duration = end_time - start_time
        logger.info("=============================================")
        logger.info(f"=== 测试脚本执行完毕，总耗时: {total_duration:.2f} 秒 ===")
        logger.info(f"=== 请查看日志文件和报告 '{report_filename}' 获取详细信息。 ===")
        logger.info("=============================================")


if __name__ == "__main__":
    # 确保在多进程环境中，子进程不会重新执行此部分代码
    # 这对于Windows和macOS上的 'spawn' 或 'forkserver' 启动方法是必需的
    multiprocessing.freeze_support()
    main() 