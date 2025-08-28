from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.models import (
    QuickReply,
    QuickReplyButton,
    MessageAction,
    DatetimePickerAction,
)

import re
import os
import requests
from urllib.parse import quote
from linebot.models import TextSendMessage, FlexSendMessage, PostbackEvent

from linebot import LineBotApi
from linebot.models import (
    RichMenu,
    RichMenuArea,
    RichMenuBounds,
    RichMenuSize,
    MessageAction,
    URIAction,
    TextSendMessage,
    FlexSendMessage,
    QuickReply,
    QuickReplyButton,
    MessageAction,
)

from io import BytesIO
from urllib.parse import parse_qs
import requests
import json
from linebot.models import FlexSendMessage
from urllib.parse import quote

import pytz
from urllib.parse import urlencode
import datetime
from pytz import timezone  # 如果要台灣時區

session_store = {}  # { user_id: { "last_results": [...] } }


def format_date_with_weekday(date_str: str | None) -> str:
    """
    傳入 YYYY-MM-DD，回傳 YYYY-MM-DD(週)
    若是 None 或空字串 → 回傳 "未選"
    """
    if not date_str:  # 這裡會擋掉 None 或空字串
        return "未選擇"
    try:
        d = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        weekdays = ["一", "二", "三", "四", "五", "六", "日"]
        return f"{date_str}({weekdays[d.weekday()]})"
    except Exception:
        return date_str  # 如果格式錯誤，就原樣回傳


def check_image_url(url):
    """檢查圖片連結是否正常（回應 200）"""
    try:
        r = requests.head(url, timeout=3)  # 用 HEAD 請求比較快
        return r.status_code == 200
    except:
        return False


def build_detail_flex(data_dict):
    """
    將單筆 JSON 轉成表單樣式的 Flex bubble
    支援欄位名稱中文化 + 欄位過濾
    """

    # 欄位對照表（英文 → 中文）
    field_map = {
        # "car_no": "車號",
        "name": "姓名",
        "sex": "性別",
        "tel": "電話",
        "car_type": "車型",
        "car_kind": "車種",
        "color": "顏色",
        "note": "備註",
        "new_date": "編輯日期",
    }

    # ✅ 白名單：只顯示這些欄位（順序就是顯示順序）
    allowed_fields = [
        "name",
        "tel",
        "car_type",
        "car_kind",
        "color",
        "note",
        "new_date",
    ]

    # 標題優先顯示車號，其次姓名
    title = str(data_dict.get("car_no") or data_dict.get("name") or "詳細資訊")

    # ==== 處理圖片連結 ====
    sex = str(data_dict.get("sex", "")).strip()
    male_url = (
        "https://hsue2000.synology.me/images/male.png"  # 主圖片網址（要改成你的）
    )
    female_url = (
        "https://hsue2000.synology.me/images/female.png"  # 主圖片網址（要改成你的）
    )
    people_url = "https://hsue2000.synology.me/images/people.png"  # 備用圖片

    if sex == "男":
        pic_url = male_url
    elif sex == "女":
        pic_url = female_url
    else:
        pic_url = people_url

    FIELD_COLOR_MAP = {
        "new_date": "#FF4500",  # 橘色
        "tel": "#9400D3",  # 紫色
        "name": "#000000",  # 黑色
        "car_type": "#227700",  # 綠色
        "color": "#FF44AA",  # 粉紅色
    }

    STATS_KEYS = {"washes_total", "washes_pass", "washes_fail"}
    # ===== 欄位 rows =====
    rows = []

    for k in allowed_fields:
        if k in STATS_KEYS:  # ← 防止重複
            continue

        val_raw = data_dict.get(k, "")
        val = format_phone(val_raw) if k == "tel" else val_raw

        # if str(val).strip():
        value_color = FIELD_COLOR_MAP.get(k, "#0000FF")  # 預設藍色
        rows.append(
            {
                "type": "box",
                "layout": "baseline",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "text",
                        "text": field_map.get(k, k),
                        "size": "md",
                        "color": "#666666",
                        "flex": 3,
                        "weight": "bold",
                        "align": "start",  # ✅ 靠左
                    },
                    {
                        "type": "text",
                        "text": (str(val) if str(val).strip() else "無"),
                        "size": "md",
                        "color": value_color,
                        "wrap": True,
                        "flex": 7,
                        "align": "start",  # ✅ 靠左
                    },
                ],
            }
        )

    # === 2) 最後統一插入分隔＋三個統計欄位 ===

    def make_stat_row(label, value, color="#0000FF"):
        return {
            "type": "box",
            "layout": "baseline",
            "spacing": "sm",
            "contents": [
                {
                    "type": "text",
                    "text": label,
                    "size": "md",
                    "color": "#666666",
                    "flex": 3,
                    "weight": "bold",
                    "align": "start",
                },
                {
                    "type": "text",
                    "text": str(value),
                    "size": "md",
                    "color": color,
                    "flex": 7,
                    "align": "start",
                },
            ],
        }

    # 若三個值在變數；若放在 data_dict 也可以從那裡拿
    w_total = (
        washes_total
        if "washes_total" in locals()
        else int(data_dict.get("washes_total", 0) or 0)
    )
    w_pass = (
        washes_pass
        if "washes_pass" in locals()
        else int(data_dict.get("washes_pass", 0) or 0)
    )
    w_fail = (
        washes_fail
        if "washes_fail" in locals()
        else int(data_dict.get("washes_fail", 0) or 0)
    )

    # 只要有統計欄位，就插入分隔與三列（就算是 0 也顯示）
    rows.extend(
        [
            {"type": "separator", "margin": "lg"},
            {
                "type": "text",
                "text": "<洗車紀錄>",
                "weight": "bold",
                "size": "md",
                "color": "#888888",
            },
            make_stat_row("洗車次數", w_total, "#0047AB"),
            make_stat_row("已完成", w_pass, "#1E9E3A"),
            make_stat_row("未完成", w_fail, "#CC3333"),
        ]
    )

    # ===== Flex bubble =====
    bg = "#F8F8FF"

    bubble = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": bg,  # ★ 讓整個 body 區域都有底色
            "contents": [
                {  # 🔹 第一列：圖片 + 標題 並排
                    "type": "box",
                    "layout": "horizontal",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "text",
                            "text": title,
                            "weight": "bold",
                            "size": "xl",
                            "wrap": True,
                            "gravity": "center",  # 讓文字跟圖片上下置中
                        },
                        {
                            "type": "image",
                            "url": pic_url,
                            "size": "xs",  # 圖片大小可調
                            "aspectMode": "fit",
                            "align": "end",  # 圖片靠右
                        },
                    ],
                },
                {  # 🔹 第二列：rows 列表
                    "type": "box",
                    "layout": "vertical",
                    "margin": "lg",
                    "spacing": "sm",
                    "contents": rows,
                },
            ],
        },
        # ★ 建議補個 footer，讓底部也同底色（就算沒有元件也可留空）
        "footer": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#F8F8FF",
            "spacing": "sm",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "height": "sm",
                    "action": {
                        "type": "message",
                        "label": "🔍 查詢洗車紀錄",
                        "text": f"紀錄 {data_dict.get("car_no")}",  # ← 會送出「洗車 AAA-111」
                    },
                }
            ],
        },
    }

    return FlexSendMessage(alt_text="詳細資訊", contents=bubble)


