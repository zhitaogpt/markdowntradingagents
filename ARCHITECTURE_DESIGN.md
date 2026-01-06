# TradingAgents 系统架构设计 (深度思考版)

## 1. 核心痛点分析
用户指出的“独立性”问题直击要害。在单一 LLM 会话中进行“角色扮演”存在以下无法回避的缺陷：
*   **记忆污染 (Memory Pollution)**: 后发言的 Agent 必然会受到先发言 Agent 的观点影响（锚定效应），无法做到真正的独立思考。
*   **虚假辩论**: 如果左右手互搏都在同一个脑子里进行，很难产生真正的批判性思维。
*   **工具局限**: `delegate_to_agent` 只能调用预设的通用 Agent（如代码分析），无法定制“金融交易员”角色。
*   **规范澄清**: `personas` 和 `workflows` 并非系统原生规范，而是工程上的文件组织约定。

## 2. 解决方案：双层架构 (Two-Layer Architecture)
为了既满足“由我调用”，又满足“真正独立”，我们需要将**意图理解**与**认知执行**物理分离。

### 层级 1: 编排与交互层 (Orchestration Layer) - **Gemini (我)**
*   **角色**: 指挥官、UI 界面、意图解析器。
*   **职责**:
    *   接收自然语言指令。
    *   决定启动哪个分析流程。
    *   **调用系统**: 通过 `run_shell_command` 触发底层的 Python 系统。
    *   **最终呈现**: 将底层系统输出的结构化数据转化为人类可读的回答。

### 层级 2: 执行与认知层 (Execution & Cognitive Layer) - **Python System**
*   **实现**: 本地 Python 代码库 (`tradingagents/`)。
*   **独立性核心**:
    *   **物理隔离**: 每个 Agent (技术、基本面、风控) 是独立的 Python 对象。
    *   **认知隔离**: 每个 Agent 初始化独立的 **LLM API Client** (OpenAI/DeepSeek 等)。
    *   **零共享上下文**: Agent A 只能看到自己的 Prompt 和数据，绝对看不到 Agent B 的“内心独白”，直到它们正式交换报告。
*   **技术实现**:
    *   使用 `asyncio` 实现分析师并行工作。
    *   使用 API Key 调用外部模型作为“独立大脑”。

## 3. 系统运作流程 (Workflow)

1.  **启动**: 你对我说 “@Gemini 深入分析 NVDA”。
2.  **调度**: 我识别任务，执行命令：
    ```bash
    python -m tradingagents.main analyze --symbol NVDA --mode deep
    ```
3.  **独立思考 (系统内部)**:
    *   *线程 A*: **技术分析师** 获取 K 线 -> 调用 API -> 生成《技术面报告》。
    *   *线程 B*: **基本面分析师** 获取财报 -> 调用 API -> 生成《估值报告》。
    *   *(此时线程 A 和 B 互不知晓)*
4.  **辩论 (系统内部)**:
    *   **辩论主持人** 拿到 A 和 B 的报告。
    *   初始化 **多头研究员** (独立 API 上下文) 和 **空头研究员** (独立 API 上下文)。
    *   进行 3 轮 API 交互，生成《多空辩论纪要》。
5.  **交付**: Python 系统输出 `final_report.json`。
6.  **展示**: 我读取 JSON，为你撰写最终回复。

## 4. 关键依赖
此方案必须依赖 **LLM API (如 OpenAI, DeepSeek, Claude)** 来为每个 Agent 提供独立的大脑。
