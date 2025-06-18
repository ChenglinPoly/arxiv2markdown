# arxiv2markdown

**English | [中文](#项目简介)**

---

## Project Overview

arxiv2markdown is an automated pipeline for batch processing arXiv TeX source packages. It extracts, filters, and converts scientific papers into structured HTML (and optionally Markdown), with AI-powered asset selection and multi-process acceleration.

---

## Features

- **Automatic extraction** of arXiv TeX source packages (.tar/.gz)
- **Main TeX file recognition** and LaTeXML Docker-based HTML conversion
- **AI-powered filtering**: Only research-valuable code/data/tables are kept (via Ollama + gemma:4b)
- **Unified assets directory** for all valuable attachments
- **Multi-process parallel processing** for high throughput
- **Progress & speed logging** for monitoring
- **Robust error handling** and failed case tracking

---

## Prerequisites

- **Python 3.8+**
- **Docker** (for LaTeXML container)
- **Pandoc** (optional, for Markdown conversion)
- **Ollama** (AI asset filtering, remote API, e.g. http://192.168.31.4:11434, model: gemma:4b)

---

## Installation

```bash
git clone https://github.com/ChenglinPoly/arxiv2markdown.git
cd arxiv2markdown

# (Recommended) Create a virtual environment
python3 -m venv arxiv_parser_env
source arxiv_parser_env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Configuration

Edit `arxiv_parser/config.py` to set:

- `SOURCE_DIR`, `OUTPUT_DIR`, `FAILED_DIR`, `TEMP_DIR`
- AI filtering: `enable_ai_filtering`, `ollama_api_url`, `ollama_model`
- Main TeX file patterns, valuable file extensions, etc.

---

## Usage

### 1. Prepare Data

Put your arXiv `.tar` or `.gz` source packages in the `Arxiv/` directory.

### 2. Batch Processing

```bash
# Batch process with 20 workers, log speed
nohup python batch_processor.py --source-dir ./Arxiv --workers 20 > logs/batch.log 2>&1 &
tail -f logs/batch.log
```

### 3. Monitor Progress

```bash
tail -f logs/speed.log
```

### 4. Test Output Folder Counting

```bash
python batch_processor.py --test-speed
```

---

## Output Structure

- `output/` : Each processed paper in a subfolder, with HTML and valuable assets
- `logs/` : Processing logs, speed logs
- `failed/` : Failed cases
- `processing_state.json` : Task state tracking

---

## Project Tree

```
arxiv2markdown/
├── arxiv_parser/           # Core logic (main, parallel, processors, utils)
├── batch_processor.py      # Batch orchestrator (with progress/speed logging)
├── run_processor_test.py   # Test script
├── output/                 # Results
├── failed/                 # Failed cases
├── logs/                   # Logs
├── requirements.txt        # Python dependencies
└── README.md
```

---

## License

MIT

---

# 项目简介

arxiv2markdown 是一个用于批量处理 arXiv TeX 源码包的自动化工具链。它可自动解压、识别主 TeX 文件、调用 LaTeXML 容器转 HTML，并用 AI 智能筛选有价值的附件，全部输出到统一目录，支持多进程加速和进度监控。

---

## 主要特性

- **自动解压** arXiv TeX 源码包（.tar/.gz）
- **主 TeX 文件智能识别**，LaTeXML Docker 转 HTML
- **AI 附件筛选**：仅保留有科研价值的代码/数据/表格（Ollama + gemma:4b）
- **统一 assets 目录**，便于后续数据集整理
- **多进程并行处理**，高效批量转换
- **进度与速度日志**，便于监控
- **健壮的异常处理与失败追踪**

---

## 依赖环境

- **Python 3.8+**
- **Docker**（用于 LaTeXML 容器）
- **Pandoc**（可选，用于 Markdown 转换）
- **Ollama**（AI 附件筛选，远程 API，如 http://192.168.31.4:11434，模型 gemma:4b）

---

## 安装步骤

```bash
git clone https://github.com/ChenglinPoly/arxiv2markdown.git
cd arxiv2markdown

# （推荐）创建虚拟环境
python3 -m venv arxiv_parser_env
source arxiv_parser_env/bin/activate

# 安装依赖
pip install -r requirements.txt
```

---

## 配置说明

编辑 `arxiv_parser/config.py`，可设置：

- 目录路径：`SOURCE_DIR`, `OUTPUT_DIR`, `FAILED_DIR`, `TEMP_DIR`
- AI筛选：`enable_ai_filtering`, `ollama_api_url`, `ollama_model`
- 主TeX文件名模式、附件有价值扩展名等

---

## 使用方法

### 1. 准备数据

将 arXiv `.tar` 或 `.gz` 源码包放入 `Arxiv/` 目录。

### 2. 批量处理

```bash
# 20线程批量处理，日志输出
nohup python batch_processor.py --source-dir ./Arxiv --workers 20 > logs/batch.log 2>&1 &
tail -f logs/batch.log
```

### 3. 实时监控进度

```bash
tail -f logs/speed.log
```

### 4. 单独测试 output 文件夹统计

```bash
python batch_processor.py --test-speed
```

---

## 输出结构

- `output/` ：每篇论文一个子目录，含 HTML 及有价值附件
- `logs/` ：处理日志、速度日志
- `failed/` ：失败案例
- `processing_state.json` ：任务状态跟踪

---

## 项目结构

```
arxiv2markdown/
├── arxiv_parser/           # 核心逻辑（主控、并行、处理器、工具）
├── batch_processor.py      # 批处理编排器（含进度/速度日志）
├── run_processor_test.py   # 测试脚本
├── output/                 # 结果输出
├── failed/                 # 失败案例
├── logs/                   # 日志
├── requirements.txt        # 依赖
└── README.md
```

---

## 许可证

MIT

---

如需进一步定制或补充示例、FAQ、贡献指南等内容，请告知！ 