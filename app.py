from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

try:
    from sparkai.llm.llm import ChatSparkLLM
    from sparkai.core.messages import ChatMessage

    from xunfei import (
        SPARKAI_URL,
        SPARKAI_APP_ID,
        SPARKAI_API_SECRET,
        SPARKAI_API_KEY,
        SPARKAI_DOMAIN,
    )

    SPARK_AVAILABLE = True
    SPARK_IMPORT_ERROR = None
except Exception as exc:
    SPARK_AVAILABLE = False
    SPARK_IMPORT_ERROR = exc


load_dotenv()

app = Flask(__name__, template_folder="templates", static_folder="static")

RASA_REST_URL = os.getenv(
    "RASA_REST_URL",
    "http://127.0.0.1:5005/webhooks/rest/webhook"
)

SPARK_CLIENT = None
USER_CARTS: Dict[str, List[Dict[str, Any]]] = {}


try:
    from actions.actions import (
        MENU,
        normalize_quantity,
        normalize_size,
        money,
        format_menu,
        format_cart,
    )
except Exception:
    MENU = {}


FOOD_ALIASES = {
    "鸡翅": "奥尔良烤翅",
    "烤翅": "奥尔良烤翅",
    "奥尔良鸡翅": "奥尔良烤翅",
    "炸鸡": "炸鸡块",
    "鸡块": "炸鸡块",
    "奶茶": "珍珠奶茶",
    "咖啡": "拿铁咖啡",
    "披萨": "牛肉披萨",
}


def all_foods() -> Dict[str, Dict[str, Any]]:
    return {item["name"]: item for foods in MENU.values() for item in foods}


def food_names_with_aliases() -> Dict[str, str]:
    names: Dict[str, str] = {}
    for food in all_foods():
        names[food] = food
    names.update(FOOD_ALIASES)
    return names


def find_food(text: str) -> Optional[str]:
    names = food_names_with_aliases()
    for name in sorted(names.keys(), key=len, reverse=True):
        if name in text:
            return names[name]
    return None


def find_foods(text: str) -> List[str]:
    result: List[str] = []
    names = food_names_with_aliases()

    for name in sorted(names.keys(), key=len, reverse=True):
        if name in text:
            food = names[name]
            if food not in result:
                result.append(food)

    return result


def find_quantity(text: str) -> int:
    m = re.search(r"(\d+|一|二|两|三|四|五|六|七|八|九|十)\s*(份|杯|碗|个|只|块)?", text)
    return normalize_quantity(m.group(1)) if m else 1


def add_to_cart(cart: List[Dict[str, Any]], food: str, qty: int = 1, size: str = "标准份") -> None:
    qty = max(1, normalize_quantity(qty))
    size = normalize_size(size)

    for item in cart:
        if item.get("food") == food and normalize_size(item.get("size")) == size:
            item["quantity"] = normalize_quantity(item.get("quantity")) + qty
            item["size"] = size
            return

    cart.append({
        "food": food,
        "quantity": qty,
        "size": size,
    })


def remove_from_cart(
    cart: List[Dict[str, Any]],
    food: Optional[str] = None,
    qty: int = 1
) -> Tuple[bool, str]:
    if not cart:
        return False, "当前购物车还是空的哦，先告诉我你想吃什么吧~"

    qty = max(1, normalize_quantity(qty))

    if not food:
        removed = cart.pop()
        return True, f"已移除最后一项：{removed.get('food', '餐品')}。"

    left = qty

    for idx in range(len(cart) - 1, -1, -1):
        item = cart[idx]

        if item.get("food") != food:
            continue

        item_qty = normalize_quantity(item.get("quantity"))

        if item_qty > left:
            item["quantity"] = item_qty - left
            return True, f"已去掉 {qty} 份 {food}。"

        left -= item_qty
        cart.pop(idx)

        if left <= 0:
            return True, f"已去掉 {qty} 份 {food}。"

    return False, f"购物车里没有找到 {food}。"


