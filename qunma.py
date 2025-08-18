from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import requests

import os
import requests
from urllib.parse import quote
from linebot.models import TextSendMessage, FlexSendMessage

from linebot.models import (
    TextSendMessage,
    FlexSendMessage,
    QuickReply,
    QuickReplyButton,
    MessageAction,
)

import requests
from linebot.models import FlexSendMessage

from datetime import datetime
from urllib.parse import quote

session_store = {}  # { user_id: { "last_results": [...] } }


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

    # ===== 欄位 rows =====
    rows = []
    for k in allowed_fields:
        val_raw = data_dict.get(k, "")

        # 只在電話欄位做 10 碼格式化（你也可依實際欄位名稱調整）
        if k in ("tel"):
            val = format_phone(val_raw)
        else:
            val = val_raw

        if str(val).strip():
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
                            "text": str(val),
                            "size": "md",
                            "color": value_color,
                            "wrap": True,
                            "flex": 7,
                            "align": "start",  # ✅ 靠左
                        },
                    ],
                }
            )

    # ===== Flex bubble =====
    bubble = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
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
        "A_item",
        "A_date",
        "A_ord_time",
        "A_time",
        "A_money",
        "A_status",
        "A_note",
        "washes_total",
        "washes_pass",
        "washes_fail",
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
        "A_item": "服務項目",
        "A_date": "預約日期",
        "A_time": "交車時間",
        "A_ord_time": "預約時間",
        "A_money": "金額",
        "A_status": "狀態",
        "A_note": "洗車備註",
        "washes_total": "累計洗車",
        "washes_pass": "已完成",
        "washes_fail": "未完成",
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
    rows_washed = []
    if washes:
        for idx, w in enumerate(washes, start=1):

            for k in allowed_wash_fields:
                val = w.get(k, "")

                # 預設顏色從 FIELD_COLOR_MAP 取，沒有就給藍色
                val_color = FIELD_COLOR_MAP.get(k, "#0000FF")

                # 動態決定顏色
                if k == "A_status":
                    if val == "已完成":
                        val = val + "✅"
                        val_color = "#9400D3"  # 紫色
                    else:
                        val = val + "❌"
                        val_color = "#FF8C00"  # 橘色

                if safe_text(val):
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
                                    "text": safe_text(val),
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

    # ===== Flex bubble =====
    bubble = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
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
                            "gravity": "center",  # 讓文字跟圖片上下置中
                        },
                        {
                            "type": "image",
                            "url": pic_url,
                            "size": "xs",
                            "aspectMode": "fit",
                            "align": "end",  # 圖片靠右
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
                {
                    "type": "box",
                    "layout": "vertical",
                    "height": "12px",  # 你要的空白高度
                },
                {"type": "separator", "margin": "md"},
                {
                    "type": "text",
                    "text": "<今日洗車>",
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
# 從 Vercel 的環境變數讀取
whitelist_str = os.getenv("LINE_WHITELIST", "")

# 轉成 set（自動去除空白）
whitelist = {uid.strip() for uid in whitelist_str.split(",") if uid.strip()}
# print(whitelist)

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
            "text": f"{title} (第{page}/{total_pages}頁)",
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
                "backgroundColor": "#FFFFBB" if idx % 2 == 0 else "#BBFFEE",
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
                    "label": "上一頁",
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
                    "label": "下一頁",
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
                "flex": 3,
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
                "flex": 4,
                "align": "center",
                "wrap": True,
            },
            {
                "type": "text",
                "text": "預約",
                "size": "xs",
                "weight": "bold",
                "flex": 2,
                "align": "center",
                "wrap": True,
            },
        ],
    }

    body = [
        {
            "type": "text",
            "text": f"{title} (第{page}/{total_pages}頁)",
            "weight": "bold",
            "size": "md",
            "align": "center",
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
        a_ord_time = safe_text(w.get("A_ord_time", ""))
        a_status = safe_text(w.get("A_status", ""))

        if a_status == "已完成":
            a_item = a_item + "✅"
        else:
            a_item = a_item + "❌"

        body.append(
            {
                "type": "box",
                "layout": "horizontal",
                "spacing": "sm",
                "backgroundColor": "#FFFFBB" if idx % 2 == 0 else "#BBFFEE",
                "contents": [
                    {
                        "type": "text",
                        "text": car_no,
                        "size": "sm",
                        "flex": 3,
                        "wrap": True,
                        "align": "center",
                    },
                    {
                        "type": "text",
                        "text": name,
                        "size": "sm",
                        "flex": 3,
                        "wrap": True,
                        "align": "center",
                    },
                    {
                        "type": "text",
                        "text": a_item,
                        "size": "xs",
                        "flex": 4,
                        "wrap": True,
                        "align": "center",
                    },
                    {
                        "type": "text",
                        "text": f"{a_ord_time}".strip(),
                        "size": "sm",
                        "flex": 2,
                        "wrap": True,
                        "align": "center",
                    },
                ],
                "action": {
                    "type": "message",
                    "label": "查詢詳情",
                    "text": f"{row_action_prefix} {car_no}",  # 例如：「車號 AAA-0000」
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
                    "label": "上一頁",
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
                    "label": "下一頁",
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
    return FlexSendMessage(alt_text="查詢今日洗車列表", contents=bubble)


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


from linebot.models import QuickReply, QuickReplyButton, MessageAction, TextSendMessage

import requests


@SECRET.add(MessageEvent, TextMessage)
def handle_message(event):

    # 讀取用戶的ID
    user_id = event.source.user_id
    # print("發訊息的用戶 ID:", user_id)

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
                            "text": "版本: V1.0 (2025/8/17)",
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
                                            "text": "♦️ 車號 [車號]",
                                            "weight": "bold",
                                            "size": "sm",
                                            "color": "#000000",
                                            "flex": 6,
                                        },
                                        {
                                            "type": "text",
                                            "text": "查詢車籍車號",
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
                                            "text": "♦️ 關於",
                                            "weight": "bold",
                                            "size": "sm",
                                            "color": "#000000",
                                            "flex": 6,
                                        },
                                        {
                                            "type": "text",
                                            "text": "作者資訊",
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
                                            "text": "♦️ ? 或 ？",
                                            "weight": "bold",
                                            "size": "sm",
                                            "color": "#000000",
                                            "flex": 6,
                                        },
                                        {
                                            "type": "text",
                                            "text": "顯示本指令列表",
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
                event.reply_token, TextSendMessage(text="查無車籍資料")
            )
        return

    # ② 翻頁（格式：列表 <類型> <值> <頁碼>）
    elif user_text.startswith("列表 "):
        parts = user_text.strip().split()  # 期待：["列表","洗車","2025-08-14","2"] 等
        if len(parts) != 4:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="分頁參數不足，請用：列表 洗車 2025-08-14 1"),
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
                    params={"A_date": val, "ok": 1, "like": 1, "token": API_TOKEN},
                    headers={"Accept": "application/json"},
                    timeout=10,
                )
            except Exception as e:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"查詢失敗：後端連線錯誤 {e}"),
                )
                return

            ctype = r.headers.get("Content-Type", "")
            if not r.ok or not ctype.startswith("application/json"):
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"查詢失敗：非 JSON 回應 ({r.status_code})"),
                )
                return

            try:
                data = r.json()
            except ValueError:
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text="查詢失敗：JSON 解析錯誤")
                )
                return

            if isinstance(data, dict) and data.get("error"):
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"查詢失敗：{data['error']}"),
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
                    event.reply_token, TextSendMessage(text=f"{val} 查無資料")
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
                TextSendMessage(text="不支援的查詢類型!"),
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
                event.reply_token, TextSendMessage(text=f"查詢失敗：後端連線錯誤 {e}")
            )
            return

        ctype2 = res.headers.get("Content-Type", "")
        if not res.ok or not ctype2.startswith("application/json"):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"查詢失敗：非 JSON 回應 ({res.status_code})"),
            )
            return

        try:
            data = res.json()
        except ValueError:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="查詢失敗：JSON 解析錯誤")
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
                event.reply_token, TextSendMessage(text=f"{val} 查無資料")
            )
            return  # ← 其他條件分支也結束

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
                event.reply_token, TextSendMessage(text="查無車型資料")
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
                event.reply_token, TextSendMessage(text="查無電話資料")
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
                event.reply_token, TextSendMessage(text="查無備註資料")
            )
        return

    elif user_text.strip() == "今日":
        # 取得今日日期 (YYYY/MM/DD)
        from datetime import datetime
        import pytz

        # 1) 取得今日日期 (YYYY-MM-DD)，這裡時區計算皆可換成「台灣時區」版本
        taiwan_tz = pytz.timezone("Asia/Taipei")
        today_str = datetime.now(taiwan_tz).strftime("%Y-%m-%d")

        # today_str = "2025-08-16"

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
                event.reply_token, TextSendMessage(text=f"查詢失敗：後端連線錯誤 {e}")
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
                event.reply_token, TextSendMessage(text=f"查詢失敗：JSON 解析錯誤")
            )
            return

        # 5) 取出 cars 陣列
        rows = data.get("cars", [])

        if rows:
            flex = build_list_pageA(
                rows,
                page=1,
                title=f"今日洗車：{data.get('query_day', today_str)}",
                query_cmd="洗車",
                query_val=today_str,
            )
            line_bot_api.reply_message(event.reply_token, flex)
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=f"{data.get('query_day', today_str)} 查無洗車資料"
                ),
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
                event.reply_token, TextSendMessage(text="查無車號資料")
            )
            return
    elif user_text.startswith("服務 "):
        serial_no = user_text.replace("服務 ", "").strip()
        # ① 車籍
        r1 = requests.get(
            f"{API_BASE_URL}?car_no={serial_no}&ok=0&ser=0&like=1&token={API_TOKEN}",
            headers={"Accept": "application/json"},
            timeout=10,
        )
        res1 = r1.json()

        # ② 洗車
        r2 = requests.get(
            f"{API_BASE_URL}?A_car_no={serial_no}&ok=0&ser=1&like=1&token={API_TOKEN}",
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
                event.reply_token, TextSendMessage(text="查無服務資料")
            )
            return

        # ✅ 若洗車沒資料就直接回文字，不進 Flex
        if not washes_list:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="查無資料")
            )
            return

        # ③ 丟進 Flex builder（注意新的參數）
        flex_msg = build_detail_flexA(car_dict, washes_list)
        line_bot_api.reply_message(event.reply_token, flex_msg)
        return

    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"❌ 指令錯誤!"),
        )
        return


if __name__ == "__main__":
    app.run(port=5000)




