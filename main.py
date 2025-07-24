from flask import Flask, request, abort
from dotenv import load_dotenv
import os
import logging

from linebot.v3.webhook import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import MessagingApi, Configuration
from linebot.v3.messaging.models import TextMessage, ReplyMessageRequest
from linebot.v3.webhooks import MessageEvent, TextMessageContent

# 載入 .env 環境變數（本地測試用）
load_dotenv()

# 初始化 Flask App
app = Flask(__name__)

# 設定 LINE Messaging API
configuration = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
messaging_api = MessagingApi(configuration)
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# Webhook 接收入口
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

# 接收文字訊息事件
@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    user_msg = event.message.text
    reply_msg = f"你剛說了：{user_msg}"

    messaging_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=reply_msg)]
        )
    )

# 啟動伺服器（支援 Render 自動指定 PORT）
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    port = int(os.environ.get("PORT", 5000))  # Render 會提供 PORT 環境變數
    app.run(host="0.0.0.0", port=port)