def replace_cart_food(
    cart: List[Dict[str, Any]],
    old_food: str,
    new_food: str,
    qty: int = 1,
    size: Optional[str] = None
) -> str:
    if not cart:
        return "当前购物车还是空的哦，先告诉我你想吃什么吧~"

    qty = max(1, normalize_quantity(qty))

    removed, msg = remove_from_cart(cart, old_food, qty)

    if not removed:
        return msg + "\n\n" + format_cart(cart)

    new_size = normalize_size(size) if size else "标准份"
    add_to_cart(cart, new_food, qty, new_size)

    return f"已把 {qty} 份 {old_food} 换成 {qty} 份 {new_size} {new_food}。\n\n{format_cart(cart)}"


def modify_size(cart: List[Dict[str, Any]], food: Optional[str], size: str) -> str:
    if not cart:
        return "当前购物车还是空的哦，先告诉我你想吃什么吧~"

    new_size = normalize_size(size)

    if food:
        for item in cart:
            if item.get("food") == food:
                item["size"] = new_size
                return f"已把 {food} 修改为 {new_size}。\n\n{format_cart(cart)}"

        return f"购物车里没有找到 {food}。\n\n{format_cart(cart)}"

    cart[-1]["size"] = new_size
    return f"已把最后一项修改为 {new_size}。\n\n{format_cart(cart)}"


def parse_replace(text: str) -> Optional[Tuple[str, str, int, str]]:
    if not any(k in text for k in ["换成", "换为", "改成", "改为"]):
        return None

    m = re.search(r"(?:把|将)?(.+?)(?:换成|换为|改成|改为)(.+)", text)

    if not m:
        return None

    old_part = m.group(1)
    new_part = m.group(2)

    old_food = find_food(old_part)
    new_food = find_food(new_part)

    if not old_food or not new_food:
        foods = find_foods(text)

        if len(foods) >= 2:
            old_food = old_food or foods[0]
            new_food = new_food or foods[1]

    if not old_food or not new_food:
        return None

    qty = find_quantity(old_part)
    size = normalize_size(new_part)

    return old_food, new_food, qty, size


def local_rasa_reply(message: str, sender_id: str) -> Optional[str]:
    text = message.strip()
    cart = USER_CARTS.setdefault(sender_id, [])

    if not MENU:
        return "菜单数据加载失败，请检查 actions/actions.py。"

    if any(k in text for k in ["菜单", "有什么", "菜品", "吃的", "推荐"]):
        return format_menu()

    if any(k in text for k in ["购物车", "已点", "订单"]):
        return format_cart(cart)

    if any(k in text for k in ["清空", "取消订单", "全部不要"]):
        cart.clear()
        return "购物车已清空。需要重新点餐可以说：查看菜单。"

    if any(k in text for k in ["确认", "下单", "提交"]):
        if not cart:
            return "当前购物车还是空的哦，先告诉我你想吃什么吧~"

        return f"🎉 订单已确认！\n\n{format_cart(cart)}\n\n后厨已经收到，我们会尽快准备。"

    replace_info = parse_replace(text)

    if replace_info:
        old_food, new_food, qty, size = replace_info
        return replace_cart_food(cart, old_food, new_food, qty, size)

    food = find_food(text)

    if any(k in text for k in ["大份", "小份", "标准份", "正常份"]) and any(
        k in text for k in ["改", "换", "变成", "修改"]
    ):
        return modify_size(cart, food, normalize_size(text))

    if food and any(k in text for k in ["多少钱", "价格", "几块", "几元"]):
        item = all_foods()[food]

        return (
            f"💰 {food} 标准份单价 ¥{item['price']}。\n"
            f"小份 ¥{money(food, 1, '小份')}，"
            f"标准份 ¥{money(food, 1, '标准份')}，"
            f"大份 ¥{money(food, 1, '大份')}。\n"
            f"要加入购物车可以说：来一份{food}。"
        )

    if any(k in text for k in ["不要", "去掉", "删除", "移除", "退掉", "减掉"]):
        qty = find_quantity(text)
        removed, msg = remove_from_cart(cart, food, qty)
        return msg + "\n\n" + format_cart(cart)

    if food:
        qty = find_quantity(text)
        size = normalize_size(text)
        add_to_cart(cart, food, qty, size)
        return f"✅ 已加入购物车：{qty}份 {size} {food}。\n\n{format_cart(cart)}"

    return None


