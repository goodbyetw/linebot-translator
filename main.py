from flask import Flask, request, abort
from dotenv import load_dotenv
import os
import logging
import requests

from linebot.v3.webhook import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import MessagingApi, Configuration
from linebot.v3.messaging.models import TextMessage, ReplyMessageRequest
from linebot.v3.webhooks import MessageEvent, TextMessageContent

# 載入 .env
load_dotenv()

# 初始化 Flask 與 LINE
app = Flask(__name__)
configuration = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
messaging_api = MessagingApi(configuration)
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# 讀取 Google Translate API 金鑰
GOOGLE_API_KEY = os.getenv("GOOGLE_TRANSLATE_API_KEY")

# 偵測語言（使用 GET 並帶上 key）
def detect_language(text):
    url = "https://translation.googleapis.com/language/translate/v2/detect"
    params = {
        "q": text,
        "key": GOOGLE_API_KEY
    }
    response = requests.get(url, params=params)
    logging.info("[Detect Result] %s", response.text)
    if response.status_code != 200:
        logging.error("[Detect Error] %d - %s", response.status_code, response.text)
        return None
    return response.json()['data']['detections'][0][0]['language']

# 翻譯文字
def translate_text(text, target_lang):
    url = "https://translation.googleapis.com/language/translate/v2"
    params = {
        "q": text,
        "target": target_lang,
        "format": "text",
        "key": GOOGLE_API_KEY
    }
    response = requests.get(url, params=params)
    logging.info("[Translate Result] %s", response.text)
    if response.status_code != 200:
        logging.error("[Translate Error] %d - %s", response.status_code, response.text)
        return None
    return response.json()['data']['translations'][0]['translatedText']

# Webhook 路由
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    logging.info("[Request Body] %s", body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

# 處理文字訊息
@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    user_msg = event.message.text
    logging.info("[User Message] %s", user_msg)

    source_lang = detect_language(user_msg)
    if not source_lang:
        return

    # 翻譯邏輯
    if source_lang == "zh-TW":
        target_lang = "id"
    elif source_lang == "id":
        target_lang = "zh-TW"
    else:
        logging.info("[Skipped] Not zh-TW or id: %s", source_lang)
        return

    translated = translate_text(user_msg, target_lang)
    if translated:
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=translated)]
            )
        )

# 啟動伺服器
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
