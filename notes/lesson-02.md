# 第 2 课：工具系统

> 课程：[工具系统](https://github.com/aa1143/NamiAgent/blob/main/docs/02-tools.md) · 代码：[lesson-02](../lesson-02/)

## 这一课解决什么问题

第 1 课加一个工具，要改三处：写函数、往 `TOOLS` 列表里加 schema、在 `TOOL_FUNCS` 里登记。

这一课把这三件事合成一件：**写一个函数，加上装饰器，就注册好了**。主循环完全不认识具体工具，只认识 `get_schemas()` 和 `execute()`。

## 代码走读

`tools.py` 的核心是一个字典和一个装饰器：

```python
TOOLS = {}   # name -> {"schema": ..., "func": ...}

def tool(name, description, parameters):
    def decorator(func):
        TOOLS[name] = {"schema": {...}, "func": func}
        return func
    return decorator
```

```python
@tool("read_file", "读取一个文本文件的内容。", _params(path="文件路径"))
def read_file(path):
    return Path(path).read_text(encoding="utf-8")
```

主循环只剩两个调用：

- `get_schemas()` → 把所有 schema 排成列表发给模型
- `execute(name, args)` → 按名字查表执行

所以 `agent.py` 相比第 1 课几乎没有变化，只是把"写死的三件套"换成了这两个函数。**这才是"加工具不改主循环"的意思。**

## `execute()` 的三个兜底

```python
def execute(name, args):
    if name not in TOOLS: return "Error: 不存在工具 ..."
    try:
        result = str(TOOLS[name]["func"](**args))
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"
    if len(result) > MAX_OUTPUT: 截断
    return result
```

1. 工具名不存在 → 告诉模型有哪些可用
2. 执行抛异常 → 变成字符串，模型能读到
3. 输出太长 → 截断到 8000 字符

这三条的共同点是：**`execute()` 永远返回字符串，永远不抛异常**。工具的失败也是一种"结果"，交给模型去处理，而不是让程序退出。

## 这一课新增的工具

| 工具 | 值得记的点 |
|---|---|
| `list_dir` | 目录不存在会抛异常，正好被 `execute()` 接住 |
| `fetch_url` | 加 `User-Agent`，设置 15 秒超时 |
| `get_time` | 没有参数，`_params()` 空调用会产生 `"required": []` |
| `edit_file` | 通过 `old` 在文件里唯一定位，出现 0 次或多次都拒绝修改，并告诉模型怎么改 |

`edit_file` 的设计很值得学：**工具自己判断能不能安全修改，判断不了就把原因返回给模型，让它重新读文件再试**。这比"模糊匹配猜一个位置"可靠得多。

## 难点 / 容易踩的坑

- **参数是模型生成的 JSON，不可信**：可能不是合法 JSON（`json.loads` 要 try），也可能是 `""`（用 `or "{}"` 兜底）。
- **`_params()` 把所有参数都当必填字符串**。现在够用，但遇到数字、布尔、可选参数就不够了，得手写 JSON Schema。
- **工具返回必须显式转字符串**。返回 `None` 或列表，回填给模型时格式会出问题。
- **注册顺序就是工具列表的顺序**，模型看到的工具顺序由 `TOOLS` 的插入顺序决定。

## 和第 1 课的区别

| | 第 1 课 | 第 2 课 |
|---|---|---|
| 加工具 | 改三处 | 写一个带装饰器的函数 |
| 执行 | 直接调 `TOOL_FUNCS[name]` | `execute()` 统一兜底 |
| 主循环 | 认识每个工具 | 只认识 `get_schemas` / `execute` |

但这一课的工具**仍然能碰任何路径、执行任何命令**——`edit_file` 也只是防止改错，不防止改到不该改的文件。所以有了第 3 课。