###################################################################################>>
def build_detail_flexA(
    car_dict: dict, washes_list: list[dict], title=None, pic_url=None
):

    # 標題優先顯示車號，其次姓名
    title = str(car_dict.get("car_no") or car_dict.get("name") or "詳細資訊")

    # ==== 處理圖片連結 ====
    sex = str(car_dict.get("sex", "")).strip()
    male_url = (
        "https://hsue2000.synology.me/images/male.png"  # 主圖片網址（要改成你的）
    )
    female_url = (
        "https://hsue2000.synology.me/images/female.png"  # 主圖片網址（要改成你的）
    )
    people_url = "https://hsue2000.synology.me/images/people.png"  # 備用圖片

    if sex == "男":
        pic_url = male_url
    elif sex == "女":
        pic_url = female_url
    else:
        pic_url = people_url

    FIELD_COLOR_MAP = {
        "new_date": "#FF4500",  # 橘色
        "tel": "#9400D3",  # 紫色
        "name": "#000000",  # 黑色
        "car_type": "#227700",  # 綠色
        "color": "#FF44AA",  # 粉紅色
        "A_item": "#FF44AA",  # 粉紅色
        "A_ord_time": "#227700",  # 綠色
        "A_money": "#FF4500",  # 橘色
        "washes_total": "#000000",  # 黑色
        "washes_pass": "#227700",  # 綠色
        "washes_fail": "#FF44AA",  # 粉紅色
    }

    # ---- 安全處理參數 ----
    car_dict = car_dict if isinstance(car_dict, dict) else {}
    washes = washes_list if isinstance(washes_list, list) else []

    # 如果你的車籍是放在 car_info 裡，先攤平
    car_info = (
        car_dict.get("car_info") if isinstance(car_dict.get("car_info"), dict) else None
    )
    base_car = car_info if car_info else car_dict

    # 你的白名單 & 顯示名稱
    allowed_car_fields = [
        # "car_no",
        "name",
        # "sex",
        "tel",
        "car_type",
        "car_kind",
        "color",
        "note",
        "new_date",
    ]
    allowed_wash_fields = [
        "A_date",
        "A_item",
        "A_ord_time",
        "A_time",
        "A_money",
        "A_status",
        "A_note",
    ]

    car_field_map = {
        # "car_no": "車號",
        "name": "姓名",
        # "sex": "性別",
        "tel": "電話",
        "car_type": "車型",
        "car_kind": "車種",
        "color": "顏色",
        "note": "車籍備註",
        "new_date": "編輯日期",
    }
    wash_fields_map = {
        "A_date": "預約日期",
        "A_item": "服務項目",
        "A_time": "交車時間",
        "A_ord_time": "預約時間",
        "A_money": "金額",
        "A_status": "狀態",
        "A_note": "洗車備註",
    }

    def safe_text(x):
        return (
            ("" if x is None else str(x)).replace("\r", "").replace("\n", " ").strip()
        )

    # ===== 車籍 rows =====
    rows_car = []
    for k in allowed_car_fields:
        val_raw = base_car.get(k, "")

        # 只在電話欄位做 10 碼格式化（你也可依實際欄位名稱調整）
        if k in ("tel"):
            val = format_phone(val_raw)
        else:
            val = val_raw

        if safe_text(val):
            rows_car.append(
                {
                    "type": "box",
                    "layout": "baseline",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "text",
                            "text": car_field_map.get(k, k),
                            "size": "md",
                            "color": "#666666",
                            "flex": 3,
                            "weight": "bold",
                            "align": "start",
                        },
                        {
                            "type": "text",
                            "text": safe_text(val),
                            "size": "md",
                            "color": FIELD_COLOR_MAP.get(k, "#0000FF"),
                            "wrap": True,
                            "flex": 7,
                            "align": "start",
                        },
                    ],
                }
            )

    # ===== 洗車 rows（可多筆；若只要第一筆就改 for w in washes[:1]）=====
    STATS_KEYS = {"washes_total", "washes_pass", "washes_fail"}
    rows_washed = []

    if washes:
        for idx, w in enumerate(washes, start=1):
            for k in allowed_wash_fields:
                if k in STATS_KEYS:  # 避免三個統計欄位在一般欄位重複出現
                    continue

                val = w.get(k, "")
                val_color = FIELD_COLOR_MAP.get(k, "#0000FF")  # 預設藍色

                # 動態決定顏色與文字
                if k == "A_status":
                    if val == "已完成":
                        val = f"{val} ✅"
                        val_color = "#9400D3"  # 紫色
                    elif val == "未完成":
                        val = f"{val} ❌"
                        val_color = "#FF8C00"  # 橘色
                    else:
                        val = f"{val}查無資料"
                        val_color = "#FF0000"  # 紅色

                # 只有 A_date 才做日期格式化
                if k == "A_date":
                    val = format_date_with_weekday(val) if val else "未選擇"

                rows_washed.append(
                    {
                        "type": "box",
                        "layout": "baseline",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "text",
                                "text": wash_fields_map.get(k, k),
                                "size": "md",
                                "color": "#666666",
                                "flex": 3,
                                "weight": "bold",
                                "align": "start",
                            },
                            {
                                "type": "text",
                                "text": (str(val).strip() or "無"),
                                "size": "md",
                                "color": val_color,
                                "wrap": True,
                                "flex": 7,
                                "align": "start",
                            },
                        ],
                    }
                )
    else:
        rows_washed.append(
            {"type": "text", "text": "（無洗車紀錄）", "size": "sm", "color": "#999999"}
        )

    # === 只在最後三個欄位前插入一次分隔＋<洗車紀錄> ===
    rows_washed.extend(
        [
            {"type": "separator", "margin": "lg"},
            {
                "type": "text",
                "text": "<洗車紀錄>",
                "weight": "bold",
                "size": "md",
                "color": "#888888",
            },
        ]
    )

    def make_stat_row(label, value, color="#0000FF"):
        return {
            "type": "box",
            "layout": "baseline",
            "spacing": "sm",
            "contents": [
                {
                    "type": "text",
                    "text": label,
                    "size": "md",
                    "color": "#666666",
                    "flex": 3,
                    "weight": "bold",
                    "align": "start",
                },
                {
                    "type": "text",
                    "text": str(value),
                    "size": "md",
                    "color": color,
                    "flex": 7,
                    "align": "start",
                },
            ],
        }

    # 取得統計數值：優先用 washes 內的 totals dict，否則用 A_status 聚合
    totals_dict = None
    if isinstance(washes, list):
        totals_dict = next(
            (
                d
                for d in washes
                if isinstance(d, dict) and any(k in d for k in STATS_KEYS)
            ),
            None,
        )

    if totals_dict:
        w_total = int(totals_dict.get("washes_total", 0) or 0)
        w_pass = int(totals_dict.get("washes_pass", 0) or 0)
        w_fail = int(totals_dict.get("washes_fail", 0) or 0)
    else:
        w_total = w_pass = w_fail = 0
    if isinstance(washes, list):
        for itm in washes:
            if not isinstance(itm, dict) or any(k in itm for k in STATS_KEYS):
                continue
            st = str(itm.get("A_status", "")).strip()
            if st:
                w_total += 1
                if st == "已完成":
                    w_pass += 1
                elif st == "未完成":
                    w_fail += 1

    # 追加三個統計欄位（就算是 0 也要顯示）
    rows_washed.extend(
        [
            make_stat_row("洗車次數", w_total, "#0047AB"),
            make_stat_row("已完成", w_pass, "#1E9E3A"),
            make_stat_row("未完成", w_fail, "#CC3333"),
        ]
    )

    # ===== Flex bubble =====
    bg = "#FFFFF0"

    bubble = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": bg,  # ★ 整個 body 區塊同底色
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "spacing": "md",
                    "contents": [
                        {
                            "type": "text",
                            "text": title,
                            "weight": "bold",
                            "size": "xl",
                            "wrap": True,
                            "gravity": "center",
                        },
                        {
                            "type": "image",
                            "url": pic_url,
                            "size": "xs",
                            "aspectMode": "fit",
                            "align": "end",
                        },
                    ],
                },
                {"type": "separator", "margin": "lg"},
                {
                    "type": "text",
                    "text": "<車籍資料>",
                    "weight": "bold",
                    "size": "md",
                    "color": "#888888",
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "margin": "md",
                    "spacing": "md",
                    "contents": rows_car
                    or [
                        {
                            "type": "text",
                            "text": "（無車籍資料）",
                            "size": "md",
                            "color": "#FF44AA",
                        }
                    ],
                },
                {"type": "box", "layout": "vertical", "height": "12px"},
                {"type": "separator", "margin": "lg"},
                # {"type": "box", "layout": "vertical", "height": "8px"},  # 下方留白
                {
                    "type": "text",
                    "text": "<洗車資料>",
                    "weight": "bold",
                    "size": "md",
                    "color": "#888888",
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "margin": "md",
                    "spacing": "md",
                    "contents": rows_washed
                    or [
                        {
                            "type": "text",
                            "text": "（無洗車資料）",
                            "size": "md",
                            "color": "#FF44AA",
                        }
                    ],
                },
            ],
        },
        # ★ 建議補個 footer，讓底部也同底色（就算沒有元件也可留空）
        "footer": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#F8F8FF",
            "spacing": "sm",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "height": "sm",
                    "action": {
                        "type": "message",
                        "label": "🔍 查詢洗車紀錄",
                        "text": f"紀錄 {car_dict.get("car_no")}",  # ← 會送出「洗車 AAA-111」
                    },
                }
            ],
        },
    }
    return FlexSendMessage(alt_text="洗車詳細資訊", contents=bubble)


###################################################################################<<

last_results = []

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
SECRET = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
API_TOKEN = os.getenv("API_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL")

# 可使用的 LINE 使用者 ID 列表（White List）
whitelist = {
    "Ub48499f073b0bd08e280ef8259978933",  # 用戶A-Ken
    "U073ecd7ad08b5e6f43736355fe8239e9",  # 用戶B-尉庭
    "U2b172ae3f85d31f169915ca02330a589",  # 用戶C-爸爸
    # 請將你自己的 LINE ID 也加入
}

"""
# 從 Vercel 的環境變數讀取
whitelist_str = os.getenv("LINE_WHITELIST", "")

# 轉成 set（自動去除空白）
whitelist = {uid.strip() for uid in whitelist_str.split(",") if uid.strip()}
# print(whitelist)
"""

CHANNEL_ACCESS_TOKEN = (os.getenv("LINE_CHANNEL_ACCESS_TOKEN") or "").strip().strip('"')
CHANNEL_SECRET = (os.getenv("LINE_CHANNEL_SECRET") or "").strip().strip('"')


