"""
对比 Rasa 与第三方对话 API 的同一句话回复自然度。
默认支持图灵机器人 API。需要在 .env 中设置：
TULING_API_KEY=你的图灵机器人apikey

运行前请先启动：
1) rasa run actionsS
2) rasa run --enable-api --cors "*"
"""
import os
from dataclasses import dataclass

import requests
from dotenv import load_dotenv

load_dotenv()

RASA_REST_URL = os.getenv("RASA_REST_URL", "http://localhost:5005/webhooks/rest/webhook")
TULING_API_URL = "http://openapi.turingapi.com/openapi/api/v2"
TULING_API_KEY = os.getenv("TULING_API_KEY", "")


@dataclass
class ReplyResult:
    source: str
    reply: str


def ask_rasa(text: str) -> ReplyResult:
    resp = requests.post(RASA_REST_URL, json={"sender": "compare_user", "message": text}, timeout=10)
    resp.raise_for_status()
    messages = resp.json()
    reply = "\n".join(m.get("text", "") for m in messages if m.get("text"))
    return ReplyResult("Rasa", reply or "无回复")


def ask_tuling(text: str) -> ReplyResult:
    if not TULING_API_KEY:
        return ReplyResult("图灵机器人", "未配置 TULING_API_KEY，跳过真实调用。")
    payload = {
        "reqType": 0,
        "perception": {"inputText": {"text": text}},
        "userInfo": {"apiKey": TULING_API_KEY, "userId": "order_bot_demo"},
    }
    resp = requests.post(TULING_API_URL, json=payload, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("results", [])
    texts = [r.get("values", {}).get("text", "") for r in results if r.get("resultType") == "text"]
    return ReplyResult("图灵机器人", "\n".join(texts) or str(data))


def score_naturalness(reply: str) -> int:
    """简单自然度打分：1-5 分，仅用于课程演示。"""
    if not reply or "无回复" in reply or "未配置" in reply:
        return 1
    score = 3
    if any(word in reply for word in ["已下单", "多少钱", "合计", "预计"]):
        score += 1
    if len(reply) >= 8 and "抱歉" not in reply:
        score += 1
    return min(score, 5)


if __name__ == "__main__":
    text = input("请输入同一句测试文本：").strip() or "我要两份牛肉面"
    results = [ask_rasa(text), ask_tuling(text)]
    print("\n=== 回复自然度对比 ===")
    for item in results:
        print(f"[{item.source}] {item.reply}")
        print(f"自然度评分：{score_naturalness(item.reply)}/5\n")
    print("建议结论：Rasa 在点餐业务意图、价格和槽位填充上更可控；通用聊天 API 语言可能更开放，但不一定遵守点餐业务规则。")
