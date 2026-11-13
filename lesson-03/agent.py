"""agent.py —— 第 3 课：工具执行前先过权限检查"""
import json
import os

from dotenv import load_dotenv

load_dotenv()  # 必须在导入 permissions 之前：它会读取 NAMI_WORKSPACE

from openai import OpenAI  # noqa: E402

from permissions import PermissionManager  # noqa: E402
from tools import get_schemas, execute  # noqa: E402

client = OpenAI(
    api_key=os.environ["API_KEY"],
    base_url=os.environ.get("BASE_URL", "https://api.deepseek.com"),
)
MODEL = os.environ.get("MODEL", "deepseek-flash")
MAX_STEPS = 20

SYSTEM = ("你是一个能使用工具的助手，在用户的工作区内完成任务。"
          "必要时调用工具，完成后用简洁的语言汇报结果。")


def handle_call(call, perms: PermissionManager):
    """解析参数 → 权限检查 → 执行。永远返回字符串。"""
    name = call.function.name
    try:
        args = json.loads(call.function.arguments or "{}")
    except json.JSONDecodeError:
        return "Error: 参数不是合法的 JSON"
    decision = perms.check(name, args)
    if not decision.allowed:
        return f"[权限拒绝] {decision.reason}"   # 拒绝也要回传，让模型换条路
    return execute(name, args)


def run(user_input, messages, perms: PermissionManager):
    messages.append({"role": "user", "content": user_input})
    for _ in range(MAX_STEPS):
        resp = client.chat.completions.create(model=MODEL, messages=messages, tools=get_schemas())
        msg = resp.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))
        if not msg.tool_calls:
            return msg.content or ""
        for call in msg.tool_calls:
            print(f"🔧 {call.function.name}({call.function.arguments[:80]})")
            result = handle_call(call, perms)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
    return "（达到最大步数，已停止）"


if __name__ == "__main__":
    messages = [{"role": "system", "content": SYSTEM}]
    perms = PermissionManager()   # 整个会话共用，"一直允许"记在它身上
    while True:
        q = input("你> ").strip()
        if q in ("exit", "quit"):
            break
        print("\n" + run(q, messages, perms) + "\n")