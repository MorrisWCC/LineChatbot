from flask import Flask, request, abort
import time
import requests
import os
import psycopg2
from multiprocessing import Process, Manager
import notification
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

LINE_BOT_API = LineBotApi('')
HANDLER = WebhookHandler('')

REGISTERED_USERS = Manager().list()
FIVE_MINS_AS_SECOND = 300

@app.route("/wakeup", methods=['GET'])
def wakeup():
    return "I need work"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        HANDLER.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@HANDLER.add(MessageEvent, message=TextMessage)
def handle_message(event):
    if event.source.user_id in REGISTERED_USERS:
        LINE_BOT_API.reply_message(event.reply_token,
                                   TextSendMessage(text="註冊過囉"))
    else:
        insert_into_database(event.source.user_id)
        REGISTERED_USERS.append(event.source.user_id)
        LINE_BOT_API.reply_message(event.reply_token,
                                   TextSendMessage(text="註冊完成"))

def send_msg(reg_list):
    while True:
        requests.get('https://pttnotification.herokuapp.com/wakeup')
        notification.start(reg_list)
        time.sleep(FIVE_MINS_AS_SECOND)

def insert_into_database(user_id):
    database_url = os.environ['DATABASE_URL']
    conn = psycopg2.connect(database_url, sslmode='require')
    cur = conn.cursor()
    sql = "insert into users (user_id) values (\'"+user_id+"\')"
    cur.execute(sql)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    database_url = os.environ['DATABASE_URL']
    conn = psycopg2.connect(database_url, sslmode='require')
    cur = conn.cursor()
    cur.execute("select * from users")
    rows = cur.fetchall()
    for row in rows:
        user = row[0]
        REGISTERED_USERS.append(user)
    conn.close()

    p = Process(target=send_msg, args=(REGISTERED_USERS,))
    p.start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 17995)))