# 使用你的 Channel Access Token
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)

# 建立 Rich Menu
rich_menu = RichMenu(
    size=RichMenuSize(width=2500, height=843),  # 官方規格
    selected=False,  # 是否預設選單
    name="四格選單範例",  # 後台管理用名稱
    chat_bar_text="🔎 按這裡打開選單 🚗",  # 使用者點選時顯示的文字
    areas=[
        # 左1區塊
        RichMenuArea(
            bounds=RichMenuBounds(x=0, y=0, width=625, height=843),
            action=MessageAction(label="1", text="今日"),
        ),
        # 左2區塊
        RichMenuArea(
            bounds=RichMenuBounds(x=625, y=0, width=625, height=843),
            action=MessageAction(label="2", text="區間"),
        ),
        # 左3區塊
        RichMenuArea(
            bounds=RichMenuBounds(x=1250, y=0, width=625, height=843),
            action=MessageAction(label="3", text="?"),
        ),
        # 左4區塊
        RichMenuArea(
            bounds=RichMenuBounds(x=1875, y=0, width=625, height=843),
            action=MessageAction(label="4", text="關於"),
        ),
    ],
)

rich_menu_id = line_bot_api.create_rich_menu(rich_menu=rich_menu)

# 透過網址下載圖片
image_url = "https://hsue2000.synology.me/images/Qunma_richmenu_1x4.png"  # 改成你的 CDN/圖床位置
response = requests.get(image_url)
image_data = BytesIO(response.content)

# 上傳圖片
line_bot_api.set_rich_menu_image(rich_menu_id, "image/png", image_data)

# 設為預設選單
line_bot_api.set_default_rich_menu(rich_menu_id)

######################################################################


def show_loading_raw(user_id: str, seconds: int = 10):
    if not (user_id and user_id.startswith("U")):
        return
    seconds = max(5, min(int(seconds), 60))
    if seconds % 5 != 0:
        seconds = int(round(seconds / 5) * 5)
    requests.post(
        "https://api.line.me/v2/bot/chat/loading/start",
        headers={
            "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        },
        json={"chatId": user_id, "loadingSeconds": seconds},
        timeout=10,
    )


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        SECRET.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"


ROWS_PER_PAGE = 10  # 每頁筆數


def build_choose_next_step_bubble(keyword, start, end=None, hint=None):
    items = [
        {
            "type": "text",
            "text": "區間日期查詢",
            "weight": "bold",
            "size": "md",
            "align": "center",
        },
        {
            "type": "text",
            "text": "已選起始日",
            "weight": "bold",
            "size": "md",
            "align": "center",
            "color": "#0000FF",
        },
        {
            "type": "text",
            "text": format_date_with_weekday(f"{start}"),
            "weight": "bold",
            "size": "md",
            "align": "center",
            "color": "#333333",
        },
    ]
    if hint and hint.strip():
        items.append(
            {
                "type": "text",
                "text": hint.strip(),
                "size": "xs",
                "align": "center",
                "color": "#CC0000",
            }
        )  # 紅字

    bubble = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": items,
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "height": "sm",
                    "color": "#3B82F6",  # 【★新增 顏色】primary 改藍色(#3B82F6)
                    "action": {
                        "type": "postback",
                        "label": "🔍 查這一天",
                        "data": f"act=submit_single&kw={keyword}&start={start}",
                        "text": f"日期 {start} {start}",  # 讓「使用者」送出
                    },
                },
                {
                    "type": "button",
                    "style": "secondary",
                    "height": "sm",
                    "color": "#F0AD4E",  # 【★新增 顏色】secondary 設橘色(#F0AD4E)
                    "action": {
                        "type": "datetimepicker",
                        "label": "📅 選擇結束日",
                        "data": f"act=set_end&kw={keyword}&start={start}",
                        "mode": "date",
                        "initial": start,
                    },
                },
            ],
        },
    }
    return FlexSendMessage(alt_text="選擇單日或區間", contents=bubble)


def build_date_picker_bubble(
    keyword: str, start: str | None, end: str | None, hint: str | None = None
):
    def tag(lbl, val):
        return {
            "type": "box",
            "layout": "baseline",
            "spacing": "md",
            "contents": [
                {"type": "text", "text": lbl, "size": "md", "color": "#555555"},
                {
                    "type": "text",
                    "text": (val or "未選擇"),
                    "size": "md",
                    "color": "#111111",
                    "wrap": True,
                },
            ],
        }

    # footer：一次只顯示一個動作
    footer_contents = []

    if not start:
        # 第一步：只讓選起始日
        footer_contents.append(
            {
                "type": "button",
                "style": "primary",
                "height": "md",
                "action": {
                    "type": "datetimepicker",
                    "label": "📅 選起始日",
                    "data": f"act=set_start&kw={keyword}&end=",
                    "mode": "date",
                },
            }
        )
    elif not end:
        # 第二步：只讓選結束日
        footer_contents.append(
            {
                "type": "button",
                "style": "secondary",
                "color": "#F0AD4E",
                "height": "md",
                "action": {
                    "type": "datetimepicker",
                    "label": "📅 選結束日",
                    "data": f"act=set_end&kw={keyword}&start={start}",
                    "mode": "date",
                },
            }
        )

    else:
        # 第三步：只顯示「開始查詢」
        footer_contents.append(
            {
                "type": "button",
                "style": "primary",
                "height": "md",
                "action": {
                    "type": "message",
                    "label": "🔍 開始查詢",
                    "text": f"日期 {start} {end}",
                },
            }
        )

    # ✅ body：標題 → (可選)紅字 hint → 起訖日
    body_contents = [
        {
            "type": "text",
            "text": "區間日期查詢",
            "weight": "bold",
            "size": "md",
            "align": "center",
            "wrap": True,
        }
    ]
    if hint and hint.strip():
        body_contents.append(
            {
                "type": "text",
                "text": hint.strip(),
                "size": "xs",
                "align": "center",
                "color": "#CC0000",  # 紅字
                "wrap": True,
                "margin": "sm",
            }
        )

    body_contents += [
        # 若你也想顯示關鍵字可把下一行解註
        # tag("關鍵字", keyword),
        tag("起始日", format_date_with_weekday(start)),
        tag("結束日", format_date_with_weekday(end)),
    ]

    bubble = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": body_contents,
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": footer_contents,
        },
    }
    return FlexSendMessage(alt_text="區間日期查詢", contents=bubble)


####################################################################################################
def build_list_bubble(
    rows,
    title,
    page,
    total_pages,
    row_action_prefix="車號",
    columns=("car_no", "name", "sex", "car_type", "color"),
    query_cmd="名稱",
    query_val="",
):
    # 標題列
    header = {
        "type": "box",
        "layout": "horizontal",
        "spacing": "sm",
        "contents": [
            {
                "type": "text",
                "text": "姓名",
                "size": "xs",
                "weight": "bold",
                "flex": 3,
                "align": "center",
                "wrap": True,
            },
            {
                "type": "text",
                "text": "性別",
                "size": "xs",
                "weight": "bold",
                "flex": 2,
                "align": "center",
                "wrap": True,
            },
            {
                "type": "text",
                "text": "車型",
                "size": "xs",
                "weight": "bold",
                "flex": 4,
                "align": "center",
                "wrap": True,
            },
            {
                "type": "text",
                "text": "顏色",
                "size": "xs",
                "weight": "bold",
                "flex": 3,
                "align": "center",
                "wrap": True,
            },
        ],
    }

    body = [
        {
            "type": "text",
            "text": f"{title}",
            "weight": "bold",
            "size": "md",
            "align": "center",
        },
        {
            "type": "text",
            "text": f"(第{page}/{total_pages}頁)",
            "weight": "bold",
            "size": "md",
            "align": "center",
        },
        {"type": "separator", "margin": "md"},
        header,
        {"type": "separator", "margin": "sm"},
    ]

    # 資料列
    for idx, d in enumerate(rows):
        car_no = str(d.get(columns[0], ""))

        body.append(
            {
                "type": "box",
                "layout": "horizontal",
                "spacing": "sm",
                "backgroundColor": "#FFFFBB" if idx % 2 == 0 else "#E0FFFF",
                "contents": [
                    {
                        "type": "text",
                        "text": safe_text(d.get("name")),  # 絕不會是空字串,
                        "size": "sm",
                        "flex": 3,
                        "wrap": True,
                        "align": "center",
                    },
                    {
                        "type": "text",
                        "text": safe_text(d.get("sex")),  # 絕不會是空字串,
                        "size": "sm",
                        "flex": 2,
                        "wrap": True,
                        "align": "center",
                    },
                    {
                        "type": "text",
                        "text": safe_text(d.get("car_type")),  # 絕不會是空字串,
                        "size": "sm",
                        "flex": 4,
                        "wrap": True,
                        "align": "center",
                    },
                    {
                        "type": "text",
                        "text": safe_text(d.get("color")),  # 絕不會是空字串,
                        "size": "sm",
                        "flex": 3,
                        "wrap": True,
                        "align": "center",
                    },
                ],
                "action": {
                    "type": "message",
                    "label": "查詢詳情",
                    "text": f"{row_action_prefix} {car_no}",
                },
                "paddingAll": "6px",
            }
        )
        body.append({"type": "separator", "margin": "sm"})

    # 分頁按鈕（把查詢種類與值帶回去）
    footer_contents = []
    if page > 1:
        footer_contents.append(
            {
                "type": "button",
                "style": "secondary",
                "height": "sm",
                "action": {
                    "type": "message",
                    "label": "⏮️ 上一頁",
                    "text": f"列表 {query_cmd} {query_val} {page-1}",
                },
            }
        )
    if page < total_pages:
        footer_contents.append(
            {
                "type": "button",
                "style": "primary",
                "height": "sm",
                "action": {
                    "type": "message",
                    "label": "⏭️ 下一頁",
                    "text": f"列表 {query_cmd} {query_val} {page+1}",
                },
            }
        )

    bubble = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": body,
        },
    }
    if footer_contents:
        bubble["footer"] = {
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "contents": footer_contents,
        }
    return bubble


