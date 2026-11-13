# 第 3 课：权限

> 课程：[权限](https://github.com/aa1143/NamiAgent/blob/main/docs/03-permissions.md) · 代码：[lesson-03](../lesson-03/)

这一课最值得记住的，不是多了一个确认弹窗，而是：**模型提出工具调用，代码决定能不能执行，允许之后才真正执行。**

下面记的是我跑代码时遇到的问题，以及顺着这些问题弄明白的东西。

## 为什么我访问 ~/.ssh，没有像教程一样直接被拒绝？

我实际输入：

```text
看看我的 ~/.ssh 下面有什么
```

模型没有调用 `list_dir`，而是先调用 `run_shell` 执行 `ls -la ~/.ssh`。命令在 Windows 默认 cmd 环境下失败后，它又改成 `dir %USERPROFILE%\\.ssh`。我按了 `y`，最后真的列出了目录。

最开始以为是工作区配置错了，后来对照原课程文章和配套代码，才发现：**原版和本地代码在这部分逻辑一致，路径检查只覆盖文件工具。**

```python
if name in ("read_file", "write_file", "list_dir"):
    path = args.get("path", ".")
    if resolve_in_workspace(path) is None:
        return f"路径 {path!r} 在工作区 {WORKSPACE} 之外，禁止访问。"
```

而 `run_shell` 只是检查危险命令正则，再要求人工确认。

| 模型选择的调用 | 实际处理 |
|---|---|
| `list_dir(path=".")` | 工作区内，直接允许 |
| `list_dir(path="~/.ssh")` | 工作区外，直接拒绝，不询问 |
| `run_shell(command="dir %USERPROFILE%\\.ssh")` | 没命中危险模式，询问用户；按 y 后执行 |

教程展示的应当是文件工具被拒绝，然后模型回复“没有访问权限”的那条路径。**相同的用户输入，不保证模型选择相同的工具。即使用原版代码，模型选 shell、用户同意，也能出现我这样的结果。**

原文第八节也明确说明了这个限制：`run_shell` 内的命令不经过 `resolve_in_workspace()`。

另外，原版和本地代码都没有直接打印每一条工具结果，`[权限拒绝] ...` 主要是回传给模型，所以教程里的终端示例也不是程序保证逐字打印的日志。

还有个容易被模型回答误导的点：Windows 上同样需要关注 SSH 私钥的访问权限，不能因为不是 Linux 就认为不用担心。要区分工具实际返回的数据和模型额外给出的判断。

## NAMI_WORKSPACE 到底是什么意思？

推荐在根目录的 `.env` 里写：

```dotenv
NAMI_WORKSPACE=workspace
```

本项目把相对路径解释为相对项目根目录，所以在我当前的目录结构里，它等价于：

```dotenv
NAMI_WORKSPACE=D:\pythonagent\agent-loop-lab\workspace
```

用相对路径，移动项目后不用改配置。这里的行为来自本地实现：

```python
_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = (_ROOT / os.environ.get("NAMI_WORKSPACE", "workspace")).resolve()
WORKSPACE.mkdir(parents=True, exist_ok=True)
```

原课程默认使用启动时的当前目录；我这里改成了默认使用项目根目录下的 `workspace`。所以要看实际代码，不能只凭变量名猜路径基准。

`agent.py` 必须先 `load_dotenv()`，再导入 `permissions`。因为 `WORKSPACE` 在模块导入时就计算了，不会每次检查权限时重新读取环境变量。

## workspace 是不是沙箱？

**目前只是由应用代码检查边界的工作目录，不是操作系统层面的沙箱。**

```python
subprocess.run(command, shell=True, cwd=WORKSPACE, ...)
```

`cwd=WORKSPACE` 只决定命令从哪里开始执行，不决定命令能访问哪里。在项目目录打开终端，仍然可以访问其他盘符、用户主目录；这里也是一样。

真正的隔离需要操作系统限制执行进程。我们讨论过的一种方案是：Agent 在主机上调用模型，文件操作和 shell 放到 Docker Desktop（WSL 2 后端）的容器内执行，只挂载需要的工作区。

```text
Windows 主机
├─ Agent：对话、调用模型、处理审批
└─ 容器：执行文件操作和 shell
   └─ /workspace：只挂载主机的 workspace 目录
```

容器仍然有自己的系统目录；关键是没有把主机的用户目录、SSH 密钥等挂进去。还可以限制容器网络、使用普通用户、只读根文件系统并移除不需要的权限。

**这个项目目前没有接入容器。单独打开一个 Docker 终端，也不会让已有 Agent 的工具自动在容器里执行。** 要实现统一隔离，工具执行必须真的进入受限环境。仅补提示词、设置环境变量或增加几条正则，都不能代替这个边界。

## 代码主线：先检查，后执行

第二课的工具注册表继续用，第三课没有重写工具系统，而是在执行前加了一道权限检查。

| 文件 | 负责什么 |
|---|---|
| `agent.py` | 请求模型、接收工具调用、检查权限、回填结果 |
| `permissions.py` | 判断路径、命令、风险等级和人工授权 |
| `tools.py` | 注册工具，真正读写文件、执行命令 |

```text
模型返回 tool_call
→ handle_call() 解析 JSON 参数
→ perms.check(name, args)
→ 允许：execute(name, args)
→ 拒绝：生成拒绝结果，不执行工具
→ 把结果追加到 messages
→ 再次请求模型
```

`Decision` 只是一个装结果的数据类：

```python
@dataclass
class Decision:
    allowed: bool
    reason: str = ""
```

允许时返回 `Decision(True)`，拒绝时返回 `Decision(False, "原因")`。

### 三道关有固定顺序

1. **硬规则**：文件路径越界、命令命中危险模式，直接拒绝。
2. **风险分级**：禁用工具拒绝；SAFE 或已经获得会话授权的工具允许。
3. **人工确认**：剩下的调用询问用户，再决定。

```python
TOOL_RISK = {
    "list_dir": Risk.SAFE,
    "read_file": Risk.SAFE,
    "write_file": Risk.CONFIRM,
    "run_shell": Risk.CONFIRM,
    "fetch_url": Risk.CONFIRM,
}
```

没有登记的工具默认需要确认。即使确认通过，`execute()` 仍然会检查工具是否真的存在。

只有 `write_file` 能通过 `a` 记住“本次会话一直允许”。`run_shell` 每次都要确认，真实终端不会接受它的 `a` 选项。

**SAFE 和会话授权都不能跳过硬规则。** 即使写文件已经按过 `a`，下一次写工作区外的路径，仍然先被第一关拒绝。

`PermissionManager()` 在输入循环外创建，整个会话共用，所以才能记住授权。它的 `always_allowed` 集合记录的是工具名，不是每个文件路径。

### 路径检查为什么要这么写？

```python
p = Path(path_str).expanduser()
if not p.is_absolute():
    p = WORKSPACE / p
p = p.resolve()
return p if p.is_relative_to(WORKSPACE) else None
```

- `expanduser()`：把 `~` 展开为当前用户主目录。
- 拼接工作区：把相对路径定位到工作区内。
- `resolve()`：解析 `..`、符号链接等，得到实际路径。
- `is_relative_to()`：判断结果是否仍位于工作区内。

只做字符串前缀判断不可靠。文件工具内部也会再次调用这个函数，保证检查和执行使用同一套路径解析。

**权限允许不代表文件存在，也不代表读写一定成功。** 路径检查只判断边界；文件不存在、编码错误等，要到实际执行时才会发现，再由 `execute()` 转成错误结果。

### 确认界面看的是实际参数

`render_call()` 展示 shell 完整命令，或写入路径和内容前 400 字。用户审批的应该是即将执行的参数，而不是模型说的“我来做一个安全操作”。

非交互环境没有人可以确认，当前实现默认拒绝。

## 拒绝工具，不等于结束这一轮任务

```python
if not decision.allowed:
    return f"[权限拒绝] {decision.reason}"
```

这里的 `return` 只是退出 `handle_call()`，没有退出整个 `run()`。

主循环仍然会执行：

```python
messages.append({
    "role": "tool",
    "tool_call_id": call.id,
    "content": result,
})
```

然后继续请求模型。模型可以说明无法执行，也可能提出另一个工具调用。只有模型不再返回 `tool_calls`，或者达到最大步数，本轮才结束。

所以要区分：

- **一次调用被拒绝**：这一次不执行。
- **本轮任务结束**：模型给出最终回答，或触发步数上限。

人工拒绝的结果里包含“不要重试同一操作”的文字；硬规则拒绝的消息主要说明越界或危险模式。无论哪种，这段文字都不是强制停止后续调用的控制语句。

`tool_call_id` 用来把工具结果与对应的工具调用关联起来。成功和拒绝都要回填，不能让模型提出了调用，却收不到相应结果。

## Ctrl 点击为什么进不去 check？

当时的函数参数没有类型注解：

```python
def handle_call(call, perms):
```

运行时，`perms` 确实是传进来的 `PermissionManager` 对象；但编辑器不一定能推断参数的类型，所以不能可靠地补全或跳转。

现在参数写成了：

```python
def handle_call(call, perms: PermissionManager):
    ...

def run(user_input, messages, perms: PermissionManager):
    ...
```

中间还踩了一个拼写坑：写成 `PermissionManage`，少了最后的 `r`。Pylance 提示“未定义”，原因是名称和导入的类名不一致。

记住：

- 类型注解有助于跳转、补全和静态检查，不代表 Python 会自动强制检查运行时类型。
- 函数参数、返回值，以及编辑器推断不出的变量，值得标注；不必机械地给每个局部变量都标注。
- Ctrl + 鼠标左键或 F12 才是跳转；跳不过去不等于代码没有调用。
- 悬停看到 `Any` 或 `Unknown` 时，可以先检查类型信息；类名也跳不了，再查导入、语言插件和解释器。

## 测试到底怎么写、怎么执行？

这里用的是 **pytest**。现有测试是 6 个 `test_` 开头的普通函数，`assert` 是 Python 自带的断言语句。

旧笔记写的“11 个用例”和 `unittest discover` 不符合当前代码。`unittest` 不会按普通 pytest 测试函数的方式收集它们；这课应该用 pytest 运行。

在已激活的虚拟环境中：

```powershell
cd D:\pythonagent\agent-loop-lab\lesson-03
python -m pip install pytest
python -m pytest tests -v
```

pytest 安装一次即可。`-v` 显示每个测试的名称和结果。单独运行一个：

```powershell
python -m pytest tests/test_permissions.py::test_read_needs_no_confirm -v
```

### assert 的意思

```python
assert decision.allowed
assert not decision.allowed
```

第一句预期允许，第二句预期拒绝。条件不成立时抛出 `AssertionError`，pytest 报告测试失败。

**预期拒绝，而程序真的拒绝了，测试就是通过。** 不要把“操作被拒绝”和“测试失败”混为一谈。

### 不真的敲键盘，怎么测试人工确认？

现有测试通过 `make()` 注入假的询问函数：

```python
def make(answer):
    calls = []

    def ask(name, args):
        calls.append(name)
        return answer, ""

    return PermissionManager(ask=ask), calls
```

`make("y")` 的意思是：如果询问用户，就自动回答允许；`calls` 记录实际询问过哪些工具。

里面的 `ask()` 能访问外层的 `answer` 和 `calls`，这是闭包。把询问函数传给权限管理器，是依赖注入：测试控制回答，不需要真的打开交互终端。

### 两个测试最值得复习

```python
def test_read_needs_no_confirm():
    pm, calls = make("n")
    assert pm.check("read_file", {"path": "README.md"}).allowed
    assert calls == []
```

故意设成“如果问我，我就拒绝”，最终却允许，而且没有询问记录，证明工作区内读取直接放行。

这里只调用 `check()`，没有真的读文件，所以 `README.md` 不需要存在。

```python
def test_path_escape_denied_even_if_user_would_allow():
    pm, calls = make("y")
    assert not pm.check("read_file", {"path": "../../etc/passwd"}).allowed
    assert not pm.check("write_file", {"path": "/etc/hosts", "content": "x"}).allowed
    assert calls == []
```

故意设成“如果问我，我就允许”，最终仍拒绝，而且没有询问记录，证明硬规则先于人工确认。

**只断言拒绝，还不能证明没有询问用户；`calls == []` 才把这个执行顺序也验证了。**

| 现有测试 | 验证的行为 |
|---|---|
| `test_read_needs_no_confirm` | 工作区内读取允许，不询问 |
| `test_path_escape_denied_even_if_user_would_allow` | 越界读写拒绝，不询问 |
| `test_dangerous_shell_denied` | `sudo rm -rf /` 被拒绝，不询问 |
| `test_shell_needs_confirm` | 普通 shell 调用要询问 |
| `test_unknown_tool_defaults_to_confirm` | 未登记工具进入确认 |
| `test_always_only_applies_to_write_file` | 写文件记住授权，shell 每次仍询问 |

最后一个测试给假的 `ask` 固定返回 `a`，用来检查 shell 不会被加入会话授权；真实终端的 shell 确认不提供 `a`。

这些测试都不调用 `execute()`，所以 `ls`、`sudo rm -rf /` 只是被检查的字符串，不会真的执行。在 Windows 上测试通过，也不代表这些 Linux 命令能运行。

### 新加的 conftest.py 负责什么？

`tests/conftest.py` 是 pytest 自动识别的测试配置文件，不需要在测试里手动导入。当前文件的顶层代码负责准备环境：

```python
WS = tempfile.mkdtemp(prefix="nami-ws-")
os.environ["NAMI_WORKSPACE"] = WS
os.environ["NAMI_STATE_DIR"] = tempfile.mkdtemp(prefix="nami-state-")
os.environ.setdefault("API_KEY", "test")
os.chdir(WS)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

| 代码 | 作用 |
|---|---|
| `tempfile.mkdtemp()` | 创建真实的临时目录并返回路径 |
| 设置 `NAMI_WORKSPACE` | 让测试使用临时工作区 |
| 设置 `NAMI_STATE_DIR` | 准备临时状态目录，但第三课当前未使用这个变量 |
| `setdefault("API_KEY", "test")` | 没有密钥时填占位值，不覆盖已有值；当前权限测试不调用模型 |
| `os.chdir(WS)` | 改变测试进程的工作目录，普通相对文件操作从这里出发 |
| `sys.path.insert(0, ...)` | 把 `lesson-03` 放到模块搜索路径前面，让测试能导入 `permissions` |

最后那串嵌套路径处理，是从 `conftest.py` 的绝对文件路径往上取两级，得到 `lesson-03`。`__file__` 指向文件自身，不是当前工作目录。

当前正常执行顺序：

```text
pytest 加载 conftest.py
→ 设置临时工作区
→ 加载 test_permissions.py
→ 导入 permissions.py，确定 WORKSPACE
→ 收集并执行 6 个测试函数
```

这些环境变量和目录切换只影响测试进程，不会改写 `.env`，也不会改变外部 PowerShell 的当前目录。

直接用普通 Python 调用测试函数，不会自动加载 `conftest.py`；要验证完整准备流程，使用 pytest。

还要记住：临时目录不是沙箱；`mkdtemp()` 创建的目录也不会自动清理，当前文件没有写清理逻辑。

本次会话中，新增 `conftest.py` 后实际通过 pytest 验证了 **6 passed**。它说明这 6 个权限判断符合断言，不代表覆盖了所有命令、真实工具执行或整个 Agent 的行为。

## messages 是不是每次都重新发给模型？

**是完整列表反复发送，不是把系统提示词反复追加进列表。**

程序启动时只追加一次系统消息：

```python
messages = [{"role": "system", "content": SYSTEM}]
```

每次用户输入，追加一次用户消息；每次模型返回，追加模型消息；每次工具处理完成，追加对应工具结果。

请求时发送的是整个列表和工具定义：

```python
client.chat.completions.create(
    model=MODEL,
    messages=messages,
    tools=get_schemas(),
)
```

例如：

```text
第一次请求：
系统提示词 + 用户问题

模型要求调用工具，执行后第二次请求：
系统提示词 + 用户问题 + 模型工具调用 + 工具结果

输入下一个问题后的请求：
上面全部消息 + 模型最终回答 + 新用户问题
```

所以一次用户输入可能触发多次模型请求，每次都携带当前完整历史。不能假设接口会自动记住之前发过什么。

当前历史只在内存里，没有持久化、清理或摘要，重启程序就没了。对话越长，请求携带的上下文也越多，这是下一课要继续处理的问题。

`MAX_STEPS = 20` 限制的是一次用户输入最多进行多少轮模型请求，不是限制整个聊天只保留 20 条消息。

## 和第二课相比，我应该记住什么？

| | 第 2 课 | 第 3 课 |
|---|---|---|
| 工具注册 | 装饰器和注册表 | 继续沿用 |
| 工具执行 | 直接执行 | 先过权限检查 |
| 文件工具路径 | 没有工作区限制 | 解析路径并检查边界 |
| shell | 直接执行 | 危险模式检查、每次确认、固定 cwd 和超时 |
| 测试 | 没有这套权限测试 | pytest + 假 ask + 临时工作区 |

再提醒自己几件事：

- 同一句话选了不同工具，走的权限分支就可能不同。
- 用户允许不能覆盖已经写进代码的硬规则，但 shell 当前没有文件工具那道路径硬规则。
- 危险命令正则主要按 Linux 写法设计，没有覆盖 Windows 的所有危险命令；黑名单本身也不是隔离边界。
- 路径检查和执行之间仍有时间差，不能把目前的实现当成能抵御恶意并发操作的完整安全方案。
- 测试应该检查具体行为和执行顺序；看到“6 passed”，要知道到底检查了哪 6 件事。
- 系统提示词、人工审批、文件路径检查、操作系统沙箱，各自解决的问题不同，不能互相替代。
