# ArXiv 论文解析器

一个用于自动处理 arXiv 论文 TeX 源码，并将其转换为结构化 HTML 和 Markdown 格式的工具。

---

## 1. 前置依赖 (Prerequisites)

在运行此项目之前，请确保您的系统中已安装以下软件和资源。

### 1.1 Docker

本项目使用 Docker 来运行 LaTeXML，以确保 TeX 编译环境的一致性。

- **macOS**: [下载 Docker Desktop for Mac](https://docs.docker.com/desktop/mac/install/)
- **Windows**: [下载 Docker Desktop for Windows](https://docs.docker.com/desktop/windows/install/)
- **Linux**: 请根据您的发行版选择合适的安装方式，例如 [Ubuntu](https://docs.docker.com/engine/install/ubuntu/)。

安装完成后，请确保 Docker 服务已启动。

### 1.2 LaTeXML Docker 镜像

项目依赖 `latexml/ar5ivist` 镜像进行 TeX 到 HTML 的转换。请在终端中运行以下命令拉取镜像：

```bash
docker pull latexml/ar5ivist
```

### 1.3 Pandoc

Pandoc 用于将 LaTeXML 生成的 HTML 文件转换为 Markdown (GFM) 格式。

- 访问 [Pandoc 官网安装页面](https://pandoc.org/installing.html) 并根据您的操作系统下载并安装。
- 在 macOS 上，您也可以使用 Homebrew 安装：
  ```bash
  brew install pandoc
  ```

安装后，请在终端运行 `pandoc --version` 检查是否安装成功。

## 2. 安装 (Installation)

首先，克隆本项目仓库到您的本地。

### 2.1 创建虚拟环境 (推荐)

建议使用虚拟环境来管理项目的 Python 依赖。

```bash
python3 -m venv arxiv_parser_env
source arxiv_parser_env/bin/activate
```

### 2.2 安装 Python 包

项目所需的 Python 依赖项已在 `requirements.txt` 中列出。运行以下命令进行安装：

```bash
pip install -r requirements.txt
```
*(注意: 如果项目中没有 `requirements.txt` 文件，请根据 `arxiv_parser/parallel_processor.py` 和 `arxiv_parser/processors/tex_processor.py` 中的导入语句手动安装 `numpy`, `requests` 等依赖。)*


## 3. 配置 (Configuration)

项目的主要配置位于 `arxiv_parser/config.py` 文件中。您可以根据需要修改此文件。

- **目录设置**:
  - `SOURCE_DIR`: 存放待处理的 arXiv `.gz` 压缩包的源目录 (默认为 `Arxiv/`)。
  - `OUTPUT_DIR`: 存放处理结果（每个文件一个子目录）的输出目录 (默认为 `output/`)。
  - `FAILED_DIR`: 存放处理失败文件的日志或移动失败文件的目录 (默认为 `failed/`)。
  - `TEMP_DIR`: 用于存放解压等操作的临时文件目录 (默认为 `temp/`)。

- **主 TeX 文件识别**:
  - `COMMON_MAIN_TEX_NAMES`: 一个列表，包含了常见的主 TeX 文件名（如 `main.tex`, `ms.tex`），用于快速定位入口文件。

- **附件筛选配置 (`FILE_FILTERING_CONFIG`)**:
  - `enable_ai_filtering`: 是否启用 AI 智能筛选附件。如果为 `True`，将调用 Ollama 服务判断文件价值；如果为 `False`，则仅基于扩展名进行筛选。
  - `valuable_extensions`: 一个集合，定义了哪些文件扩展名被认为是"有价值的"，在`enable_ai_filtering`为`False`时或对于非文本文件时使用。
  - `ollama_api_url`: 您的 Ollama 服务 API 地址。
  - `ollama_model`: 用于判断文件价值的 Ollama 模型名称（例如 `gemma:4b`）。

---

配置完成后，您可以通过运行测试脚本来启动处理器：
```bash
python run_processor_test.py
```



## 项目结构

```
arxiv2markdown/
├── arxiv_parser/                 # 核心处理模块
│   ├── __init__.py
│   ├── main.py                   # 主处理逻辑
│   ├── parallel_processor.py     # 并行处理模块
│   ├── config.py                 # 配置文件
│   ├── processors/               # 处理器模块
│   │   ├── __init__.py
│   │   └── tex_processor.py      # TeX文件处理器
│   └── utils/                    # 工具模块
│       ├── __init__.py
│       ├── logger.py             # 日志工具
│       └── file_system.py        # 文件系统工具
├── Arxiv/                        # 源文件目录（用户放置arXiv文件）
├── output/                       # 成功转换的文件输出目录
├── failed/                       # 失败文件目录
│   └── fail.log                  # 失败详情日志
├── temp/                         # 临时工作目录
├── test_parallel_processing.py   # 并行处理测试脚本
└── README.md
```

## 使用方法

### 1. 准备文件

将arXiv TeX压缩包（.gz或.tar.gz文件）放入 `Arxiv/` 目录中。

> 注意：系统会自动跳过PDF文件，仅处理TeX源码包。

### 2. 基本使用

**串行处理（单线程）:**
```bash
python -m arxiv_parser.main
```

**并行处理（推荐）:**
```bash
# 使用默认4个worker
python test_parallel_processing.py

# 指定worker数量
python test_parallel_processing.py --workers 8

# 简短形式
python test_parallel_processing.py -w 6
```

### 3. 输出结果

处理完成后，文件将分类存放：

- **成功文件**: `output/文件名/` 目录
  - `文件名.md`: 转换后的Markdown文件
  - `assets/`: 提取的图片资源
  - `source_code/`: 源代码文件（如有）

- **失败文件**: `failed/` 目录
  - 原始文件移动至此
  - `fail.log`: 详细的失败原因日志

## 配置选项

### 主要配置（`arxiv_parser/config.py`）

- `SOURCE_DIR`: 源文件目录路径
- `OUTPUT_DIR`: 输出目录路径
- `FAILED_DIR`: 失败文件目录路径
- `TEMP_DIR`: 临时工作目录路径
- `PANDOC_PATH`: Pandoc可执行文件路径

### 处理参数

- **超时设置**: Pandoc转换超时时间为180秒（3分钟）
- **并发数量**: 默认4个worker，可根据系统性能调整
- **文件过滤**: 自动跳过LaTeX辅助文件和模板文件

## 处理报告


## 示例输出

```
🎯 并行处理完成！详细报告如下：
================================================================================
Metric,Value
总耗时 (s),1299.72
已处理文件数 (成功+失败),107
成功文件数,99
失败文件数,8
成功率 (%),92.52
平均处理时长 (s),58.46/单进程
平均处理时长(s),12.14/workers:5
中位数处理时长 (s),53.58
最高处理时长 (s),244.17
最低处理时长 (s),0.00
中部80%处理时长范围 (s),13.22 - 123.52
 Latex处理tikz图表问题 1
 docker 资源超限 1
 宏定义问题/语法错误 2
 文件受损，解压失败 4
================================================================================
``` 