def build_list_page(all_rows, page=1, title="查詢結果", query_cmd="名稱", query_val=""):
    total = len(all_rows)
    total_pages = max(1, (total + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE)
    page = max(1, min(page, total_pages))
    start = (page - 1) * ROWS_PER_PAGE
    page_rows = all_rows[start : start + ROWS_PER_PAGE]
    bubble = build_list_bubble(
        page_rows,
        title=title,
        page=page,
        total_pages=total_pages,
        query_cmd=query_cmd,
        query_val=query_val,
    )
    return FlexSendMessage(alt_text="查詢車籍列表", contents=bubble)


################################################################################################>>
def safe_text(x):
    s = "" if x is None else str(x)
    # LINE 建議每行不要太長，避免溢出
    return s.replace("\r", "").replace("\n", " ").strip()


def _get_car_info_as_dict(car_info):
    """car_info 可能是 dict，也可能被包成單元素 list；統一回 dict。"""
    if isinstance(car_info, list) and car_info:
        return car_info[0]
    return car_info if isinstance(car_info, dict) else {}


def _get_latest_wash(washes):
    """回傳最近一筆洗車 dict；若無則回 {}。"""
    if isinstance(washes, list) and washes:
        return washes[0]
    return {}


def build_list_bubbleA(
    rows,
    title,
    page,
    total_pages,
    row_action_prefix="服務",
    query_cmd="名稱",
    query_val="",
):
    # 標題列
    header = {
        "type": "box",
        "layout": "horizontal",
        "spacing": "sm",
        "contents": [
            {
                "type": "text",
                "text": "車號",
                "size": "xs",
                "weight": "bold",
                "flex": 5,
                "align": "center",
                "wrap": True,
            },
            {
                "type": "text",
                "text": "姓名",
                "size": "xs",
                "weight": "bold",
                "flex": 3,
                "align": "center",
                "wrap": True,
            },
            {
                "type": "text",
                "text": "服務項目",
                "size": "xs",
                "weight": "bold",
                "flex": 5,
                "align": "center",
                "wrap": True,
            },
            {
                "type": "text",
                "text": "預約",
                "size": "xs",
                "weight": "bold",
                "flex": 3,
                "align": "center",
                "wrap": True,
            },
        ],
    }

    body = [
        {
            "type": "text",
            "text": f"{title}",
            "weight": "bold",
            "size": "md",
            "align": "center",
        },
        {
            "type": "text",
            "text": f"(第{page}/{total_pages}頁)",
            "weight": "bold",
            "size": "md",
            "align": "center",
        },
        {"type": "separator", "margin": "md"},
        {
            "type": "text",
            "text": "狀態表示: ✅已完成｜❌未完成",
            "size": "xs",
            "align": "center",
            "color": "#666666",  # 6 碼 HEX
            "wrap": True,
            "margin": "sm",
        },
        {"type": "separator", "margin": "md"},
        header,
        {"type": "separator", "margin": "sm"},
    ]

    # 資料列（rows 來自 data["cars"]）
    for idx, d in enumerate(rows):
        car_no = safe_text(d.get("car_no", "-"))
        car_info = _get_car_info_as_dict(d.get("car_info", {}))
        name = safe_text(car_info.get("name", "-"))

        w = _get_latest_wash(d.get("washes", []))
        # 這裡示範把 washes[0] 的 A_date/A_time 顯示在「預約時間」欄位
        a_item = safe_text(w.get("A_item", ""))
        a_time = safe_text(w.get("A_time", ""))
        a_date = safe_text(w.get("A_date", ""))
        a_ord_time = safe_text(w.get("A_ord_time", ""))
        a_status = safe_text(w.get("A_status", ""))

        if a_status == "已完成":
            a_item = a_item + " ✅"
        elif a_status == "未完成":
            a_item = a_item + " ❌"
        else:
            a_item = ""

        body.append(
            {
                "type": "box",
                "layout": "horizontal",
                "spacing": "sm",
                "backgroundColor": "#FFFFBB" if idx % 2 == 0 else "#E0FFFF",
                "contents": [
                    {
                        "type": "text",
                        "text": car_no,
                        "size": "xs",
                        "flex": 5,
                        "wrap": True,
                        "align": "center",
                    },
                    {
                        "type": "text",
                        "text": name,
                        "size": "xs",
                        "flex": 3,
                        "wrap": True,
                        "align": "center",
                    },
                    {
                        "type": "text",
                        "text": a_item,
                        "size": "xs",
                        "flex": 5,
                        "wrap": True,
                        "align": "center",
                    },
                    {
                        "type": "text",
                        "text": f"{a_ord_time}".strip(),
                        "size": "xs",
                        "flex": 3,
                        "wrap": True,
                        "align": "center",
                    },
                ],
                "action": {
                    "type": "message",
                    "label": "查詢詳情",
                    "text": f"{row_action_prefix} {car_no} {a_date}",  # 例如：「車號 AAA-0000」
                },
                "paddingAll": "6px",
            }
        )
        body.append({"type": "separator", "margin": "sm"})

    # 分頁按鈕
    footer_contents = []
    if page > 1:
        footer_contents.append(
            {
                "type": "button",
                "style": "secondary",
                "height": "sm",
                "action": {
                    "type": "message",
                    "label": "⏮️ 上一頁",
                    "text": f"列表 {query_cmd} {query_val} {page-1}",
                },
            }
        )
    if page < total_pages:
        footer_contents.append(
            {
                "type": "button",
                "style": "primary",
                "height": "sm",
                "action": {
                    "type": "message",
                    "label": "⏭️ 下一頁",
                    "text": f"列表 {query_cmd} {query_val} {page+1}",
                },
            }
        )

    bubble = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": body,
        },
    }
    if footer_contents:
        bubble["footer"] = {
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "contents": footer_contents,
        }
    return bubble


def build_list_pageA(
    all_rows, page=1, title="查詢結果", query_cmd="名稱", query_val=""
):
    total = len(all_rows)
    total_pages = max(1, (total + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE)
    page = max(1, min(page, total_pages))
    start = (page - 1) * ROWS_PER_PAGE
    page_rows = all_rows[start : start + ROWS_PER_PAGE]
    bubble = build_list_bubbleA(
        page_rows,
        title=title,
        page=page,
        total_pages=total_pages,
        query_cmd=query_cmd,
        query_val=query_val,
    )
    return FlexSendMessage(alt_text="查詢洗車列表", contents=bubble)


#############################################################################################<<


def build_list_bubbleB(
    rows,
    title,
    page,
    total_pages,
    row_action_prefix="其他日",
    query_cmd="日期",
    query_val="",
):
    # 標題列
    header = {
        "type": "box",
        "layout": "horizontal",
        "spacing": "sm",
        "contents": [
            {
                "type": "text",
                "text": "日期",
                "size": "sm",
                "weight": "bold",
                "flex": 6,
                "align": "center",
                "wrap": True,
            },
            {
                "type": "text",
                "text": "台",
                "size": "sm",
                "weight": "bold",
                "flex": 2,
                "align": "center",
                "wrap": True,
            },
            {
                "type": "text",
                "text": "日期標記",
                "size": "sm",
                "weight": "bold",
                "flex": 4,
                "align": "center",
                "wrap": True,
            },
        ],
    }

    body = [
        {
            "type": "text",
            "text": "區間日期查詢",
            "weight": "bold",
            "size": "md",
            "align": "center",
            "color": "#000000",
        },
        {
            "type": "text",
            "text": f"{title}",
            "weight": "bold",
            "size": "md",
            "align": "center",
        },
        {
            "type": "text",
            "text": f"(第{page}/{total_pages}頁)",
            "weight": "bold",
            "size": "md",
            "align": "center",
            "color": "#000000",
            "wrap": True,
        },
        {"type": "separator", "margin": "md"},
        header,
        {"type": "separator", "margin": "sm"},
    ]

    # 資料列
    for idx, d in enumerate(rows):
        day = safe_text(d.get("day", "-"))
        cnt = safe_text(d.get("cnt", "-"))
        H_Note = safe_text(d.get("H_Note", "-"))

        body.append(
            {
                "type": "box",
                "layout": "horizontal",
                "spacing": "sm",
                "backgroundColor": "#FFFFBB" if idx % 2 == 0 else "#E0FFFF",
                "contents": [
                    {
                        "type": "text",
                        "text": format_date_with_weekday(day),
                        "size": "sm",
                        "flex": 6,
                        "wrap": True,
                        "align": "center",
                    },
                    {
                        "type": "text",
                        "text": cnt,
                        "size": "sm",
                        "flex": 2,
                        "wrap": True,
                        "color": "#0000FF",
                        "align": "center",
                    },
                    {
                        "type": "text",
                        "text": H_Note,
                        "size": "sm",
                        "flex": 4,
                        "wrap": True,
                        "color": "#000000",
                        "align": "center",
                    },
                ],
                "action": {
                    "type": "message",
                    "label": "查詢詳情",
                    "text": f"{row_action_prefix} {day}",  # 例如：「車號 AAA-0000」
                },
                "paddingAll": "6px",
            }
        )
        body.append({"type": "separator", "margin": "sm"})

    # 分頁按鈕
    footer_contents = []
    if page > 1:
        footer_contents.append(
            {
                "type": "button",
                "style": "secondary",
                "height": "sm",
                "action": {
                    "type": "message",
                    "label": "⏮️ 上一頁",
                    "text": f"日列 {query_cmd} {query_val} {page-1}",
                },
            }
        )
    if page < total_pages:
        footer_contents.append(
            {
                "type": "button",
                "style": "primary",
                "height": "sm",
                "action": {
                    "type": "message",
                    "label": "⏭️ 下一頁",
                    "text": f"日列 {query_cmd} {query_val} {page+1}",
                },
            }
        )

    bubble = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": body,
        },
    }
    if footer_contents:
        bubble["footer"] = {
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "contents": footer_contents,
        }
    return bubble


