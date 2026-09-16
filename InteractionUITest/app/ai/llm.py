"""调用本地 llama-server 的 OpenAI 兼容接口，用「工具调用」选出一个动作 id。

为什么是工具调用而不是「让模型输出文字再用正则抠」——实测数据见 AI操控方案.md：
工具调用在两个场景下准确率最高（100% / 91.7%），耗时也最低；
自由文本 + 正则提取只有 58%~75%，且慢 3 倍以上。

这里只用标准库 urllib，不引入 requests，这样在任意 Python 环境里都能跑。
"""

import json
import urllib.error
import urllib.request


class LlmError(RuntimeError):
    """LLM 调用失败（网络、超时、返回格式不对等）。"""


SYSTEM_PROMPT = (
    "你是康复训练界面的操作助手。"
    "根据用户的一句口语，判断当前页面上应该点击哪一个控件。"
)

NONE_ID = "none"
NONE_DESC = "当前页面上没有与用户意图匹配的控件"


def tool_schema(actions):
    """把动作表变成工具的 enum —— 模型在解码层就不可能吐出页面外的 id。"""
    return [
        {
            "type": "function",
            "function": {
                "name": "click_button",
                "description": "点击当前界面上的一个控件",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action_id": {
                            "type": "string",
                            "enum": [a["id"] for a in actions] + [NONE_ID],
                        }
                    },
                    "required": ["action_id"],
                },
            },
        }
    ]


def user_message(page_label, actions, text):
    lines = ["- %s: %s —— %s" % (a["id"], a["label"], a["desc"]) for a in actions]
    lines.append("- %s: %s" % (NONE_ID, NONE_DESC))
    return (
        "当前页面：%s\n当前页面可用控件：\n%s\n\n用户说：「%s」"
        % (page_label, "\n".join(lines), text)
    )


def _post(url, payload, timeout_s):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        return json.loads(response.read().decode("utf-8"))


def choose_action(text, actions, page_label, config):
    """返回动作 id（可能是 "none"）。失败抛 LlmError。

    注意 max_tokens：这类带思考的模型会把 reasoning 也算进预算，
    给得太小（比如 64）会把工具参数的 JSON 截断，导致解析失败。默认 512。
    """
    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message(page_label, actions, text)},
        ],
        "tools": tool_schema(actions),
        "tool_choice": "required",
        "temperature": 0,
        "max_tokens": config.max_tokens,
    }

    try:
        data = _post(config.llm_url, payload, config.llm_timeout_s)
    except urllib.error.HTTPError as error:
        detail = ""
        try:
            detail = error.read().decode("utf-8", "replace")[:200]
        except Exception:
            pass
        raise LlmError("AI 服务返回 HTTP %s %s" % (error.code, detail))
    except urllib.error.URLError as error:
        raise LlmError("连不上 AI 服务（%s）：%s" % (config.llm_url, error.reason))
    except TimeoutError:
        raise LlmError("AI 服务响应超时")
    except json.JSONDecodeError:
        raise LlmError("AI 服务返回的不是合法 JSON")

    try:
        message = data["choices"][0]["message"]
    except (KeyError, IndexError, TypeError):
        raise LlmError("AI 服务返回结构异常")

    tool_calls = message.get("tool_calls") or []
    if not tool_calls:
        # 兜底：个别模型/模板下工具调用会退化成纯文本 JSON，尝试解析一次
        content = (message.get("content") or "").strip()
        if content:
            try:
                return json.loads(content)["action_id"]
            except Exception:
                pass
        raise LlmError("AI 没有给出工具调用结果")

    raw = tool_calls[0].get("function", {}).get("arguments") or ""
    try:
        return json.loads(raw)["action_id"]
    except (json.JSONDecodeError, KeyError, TypeError):
        raise LlmError("工具参数解析失败：%r" % raw[:120])
