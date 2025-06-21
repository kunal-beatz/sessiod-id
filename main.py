import time
import requests
import json
import os
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
BOT_URL = f'https://api.telegram.org/bot{BOT_TOKEN}'
user_states = {}
bot_stats = {"users": set(), "notified_users": set()}

def send_message(chat_id, text, reply_markup=None, parse_mode=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    if parse_mode:
        payload["parse_mode"] = parse_mode
    requests.post(f"{BOT_URL}/sendMessage", json=payload)

def send_photo(chat_id, photo_url, caption, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    requests.post(f"{BOT_URL}/sendPhoto", json=payload)

def get_updates(offset=None):
    params = {"timeout": 100}
    if offset:
        params["offset"] = offset
    return requests.get(f"{BOT_URL}/getUpdates", params=params).json()

def insta_login(username, password):
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.instagram.com/accounts/login/",
        "Accept-Language": "en-US,en;q=0.9"
    })
    try:
        start_time = time.time()
        session.get("https://www.instagram.com/accounts/login/")
        csrf_token = session.cookies.get_dict().get('csrftoken')
        if not csrf_token:
            return None, 0

        enc_password = f"#PWD_INSTAGRAM_BROWSER:0:{int(time.time())}:{password}"
        payload = {
            "username": username,
            "enc_password": enc_password,
            "queryParams": "{}",
            "optIntoOneTap": "false"
        }
        session.headers.update({
            "X-CSRFToken": csrf_token,
            "Content-Type": "application/x-www-form-urlencoded"
        })
        login_resp = session.post("https://www.instagram.com/api/v1/web/accounts/login/ajax/", data=payload)
        data = login_resp.json()
        elapsed = round(time.time() - start_time, 2)
        if data.get("authenticated"):
            return session.cookies.get_dict().get("sessionid"), elapsed
        return None, elapsed
    except:
        return None, 0

def notify_admin_new_user(user):
    if user['id'] not in bot_stats['notified_users']:
        first = user.get('first_name', '')
        last = user.get('last_name', '')
        name = f"{first} {last}".strip()
        username = user.get('username', 'N/A')
        user_id = user['id']
        time_str = time.strftime('%Y-%m-%d %H:%M:%S')
        total = len(bot_stats["users"])

        msg = (
            "📢 *New User Alert!*\n\n"
            f"👤 Name: {name}\n"
            f"🔗 Username: @{username}\n"
            f"🆔 User ID: `{user_id}`\n"
            f"🕒 Time: {time_str}\n"
            f"👥 Total Users: {total}"
        )

        send_message(ADMIN_ID, msg, parse_mode="Markdown")
        bot_stats['notified_users'].add(user_id)

def process_message(message):
    chat_id = message['chat']['id']
    text = message.get('text')
    user = message['from']
    user_name = user.get('first_name', 'Unknown')
    bot_stats["users"].add(chat_id)

    notify_admin_new_user(user)

    if text == "/start":
        send_photo(
            chat_id,
            photo_url="https://i.ibb.co/pjyb2LKR/ziddi.jpg",
            caption="*Welcome to Meta Session Bot\nGet your Instagram Session ID easily!*",
            reply_markup={
                "inline_keyboard": [
                    [
                        {"text": "👨‍💻 Developer", "url": "https://t.me/nobi_shops"},
                        {"text": "📢 Channel", "url": "https://t.me/meta_server"}
                    ],
                    [
                        {"text": "🔑 Get Session ID", "callback_data": "get_session"}
                    ]
                ]
            }
        )

    elif chat_id in user_states:
        step = user_states[chat_id].get("step")

        if step == "username":
            user_states[chat_id]["username"] = text
            user_states[chat_id]["step"] = "password"
            send_message(chat_id, "🔐 Enter your Instagram password:")

        elif step == "password":
            username = user_states[chat_id]["username"]
            password = text
            send_message(chat_id, "🧠 Processing login... please wait")
            session_id, taken = insta_login(username, password)
            if session_id:
                send_message(
                    chat_id,
                    f"✅ *Login Successful!*\n\n"
                    f"*Your Session ID:* `{session_id}`\n"
                    f"👤 *Requested by:* {user_name}\n"
                    f"⏱️ *Time Taken:* {taken}s\n\n"
                    f"_By Meta Server_",
                    parse_mode="Markdown"
                )
            else:
                send_message(chat_id, "❌ Login Failed. Invalid credentials or blocked by Instagram.")
            del user_states[chat_id]

    elif text == "/stats" and chat_id == ADMIN_ID:
        send_message(chat_id, f"📊 Total Users: {len(bot_stats['users'])}")

    elif text and text.startswith("/broadcast ") and chat_id == ADMIN_ID:
        msg = text.split(" ", 1)[1]
        for uid in bot_stats['users']:
            send_message(uid, f"📢 *Broadcast:*\n\n{msg}", parse_mode="Markdown")
        send_message(chat_id, "✅ Broadcast Sent!")
    else:
        send_message(chat_id, "❗ Use /start to begin.")

def process_callback(callback):
    chat_id = callback['message']['chat']['id']
    data = callback['data']

    if data == "get_session":
        user_states[chat_id] = {"step": "username"}
        send_message(chat_id, "👤 Enter your Instagram username:")

def main():
    offset = None
    print("🤖 Bot Running on Railway...")
    while True:
        updates = get_updates(offset)
        if updates.get("ok"):
            for result in updates["result"]:
                offset = result["update_id"] + 1
                if "message" in result:
                    process_message(result["message"])
                elif "callback_query" in result:
                    process_callback(result["callback_query"])

if __name__ == '__main__':
    main()
