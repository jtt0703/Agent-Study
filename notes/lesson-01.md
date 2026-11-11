# 第 1 课：最小循环

> 课程：[最小循环](https://github.com/aa1143/NamiAgent/blob/main/docs/01-minimal-loop.md) · 代码：[lesson-01](../lesson-01/)

## 这一课解决什么问题

用不到 100 行，写出第一个能自己调用工具、看结果、再继续做事的 Agent。

在写之前我总以为 Agent 是个很复杂的东西，写完发现核心就三件事：

1. 把用户的话放进 `messages`
2. 调模型，看它要不要调工具
3. 要调就执行，把结果塞回 `messages`，再调一次

模型不再要工具，就是它认为活儿干完了。

## 代码走读

```
messages = [system, user]
    ↓
while 步数 < MAX_STEPS:
    resp = 调模型(messages, tools)
    msg  = resp.choices[0].message
    messages.append(msg)
    ↓
    没有 tool_calls  → 返回 msg.content，结束
    有 tool_calls    → 逐个执行，append {"role": "tool", ...}，回到循环开头
```

关键代码在 `agent.py` 的 `run()`：

- `msg.model_dump(exclude_none=True)`：把模型返回的消息原样存回上下文，下次还要发回去
- `if not msg.tool_calls: return`：这是循环唯一的正常出口
- `MAX_STEPS = 20`：防止模型原地打转，转到 20 圈强制停

工具这边只有三个：`read_file`、`write_file`、`run_shell`。`run_shell` 每次执行前都用 `input()` 问一句 y/n，这是最朴素的权限控制，也是第 3 课的伏笔。

## 难点 / 容易踩的坑

- **`tool` 消息必须带 `tool_call_id`**，而且模型一轮可能要调多个工具，每个调用都要有一条对应的结果消息。少一条，下一次请求就会报错。
- **工具出错不能让程序崩**。异常要捕获成字符串返回给模型，模型看到错误会自己调整；直接抛异常就整个会话结束了。
- **工具输出要截断**。我用了 `[-4000:]`，不然读一个大文件就能把上下文撑爆。
- **`messages` 是不断变长的**。每次循环都往里追加，模型能看到之前所有步骤——这既是 Agent 能连续做事的原因，也是第 4 课要解决上下文问题的原因。
- Windows 上 `subprocess.run(command, shell=True)` 走的是 `cmd.exe`，Linux 的 `ls`、`cat` 不一定有，得用 `dir`、`type`。

## 这一课的局限

- 工具定义写死在 `agent.py` 里：加一个工具要同时改 schema、函数表和主循环三处。
- 没有任何边界：Agent 可以读写任何路径、执行任何命令，只靠人工点头。

这两个问题分别对应第 2 课和第 3 课。
