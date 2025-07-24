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
    if response.status_code != 200:
        logging.error(f"[Detect Error] {response.status_code} - {response.text}")
        return None
    lang = response.json()['data']['detections'][0][0]['language']
    logging.info(f"Detected language: {lang}")
    return lang

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
    if response.status_code != 200:
        logging.error(f"[Translate Error] {response.status_code} - {response.text}")
        return None
    translated = response.json()['data']['translations'][0]['translatedText']
    logging.info(f"Translated text: {translated}")
    return translated

# Webhook 路由
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    logging.info(f"[Webhook] Received body: {body}")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logging.warning("Invalid signature.")
        abort(400)

    return "OK"

# 處理文字訊息事件
@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    user_msg = event.message.text
    logging.info(f"[User Message] {user_msg}")

    source_lang = detect_language(user_msg)
    if not source_lang:
        return

    if source_lang.startswith("zh"):
        target_lang = "id"
    elif source_lang in ["id", "ms"]:
        target_lang = "zh-TW"
    else:
        logging.info(f"No translation performed for language: {source_lang}")
        return

    translated = translate_text(user_msg, target_lang)
    if not translated:
        return

    # 發送回應
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
