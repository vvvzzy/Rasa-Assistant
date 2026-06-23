from __future__ import annotations
import re
from typing import Any, Dict, List, Text, Optional, Tuple

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
from rasa_sdk.events import SlotSet

MENU: Dict[str, List[Dict[str, Any]]] = {
    "主食面食": [
        {"name": "牛肉面", "price": 18, "tag": "招牌"},
        {"name": "番茄鸡蛋面", "price": 15, "tag": "清爽"},
        {"name": "酸辣粉", "price": 14, "tag": "酸辣"},
        {"name": "杂酱面", "price": 16, "tag": "经典"},
        {"name": "油泼面", "price": 17, "tag": "香辣"},
        {"name": "馄饨面", "price": 16, "tag": "暖胃"},
        {"name": "肥肠面", "price": 22, "tag": "重口"},
    ],
    "中式盖饭": [
        {"name": "鸡腿饭", "price": 22, "tag": "热销"},
        {"name": "宫保鸡丁饭", "price": 24, "tag": "下饭"},
        {"name": "鱼香肉丝饭", "price": 23, "tag": "经典"},
        {"name": "青椒肉丝饭", "price": 21, "tag": "家常"},
        {"name": "红烧牛肉饭", "price": 28, "tag": "足量"},
        {"name": "土豆丝盖饭", "price": 16, "tag": "素食"},
        {"name": "梅菜扣肉饭", "price": 26, "tag": "浓香"},
    ],
    "西式简餐": [
        {"name": "汉堡", "price": 18, "tag": "快捷"},
        {"name": "奥尔良烤翅", "price": 20, "tag": "人气"},
        {"name": "意式肉酱面", "price": 25, "tag": "浓郁"},
        {"name": "炸鸡块", "price": 16, "tag": "酥脆"},
        {"name": "牛肉披萨", "price": 39, "tag": "分享"},
        {"name": "热狗", "price": 12, "tag": "轻食"},
    ],
    "饮品": [
        {"name": "珍珠奶茶", "price": 12, "tag": "甜饮"},
        {"name": "可乐", "price": 5, "tag": "冰爽"},
        {"name": "柠檬水", "price": 8, "tag": "解腻"},
        {"name": "橙汁", "price": 9, "tag": "果香"},
        {"name": "冰红茶", "price": 6, "tag": "清凉"},
        {"name": "拿铁咖啡", "price": 16, "tag": "提神"},
    ],
    "小吃": [
        {"name": "薯条", "price": 10, "tag": "酥脆"},
        {"name": "鸡米花", "price": 13, "tag": "热销"},
        {"name": "炸年糕", "price": 11, "tag": "软糯"},
        {"name": "香酥地瓜条", "price": 12, "tag": "香甜"},
    ],
}

CATEGORY_ALIASES = {
    "主食": "主食面食", "面食": "主食面食", "主食面食": "主食面食", "面条": "主食面食",
    "中式": "中式盖饭", "盖饭": "中式盖饭", "米饭": "中式盖饭", "中式盖饭": "中式盖饭",
    "西式": "西式简餐", "西餐": "西式简餐", "汉堡": "西式简餐", "西式简餐": "西式简餐",
    "饮料": "饮品", "喝的": "饮品", "饮品": "饮品",
    "小吃": "小吃", "小食": "小吃", "炸物": "小吃",
}

CN_NUM = {
    "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10
}


def all_foods() -> Dict[str, Dict[str, Any]]:
    return {item["name"]: item for foods in MENU.values() for item in foods}


def normalize_quantity(value: Any) -> int:
    if value is None or value == "":
        return 1

    text = str(value).strip()
    for unit in ["份", "杯", "碗", "个", "只", "块"]:
        text = text.replace(unit, "")

    if text.isdigit():
        return max(1, int(text))

    if text in CN_NUM:
        return CN_NUM[text]

    return 1

def extract_quantity_from_text(text: str) -> int:
    m = re.search(
        r"(\d+|一|二|两|三|四|五|六|七|八|九|十|十一|十二|十三|十四|十五|十六|十七|十八|十九|二十|三十)\s*(份|杯|碗|个|只|块|对|根)?",
        text or ""
    )
    return normalize_quantity(m.group(1)) if m else 1


def get_quantity_from_tracker(tracker: Tracker) -> int:
    quantity_slot = tracker.get_slot("quantity")
    if quantity_slot:
        return normalize_quantity(quantity_slot)
    return extract_quantity_from_text(tracker.latest_message.get("text", ""))
