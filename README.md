# 📚 ArXiv Paper Search & Translation Skill

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Antigravity Skill](https://img.shields.io/badge/Antigravity-Skill-green.svg)](https://github.com/namelessfei/arxiv-paper-search)

一个专为学术研究人员与 AI 开发者设计的高效学术论文追踪、定向多领域检索与原摘要专业中文翻译工具。

既可作为 **Google Antigravity Agent Skill** 直接在对话中智能调度，也可作为**独立 Python 命令行工具**在任何环境中独立运行。

---

## ✨ 核心特性

- 🎯 **自定义领域与关键词过滤**：
  - 内置多种学术前沿预设领域（脑机接口、RAG 检索、信息抽取、大模型底座与推理、具身智能等）。
  - 支持用户任意输入自定义关键词（如：`diffusion models`、`medical AI`、`KV cache compression` 等）。
- 📅 **指定日期 / 区间回溯**：
  - 轻松查询指定单日或日期范围（如 `2026-10-16`）的全部 arXiv / arXivDaily 新论文。
- 🔍 **双轨防遗漏检索**：
  - 自动抓取学科分类 Feed（如 `cs.CL`、`cs.AI` 等）全量页面。
  - 跨学科全库联合高级检索，通过倒排去重与相关性评分机制，确保跨领域交叉论文不被遗漏。
- 📖 **原版英文摘要自动拉取与专业精翻**：
  - 自动从 `arxiv.org/abs/{id}` 抓取未经截断的完整原版英文摘要。
  - 生成学术级全段落中文精翻，保留严谨规范的术语表达与结构化层次。
- 🔗 **下游学术工具链协同**：
  - 与 PDF 精排翻译工具、论文汇报 PPT 生成工具（如 `codex-ppt`、`ppt-master`）无缝衔接。

---

## 📂 项目结构

```text
arxiv-paper-search/
├── SKILL.md                     # Antigravity Skill 标准规范文件
├── requirements.txt             # Python 依赖项
├── .env.example                 # 环境变量模板
├── .gitignore                   # Git 忽略配置
├── LICENSE                      # MIT 开源许可证
├── README.md                    # 项目说明文档
└── scripts/
    ├── domain_presets.json      # 预设研究领域与关键词匹配表
    └── query_papers.py          # 自动化检索、评分、去重与摘要抓取核心脚本
```

---

## 🛠️ 安装与配置

### 1. 克隆仓库

```bash
git clone https://github.com/namelessfei/arxiv-paper-search.git
cd arxiv-paper-search
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置账号（可选）

如需使用 arXivDaily 的高级搜索功能，建议配置登录凭证（三种配置方式任选其一）：

* **方式 A：环境变量（推荐）**
  ```bash
  export ARXIVDAILY_USERNAME="your_username"
  export ARXIVDAILY_PASSWORD="your_password"
  ```
* **方式 B：本地配置文件**
  复制并在 `scripts/` 目录下创建 `config.local.json`（已被 `.gitignore` 自动忽略，安全不泄露）：
  ```json
  {
    "username": "your_username",
    "password": "your_password"
  }
  ```
* **方式 C：命令行直接传参**
  在运行脚本时添加 `--username your_user --password your_pass`。

---

## 🚀 使用指南

### 方式一：作为 Antigravity Skill 智能调用

将本目录放置在工作区 `.agents/skills/arxiv-paper-search` 或全局配置目录中。

在日常对话中，直接向 AI 提出论文检索需求：
> *“帮我查一下 2026-10-16 的论文，重点关注脑机接口、大模型检索和 KV Cache 压缩，把原摘要翻译成中文输出。”*

AI 将自动识别意图、调用 `query_papers.py` 获取数据、进行相关性筛选，并生成结构化论文速递卡片。

---

### 方式二：作为独立命令行工具运行

```bash
python scripts/query_papers.py \
  --date "2026-10-16" \
  --domains "brain,rag,foundation" \
  --keywords "embodied,robotics" \
  --fetch-abstracts \
  --output "results.json"
```

#### 常用参数说明：

| 参数 | 类型 | 默认值 | 描述 |
| :--- | :--- | :--- | :--- |
| `--date` | string | 当天日期 | 目标检索日期（格式：`YYYY-MM-DD`） |
| `--date-from` | string | - | 起始日期（支持跨日期检索） |
| `--date-to` | string | - | 截止日期 |
| `--domains` | string | `brain,rag,ie,foundation` | 领域预设 Key 或自定义领域名称（逗号分隔） |
| `--keywords` | string | 空 | 补充搜索关键词（逗号分隔） |
| `--subcat` | string | `cs.CL` | 主爬取分类 Feed（如 `cs.CL`, `cs.AI`, `cs.LG` 等） |
| `--fetch-abstracts` | flag | 否 | 开启后自动从 `arxiv.org` 拉取完整未截断英文原摘要 |
| `--limit-per-domain`| int | 15 | 每个领域精选论文保留上限 |
| `--output` | string | 自动命名 | 结果输出 JSON 路径 |

---

## 🏷️ 预设领域对照表

| 预设代码 | 领域名称 | 包含重点关键词 |
| :--- | :--- | :--- |
| `brain` | 脑电 / 脑磁 / 脑机接口 / 神经解码 | EEG, MEG, BCI, Neural Decoding, fMRI, Cortex |
| `rag` | 大模型检索 / RAG / 记忆检索 | RAG, Dense Retrieval, Sparse Retrieval, SPLADE, Memory, KV-Cache Reuse |
| `ie` | 信息抽取 / 知识图谱 / 实体对齐 | Information Extraction, NER, Relation, Event, KGQA, Entity Matching |
| `foundation` | 大模型基础 / 推理 / 剪枝 / 量化 | Pre-training, Reasoning, CoT, KV Cache, Quantization, Pruning, Alignment |
| `agent` | 智能体系统 / 工具调用 / 规划反思 | Agent, Multi-Agent, Tool Creation, Planning, Reflection |
| `multimodal` | 多模态大模型 / 视觉语言 | Multimodal, Vision-Language, VLM, MLLM, Video LLM |
| `embodied` | 具身智能 / 机器人大模型 | Embodied AI, Robotics, Manipulation, Sim-to-Real |

---

## 📄 开源许可证

本项目基于 [MIT License](LICENSE) 许可协议开源。
欢迎学术同行与开发者提交 Issue 与 Pull Request！
