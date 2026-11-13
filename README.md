<div align="center">

# 从零手写 Agent · 学习记录

跟着 [NamiAgent](https://github.com/aa1143/NamiAgent) 一课一课地学，把每一课的代码和心得留在这里。

[课程图文版](https://namiai.tech/agent/) · [NamiAgent 源码](https://github.com/aa1143/NamiAgent) · [Agent 可视化](https://namiai.tech/matrix/agent/)

</div>

## 关于这个仓库

这不是教程，是我自己的学习记录。

学 Agent 之前我以为它很神秘，读进去才发现核心就是一个 while 循环：**调模型 → 执行工具 → 把结果写回上下文 → 再调模型**，直到模型不再要工具为止。剩下的所有东西——权限、上下文管理、Skills、MCP、子 Agent——都是在这个循环外面一层层加上去的。

所以我用最笨也最有效的办法：跟着课程，一课写一遍，每学完一课就提交一次。`lesson-0X/` 就是我当时写出来的完整代码，能直接运行，相邻两课也能直接 diff 出"这一课到底加了什么"。

课程和示例代码来自 [aa1143/NamiAgent](https://github.com/aa1143/NamiAgent)，这里是我自己的复现和笔记，不是官方仓库。

## 学习进度

### 第一部分：手写核心

| 课 | 主题 | 状态 | 这一课我搞懂了什么 |
|---|---|---|---|
| 01 | [最小循环](https://github.com/aa1143/NamiAgent/blob/main/docs/01-minimal-loop.md) | ✅ [笔记](notes/lesson-01.md) | 一个 `while` + `tool_calls` 就是 Agent；工具结果要按 `tool_call_id` 回填；`MAX_STEPS` 防止死循环 |
| 02 | [工具系统](https://github.com/aa1143/NamiAgent/blob/main/docs/02-tools.md) | ✅ [笔记](notes/lesson-02.md) | 用装饰器把函数注册进 `TOOLS`；加工具只写函数，不改主循环 |
| 03 | [权限](https://github.com/aa1143/NamiAgent/blob/main/docs/03-permissions.md) | ✅ [笔记](notes/lesson-03.md) | 硬规则 → 风险分级 → 人工确认；工作区不等于沙箱；用 pytest 验证权限分支 |
| 04 | [上下文管理](https://github.com/aa1143/NamiAgent/blob/main/docs/04-context.md) | ⬜ | 截断 / 清理 / 摘要，会话持久化 |
| 05 | [Skills](https://github.com/aa1143/NamiAgent/blob/main/docs/05-skills.md) | ⬜ | AGENTS.md 常驻，技能按需加载 |
| 06 | [接入聊天软件](https://github.com/aa1143/NamiAgent/blob/main/docs/06-chat-apps.md) | ⬜ | 常驻进程、聊天里确认、白名单 |
| 07 | [定时任务与心跳](https://github.com/aa1143/NamiAgent/blob/main/docs/07-scheduler-heartbeat.md) | ⬜ | 无人值守的预授权 |

### 第二部分：补上主流能力

| 课 | 主题 | 状态 |
|---|---|---|
| 08 | [MCP](https://github.com/aa1143/NamiAgent/blob/main/docs/08-mcp.md) | ⬜ |
| 09 | [子 Agent 与多 Agent](https://github.com/aa1143/NamiAgent/blob/main/docs/09-subagents.md) | ⬜ |
| 10 | [计划](https://github.com/aa1143/NamiAgent/blob/main/docs/10-planning.md) | ⬜ |
| 11 | [记忆](https://github.com/aa1143/NamiAgent/blob/main/docs/11-memory.md) | ⬜ |

### 第三部分：拆解主流 Agent（只有文章）

⬜ [12 Claude Code](https://github.com/aa1143/NamiAgent/blob/main/docs/12-claude-code.md) ·
⬜ [13 Codex](https://github.com/aa1143/NamiAgent/blob/main/docs/13-codex.md) ·
⬜ [14 Pi](https://github.com/aa1143/NamiAgent/blob/main/docs/14-pi.md) ·
⬜ [15 Grok Bot](https://github.com/aa1143/NamiAgent/blob/main/docs/15-grok-bot.md) ·
⬜ [16 DeepSeek Harness](https://github.com/aa1143/NamiAgent/blob/main/docs/16-deepseek-harness.md) ·
⬜ [17 OpenClaw 与 Hermes](https://github.com/aa1143/NamiAgent/blob/main/docs/17-openclaw-hermes.md) ·
⬜ [18 总对照表](https://github.com/aa1143/NamiAgent/blob/main/docs/18-comparison.md)

## 目录结构

```
Agent-Study/
├── README.md                 # 总览：学习路线、进度、怎么跑
├── notes/                    # 每课一篇学习笔记
│   ├── _template.md          # 新笔记从这里复制
│   ├── lesson-01.md
│   ├── lesson-02.md
│   └── lesson-03.md
│
├── .env.example              # 配置模板（真实的 .env 不提交）
├── requirements.txt          # 只有 openai 和 python-dotenv
├── workspace/                # 第 3 课文件工具的工作区，不是系统沙箱
│
├── lesson-01/                # 最小 Agent：一个循环 + 三个工具
│   └── agent.py
│
├── lesson-02/                # 工具系统：注册表 + 装饰器 + execute() 兜底
│   ├── agent.py
│   └── tools.py
│
└── lesson-03/                # 权限：硬规则、风险分级、人工确认
    ├── agent.py
    ├── tools.py
    ├── permissions.py
    └── tests/
        ├── conftest.py        # 准备临时工作区和导入路径
        └── test_permissions.py
```

## 学习笔记

`notes/` 里一课一篇，和 `lesson-0X/` 的代码一一对应。README 只放总览和进度，具体心得都写在笔记里，免得这个文件越写越长。

笔记是自己的随心记，按当时遇到的问题整理，不必固定格式。可以从这几个方向记：

1. **这一课解决什么问题**：上一课留下了什么坑
2. **代码走读**：用自己的话把主流程讲一遍
3. **难点 / 容易踩的坑**
4. **和上一课的区别**
5. **还没想明白的**：留着以后回来补

新学一课可以从 `notes/_template.md` 开始，也可以直接记问题和复盘；学完后在上方进度表里更新状态并链接笔记。

[第三课笔记](notes/lesson-03.md) 记录了 `~/.ssh` 为什么通过 shell 被访问、工作区与沙箱的区别、类型注解与方法跳转、pytest 和 `conftest.py`，以及消息历史如何发送给模型。

> 检验标准：合上代码，能不能只靠这篇笔记把这一课讲给别人听。

## 怎么运行

需要 Python 3.10+。

```bash
git clone https://github.com/jtt0703/Agent-Study.git
cd Agent-Study

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

pip install -r requirements.txt
```

`requirements.txt` 只有 `openai` 和 `python-dotenv` 两个包。

然后配置密钥：

```bash
cp .env.example .env
```

打开 `.env` 填上 `API_KEY`，其余保持默认即可：

```ini
API_KEY=你的密钥
BASE_URL=https://api.deepseek.com
MODEL=deepseek-chat
NAMI_WORKSPACE=workspace
```

`NAMI_WORKSPACE=workspace` 从第三课开始使用，相对项目根目录解析；当前等价于项目下的 `workspace/`。它限制文件工具的访问路径，并作为 shell 的起始目录，不提供系统级隔离。

运行：

```powershell
# 第 1 课：一次性任务
.\venv\Scripts\python.exe .\lesson-01\agent.py "把当前目录的文件列出来并总结"

# 第 2 课：交互式，可以连续追问
.\venv\Scripts\python.exe .\lesson-02\agent.py

# 第 3 课：执行工具前检查权限
.\venv\Scripts\python.exe .\lesson-03\agent.py
```

macOS / Linux 把 `.\venv\Scripts\python.exe` 换成 `python` 即可。

### 运行第三课测试

运行依赖仍然只有 `openai` 和 `python-dotenv`。测试另外安装 `pytest`，以下命令在项目根目录执行：

```powershell
.\venv\Scripts\python.exe -m pip install pytest
.\venv\Scripts\python.exe -m pytest .\lesson-03\tests -v
```

当前有 6 个测试。pytest 会自动加载 `tests/conftest.py`，先创建临时工作区，再运行权限测试。测试通过注入假的询问函数模拟用户回答，不请求模型，也不真正执行 shell 或读写业务文件；准备测试环境会创建临时目录。

这些是普通 pytest 测试函数，不能用 `unittest discover` 代替运行。

## 和原课程不一样的地方

课程示例跑在 macOS / Linux 上，我这里做了几处 Windows 适配，顺便记录一下：

| 课程里的写法 | 我的做法 | 原因 |
|---|---|---|
| `export API_KEY=...` 每次都设 | 根目录一份 `.env` + `python-dotenv` | PowerShell 里没有 `export`，每次设太麻烦 |
| `export NAMI_WORKSPACE=~/agent-workspace` | `.env` 里 `NAMI_WORKSPACE=workspace`，相对项目根目录 | 不用记路径，换电脑也能跑 |
| 课程目录 `lessons/lesson-0X` | 根目录 `lesson-0X/` | 目录更浅，打开就是这一课 |

`.env` 每个 `agent.py` 顶部用两行加载：

```python
from dotenv import load_dotenv
load_dotenv()
```

`load_dotenv()` 会从当前文件所在目录**逐级向上**找 `.env`，所以所有 lesson 共用根目录那一份，改一处全部生效；已存在的环境变量优先级更高，临时覆盖也方便。

## 提交约定

每学完一课提交一次，代码和笔记放在同一个 commit 里，message 统一用 `lesson-0X: 主题`：

```bash
git add lesson-0X notes/lesson-0X.md
git commit -m "lesson-0X: 主题"
```

```
lesson-01: 最小循环
lesson-02: 工具系统
lesson-03: 权限
```

这样以后 `git log --oneline` 就是一条学习时间线，也能配合 `git show <commit>` 回看每一课到底改了什么。

## 安全提醒

这是教学代码，Agent 会**真的**执行命令、读写文件。

- 第 1、2 课没有沙箱，相对路径就是启动时的当前目录，别在重要目录里跑。
- 第 3 课的 `list_dir`、`read_file`、`write_file` 会检查路径是否位于 `NAMI_WORKSPACE` 内；`run_shell` 只设置起始目录、检查危险命令模式并要求确认，**仍可访问工作区外的路径**。
- 当前没有接入操作系统沙箱。工作目录和人工审批不等于系统隔离，真实隔离需要容器、受限用户或系统沙箱等机制。
- 不要把工作区指向主目录，更不要把 `.env` 提交上去。

## 鸣谢

- 课程与示例代码：[aa1143/NamiAgent](https://github.com/aa1143/NamiAgent)（代码 MIT，文章 CC BY-NC 4.0）
- 图文教程：[namiai.tech/agent](https://namiai.tech/agent/)
- Agent 工作原理可视化：[namiai.tech/matrix/agent](https://namiai.tech/matrix/agent/)

本仓库是个人学习记录，遵循原课程的许可，不用于商业用途。
