import logging
import asyncio
import requests
import io
import os
import re  
import json
import phonenumbers
import cloudscraper 
from phonenumbers import geocoder
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from telegram.error import BadRequest, Forbidden

# --- [ কনফিগারেশন ] ---
BOT_TOKEN = "8717183781:AAHq3TQ26aTaiSS4E2dDU3QKEevhw5JuhfA"
USER_EMAIL = "kmssrti69@gmail.com"
USER_PASS = "Murad@69"

RANGE_BOT_TOKEN = "8320466114:AAEnHH9LUJdyyQSUOsxmrWAdr2Z3YUz2fnk"
RANGE_CHAT_ID = -1003800110883
RANGE_GROUP_ID = -1003800110883

ADMIN_ID = 1536185224
GROUP_CHAT_ID = -1003711431933
OTP_GROUP_ID = -1003711431933

GROUP_LINK = "https://t.me/otpmastermurad99"
RANGE_GROUP_LINK = "https://t.me/master_murad_range"
DB_FILE = "MASTER_MURAD_USERS.txt"
WALLET_FILE = "Delete_Balanse.json"
CONFIG_FILE = "config.json"
BAN_FILE = "All_Users_Deails.txt"

# --- [ লোড কনফিগারেশন ] ---
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"otp_rate": 0.003}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

current_config = load_config()
OTP_RATE = current_config["otp_rate"]

# API Endpoints
LOGIN_API = "https://x.mnitnetwork.com/mapi/v1/mauth/login"
BUY_API = "https://x.mnitnetwork.com/mapi/v1/mdashboard/getnum/number"
STATUS_API = "https://x.mnitnetwork.com/mapi/v1/mdashboard/getnum/info"
CONSOLE_API = "https://x.mnitnetwork.com/mapi/v1/mdashboard/console/info"

scraper = cloudscraper.create_scraper()
range_bot = Bot(token=RANGE_BOT_TOKEN)

session = {
    "token": None, 
    "cookie": "cf_clearance=KUpNlWYQ7qXJv3ObbfN.GetYsLiJBR3FZoPXv0Hq.24-1772209316-1.2.1.1-p0y0rJVPEi_Cv.lTrK3akyeI1iKJecKmZaa1TQ54qFybekPDW223yf6NhxAdktnrHqMruIFNKNEmzltG0Aa0k3IRebw27AEBZYGhLjP.RQSSTjeGg4iAdG8f54_iXY_unORmShktfXSuNJJk1M_HKUOeE32D5Vcp9DvS.qh8VZJA7_nzeV4voT1W4OBEPA62kjgo73XAgBhas_WCG4IapEjcWTWZr0mtjvdUeCCJBdk"
}

user_state = {}
last_range = {}
processed_console_ids = set()

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- [ Ban Helpers ] ---
def is_banned(user_id):
    if not os.path.exists(BAN_FILE): return False
    with open(BAN_FILE, "r") as f:
        return str(user_id) in [line.strip() for line in f]

def ban_user(user_id):
    with open(BAN_FILE, "a") as f:
        f.write(f"{user_id}\n")

# --- [ SMS Parsing Helper ] ---
def parse_otp_info(sms_text):
    otp = re.search(r'\b\d{4,8}\b', sms_text)
    otp_code = otp.group(0) if otp else "N/A"
    
    app_name = "Service"
    apps = ['Facebook', 'WhatsApp', 'Telegram', 'Google', 'IMO', 'TikTok', 'Instagram', 'Netflix', 'Twitter', 'Viber']
    for app in apps:
        if app.lower() in sms_text.lower():
            app_name = app
            break
    return otp_code, app_name

# --- [ Wallet Helpers ] ---
def load_wallets():
    if os.path.exists(WALLET_FILE):
        with open(WALLET_FILE, "r") as f:
            return json.load(f)
    return {}

def save_wallets(data):
    with open(WALLET_FILE, "w") as f:
        json.dump(data, f, indent=4)

def update_otp_count(user_id):
    wallets = load_wallets()
    uid = str(user_id)
    if uid not in wallets:
        wallets[uid] = {"total_otp": 0}
    wallets[uid]["total_otp"] = wallets[uid].get("total_otp", 0) + 1 
    save_wallets(wallets)

