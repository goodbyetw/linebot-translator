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

# 載入環境變數
load_dotenv()

# 初始化 Flask 與 LINE Bot
app = Flask(__name__)
configuration = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
messaging_api = MessagingApi(configuration)
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# Google Translate API Key
GOOGLE_API_KEY = os.getenv("GOOGLE_TRANSLATE_API_KEY")

# 偵測語言
def detect_language(text):
    url = "https://translation.googleapis.com/language/translate/v2/detect"
    params = {
        "q": text,
        "key": GOOGLE_API_KEY
    }
    response = requests.post(url, data=params)
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
    response = requests.post(url, data=params)
    return response.json()['data']['translations'][0]['translatedText']

# Webhook 路由
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

# 處理訊息事件
@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    user_msg = event.message.text
    source_lang = detect_language(user_msg)

    if source_lang == "zh-TW":
        target_lang = "id"
    elif source_lang == "id":
        target_lang = "zh-TW"
    else:
        # 若不是印尼文或中文就不翻譯
        return

    translated = translate_text(user_msg, target_lang)

    messaging_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=translated)]
        )
    )

# 伺服器啟動
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

