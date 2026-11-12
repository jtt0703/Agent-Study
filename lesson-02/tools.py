# tools.py
import subprocess
import urllib.request
from pathlib import Path
from datetime import datetime


MAX_OUTPUT = 8000   # 工具返回给模型的最大字符数
TOOLS = {}          # 注册表：name -> {"schema": ..., "func": ...}


def tool(name, description, parameters):
    """装饰器：把一个函数注册为工具"""
    def decorator(func):
        TOOLS[name] = {
            "schema": {"type": "function", "function": {
                "name": name, "description": description, "parameters": parameters}},
            "func": func,
        }
        return func
    return decorator


def get_schemas():
    """返回给模型看的全部工具说明书"""
    return [t["schema"] for t in TOOLS.values()]


def _params(**props):
    """简写：所有参数都是必填的字符串"""
    return {"type": "object",
            "properties": {k: {"type": "string", "description": v} for k, v in props.items()},
            "required": list(props)}

@tool("list_dir", "列出某个目录下的文件和子目录。", _params(path="目录路径，当前目录写 ."))
def list_dir(path="."):
    p = Path(path)
    return "\n".join(sorted(x.name + ("/" if x.is_dir() else "") for x in p.iterdir())) or "(空目录)"


@tool("read_file", "读取一个文本文件的内容。", _params(path="文件路径"))
def read_file(path):
    return Path(path).read_text(encoding="utf-8")


@tool("write_file", "把内容写入文件，已存在则覆盖，目录不存在会自动创建。",
      _params(path="文件路径", content="要写入的完整内容"))
def write_file(path, content):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"已写入 {path}（{len(content)} 字符）"


@tool("run_shell", "在当前目录执行一条 shell 命令，返回退出码、标准输出和错误输出。",
      _params(command="要执行的命令"))
def run_shell(command):
    p = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
    return f"[exit {p.returncode}]\n{p.stdout}{p.stderr}"


@tool("fetch_url", "抓取一个网页或接口的文本内容。url 必须以 http 或 https 开头。",
      _params(url="完整的 URL"))
def fetch_url(url):
    req = urllib.request.Request(url, headers={"User-Agent": "nami-agent"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="replace")


@tool("get_time", "获取当前时间（本地时区）", _params())
def get_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@tool(
    "edit_file",
    "精确修改文件内容。通过 old 定位原文，要求 old 在原始文件中恰好出现一次，否则拒绝修改。"
    "如果匹配失败，请根据错误信息提供更长、更准确的原文。",
    _params(
        path="需要修改的文件路径",
        old="需要替换的原始文本，必须能够在文件中唯一定位",
        new="替换后的新文本"
    )
)
def edit_file(path, old, new):
    p = Path(path)

    # 1. 检查文件是否存在
    if not p.exists():
        return f"Error: 文件不存在：{path}"

    # 2. 检查是否为普通文件
    if not p.is_file():
        return f"Error: 路径不是一个文件：{path}"

    # 3. 读取原始文件
    try:
        content = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"Error: 文件不是有效的 UTF-8 文本文件：{path}"

    # 4. 检查 old 是否为空
    if not old:
        return "Error: old 不能为空，请提供需要替换的原始文本。"

    # 5. 在原始文件中统计匹配次数
    count = content.count(old)

    if count == 0:
        return (
            "Error: 未找到需要替换的原文。\n"
            "请重新读取文件，提供更长、更准确的原始文本。"
        )

    if count > 1:
        return (
            f"Error: 原文在文件中出现了 {count} 次，无法确定修改位置。\n"
            "请提供更长、更具体的原文，确保它在文件中只出现一次。"
        )

    # 6. 生成修改后的内容
    new_content = content.replace(old, new, 1)

    # 7. 写入文件
    try:
        p.write_text(new_content, encoding="utf-8")
    except OSError as e:
        return f"Error: 文件写入失败：{e}"

    # 8. 返回执行结果
    return (
        f"Successfully edited {path}.\n"
        f"Replaced 1 occurrence.\n"
        f"Old length: {len(old)} characters.\n"
        f"New length: {len(new)} characters."
    )


# 统一执行器
def execute(name, args):
    """执行工具，永远返回字符串，永远不抛异常"""
    if name not in TOOLS:
        return f"Error: 不存在工具 '{name}'，可用工具：{', '.join(TOOLS)}"
    try:
        result = str(TOOLS[name]["func"](**args))
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"
    if len(result) > MAX_OUTPUT:
        result = result[:MAX_OUTPUT] + f"\n...（已截断，共 {len(result)} 字符）"
    return result