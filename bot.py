import re
import telebot
import json
import time
import threading
import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 8201189040

bot = telebot.TeleBot(BOT_TOKEN)

# ===== MENU =====
user_commands = [
    BotCommand("start", "Start bot"),
    BotCommand("help", "Help")
]

admin_commands = [
    BotCommand("add", "Add data"),
    BotCommand("delete", "Delete data"),
    BotCommand("list", "List IDs"),
    BotCommand("status", "Check stats")
]

bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())
bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=ADMIN_ID))

# ===== DATA =====
def load(file):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except:
        return {}

def save(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

DATA = load("data.json")
STATS = load("stats.json")

WAITING_FOR_ORDER = {}

# ===== START =====
@bot.message_handler(commands=['start'])
def start(msg):
    bot.reply_to(msg, "Hi 👋\nSend me any deal ID.")

# ===== HELP =====
@bot.message_handler(commands=['help'])
def help_cmd(msg):
    bot.reply_to(msg, "Need help?\nContact: @Shivansh_raj")

# ===== ADD =====
@bot.message_handler(commands=['add'])
def add(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        parts = msg.text.split("\n", 1)
        deal_id = parts[0].split()[1].upper()
        DATA[deal_id] = parts[1]
        save("data.json", DATA)
        bot.reply_to(msg, f"✅ Saved {deal_id}")
    except:
        bot.reply_to(msg, "❌ Use:\n/add EF123\nYour data")

# ===== DELETE =====
@bot.message_handler(commands=['delete'])
def delete(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        deal_id = msg.text.split()[1].upper()
        DATA.pop(deal_id, None)
        save("data.json", DATA)
        bot.reply_to(msg, f"🗑 Deleted {deal_id}")
    except:
        bot.reply_to(msg, "❌ Use /delete EF123")

# ===== LIST =====
@bot.message_handler(commands=['list'])
def list_cmd(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    bot.reply_to(msg, "\n".join(DATA.keys()) or "No data")

# ===== STATUS =====
@bot.message_handler(commands=['status'])
def status(msg):
    if msg.from_user.id != ADMIN_ID:
        return

    args = msg.text.split(maxsplit=1)

    if len(args) == 1:
        out = "📊 All Deals:\n\n"
        for k, v in STATS.items():
            out += f"{k} → {len(v.get('order_ids', []))} orders\n"
        bot.reply_to(msg, out)
        return

    deal = args[1].upper()

    if deal not in STATS:
        bot.reply_to(msg, "❌ No data")
        return

    v = STATS[deal]

    out = f"📊 {deal}\n\n"
    out += f"👁 Requests: {v.get('requests',0)}\n"
    out += f"🛒 Purchased: {len(v.get('purchased',[]))}\n"
    out += f"🧾 Orders: {len(v.get('order_ids',[]))}\n\n"

    if v.get("order_ids"):
        out += "📦 Order IDs:\n"
        for o in v["order_ids"]:
            out += f"• {o['order_id']}\n"
    else:
        out += "No order IDs yet"

    bot.reply_to(msg, out)

# ===== FOLLOW-UP =====
def follow_up(chat_id, deal_id, reply_id):
    time.sleep(60)

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("Yes", callback_data=f"yes_{deal_id}"),
        InlineKeyboardButton("No", callback_data=f"no_{deal_id}")
    )

    bot.send_message(
        chat_id,
        f"Did you purchase this product? ({deal_id})",
        reply_markup=kb,
        reply_to_message_id=reply_id
    )

# ===== BUTTONS =====
@bot.callback_query_handler(func=lambda c: True)
def buttons(call):
    uid = call.from_user.id
    deal = call.data.split("_")[1]

    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

    if deal not in STATS:
        STATS[deal] = {"requests":0,"purchased":[],"order_ids":[]}

    if call.data.startswith("yes_"):

        if uid in WAITING_FOR_ORDER:
            return

        if uid not in STATS[deal]["purchased"]:
            STATS[deal]["purchased"].append(uid)

        WAITING_FOR_ORDER[uid] = deal
        save("stats.json", STATS)

        bot.send_message(
            call.message.chat.id,
            f"Please send your Order ID for {deal}"
        )

    else:
        bot.send_message(call.message.chat.id, "Thanks 🙌")

# ===== ORDER CAPTURE =====
@bot.message_handler(func=lambda m: m.from_user.id in WAITING_FOR_ORDER)
def capture(msg):
    uid = msg.from_user.id
    deal = WAITING_FOR_ORDER.get(uid)

    if not deal:
        return

    text = msg.text.strip()

    # 👉 If user sends another deal ID → exit order mode
    if text.upper() in DATA:
        WAITING_FOR_ORDER.pop(uid, None)
        return

    # clean input
    order = re.sub(r"\s+", "", text)

    # ✅ VALID ORDER ID
    if re.fullmatch(r"\d{3}-\d{7}-\d{7}", order):

        # duplicate check
        for o in STATS[deal]["order_ids"]:
            if o["order_id"] == order:
                bot.reply_to(msg, "⚠️ Order ID already submitted")
                return

        STATS[deal]["order_ids"].append({
            "chat_id": msg.chat.id,
            "order_id": order
        })

        save("stats.json", STATS)
        WAITING_FOR_ORDER.pop(uid, None)

        bot.reply_to(
            msg,
            f"✅ Order ID saved successfully for {deal}\n\nThank you 🙌"
        )

    # ❌ INVALID ORDER ID (only if it looks like an attempt)
    elif "-" in order or order.isdigit():
        bot.reply_to(
            msg,
            "❌ Invalid Order ID format\n\nSend like: 123-1234567-1234567\nContact: @Shivansh_raj"
        )

    # 🤫 Ignore random messages
    else:
        return
# ===== AUTO REPLY =====
@bot.message_handler(func=lambda m: True, content_types=['text','photo'])
def reply(msg):
    text = (msg.text or msg.caption or "").upper()

    deal = None
    for k in DATA:
        if k in text or f"#{k}" in text:
            deal = k
            break

    if not deal:
        return

    if deal not in STATS:
        STATS[deal] = {"requests":0,"purchased":[],"order_ids":[]}

    STATS[deal]["requests"] += 1
    save("stats.json", STATS)

    bot.reply_to(msg, DATA[deal])

    threading.Thread(
        target=follow_up,
        args=(msg.chat.id, deal, msg.message_id)
    ).start()

print("Bot running...")
bot.infinity_polling()