def build_list_pageB(
    all_rows, page=1, title="查詢結果", query_cmd="名稱", query_val=""
):
    total = len(all_rows)
    total_pages = max(1, (total + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE)
    page = max(1, min(page, total_pages))
    start = (page - 1) * ROWS_PER_PAGE
    page_rows = all_rows[start : start + ROWS_PER_PAGE]
    bubble = build_list_bubbleB(
        page_rows,
        title=title,
        page=page,
        total_pages=total_pages,
        query_cmd=query_cmd,
        query_val=query_val,
    )
    return FlexSendMessage(alt_text="查詢洗車日期列表", contents=bubble)


####################################################################################################
def build_list_bubbleC(
    rows,
    title,
    page,
    total_pages,
    row_action_prefix="服務",
    columns=("A_car_no", "A_date", "A_time", "A_final", "A_status"),
    query_cmd="紀錄",
    query_val="",
):
    # 標題列
    header = {
        "type": "box",
        "layout": "horizontal",
        "spacing": "sm",
        "contents": [
            {
                "type": "text",
                "text": "預約日期",
                "size": "xs",
                "weight": "bold",
                "flex": 6,
                "align": "center",
                "wrap": True,
            },
            {
                "type": "text",
                "text": "預約時間",
                "size": "xs",
                "weight": "bold",
                "flex": 3,
                "align": "center",
                "wrap": True,
            },
            {
                "type": "text",
                "text": "狀態",
                "size": "xs",
                "weight": "bold",
                "flex": 4,
                "align": "center",
                "wrap": True,
            },
        ],
    }

    body = [
        {
            "type": "text",
            "text": f"{title}",
            "weight": "bold",
            "size": "md",
            "align": "center",
        },
        {
            "type": "text",
            "text": f"(第{page}/{total_pages}頁)",
            "weight": "bold",
            "size": "md",
            "align": "center",
        },
        {"type": "separator", "margin": "md"},
        {
            "type": "text",
            "text": "狀態表示: ✅已完成｜❌未完成",
            "size": "xs",
            "align": "center",
            "color": "#666666",  # 6 碼 HEX
            "wrap": True,
            "margin": "sm",
        },
        {"type": "separator", "margin": "md"},
        header,
        {"type": "separator", "margin": "sm"},
    ]

    # 資料列
    for idx, d in enumerate(rows):
        A_car_no = str(d.get(columns[0], ""))
        A_status = safe_text(d.get("A_status", "-"))
        A_date = safe_text(d.get("A_date", "-"))

        if A_status == "已完成":
            A_status = A_status + " ✅"
        elif A_status == "未完成":
            A_status = A_status + " ❌"

        body.append(
            {
                "type": "box",
                "layout": "horizontal",
                "spacing": "sm",
                "backgroundColor": "#FFFFBB" if idx % 2 == 0 else "#E0FFFF",
                "contents": [
                    {
                        "type": "text",
                        "text": format_date_with_weekday(
                            safe_text(d.get("A_date"))
                        ),  # 絕不會是空字串,
                        "size": "xs",
                        "flex": 6,
                        "wrap": True,
                        "align": "center",
                    },
                    {
                        "type": "text",
                        "text": safe_text(d.get("A_time")),  # 絕不會是空字串,
                        "size": "xs",
                        "flex": 3,
                        "wrap": True,
                        "align": "center",
                    },
                    {
                        "type": "text",
                        "text": A_status,  # 絕不會是空字串,
                        "size": "xs",
                        "flex": 4,
                        "wrap": True,
                        "align": "center",
                    },
                ],
                "action": {
                    "type": "message",
                    "label": "查詢詳情",
                    "text": f"{row_action_prefix} {A_car_no} {A_date}",
                },
                "paddingAll": "6px",
            }
        )
        body.append({"type": "separator", "margin": "sm"})

    # 分頁按鈕（把查詢種類與值帶回去）
    footer_contents = []
    if page > 1:
        footer_contents.append(
            {
                "type": "button",
                "style": "secondary",
                "height": "sm",
                "action": {
                    "type": "message",
                    "label": "⏮️ 上一頁",
                    "text": f"歷史 {query_cmd} {query_val} {page-1}",
                },
            }
        )
    if page < total_pages:
        footer_contents.append(
            {
                "type": "button",
                "style": "primary",
                "height": "sm",
                "action": {
                    "type": "message",
                    "label": "⏭️ 下一頁",
                    "text": f"歷史 {query_cmd} {query_val} {page+1}",
                },
            }
        )

    bubble = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": body,
        },
    }
    if footer_contents:
        bubble["footer"] = {
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "contents": footer_contents,
        }
    return bubble


def build_list_pageC(
    all_rows, page=1, title="查詢結果", query_cmd="紀錄", query_val=""
):
    total = len(all_rows)
    total_pages = max(1, (total + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE)
    page = max(1, min(page, total_pages))
    start = (page - 1) * ROWS_PER_PAGE
    page_rows = all_rows[start : start + ROWS_PER_PAGE]
    bubble = build_list_bubbleC(
        page_rows,
        title=title,
        page=page,
        total_pages=total_pages,
        query_cmd=query_cmd,
        query_val=query_val,
    )
    return FlexSendMessage(alt_text="查詢洗車紀錄列表", contents=bubble)


#############################################################################################<<
def format_phone(phone: str) -> str:
    """將10碼電話轉成 xxxx-xxx-xxx 格式"""
    digits = "".join(filter(str.isdigit, str(phone)))
    if len(digits) == 10:
        return f"{digits[:4]}-{digits[4:7]}-{digits[7:]}"
    return phone  # 若不是10碼，就原樣返回


def safe_text(v, default="-"):
    # 把 None / 空白 轉成預設字元，並確保是 str
    s = "" if v is None else str(v)
    s = s.strip()
    return s if s else default


#############################################################################################<<
def _to_date(s: str):
    return datetime.datetime.strptime(s, "%Y-%m-%d").date()


@SECRET.add(PostbackEvent)
def on_postback(event):
    data_qs = parse_qs(event.postback.data or "")
    act = (data_qs.get("act") or [""])[0]
    kw = (data_qs.get("kw") or ["未指定"])[0]
    start = (data_qs.get("start") or [""])[0] or None
    end = (data_qs.get("end") or [""])[0] or None

    picked = (event.postback.params or {}).get("date")  # 只有 datetimepicker 才會有

    # 使用者剛選了起始日
    if act == "set_start" and picked:
        start = picked
        # 若原本 already 有 end 但比 start 早 → 清空 end，要求重選
        if end:
            try:
                if _to_date(end) < _to_date(start):
                    end = None
                    # 【★修改】改成顯示二選一泡泡（單日 / 續選結束日），不再只顯示原本泡泡
                    msg = build_choose_next_step_bubble(
                        kw, start, end
                    )  # 【★新增 呼叫】
                    line_bot_api.reply_message(event.reply_token, msg)
                    return
            except Exception:
                end = None
        # 【★修改】選完起始日一律顯示二選一泡泡
        msg = build_choose_next_step_bubble(kw, start, end)  # 【★新增 呼叫】
        line_bot_api.reply_message(event.reply_token, msg)
        return

    # 使用者剛選了結束日
    if act == "set_end" and picked:
        # 若結束日比起始日早 → 不接受，請重選結束日（保留 start）

        if _to_date(picked) < _to_date(start):
            msg = build_date_picker_bubble(
                kw, start, None, hint="⚠️ 結束日不可早於起始日，請重新選擇結束日"
            )
            line_bot_api.reply_message(event.reply_token, msg)
            return
        else:
            end = picked
            msg = build_date_picker_bubble(kw, start, end)
            line_bot_api.reply_message(event.reply_token, msg)
            return

    # 【★新增】單日查詢分支：使用者按了「查這一天」
    if act == "submit_single":
        if not start:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="⚠️ 請先選擇日期")
            )
            return
        # ✅ 這裡執行你的「單日」查詢
        # ... do single-day query with start ...
        # line_bot_api.reply_message(
        #    event.reply_token, TextSendMessage(text=f"日期 {start} {start}")
        # )
        return

    # 送出前再做一次保險檢查
    if act == "submit":
        if not (start and end):
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="⚠️ 請先選擇起始日與結束日")
            )
            return
        try:
            if _to_date(end) < _to_date(start):
                # 清掉 end，強制重選
                msg = build_date_picker_bubble(
                    kw, start, None, hint="⚠️ 結束日不可早於起始日，請重新選擇結束日"
                )
                line_bot_api.reply_message(event.reply_token, msg)
                return
        except Exception:
            msg = build_date_picker_bubble(
                kw, start, None, hint="⚠️ 日期格式錯誤，請重新選擇結束日"
            )
            line_bot_api.reply_message(event.reply_token, msg)
            return

        # ✅ 通過檢查，這裡執行你的查詢
        # ... do query ...
        line_bot_api.reply_message(
            event.reply_token, TextSendMessage(text=f"日期 {start} {end}")
        )
        return