def normalize_size(value: Any) -> str:
    text = str(value or "标准份")
    if "大" in text:
        return "大份"
    if "小" in text:
        return "小份"
    return "标准份"


def size_extra(size: Any) -> int:
    size = normalize_size(size)
    if size == "小份":
        return -2
    if size == "大份":
        return 4
    return 0


def normalize_category(value: Any) -> Optional[str]:
    if not value:
        return None
    text = str(value).strip()
    return CATEGORY_ALIASES.get(text, text if text in MENU else None)


def money(food: str, qty: int = 1, size: Any = "标准份") -> int:
    base_price = int(all_foods().get(food, {}).get("price", 0))
    unit_price = max(1, base_price + size_extra(size))
    return unit_price * normalize_quantity(qty)


def format_menu() -> str:
    lines = ["✨ 今日菜单分类如下："]
    for category, items in MENU.items():
        names = "、".join(f"{i['name']}¥{i['price']}" for i in items[:6])
        lines.append(f"• {category}：{names}")
    lines.append("\n大小份规则：小份 -2 元，标准份原价，大份 +4 元。")
    lines.append("你可以直接说：我要两份牛肉面 / 查看饮品 / 可乐多少钱。")
    return "\n".join(lines)


def format_cart(cart: List[Dict[str, Any]]) -> str:
    if not cart:
        return "当前购物车还是空的哦，先告诉我你想吃什么吧~"

    lines = ["🛒 当前购物车："]
    total = 0

    for idx, item in enumerate(cart, 1):
        qty = normalize_quantity(item.get("quantity"))
        food = item.get("food", "未知餐品")
        size = normalize_size(item.get("size"))
        subtotal = money(food, qty, size)
        total += subtotal

        unit_price = money(food, 1, size)
        lines.append(
            f"{idx}. {qty}份 {size} {food}｜单价 ¥{unit_price}｜小计 ¥{subtotal}"
        )

    lines.append(f"\n合计：¥{total}")
    lines.append("确认请说：确认下单；修改请说：去掉一份汉堡 / 把一个汉堡换成鸡翅 / 改成大份。")
    return "\n".join(lines)


def add_to_cart(cart: List[Dict[str, Any]], food: str, qty: int = 1, size: Any = "标准份") -> List[Dict[str, Any]]:
    qty = normalize_quantity(qty)
    size = normalize_size(size)

    for item in cart:
        if item.get("food") == food and normalize_size(item.get("size")) == size:
            item["quantity"] = normalize_quantity(item.get("quantity")) + qty
            item["size"] = size
            return cart

    cart.append({
        "food": food,
        "quantity": qty,
        "size": size,
    })
    return cart


def remove_from_cart(cart: List[Dict[str, Any]], food: Optional[str], qty: int = 1) -> Tuple[List[Dict[str, Any]], bool]:
    if not cart:
        return cart, False

    qty = normalize_quantity(qty)

    if not food:
        cart.pop()
        return cart, True

    left = qty

    for idx in range(len(cart) - 1, -1, -1):
        item = cart[idx]
        if item.get("food") != food:
            continue

        item_qty = normalize_quantity(item.get("quantity"))

        if item_qty > left:
            item["quantity"] = item_qty - left
            return cart, True

        left -= item_qty
        cart.pop(idx)

        if left <= 0:
            return cart, True

    return cart, False


class ActionShowCategories(Action):
    def name(self) -> Text:
        return "action_show_categories"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> List[Any]:
        dispatcher.utter_message(text=format_menu())
        return []


class ActionShowCategoryItems(Action):
    def name(self) -> Text:
        return "action_show_category_items"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> List[Any]:
        category = normalize_category(tracker.get_slot("category"))

        if not category:
            dispatcher.utter_message(text="这个分类我没找到。可选：主食面食、中式盖饭、西式简餐、饮品、小吃。")
            return []

        items = MENU[category]
        text = f"🍽️ {category} 推荐：\n" + "\n".join(
            f"• {i['name']}｜¥{i['price']}｜{i['tag']}" for i in items
        ) + "\n\n想点哪个？比如：我要两份牛肉面。"

        dispatcher.utter_message(text=text)
        return [SlotSet("category", category)]