# --- [ Basic Helpers ] ---
def save_user(user_id):
    if not os.path.exists(DB_FILE):
        open(DB_FILE, "w").close()
    with open(DB_FILE, "r") as f:
        users = [line.strip() for line in f]
    if str(user_id) not in users:
        with open(DB_FILE, "a") as f:
            f.write(f"{user_id}\n")

def get_all_users():
    if not os.path.exists(DB_FILE): return []
    with open(DB_FILE, "r") as f:
        return [line.strip() for line in f if line.strip()]

def get_country_info(phone_number):
    try:
        if not phone_number.startswith('+'):
            phone_number = '+' + phone_number
        parsed_num = phonenumbers.parse(phone_number)
        country = geocoder.description_for_number(parsed_num, "en")
        country_code = phonenumbers.region_code_for_number(parsed_num)
        flag = "".join(chr(127397 + ord(c)) for c in country_code.upper())
        return f"{flag} {country}"
    except:
        return "🌍 Unknown Country"

def mask_phone_number(number):
    num_str = str(number)
    if not num_str.startswith('+'):
        num_str = '+' + num_str
    if len(num_str) > 10:
        return f"{num_str[:-6]}**{num_str[-4:]}"
    return num_str

def do_login():
    headers = {
        "Content-Type": "application/json",
        "Cookie": session["cookie"],
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    try:
        payload = {"email": USER_EMAIL, "password": USER_PASS}
        response = scraper.post(LOGIN_API, json=payload, headers=headers, timeout=20)
        if response.status_code == 200:
            data = response.json()
            if data.get("meta", {}).get("status") == "success":
                session["token"] = data['data']['token']
                return True
    except: pass
    return False

def get_auth_headers():
    if not session["token"]: do_login()
    return {
        "mauthtoken": str(session["token"]), 
        "Cookie": f"{session['cookie']}; mauthtoken={session['token']}", 
        "Content-Type": "application/json"
    }

# --- [ Force Join Helper ] ---
async def check_membership(user_id, context):
    channels = ["@otpmastermurad99", "@OTP_MASTER_MURAD_100"]
    for channel in channels:
        try:
            member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ['left', 'kicked']:
                return False
        except Exception:
            return False
    return True

# --- [ Handlers ] ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if is_banned(user_id):
        await update.message.reply_text("❌ You are banned from using this bot.")
        return

    # --- Force Join Check ---
    is_member = await check_membership(user_id, context)
    if not is_member:
        keyboard = [
            [InlineKeyboardButton("💬 OTP Group", url="https://t.me/otpmastermurad99")],
            [InlineKeyboardButton("📢 Update Group", url="https://t.me/OTP_MASTER_MURAD_100")],
            [InlineKeyboardButton("✅ Verify", callback_data="verify_join")]
        ]
        await update.message.reply_text(
            "🚦 **Access Denied**\n\nApni Amader OTP Group And Update Group A Join Kore Verify Batton A Chap Den\n\n"
            "💬 [OTP Group](https://t.me/otpmastermurad99)\n"
            "📢 [Update Group](https://t.me/OTP_MASTER_MURAD_100)\n\n"
            "After Joining, Press ✅ Verify",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
        return

    save_user(user_id)
    user_state[user_id] = None 
    
    keyboard = [
        [KeyboardButton("📱 GET NUMBER 📱")],
        [KeyboardButton("🚀 GET 30 NUMBER 🚀")],
        [KeyboardButton("🔗 View Range")]
    ]
    if user_id == ADMIN_ID:
        keyboard.append([KeyboardButton("⚙️ ADMIN PANEL ⚙️")])
    
    await update.message.reply_text(
        "🔥 **OTP MASTER MURAD** 🔥\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Select Your Service Number Button\n", 
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True), 
        parse_mode="Markdown"
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    global OTP_RATE

    if is_banned(user_id):
        await query.answer("❌ You are banned!", show_alert=True)
        return

    # --- Handle Verification Button ---
    if data == "verify_join":
        is_member = await check_membership(user_id, context)
        if is_member:
            await query.answer("✅ Verification Successful!", show_alert=True)
            try:
                await query.message.delete()
            except:
                pass
            
            save_user(user_id)
            user_state[user_id] = None 
            
            keyboard = [
                [KeyboardButton("📱 GET NUMBER 📱")],
                [KeyboardButton("🚀 GET 30 NUMBER 🚀")],
                [KeyboardButton("🔗 View Range")]
            ]
            if user_id == ADMIN_ID:
                keyboard.append([KeyboardButton("⚙️ ADMIN PANEL ⚙️")])
            
            await context.bot.send_message(
                chat_id=user_id,
                text="🔥 **OTP MASTER MURAD NUMBER PANEL** 🔥\n"
                     "━━━━━━━━━━━━━━━━━━\n"
                     "Select Your Service Number Button\n", 
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True), 
                parse_mode="Markdown"
            )
        else:
            await query.answer("❌ You must join ALL channels first!", show_alert=True)
        return

    await query.answer()

    if data.startswith('change_num_'):
        range_id = data.split('_')[2]
        try:
            await query.message.edit_reply_markup(reply_markup=None)
        except: pass
        await generate_single_number(query.message, range_id, user_id, context, is_edit=False)


# --- [ SMS Checker ] ---
async def single_otp_checker(context, msg_obj, num, target_id, range_id, keyboard, user_data=None):
    received_otps = set() 
    for _ in range(30): 
        await asyncio.sleep(10)
        try:
            r = scraper.get(STATUS_API, headers=get_auth_headers(), params={"date": datetime.now().strftime("%Y-%m-%d")}, timeout=10).json()
            if r.get("meta", {}).get("status") == "success":
                match = next((x for x in r['data']['numbers'] if str(x['number']).replace('+', '') == str(num)), None)
                if match and match.get('otp'):
                    full_sms = match['otp']
                    
                    if full_sms not in received_otps:
                        received_otps.add(full_sms) 
                        update_otp_count(target_id) 
                        
                        otp_code, app_name = parse_otp_info(full_sms)
                        country_info = get_country_info(num)
                        
                        private_msg = (f"✅ OTP Received Successfully ✅\n\n"
                                       f"🌍 Country: {country_info}\n\n"
                                       f"📱 Service: {app_name}\n"
                                       f"📞 Number: `+{num}`\n"  
                                       f"🔑 OTP: `{otp_code}`\n\n"
                                       f"📩 Full SMS: `{full_sms}`")
                        
                        group_msg = (f"✅ OTP Received Successfully ✅\n\n"
                                     f"🌍 Country: {country_info}\n\n"
                                     f"📱 Service: {app_name}\n"
                                     f"📞 Number: `{mask_phone_number(num)}`\n" 
                                     f"🔑 OTP: `{otp_code}`\n\n"
                                     f"📩 Full SMS: `{full_sms}`")
                        
                        otp_group_markup = InlineKeyboardMarkup([
                            [InlineKeyboardButton("💥 NUMBER PANEL 💥", url="https://t.me/OTP_MASTER_MURAD_BOT")]
                        ])
                        
                        try:
                            await context.bot.send_message(chat_id=target_id, text=private_msg, parse_mode="Markdown")
                        except:
                            await context.bot.send_message(chat_id=target_id, text=private_msg)

                        try:
                            await context.bot.send_message(chat_id=OTP_GROUP_ID, text=group_msg, parse_mode="Markdown", reply_markup=otp_group_markup)
                        except:
                            await context.bot.send_message(chat_id=OTP_GROUP_ID, text=group_msg, reply_markup=otp_group_markup)
        except: continue

async def bulk_otp_checker(context, target_id, numbers, range_val, user_data=None):
    known_otps = {} 
    for _ in range(120): 
        await asyncio.sleep(15)
        try:
            r = scraper.get(STATUS_API, headers=get_auth_headers(), params={"date": datetime.now().strftime("%Y-%m-%d")}, timeout=10).json()
            if r.get("meta", {}).get("status") == "success":
                for n in numbers:
                    match = next((x for x in r['data']['numbers'] if str(x['number']).replace('+', '') == str(n)), None)
                    if match and match.get('otp'):
                        full_sms = match['otp']
                        if n not in known_otps or known_otps[n] != full_sms:
                            known_otps[n] = full_sms
                            update_otp_count(target_id)
                            
                            otp_code, app_name = parse_otp_info(full_sms)
                            country_info = get_country_info(n)

                            private_msg = (f"✅ OTP Received Successfully ✅\n\n"
                                           f"🌍 Country: {country_info}\n\n"
                                           f"📱 Service: {app_name}\n"
                                           f"📞 Number: `+{n}`\n" 
                                           f"🔑 OTP: `{otp_code}`\n\n"
                                           f"📩 Full SMS: `{full_sms}`")
                            
                            group_msg = (f"✅ OTP Received Successfully ✅\n\n"
                                         f"🌍 Country: {country_info}\n\n"
                                         f"📱 Service: {app_name}\n"
                                         f"📞 Number: `{mask_phone_number(n)}`\n" 
                                         f"🔑 OTP: `{otp_code}`\n\n"
                                         f"📩 Full SMS: `{full_sms}`")
                            
                            otp_group_markup = InlineKeyboardMarkup([
                                [InlineKeyboardButton("💥 NUMBER PANEL 💥", url="https://t.me/OTP_MASTER_MURAD_BOT")]
                            ])
                            
                            try:
                                await context.bot.send_message(chat_id=target_id, text=private_msg, parse_mode="Markdown")
                            except:
                                await context.bot.send_message(chat_id=target_id, text=private_msg)

                            try:
                                await context.bot.send_message(chat_id=OTP_GROUP_ID, text=group_msg, parse_mode="Markdown", reply_markup=otp_group_markup)
                            except:
                                await context.bot.send_message(chat_id=OTP_GROUP_ID, text=group_msg, reply_markup=otp_group_markup)
        except: continue

# --- [ Background Broadcast Task ] ---
async def broadcast_task(context, message_obj, user_list):
    text = f"📢 **ADMIN NOTICE**\n\n{message_obj.text or message_obj.caption or ''}"
    photo = message_obj.photo[-1].file_id if message_obj.photo else None
    video = message_obj.video.file_id if message_obj.video else None
    document = message_obj.document.file_id if message_obj.document else None

    for uid in user_list:
        try:
            if photo:
                await context.bot.send_photo(chat_id=uid, photo=photo, caption=text, parse_mode="Markdown")
            elif video:
                await context.bot.send_video(chat_id=uid, video=video, caption=text, parse_mode="Markdown")
            elif document:
                await context.bot.send_document(chat_id=uid, document=document, caption=text, parse_mode="Markdown")
            else:
                await context.bot.send_message(chat_id=uid, text=text, parse_mode="Markdown")
            await asyncio.sleep(0.05)
        except:
            continue

# --- [ Rest of the Logic ] ---
async def generate_bulk_numbers_task(context, user_id, range_id, user_obj):
    status_msg = await context.bot.send_message(chat_id=user_id, text=f"⏳ **Collecting 30 Numbers... Please wait.**\n[░░░░░░░░░░] 0%", parse_mode="Markdown")
    numbers = []
    attempts = 0
    max_attempts = 150 
    country_name = "Unknown Country"
    
    while len(numbers) < 30 and attempts < max_attempts:
        attempts += 1
        try:
            r = scraper.post(BUY_API, headers=get_auth_headers(), json={"range": range_id}, timeout=15).json()
            if r.get("meta", {}).get("status") == "success":
                num = str(r['data']['number']).replace('+', '')
                if not numbers: 
                    country_name = get_country_info(num)
                if num not in numbers: 
                    numbers.append(num)
                    percent = int((len(numbers) / 30) * 100)
                    filled = int(percent / 10)
                    bar = "█" * filled + "░" * (10 - filled)
                    try:
                        await status_msg.edit_text(f"⏳ **Collecting 30 Numbers...**\n`[{bar}]` {percent}% ({len(numbers)}/30)", parse_mode="Markdown")
                    except: pass
            else: 
                await asyncio.sleep(2)
            await asyncio.sleep(0.5) 
        except: 
            await asyncio.sleep(1)
            continue
    
    if numbers:
        file_obj = io.BytesIO("\n".join(numbers).encode('utf-8'))
        file_obj.name = f"30_Numbers_{range_id}.txt"
        caption_text = (f"✅ **Done! Numbers Collected**\n\n📶 Range Name: `{range_id}`\n🌍 Country Name: {country_name}\n🔢 Total Number: `{len(numbers)}`")
        await status_msg.delete()
        await context.bot.send_document(chat_id=user_id, document=file_obj, caption=caption_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📩 View OTP", url=GROUP_LINK)]]), parse_mode="Markdown")
        asyncio.create_task(bulk_otp_checker(context, user_id, numbers, range_id, user_obj))
    else:
        await status_msg.edit_text(f"❌ Could not collect numbers.")

async def handle_range_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if is_banned(user_id):
        return

    # --- Force Join Check for Text Commands ---
    is_member = await check_membership(user_id, context)
    if not is_member:
        keyboard = [
            [InlineKeyboardButton("💬 OTP Group", url="https://t.me/otpmastermurad99")],
            [InlineKeyboardButton("📢 Update Group", url="https://t.me/OTP_MASTER_MURAD_100")],
            [InlineKeyboardButton("✅ Verify", callback_data="verify_join")]
        ]
        await update.message.reply_text(
            "🚦 **Access Denied**\n\nTo use this BOT, you must Join ALL Channels:\n\n"
            "💬 [OTP Group](https://t.me/otpmastermurad99)\n"
            "📢 [Update Group](https://t.me/OTP_MASTER_MURAD_100)\n\n"
            "After Joining, Press ✅ Verify",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
        return

    text = update.message.text.strip() if update.message.text else ""
    global OTP_RATE

    # --- [ Reply Keyboard Actions ] ---
    if text == "📱 GET NUMBER 📱":
        user_state[user_id] = "WAITING_FOR_SINGLE_RANGE"
        await update.message.reply_text("⌨️ **Enter Range ID (1 Number):**", parse_mode="Markdown")
        return
    elif text == "🚀 GET 30 NUMBER 🚀":
        user_state[user_id] = "WAITING_FOR_BULK_RANGE"
        await update.message.reply_text("⌨️ **Enter Range ID (30 Number):**", parse_mode="Markdown")
        return
    elif text == "🔗 View Range":
        # এই বাটনটি চাপলে এখন সরাসরি রেঞ্জ গ্রুপের লিঙ্ক দেখাবে এবং একটি ক্লিকযোগ্য বাটন দেবে
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("🚀 View Range", url=RANGE_GROUP_LINK)]])
        await update.message.reply_text(f"🔗 **Nesa View Range Batton A Click Kore Range Nen**", reply_markup=markup, parse_mode="Markdown")
        return
    elif text == "⚙️ ADMIN PANEL ⚙️" and user_id == ADMIN_ID:
        keyboard = [
            [KeyboardButton("🔄 Change OTP Rate")],
            [KeyboardButton("📢 Send Notification")],
            [KeyboardButton("📊 User Stats & List")],
            [KeyboardButton("🚫 Ban User")],
            [KeyboardButton("⬅️ Back to Main Menu")]
        ]
        await update.message.reply_text(f"🛠 **Admin Control Panel**\n\nCurrent OTP Rate: `{OTP_RATE}$`", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True), parse_mode="Markdown")
        return
    elif text == "🔄 Change OTP Rate" and user_id == ADMIN_ID:
        user_state[user_id] = "WAITING_FOR_RATE"
        await update.message.reply_text("⌨️ **Enter New OTP Rate (e.g., 0.005):**", parse_mode="Markdown")
        return
    elif text == "📢 Send Notification" and user_id == ADMIN_ID:
        user_state[user_id] = "WAITING_FOR_BROADCAST"
        await update.message.reply_text("✉️ **Send any message (Text, Photo, Video) to broadcast to ALL users:**", parse_mode="Markdown")
        return
    elif text == "📊 User Stats & List" and user_id == ADMIN_ID:
        users = get_all_users()
        wallets = load_wallets()
        report = "📊 **USER STATISTICS & LIST**\n━━━━━━━━━━━━━━━━━━\n"
        for u in users:
            w = wallets.get(str(u), {"total_otp": 0})
            total_otp = w.get('total_otp', 0)
            report += f"👤 ID: `{u}`\n🔢 OTP: `{total_otp}`\n\n"
        
        report += f"👥 **Total Active Users: {len(users)}**"
        
        if len(report) > 4000:
            file_obj = io.BytesIO(report.encode('utf-8'))
            file_obj.name = "user_stats.txt"
            await update.message.reply_document(document=file_obj, caption="📊 Full User Stats List")
        else:
            await update.message.reply_text(report, parse_mode="Markdown")
        return
    elif text == "🚫 Ban User" and user_id == ADMIN_ID:
        user_state[user_id] = "WAITING_FOR_BAN_ID"
        await update.message.reply_text("🚫 **Enter User ID to Ban:**", parse_mode="Markdown")
        return
    elif text == "⬅️ Back to Main Menu":
        keyboard = [
            [KeyboardButton("📱 GET NUMBER 📱")],
            [KeyboardButton("🚀 GET 30 NUMBER 🚀")],
            [KeyboardButton("🔗 View Range")]
        ]
        if user_id == ADMIN_ID:
            keyboard.append([KeyboardButton("⚙️ ADMIN PANEL ⚙️")])
        await update.message.reply_text("🔥 **OTP MASTER MURAD NUMBER PANEL** 🔥", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True), parse_mode="Markdown")
        return


    # --- [ State Based Logic ] ---
    if user_id not in user_state or user_state[user_id] is None: return
    state = user_state[user_id]
    
    if state == "WAITING_FOR_RATE" and user_id == ADMIN_ID:
        user_state[user_id] = None
        try:
            OTP_RATE = float(text)
            current_config["otp_rate"] = OTP_RATE
            save_config(current_config)
            await update.message.reply_text(f"✅ OTP Rate: `{OTP_RATE}$`")
        except: pass
    elif state == "WAITING_FOR_BROADCAST" and user_id == ADMIN_ID:
        user_state[user_id] = None
        users = get_all_users()
        asyncio.create_task(broadcast_task(context, update.message, users))
        await update.message.reply_text(f"✅ Broadcast initiated to {len(users)} users.")
    elif state == "WAITING_FOR_BAN_ID" and user_id == ADMIN_ID:
        user_state[user_id] = None
        ban_user(text)
        await update.message.reply_text(f"✅ User `{text}` has been banned.")
    elif state == "WAITING_FOR_SINGLE_RANGE":
        user_state[user_id] = None
        await generate_single_number(update.message, text, user_id, context)
    elif state == "WAITING_FOR_BULK_RANGE":
        user_state[user_id] = None
        asyncio.create_task(generate_bulk_numbers_task(context, user_id, text, update.effective_user))