@SECRET.add(MessageEvent, TextMessage)
def handle_message(event):
    # 讀取用戶的ID
    user_id = event.source.user_id
    # print("發訊息的用戶 ID:",user_id)

    if user_id:
        show_loading_raw(user_id, seconds=15)

    url = f"https://hsue2000.synology.me/api/Qsearch.php?token={API_TOKEN}"
    data = {"action": "GET_COUNT"}

    response = requests.post(url, data=data)

    # 檢查是否為白名單成員
    if user_id not in whitelist:
        line_bot_api.reply_message(
            event.reply_token, TextSendMessage(text="⚠️ 未授權你使用本機器人!")
        )
        return

    user_text = event.message.text.strip()

    if user_text == "關於":

        flex_message = FlexSendMessage(
            alt_text="關於機器人",
            contents={
                "type": "bubble",
                "backgroundColor": "#FFF9C4",  # ✅ 整個泡泡背景
                "hero": {
                    "type": "image",
                    "url": "https://hsue2000.synology.me/images/KenKen.png",  # 🖼️ 替換為作者頭像圖片 URL
                    "size": "full",
                    "backgroundColor": "#E0FFFF",  # ✅ 修改這裡為你想要的底色
                    "aspectRatio": "1:1",
                    "aspectMode": "cover",
                    "size": "100px",  # ✅ 縮小頭像尺寸
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "backgroundColor": "#E0FFFF",  # ✅ 修改這裡為你想要的底色
                    "spacing": "md",
                    "contents": [
                        {
                            "type": "text",
                            "text": "『Qunma洗車查詢機器人』",
                            "weight": "bold",
                            "size": "lg",
                            "color": "#0000CD",
                            "align": "center",
                        },
                        {
                            "type": "text",
                            "text": "僅限系統內部使用",
                            "size": "md",
                            "weight": "bold",
                            "color": "#FF44AA",
                            "align": "center",
                        },
                        {
                            "type": "text",
                            "text": "Ken Hsu",
                            "size": "md",
                            "weight": "bold",
                            "color": "#333333",
                            "align": "center",
                        },
                        {
                            "type": "text",
                            "text": "版本: V1.2 (2025/8/28)",
                            "size": "sm",
                            "weight": "bold",
                            "wrap": True,
                            "color": "#FF4500",
                            "align": "center",
                        },
                        {
                            "type": "text",
                            "text": "(C)2025 Qunma. All Rights Reserved.",
                            "size": "sm",
                            "weight": "bold",
                            "wrap": True,
                            "color": "#4E0DE7",
                            "align": "center",
                        },
                    ],
                },
            },
        )
        line_bot_api.reply_message(event.reply_token, flex_message)
        return

    elif user_text == "?" or user_text == "？":
        flex_message = FlexSendMessage(
            alt_text="查詢指令",
            contents={
                "type": "bubble",
                "size": "mega",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "backgroundColor": "#F5F5F5",
                    "contents": [
                        {
                            "type": "image",
                            "url": "https://hsue2000.synology.me/images/qunma1.png",  # 圖片 URL (必須 HTTPS)
                            "size": "md",
                            "aspect_ratio": "1:1",
                            "aspect_mode": "cover",
                        },
                        {
                            "type": "text",
                            "text": "本機器人可使用的指令列表",
                            "weight": "bold",
                            "size": "lg",
                            "align": "center",
                        },
                        {
                            "type": "text",
                            "text": "(英文字母不分大小寫)",
                            "weight": "bold",
                            "size": "md",
                            "align": "center",
                            "color": "#FF4500",
                        },
                        {"type": "separator", "margin": "md"},
                        {
                            "type": "box",
                            "layout": "vertical",
                            "spacing": "sm",
                            "contents": [
                                {
                                    "type": "box",
                                    "layout": "baseline",
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": "♦️ 車籍 [車號]",
                                            "weight": "bold",
                                            "size": "sm",
                                            "color": "#000000",
                                            "flex": 6,
                                        },
                                        {
                                            "type": "text",
                                            "text": "模糊搜尋車籍車號",
                                            "weight": "bold",
                                            "size": "sm",
                                            "color": "#007AFF",
                                            "flex": 6,
                                            "wrap": True,
                                        },
                                    ],
                                },
                                {
                                    "type": "box",
                                    "layout": "baseline",
                                    f"contents": [
                                        {
                                            "type": "text",
                                            "text": "♦️ 車型 [關鍵字]",
                                            "weight": "bold",
                                            "size": "sm",
                                            "color": "#000000",
                                            "flex": 6,
                                        },
                                        {
                                            "type": "text",
                                            "text": "模糊搜尋車籍車型",
                                            "weight": "bold",
                                            "size": "sm",
                                            "color": "#007AFF",
                                            "flex": 6,
                                            "wrap": True,
                                        },
                                    ],
                                },
                                {
                                    "type": "box",
                                    "layout": "baseline",
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": "♦️ 電話 [關鍵字]",
                                            "weight": "bold",
                                            "size": "sm",
                                            "color": "#000000",
                                            "flex": 6,
                                        },
                                        {
                                            "type": "text",
                                            "text": "模糊搜尋車籍電話",
                                            "weight": "bold",
                                            "size": "sm",
                                            "color": "#007AFF",
                                            "flex": 6,
                                            "wrap": True,
                                        },
                                    ],
                                },
                                {
                                    "type": "box",
                                    "layout": "baseline",
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": "♦️ 備註 [關鍵字]",
                                            "weight": "bold",
                                            "size": "sm",
                                            "color": "#000000",
                                            "flex": 6,
                                        },
                                        {
                                            "type": "text",
                                            "text": "模糊搜尋車籍備註",
                                            "weight": "bold",
                                            "size": "sm",
                                            "color": "#007AFF",
                                            "flex": 6,
                                            "wrap": True,
                                        },
                                    ],
                                },
                                {
                                    "type": "box",
                                    "layout": "baseline",
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": "♦️ 今日",
                                            "weight": "bold",
                                            "size": "sm",
                                            "color": "#000000",
                                            "flex": 6,
                                        },
                                        {
                                            "type": "text",
                                            "text": "查詢今日洗車資訊",
                                            "weight": "bold",
                                            "size": "sm",
                                            "color": "#007AFF",
                                            "flex": 6,
                                            "wrap": True,
                                        },
                                    ],
                                },
                                {
                                    "type": "box",
                                    "layout": "baseline",
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": "♦️ 區間",
                                            "weight": "bold",
                                            "size": "sm",
                                            "color": "#000000",
                                            "flex": 6,
                                        },
                                        {
                                            "type": "text",
                                            "text": "查詢區間洗車資訊",
                                            "weight": "bold",
                                            "size": "sm",
                                            "color": "#007AFF",
                                            "flex": 6,
                                            "wrap": True,
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                },
            },
        )
        line_bot_api.reply_message(event.reply_token, flex_message)
        return  # 必要：避免往下繼續跑

    # 列表頁
    # ① 第一次查詢（名稱 關鍵字）
    if user_text.startswith("車籍 "):
        val = user_text.replace("車籍 ", "").strip()
        encoded = quote(val)
        api_url = f"{API_BASE_URL}?car_no={encoded}&ok=0&ser=0&like=1&token={API_TOKEN}"
        res = requests.get(api_url).json()  # 預期回傳 list[dict]

        if isinstance(res, list) and res:
            flex = build_list_page(
                res, page=1, title=f"車籍:{val}", query_cmd="車籍", query_val=val
            )
            line_bot_api.reply_message(event.reply_token, flex)
        else:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="⚠️ 查無車籍資料")
            )
        return

    # ② 翻頁（格式：列表 <類型> <值> <頁碼>）
    elif user_text.startswith("列表 "):
        parts = user_text.strip().split()  # 期待：["列表","洗車","2025-08-14","2"] 等
        if len(parts) != 4:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="⚠️ 分頁參數不足，請用：列表 洗車 2025-08-14 1"),
            )
            return  # ← 不足就直接結束

        # 確定有 4 個再解析
        _, cmd, val, page_str = parts
        try:
            page = int(page_str)
        except ValueError:
            page = 1

        # ===== A) 洗車：A_date / ok / like / token =====
        if cmd == "洗車":
            try:
                r = requests.get(
                    API_BASE_URL,
                    params={
                        "A_date": val,
                        "ok": 1,
                        "ser": 0,
                        "like": 1,
                        "token": API_TOKEN,
                    },
                    headers={"Accept": "application/json"},
                    timeout=10,
                )
            except Exception as e:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"⚠️ 查詢失敗：後端連線錯誤 {e}"),
                )
                return

            ctype = r.headers.get("Content-Type", "")
            if not r.ok or not ctype.startswith("application/json"):
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"⚠️ 查詢失敗：非 JSON 回應 ({r.status_code})"),
                )
                return

            try:
                data = r.json()
            except ValueError:
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text="⚠️ 查詢失敗：JSON 解析錯誤")
                )
                return

            if isinstance(data, dict) and data.get("error"):
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"⚠️ 查詢失敗：{data['error']}"),
                )
                return

            rows = (
                data.get("cars", [])
                if isinstance(data, dict)
                else (data if isinstance(data, list) else [])
            )
            if rows:
                flex = build_list_pageA(
                    rows,
                    page=page,
                    title=f"洗車：{data.get('query_day', val) if isinstance(data, dict) else val}",
                    query_cmd="洗車",
                    query_val=(
                        data.get("query_day", val) if isinstance(data, dict) else val
                    ),
                )
                line_bot_api.reply_message(event.reply_token, flex)
            else:
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=f"⚠️ {val} 查無資料")
                )
            return  # ← 洗車分支做完就結束，不會往下跑

        # ===== B) 其他條件：車籍/車型/電話/備註（使用對應 key）=====
        key_map = {
            "車籍": "car_no",
            "車型": "car_type",
            "電話": "tel",
            "備註": "note",
        }
        key = key_map.get(cmd)
        if not key:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="⚠️ 不支援的查詢類型!"),
            )
            return

        encoded = quote(val)
        api_url = f"{API_BASE_URL}?{key}={encoded}&ok=0&ser=0&like=1&token={API_TOKEN}"

        try:
            res = requests.get(
                api_url, headers={"Accept": "application/json"}, timeout=10
            )
        except Exception as e:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text=f"⚠️ 查詢失敗：後端連線錯誤 {e}")
            )
            return

        ctype2 = res.headers.get("Content-Type", "")
        if not res.ok or not ctype2.startswith("application/json"):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"⚠️ 查詢失敗：非 JSON 回應 ({res.status_code})"),
            )
            return

        try:
            data = res.json()
        except ValueError:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="⚠️ 查詢失敗：JSON 解析錯誤")
            )
            return

        rows = (
            data.get("cars", [])
            if isinstance(data, dict)
            else (data if isinstance(data, list) else [])
        )
        if rows:
            flex = build_list_page(
                rows,
                page=page,
                title=f"{cmd}：{val}",
                query_cmd=cmd,
                query_val=val,
            )
            line_bot_api.reply_message(event.reply_token, flex)
        else:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text=f"⚠️ {val} 查無資料")
            )
            return  # ← 其他條件分支也結束

    elif user_text.startswith(("歷史 ")):
        # ★修正：全形空白→半形，再切片
        raw = (user_text or "").replace("\u3000", " ").strip()
        parts = raw.split()

        # 期待：歷史 <查詢種類> <查詢值> [頁碼]
        if len(parts) < 3:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="格式：歷史 <查詢種類> <查詢值> [頁碼]\n例如：歷史 紀錄 AAA-111 2"
                ),
            )
            return

        query_cmd = parts[1]  # 例：紀錄
        # ★修正：頁碼可省略；若最後一段是數字當頁碼，否則預設 1
        if len(parts) >= 4 and parts[-1].isdigit():
            page = int(parts[-1])
            query_val = " ".join(parts[2:-1])  # 中間都視為查詢值（支援含空白）
        else:
            page = 1
            query_val = " ".join(parts[2:])

        # ===== 呼叫 API =====
        params = {
            "A_car_no": query_val,
            "ok": 0,
            "ser": 3,
            "like": 0,
            "token": API_TOKEN,
        }
        try:
            r = requests.get(
                API_BASE_URL,
                params=params,
                headers={"Accept": "application/json"},
                timeout=10,
            )
            r.raise_for_status()  # ★修正：補 HTTP 錯誤檢查
            rows_all = r.json()
        except requests.exceptions.RequestException as e:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text=f"⚠️ API 連線失敗：{e}")
            )
            return
        except ValueError:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="⚠️ API 回應非 JSON")
            )
            return

        # ★修正：確認 rows_all 型別並非空
        if not isinstance(rows_all, list) or not rows_all:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"⚠️ 找不到「{query_cmd} {query_val}」的歷史紀錄"),
            )
            return

        # ★修正：把正確的資料變數丟進分頁元件
        flex = build_list_pageC(
            all_rows=rows_all,
            page=page,
            title=f"歷史 {query_cmd}：{query_val}",
            query_cmd=query_cmd,
            query_val=query_val,
        )
        line_bot_api.reply_message(event.reply_token, flex)
        return

    elif user_text.startswith(("日列 ")):
        tokens = user_text.split()
        if len(tokens) < 3:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="⚠️ 參數不足")
            )
            return

        # 頁碼：抓最後一個 token；不是數字就預設 1
        try:
            page = int(tokens[-1])
            core_tokens = tokens[1:-1]  # 去掉頁碼
        except ValueError:
            page = 1
            core_tokens = tokens[1:]

        if not core_tokens:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="⚠️ 參數不足")
            )
            return

        cmd = core_tokens[0]  # e.g. "日期"
        core = " ".join(
            core_tokens[1:]
        )  # e.g. "2025-08-01,2025-08-19" 或 "2025-08-01 2025-08-19"

        # --- 解析日期（耐用版）---
        start_date = end_date = None
        dates = []  # 先初始化，避免未定義

        if "," in core:
            s, e = core.split(",", 1)
            start_date, end_date = s.strip(), e.strip()
        else:
            dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", core)
        if len(dates) >= 2:
            start_date, end_date = dates[0], dates[1]

        if not (start_date and end_date):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="⚠️ 日期參數缺少，請用：日列 日期 2025-08-01 2025-08-19 2"
                ),
            )
            return

        # 呼叫 API
        params = {
            "start_date": start_date,
            "end_date": end_date,
            "ok": 0,
            "ser": 2,
            "like": 0,
            "token": API_TOKEN,
        }
        r = requests.get(
            API_BASE_URL,
            params=params,
            headers={"Accept": "application/json"},
            timeout=10,
        )
        try:
            rows_all = r.json()
        except Exception:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="⚠️ API 回應非 JSON")
            )
            return

        if not isinstance(rows_all, list) or not rows_all:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="⚠️ 查無日期資料")
            )
            return

        # 用「逗號」回填 query_val，之後上下頁都用同一格式，不會再被空白切裂
        flex_msg = build_list_pageB(
            all_rows=rows_all,
            page=page,
            title=f"{start_date} ~ {end_date}",
            query_cmd="日期",
            query_val=f"{start_date},{end_date}",
        )
        line_bot_api.reply_message(event.reply_token, flex_msg)
        return

    elif user_text.startswith("車型 "):
        val = user_text.replace("車型 ", "").strip()
        encoded = quote(val)
        api_url = (
            f"{API_BASE_URL}?car_type={encoded}&ok=0&ser=0&like=1&token={API_TOKEN}"
        )
        res = requests.get(api_url).json()  # 預期回傳 list[dict]

        if isinstance(res, list) and res:
            flex = build_list_page(
                res, page=1, title=f"車型：{val}", query_cmd="車型", query_val=val
            )
            line_bot_api.reply_message(event.reply_token, flex)
        else:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="⚠️ 查無車型資料")
            )
        return

    elif user_text.startswith("電話 "):
        val = user_text.replace("電話 ", "").strip()
        encoded = quote(val)
        api_url = f"{API_BASE_URL}?tel={encoded}&ok=0&ser=0&like=1&token={API_TOKEN}"
        res = requests.get(api_url).json()  # 預期回傳 list[dict]

        if isinstance(res, list) and res:
            flex = build_list_page(
                res, page=1, title=f"電話：{val}", query_cmd="電話", query_val=val
            )
            line_bot_api.reply_message(event.reply_token, flex)
        else:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="⚠️ 查無電話資料")
            )
        return

    elif user_text.startswith("備註 "):
        val = user_text.replace("備註 ", "").strip()
        encoded = quote(val)
        api_url = f"{API_BASE_URL}?note={encoded}&ok=0&ser=0&like=1&token={API_TOKEN}"
        res = requests.get(api_url).json()  # 預期回傳 list[dict]

        if isinstance(res, list) and res:
            flex = build_list_page(
                res, page=1, title=f"備註：{val}", query_cmd="備註", query_val=val
            )
            line_bot_api.reply_message(event.reply_token, flex)
        else:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="⚠️ 查無備註資料")
            )
        return

    elif user_text.startswith("紀錄 "):
        val = user_text.replace("紀錄 ", "").strip()
        encoded = quote(val)
        api_url = (
            f"{API_BASE_URL}?A_car_no={encoded}&ok=0&ser=3&like=0&token={API_TOKEN}"
        )
        res = requests.get(api_url).json()  # 預期回傳 list[dict]

        if isinstance(res, list) and res:
            flex = build_list_pageC(
                res, page=1, title=f"紀錄：{val}", query_cmd="紀錄", query_val=val
            )
            line_bot_api.reply_message(event.reply_token, flex)
        else:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="⚠️ 查無洗車紀錄")
            )
        return

    elif user_text.startswith("今日") or user_text.startswith("其他日 "):

        if user_text.startswith("今日"):
            # 1) 取得今日日期 (YYYY-MM-DD)，這裡時區計算皆可換成「台灣時區」版本
            taiwan_tz = timezone("Asia/Taipei")
            today_str = datetime.datetime.now(taiwan_tz).strftime("%Y-%m-%d")
            # today_str = "2025-08-08"
        elif user_text.startswith("其他日 "):
            today_str = user_text.replace("其他日 ", "").strip()

        # 2) 呼叫 PHP API（你的 PHP 是用 ?day=YYYY-MM-DD）
        #    用 params 比自己串 query string 更安全
        try:
            r = requests.get(
                API_BASE_URL,  # e.g. "https://your.domain/Qsearch.php"
                params={
                    "A_date": today_str,  # 原本 encoded 後的日期
                    "ok": 1,  # 原本 ?ok=1
                    "ser": 0,
                    "like": 1,  # 原本 &like=1
                    "token": API_TOKEN,  # 原本 &token=...
                },
                headers={
                    "Accept": "application/json",
                    # 如果 API 驗證不是用 HTTP Header，就可以刪掉這行
                    "Authorization": f"Bearer {API_TOKEN}",
                },
                timeout=10,
            )
        except Exception as e:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text=f"⚠️ 查詢失敗：後端連線錯誤 {e}")
            )
            return

        # 3) 確認回傳是 JSON
        ctype = r.headers.get("Content-Type", "")

        if not r.ok or not ctype.startswith("application/json"):
            preview = (r.text or "")[:160]
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=f"查詢失敗：非 JSON 回應 ({r.status_code})\n{preview}"
                ),
            )
            return

        # 4) 解析 JSON（格式：{"query_day": "...", "count": N, "cars": [...] }）
        try:
            data = r.json()
        except ValueError:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text=f"⚠️ 查詢失敗：JSON 解析錯誤")
            )
            return

        # 5) 取出 cars 陣列
        rows = data.get("cars", [])

        # ★修改：先決定原始日期字串與格式化後字串
        query_day_raw = data.get("query_day") or today_str  # e.g. "2025-08-24"
        query_day_fmt = format_date_with_weekday(query_day_raw)  # e.g. "2025-08-24(日)"

        if rows:
            flex = build_list_pageA(
                rows,
                page=1,
                title=f"洗車日期：{query_day_fmt}",  # ★修改：顯示帶星期
                query_cmd="洗車",
                query_val=query_day_raw,  # ★修改：建議把原始日期往下傳（之後好再運算）
            )
            line_bot_api.reply_message(event.reply_token, flex)
        else:
            # 統一套上星期幾
            text = f"⚠️ {query_day_fmt} 查無洗車資料"  # ★修改：顯示帶星期

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=text),
            )
        return

    elif user_text.startswith("車號 "):

        serial_no = user_text.replace("車號 ", "").strip()
        api_url = (
            f"{API_BASE_URL}?car_no={serial_no}&ok=0&ser=0&like=0&token={API_TOKEN}"
        )
        res = requests.get(api_url).json()
        if isinstance(res, list) and res:
            flex_msg = build_detail_flex(res[0])
            line_bot_api.reply_message(event.reply_token, flex_msg)
        else:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="⚠️ 查無車號資料")
            )
            return

    elif user_text.startswith("日期 "):
        content = user_text.replace("日期 ", "", 1).strip()
        parts = content.split()  # 期望: ["2025-08-01", "2025-09-01"]

        # 檢查兩個日期都有
        if len(parts) < 2:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="⚠️ 用法：日期 2025-08-01 2025-09-01"),
            )
            return

        start_date, end_date = parts[0], parts[1]

        # （可選）基本格式檢查 YYYY-MM-DD
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", start_date) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}", end_date
        ):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="日期格式錯誤，請用 YYYY-MM-DD，例如：日期 2025-08-01 2025-09-01"
                ),
            )
            return

        # 呼叫 API（建議用 params）
        params = {
            "start_date": start_date,
            "end_date": end_date,
            "ok": 0,
            "ser": 2,
            "like": 0,
            "token": API_TOKEN,
        }
        r = requests.get(
            API_BASE_URL,
            params=params,
            headers={"Accept": "application/json"},
            timeout=10,
        )

        # 先看原始字串除錯（需要時打開）
        # print(r.url); print(r.text)

        # 解析 JSON
        try:
            res = r.json()
        except Exception:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="⚠️ API 回應非 JSON")
            )
            return

        # 期待 API 回傳是 list，例如：[{ "day": "2025-08-01", "cnt": 3 }, ...]
        if isinstance(res, list) and len(res) > 0:
            # 第 1 頁
            flex_msg = build_list_pageB(
                all_rows=res,
                page=1,
                title=f"{start_date} ~ {end_date}",
                query_cmd="日期",
                query_val=f"{start_date} {end_date}",
            )
            line_bot_api.reply_message(event.reply_token, flex_msg)
            return

    elif user_text == "區間":
        # 可以直接給個空 keyword 或預設值
        keyword = "未指定"

        # 呼叫你寫好的 build_date_picker_bubble
        msg = build_date_picker_bubble(keyword=keyword, start=None, end=None)

        line_bot_api.reply_message(event.reply_token, msg)

    elif user_text.startswith("服務 "):
        content = user_text.replace("服務 ", "").strip()
        parts = content.split()  # ["AAA-111", "2025-08-23"]

        serial_no = parts[0]  # 取第一個欄位 → "AAA-111"
        date_str = parts[1] if len(parts) > 1 else None  # 取第二個欄位 → "2025-08-23"

        # ① 車籍
        r1 = requests.get(
            f"{API_BASE_URL}?car_no={serial_no}&ok=0&ser=0&like=1&token={API_TOKEN}",
            headers={"Accept": "application/json"},
            timeout=10,
        )
        res1 = r1.json()

        # ② 洗車
        r2 = requests.get(
            f"{API_BASE_URL}?A_car_no={serial_no}&A_date={date_str}&ok=0&ser=1&like=0&token={API_TOKEN}",
            headers={"Accept": "application/json"},
            timeout=10,
        )
        res2 = r2.json()

        # --- 正規化：把 res1 -> car_dict, res2 -> washes_list ---
        def _first_dict(x):
            if isinstance(x, dict):
                return x
            if isinstance(x, list):
                for it in x:
                    if isinstance(it, dict):
                        return it
            return {}

        def _as_wash_list(x):
            # 允許 list[dict] 或單一 dict；其他情況給空陣列
            if isinstance(x, list):
                return [it for it in x if isinstance(it, dict)]
            if isinstance(x, dict):
                return [x]
            return []

        car_dict = _first_dict(res1)  # 車籍只取第一筆
        washes_list = _as_wash_list(res2)  # 洗車可多筆

        # 沒任一資料就回覆
        if not car_dict and not washes_list:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="⚠️ 查無服務資料")
            )
            return

        # ✅ 若洗車沒資料就直接回文字，不進 Flex
        if not washes_list:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="⚠️ 查無洗車資料")
            )
            return

        # ③ 丟進 Flex builder（注意新的參數）
        flex_msg = build_detail_flexA(car_dict, washes_list)
        line_bot_api.reply_message(event.reply_token, flex_msg)
        return

    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"⚠️ 指令錯誤,請重新輸入!"),
        )
        return


if __name__ == "__main__":
    app.run(port=5000)