class ActionQueryPrice(Action):
    def name(self) -> Text:
        return "action_query_price"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> List[Any]:
        food = tracker.get_slot("food")
        item = all_foods().get(str(food))

        if not item:
            dispatcher.utter_message(text="我暂时没查到这个餐品价格。你可以说“查看菜单”看看可选餐品。")
            return []

        dispatcher.utter_message(
            text=(
                f"💰 {food} 标准份单价 ¥{item['price']}。\n"
                f"小份 ¥{money(str(food), 1, '小份')}，"
                f"标准份 ¥{money(str(food), 1, '标准份')}，"
                f"大份 ¥{money(str(food), 1, '大份')}。"
            )
        )
        return []

class ActionAddToCart(Action):
    def name(self) -> Text:
        return "action_add_to_cart"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> List[Any]:
        food = tracker.get_slot("food")

        if not food or str(food) not in all_foods():
            dispatcher.utter_message(text="我还不知道你要点哪个餐品。可以说：我要两份牛肉面，或先说“查看菜单”。")
            return []

        qty = get_quantity_from_tracker(tracker)
        size = normalize_size(tracker.get_slot("size"))
        cart = list(tracker.get_slot("cart") or [])

        cart = add_to_cart(cart, str(food), qty, size)

        dispatcher.utter_message(text=f"✅ 已加入购物车：{qty}份 {size} {food}。\n\n{format_cart(cart)}")
        return [SlotSet("cart", cart), SlotSet("order_status", "has_items")]


class ActionRemoveFromCart(Action):
    def name(self) -> Text:
        return "action_remove_from_cart"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> List[Any]:
        food = tracker.get_slot("food")
        qty = get_quantity_from_tracker(tracker)
        cart = list(tracker.get_slot("cart") or [])

        if not cart:
            dispatcher.utter_message(response="utter_cart_empty")
            return []

        cart, ok = remove_from_cart(cart, str(food) if food else None, qty)

        if not ok:
            dispatcher.utter_message(text=f"购物车里没有找到 {food}。\n\n{format_cart(cart)}")
            return [SlotSet("cart", cart)]

        if food:
            dispatcher.utter_message(text=f"已去掉 {qty}份 {food}。\n\n{format_cart(cart)}")
        else:
            dispatcher.utter_message(text=f"已移除最后一项。\n\n{format_cart(cart)}")

        return [SlotSet("cart", cart), SlotSet("order_status", "has_items" if cart else "empty")]


class ActionShowCart(Action):
    def name(self) -> Text:
        return "action_show_cart"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> List[Any]:
        dispatcher.utter_message(text=format_cart(list(tracker.get_slot("cart") or [])))
        return []


class ActionClearCart(Action):
    def name(self) -> Text:
        return "action_clear_cart"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> List[Any]:
        dispatcher.utter_message(text="购物车已清空。需要重新点餐可以说：查看菜单。")
        return [SlotSet("cart", []), SlotSet("order_status", "empty")]


class ActionModifyOrder(Action):
    def name(self) -> Text:
        return "action_modify_order"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> List[Any]:
        cart = list(tracker.get_slot("cart") or [])

        if not cart:
            dispatcher.utter_message(response="utter_cart_empty")
            return []

        food = tracker.get_slot("food")
        qty = tracker.get_slot("quantity")
        size = tracker.get_slot("size")

        target_index = None

        if food:
            for idx, item in enumerate(cart):
                if item.get("food") == str(food):
                    target_index = idx
                    break

        if target_index is None:
            target_index = len(cart) - 1

        if food and str(food) in all_foods():
            cart[target_index]["food"] = str(food)

        if qty:
            cart[target_index]["quantity"] = normalize_quantity(qty)

        if size:
            cart[target_index]["size"] = normalize_size(size)

        dispatcher.utter_message(text=f"已修改订单。\n\n{format_cart(cart)}")
        return [SlotSet("cart", cart), SlotSet("order_status", "has_items")]


class ActionConfirmOrder(Action):
    def name(self) -> Text:
        return "action_confirm_order"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> List[Any]:
        cart = list(tracker.get_slot("cart") or [])

        if not cart:
            dispatcher.utter_message(response="utter_cart_empty")
            return []

        dispatcher.utter_message(text=f"🎉 订单已确认！\n\n{format_cart(cart)}\n\n后厨已经收到，我们会尽快准备。")
        return [SlotSet("order_status", "confirmed")]


class ActionDefaultFallback(Action):
    def name(self) -> Text:
        return "action_default_fallback"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> List[Any]:
        dispatcher.utter_message(
            text="抱歉，我没理解。你可以试试：查看菜单 / 我要两份牛肉面 / 把一个汉堡换成鸡翅 / 去掉一份汉堡 / 改成大份。"
        )
        return []