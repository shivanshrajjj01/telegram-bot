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

# ================= MENU SETUP (ADDED) ================= #

# 👤 User menu
user_commands = [
    BotCommand("start", "Start bot"),
    BotCommand("help", "Help")
]

# 👑 Admin menu
admin_commands = [
    BotCommand("add", "Add data"),
    BotCommand("delete", "Delete data"),
    BotCommand("list", "List IDs"),
    BotCommand("status", "Check stats")
]

# Apply menus
bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())
bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=ADMIN_ID))

# ===================================================== #

# ---------- LOAD & SAVE ---------- #
def load_json(file):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except:
        return {}

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

DATA = load_json("data.json")
STATS = load_json("stats.json")

# ---------- START ---------- #
@bot.message_handler(commands=['start'])
def start_command(message):
    bot.reply_to(
        message,
        "Hi 👋\nAssistant of Shivansh here 😉\nJust send me post and get started."
    )

# ---------- HELP ---------- #
@bot.message_handler(commands=['help'])
def help_command(message):
    bot.reply_to(
        message,
        "Need help?\n\nInstagram: yourusername\nTelegram: @yourusername"
    )

# ---------- ADD ---------- #
@bot.message_handler(commands=['add'])
def add_data(message):
    if message.from_user.id != ADMIN_ID:
        return

    try:
        text = message.text.split("\n", 1)
        deal_id = text[0].split()[1].upper()
        content = text[1]

        DATA[deal_id] = content
        save_json("data.json", DATA)

        bot.reply_to(message, f"✅ Saved {deal_id}")
    except:
        bot.reply_to(message, "❌ Use:\n/add CF123\nYour data")

# ---------- DELETE ---------- #
@bot.message_handler(commands=['delete'])
def delete_data(message):
    if message.from_user.id != ADMIN_ID:
        return

    try:
        deal_id = message.text.split()[1].upper()

        if deal_id in DATA:
            del DATA[deal_id]
            save_json("data.json", DATA)
            bot.reply_to(message, f"🗑 Deleted {deal_id}")
        else:
            bot.reply_to(message, "❌ ID not found")
    except:
        bot.reply_to(message, "❌ Use:\n/delete CF123")

# ---------- DELETE ALL (HIDDEN) ---------- #
@bot.message_handler(commands=['deleteall'])
def delete_all_data(message):
    if message.from_user.id != ADMIN_ID:
        return

    global DATA, STATS
    DATA = {}
    STATS = {}

    save_json("data.json", DATA)
    save_json("stats.json", STATS)

    bot.reply_to(message, "🗑 All data deleted successfully")

# ---------- LIST ---------- #
@bot.message_handler(commands=['list'])
def list_data(message):
    if message.from_user.id != ADMIN_ID:
        return

    if not DATA:
        bot.reply_to(message, "❌ No data saved")
        return

    bot.reply_to(message, "\n".join(DATA.keys()))

# ---------- STATUS ---------- #
@bot.message_handler(commands=['status'])
def status_command(message):
    if message.from_user.id != ADMIN_ID:
        return

    if not STATS:
        bot.reply_to(message, "❌ No data yet")
        return

    args = message.text.split(maxsplit=1)
    msg = "📊 Deal Performance:\n\n"

    if len(args) == 1:
        for key, v in STATS.items():
            msg += (
                f"{key}\n"
                f"👁 Requests: {v.get('requests', 0)}\n"
                f"🛒 Purchased: {len(v.get('purchased', []))}\n\n"
            )
    else:
        ids = args[1].replace(",", " ").split()

        for deal_id in ids:
            deal_id = deal_id.upper()

            if deal_id in STATS:
                v = STATS[deal_id]
                msg += (
                    f"{deal_id}\n"
                    f"👁 Requests: {v.get('requests', 0)}\n"
                    f"🛒 Purchased: {len(v.get('purchased', []))}\n\n"
                )
            else:
                msg += f"{deal_id} ❌ No data\n\n"

    bot.reply_to(message, msg)

# ---------- FOLLOW-UP ---------- #
def follow_up(chat_id, deal_id):
    time.sleep(180)

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("Yes", callback_data=f"buy_yes_{deal_id}"),
        InlineKeyboardButton("No", callback_data=f"buy_no_{deal_id}")
    )

    bot.send_message(chat_id, "Did you purchase this product?", reply_markup=markup)

# ---------- BUTTON HANDLER ---------- #
@bot.callback_query_handler(func=lambda call: True)
def handle_buttons(call):
    user = call.from_user.username or call.from_user.first_name

    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

    if call.data.startswith("buy_yes_"):
        deal_id = call.data.split("_")[2]

        if deal_id not in STATS:
            STATS[deal_id] = {"requests": 0, "users": [], "purchased": []}

        if user not in STATS[deal_id]["purchased"]:
            STATS[deal_id]["purchased"].append(user)

        save_json("stats.json", STATS)

        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("Yes", callback_data="sent_yes"),
            InlineKeyboardButton("No", callback_data="sent_no")
        )

        bot.send_message(
            call.message.chat.id,
            "Did you send order screenshot and order ID to @Shivansh_raj?",
            reply_markup=markup
        )

    elif call.data.startswith("buy_no_"):
        bot.send_message(call.message.chat.id, "Thank you for your time 🙌")

    elif call.data == "sent_no":
        bot.send_message(
            call.message.chat.id,
            "Please send order ID and screenshot to @Shivansh_raj"
        )

    elif call.data == "sent_yes":
        bot.send_message(call.message.chat.id, "Thank you for purchasing 😊")

# ---------- AUTO REPLY ---------- #
@bot.message_handler(func=lambda m: True, content_types=['text', 'photo'])
def reply_data(message):
    text = message.text or message.caption
    if not text:
        return

    text = text.upper()
    user = message.from_user.username or message.from_user.first_name

    for key in DATA:
        if key in text or f"#{key}" in text:

            if key not in STATS:
                STATS[key] = {"requests": 0, "users": [], "purchased": []}

            STATS[key]["requests"] += 1

            if user not in STATS[key]["users"]:
                STATS[key]["users"].append(user)

            save_json("stats.json", STATS)

            bot.reply_to(message, DATA[key])

            threading.Thread(target=follow_up, args=(message.chat.id, key)).start()
            break

print("Bot running...")
bot.infinity_polling() 