def join_rasa_messages(messages: List[Dict[str, Any]]) -> str:
    parts: List[str] = []

    for msg in messages:
        if msg.get("text"):
            parts.append(str(msg["text"]))

        if msg.get("buttons"):
            titles = [b.get("title") for b in msg["buttons"] if b.get("title")]
            if titles:
                parts.append("可选操作：" + " / ".join(titles))

        if msg.get("image"):
            parts.append(f"[图片] {msg['image']}")

    return "\n".join(parts).strip()


def ask_rasa(message: str, sender_id: str) -> str:
    payload = {
        "sender": sender_id or "web_user",
        "message": message
    }

    try:
        resp = requests.post(RASA_REST_URL, json=payload, timeout=8)
        resp.raise_for_status()
        data = resp.json()

        if isinstance(data, list):
            reply = join_rasa_messages(data)

            if reply and "抱歉" not in reply and "没理解" not in reply:
                return reply

    except Exception as exc:
        app.logger.warning("Rasa 调用失败: %s", exc)

    local = local_rasa_reply(message, sender_id)

    if local:
        return local

    return "我暂时没理解，可以试试：查看菜单 / 我要两份牛肉面 / 去掉一份汉堡 / 把一个汉堡换成鸡翅 / 改成大份。"


def get_spark_client():
    global SPARK_CLIENT

    if not SPARK_AVAILABLE:
        raise RuntimeError(f"sparkai 或 xunfei.py 导入失败：{SPARK_IMPORT_ERROR}")

    if SPARK_CLIENT is None:
        SPARK_CLIENT = ChatSparkLLM(
            spark_api_url=SPARKAI_URL,
            spark_app_id=SPARKAI_APP_ID,
            spark_api_key=SPARKAI_API_KEY,
            spark_api_secret=SPARKAI_API_SECRET,
            spark_llm_domain=SPARKAI_DOMAIN,
            streaming=False,
        )

    return SPARK_CLIENT


def ask_xunfei(message: str, sender_id: str) -> str:
    try:
        spark = get_spark_client()

        messages = [
            ChatMessage(
                role="system",
                content=(
                    "你是一个中文智能点餐助手。"
                    "请独立回答用户问题，不要依赖 Rasa。"
                    "用户可能会询问菜单、点餐、退餐、改餐、大小份、价格、购物车等问题。"
                    "你需要像真实点餐助手一样自然回答。"
                    "回答要简洁、友好、明确。"
                )
            ),
            ChatMessage(role="user", content=message)
        ]

        result = spark.generate([messages])

        try:
            reply = result.generations[0][0].text
        except Exception:
            reply = ""

        reply = str(reply or "").strip()

        if reply:
            return reply

        return "科大讯飞没有返回有效内容。"

    except Exception as exc:
        app.logger.exception("科大讯飞调用失败: %s", exc)
        return f"科大讯飞调用失败：{exc}"


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/health")
def health():
    return jsonify({
        "ok": True,
        "rasa_url": RASA_REST_URL,
        "spark_available": SPARK_AVAILABLE,
        "spark_error": str(SPARK_IMPORT_ERROR) if SPARK_IMPORT_ERROR else None,
        "menu_loaded": bool(MENU),
    })


@app.post("/chat")
def chat():
    body = request.get_json(silent=True) or {}

    message = str(body.get("message") or "").strip()
    sender_id = str(
        body.get("senderId")
        or body.get("sender")
        or "web_user"
    )

    chat_type = str(
        body.get("chatType")
        or body.get("engine")
        or "rasa"
    ).lower()

    if not message:
        return jsonify({
            "ok": False,
            "reply": "请输入内容后再发送。"
        }), 400

    if chat_type == "rasa":
        reply = ask_rasa(message, sender_id)

    elif chat_type == "xunfei":
        reply = ask_xunfei(message, sender_id)

    else:
        reply = "未知引擎类型，请选择 rasa 或 xunfei。"

    return jsonify({
        "ok": True,
        "engine": chat_type,
        "reply": reply
    })


if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=True)