async def generate_single_number(message_obj, range_id, user_id, context, is_edit=False):
    status_msg = await message_obj.reply_text("📡 Searching...") 
    try:
        res = scraper.post(BUY_API, headers=get_auth_headers(), json={"range": range_id}, timeout=15).json()
        if res.get("meta", {}).get("status") == "success":
            num = str(res['data']['number']).replace('+', '')
            country_info = get_country_info(num)
            keyboard = [[InlineKeyboardButton("🔄 Change Number", callback_data=f'change_num_{range_id}')],[InlineKeyboardButton("📩 View OTP", url=GROUP_LINK)]]
            msg = (f"✅ **YOUR NUMBER ADDED ✅**\n\n📶 Range: `{range_id}`\n🌍 Country: `{country_info}`\n\n📞 Number: `+{num}`\n\n📩 SMS Status: `Waiting...` ")
            await status_msg.edit_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            
            u_obj = message_obj.from_user if not is_edit else None
            asyncio.create_task(single_otp_checker(context, status_msg, num, user_id, range_id, keyboard, u_obj))
        else: await status_msg.edit_text("❌ Range empty.")
    except: await status_msg.edit_text("❌ Error.")

async def consol_sms_logger():
    while True:
        try:
            response = scraper.get(CONSOLE_API, headers=get_auth_headers(), timeout=10).json()
            if response.get("meta", {}).get("status") == "success":
                logs = response.get('data', {}).get('logs', [])
                for entry in reversed(logs):
                    msg_id = entry.get('id')
                    if msg_id not in processed_console_ids:
                        range_val, country, app_name, sms_text = entry.get('range'), entry.get('country'), entry.get('app_name'), entry.get('sms')
                        
                        country_display = country
                        try:
                            parsed_range = phonenumbers.parse("+" + str(range_val))
                            c_code = phonenumbers.region_code_for_number(parsed_range)
                            flag = "".join(chr(127397 + ord(c)) for c in c_code.upper())
                            country_display = f"{flag} {country}"
                        except: pass

                        msg = (f"✅ New Active Range ✅\n\n"
                               f"🌍 Country: {country_display}\n"
                               f"📶 Range `{range_val}XXX`\n\n"
                               f"🔵 Service: {app_name}\n\n"
                               f"📩 Full SMS: {sms_text}")
                               
                        try:
                            await range_bot.send_message(chat_id=RANGE_CHAT_ID, text=msg, parse_mode="Markdown")
                            processed_console_ids.add(msg_id)
                        except: pass
        except: pass
        await asyncio.sleep(10)

async def post_init(application):
    asyncio.create_task(consol_sms_logger())

if __name__ == '__main__':
    do_login()
    application = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), handle_range_input))
    print("🚀 Bot LIVE!")
    application.run_polling(drop_pending_updates=True)
