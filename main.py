import sqlite3
import time
import telebot
from telebot import types

# 1. CONFIGURATION
TOKEN = "8644356851:AAG6RTH7tU6LNuID1TsTvT2kS_Z9FkUgg5M"
ADMIN_ID = 8481534132

# Replace this with your actual Group Chat ID after running /getid
GROUP_CHAT_ID = -1004360479489

bot = telebot.TeleBot(TOKEN)

# 2. Database Initialization
def init_db():
    conn = sqlite3.connect("users_verification.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pending_users (
            user_id INTEGER PRIMARY KEY, 
            username TEXT, 
            fullname TEXT,
            phone TEXT, 
            gender TEXT, 
            nationality TEXT, 
            location TEXT,
            reason TEXT,
            step TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS verified_users (
            user_id INTEGER PRIMARY KEY, 
            username TEXT, 
            fullname TEXT,
            phone TEXT, 
            gender TEXT, 
            nationality TEXT, 
            location TEXT, 
            reason TEXT,
            status TEXT
        )
    ''')
    
    cursor.execute("PRAGMA table_info(pending_users)")
    existing_cols = [column[1] for column in cursor.fetchall()]
    
    required_cols = {
        'username': 'TEXT',
        'fullname': 'TEXT',
        'phone': 'TEXT',
        'gender': 'TEXT',
        'nationality': 'TEXT',
        'location': 'TEXT',
        'reason': 'TEXT',
        'step': 'TEXT'
    }
    
    for col_name, col_type in required_cols.items():
        if col_name not in existing_cols:
            cursor.execute(f"ALTER TABLE pending_users ADD COLUMN {col_name} {col_type}")

    conn.commit()
    conn.close()

init_db()

SECURITY_NOTICE = (
    "🔒 <b>Group Security & Access Protocol</b>\n\n"
    "To maintain group safety and prevent unauthorized access or spam, "
    "all members must complete identity verification prior to joining. "
    "Your provided information will be securely held for administrative review."
)

def update_user_field(user_id, field, value):
    conn = sqlite3.connect("users_verification.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO pending_users (user_id) VALUES (?)", (user_id,))
    cursor.execute(f"UPDATE pending_users SET {field} = ? WHERE user_id = ?", (value, user_id))
    conn.commit()
    conn.close()

def get_user_step(user_id):
    conn = sqlite3.connect("users_verification.db")
    cursor = conn.cursor()
    cursor.execute("SELECT step FROM pending_users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

# 3. GET GROUP ID COMMAND (Private DM to Admin Only)
@bot.message_handler(commands=['getid'])
def send_group_id(message):
    if message.from_user.id == ADMIN_ID:
        if message.chat.type in ['group', 'supergroup']:
            try:
                bot.send_message(
                    ADMIN_ID, 
                    f"📌 <b>Group Chat ID:</b> <code>{message.chat.id}</code>", 
                    parse_mode="HTML"
                )
                print(f"GROUP ID: {message.chat.id}")
            except Exception as e:
                bot.reply_to(message, f"📌 Group ID: <code>{message.chat.id}</code>", parse_mode="HTML")
    else:
        pass

# 4. Start Command Handler
@bot.message_handler(commands=['start'])
def start_verification(message):
    user_id = message.from_user.id
    username = message.from_user.username or "No Username"
    
    conn = sqlite3.connect("users_verification.db")
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM verified_users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()

    if result and result[0] == 'APPROVED':
        try:
            invite_link = bot.create_chat_invite_link(
                chat_id=GROUP_CHAT_ID,
                creates_join_request=True,
                member_limit=1
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🚀 Join Group Now", url=invite_link.invite_link))
            
            bot.send_message(
                message.chat.id, 
                "✅ <b>You are already verified!</b>\n\nClick the button below to join:",
                parse_mode="HTML",
                reply_markup=markup
            )
        except Exception:
            bot.send_message(message.chat.id, "✅ You are verified! Request to join the group.")
        return

    update_user_field(user_id, "username", username)
    update_user_field(user_id, "step", "AWAITING_NAME")

    bot.send_message(message.chat.id, SECURITY_NOTICE, parse_mode="HTML")
    bot.send_message(message.chat.id, "👤 <b>Step 1:</b> Please type and send your <b>Full Name</b>:", parse_mode="HTML")

# 5. Universal Text Message Handler
@bot.message_handler(content_types=['text', 'contact', 'location'])
def handle_all_messages(message):
    user_id = message.from_user.id
    current_step = get_user_step(user_id)

    if not current_step:
        return

    if current_step == "AWAITING_NAME":
        if message.content_type == 'text':
            fullname = message.text.strip()
            update_user_field(user_id, "fullname", fullname)
            update_user_field(user_id, "step", "AWAITING_PHONE")

            markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            markup.add(types.KeyboardButton(text="📱 Share Contact", request_contact=True))

            bot.send_message(
                message.chat.id, 
                "📱 <b>Step 2:</b> Click the official <b>'📱 Share Contact'</b> button below to share your verified phone number:", 
                parse_mode="HTML",
                reply_markup=markup
            )

    elif current_step == "AWAITING_PHONE":
        if message.contact:
            phone = message.contact.phone_number
            update_user_field(user_id, "phone", phone)
            update_user_field(user_id, "step", "AWAITING_GENDER")

            hide_markup = types.ReplyKeyboardRemove()
            bot.send_message(message.chat.id, "Phone number verified and saved.", reply_markup=hide_markup)

            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("Male", callback_data="gender_Male"),
                types.InlineKeyboardButton("Female", callback_data="gender_Female")
            )
            bot.send_message(message.chat.id, "⚧ <b>Step 3:</b> Select your gender:", parse_mode="HTML", reply_markup=markup)
        else:
            markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            markup.add(types.KeyboardButton(text="📱 Share Contact", request_contact=True))
            bot.send_message(
                message.chat.id, 
                "⚠️ <b>Manual typing is not allowed!</b>\n\nPlease click the official <b>'📱 Share Contact'</b> button below:", 
                parse_mode="HTML",
                reply_markup=markup
            )

    elif current_step == "AWAITING_NATIONALITY":
        if message.content_type == 'text':
            update_user_field(user_id, "nationality", message.text.strip())
            update_user_field(user_id, "step", "AWAITING_LOCATION")

            markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            markup.add(types.KeyboardButton(text="📍 Send Current Location", request_location=True))

            notice_msg = (
                "📍 <b>Step 5:</b> Please make sure your phone's <b>Location (GPS)</b> is turned ON!\n\n"
                "Click <b>\"📍 Send Current Location\"</b> below or type your city/place name manually:"
            )
            bot.send_message(message.chat.id, notice_msg, parse_mode="HTML", reply_markup=markup)

    elif current_step == "AWAITING_LOCATION":
        if message.location:
            lat = message.location.latitude
            lon = message.location.longitude
            loc_str = f"https://maps.google.com/?q={lat},{lon}"
        elif message.content_type == 'text':
            loc_str = message.text.strip()
        else:
            loc_str = "Not Provided"

        update_user_field(user_id, "location", loc_str)
        update_user_field(user_id, "step", "AWAITING_REASON")

        hide_markup = types.ReplyKeyboardRemove()
        bot.send_message(message.chat.id, "Location recorded successfully.", reply_markup=hide_markup)
        bot.send_message(
            message.chat.id, 
            "❓ <b>Step 6 (Final):</b> Briefly state your <b>purpose/reason</b> for joining this group:", 
            parse_mode="HTML"
        )

    elif current_step == "AWAITING_REASON":
        if message.content_type == 'text':
            reason = message.text.strip()
            update_user_field(user_id, "reason", reason)
            update_user_field(user_id, "step", "COMPLETED")

            conn = sqlite3.connect("users_verification.db")
            cursor = conn.cursor()
            cursor.execute("SELECT username, fullname, phone, gender, nationality, location, reason FROM pending_users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            conn.close()

            if row:
                username, fullname, phone, gender, nationality, location, reason_text = row
                caption = (
                    f"📥 <b>New Access Request!</b>\n\n"
                    f"👤 <b>Name:</b> {fullname}\n"
                    f"🔗 <b>User:</b> @{username} (ID: <code>{user_id}</code>)\n"
                    f"📞 <b>Phone:</b> {phone}\n"
                    f"⚧ <b>Gender:</b> {gender}\n"
                    f"🌍 <b>Nationality:</b> {nationality}\n"
                    f"📍 <b>Location:</b> {location}\n"
                    f"📝 <b>Reason:</b> {reason_text}"
                )

                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton("✅ Approve", callback_data=f"app_{user_id}"),
                    types.InlineKeyboardButton("❌ Reject", callback_data=f"rej_{user_id}")
                )

                try:
                    bot.send_message(ADMIN_ID, caption, parse_mode="HTML", reply_markup=markup)
                    bot.send_message(message.chat.id, "✅ Your information has been submitted! Please wait for admin approval.")
                except Exception as e:
                    print(f"Error notifying admin: {e}")

# Gender Callback Handler
@bot.callback_query_handler(func=lambda call: call.data.startswith('gender_'))
def get_gender(call):
    user_id = call.from_user.id
    gender = call.data.split('_')[1]
    
    update_user_field(user_id, "gender", gender)
    update_user_field(user_id, "step", "AWAITING_NATIONALITY")

    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "🌍 <b>Step 4:</b> Please enter your Nationality (e.g., Ethiopian):", parse_mode="HTML")

# Admin Action Handler (Approve / Reject)
@bot.callback_query_handler(func=lambda call: call.data.startswith(('app_', 'rej_')))
def admin_action(call):
    try:
        data_parts = call.data.split('_')
        action = data_parts[0]
        target_user_id = int(data_parts[1])

        if action == 'app':
            conn = sqlite3.connect("users_verification.db")
            cursor = conn.cursor()
            cursor.execute("SELECT username, fullname, phone, gender, nationality, location, reason FROM pending_users WHERE user_id = ?", (target_user_id,))
            row = cursor.fetchone()

            if row:
                username, fullname, phone, gender, nationality, location, reason_text = row
                cursor.execute('''
                    INSERT OR REPLACE INTO verified_users 
                    (user_id, username, fullname, phone, gender, nationality, location, reason, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (target_user_id, username, fullname, phone, gender, nationality, location, reason_text, 'APPROVED'))
                conn.commit()

            conn.close()

            try:
                invite_link = bot.create_chat_invite_link(
                    chat_id=GROUP_CHAT_ID,
                    creates_join_request=True,
                    member_limit=1
                )

                group_markup = types.InlineKeyboardMarkup()
                group_markup.add(types.InlineKeyboardButton("🚀 Join Group Now", url=invite_link.invite_link))

                bot.send_message(
                    target_user_id, 
                    "🎉 <b>Congratulations! You are verified!</b>\n\n"
                    "Click the button below to join the group. Your request will be accepted automatically!",
                    parse_mode="HTML",
                    reply_markup=group_markup
                )
            except Exception as e:
                bot.send_message(target_user_id, "🎉 You are verified! Please request to join the group.")
                print(f"Link Error: {e}")

            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="✅ <b>User Approved & Link Sent!</b>", parse_mode="HTML")
            bot.answer_callback_query(call.id, "Approved!")

        elif action == 'rej':
            bot.send_message(target_user_id, "❌ Sorry, your verification request was rejected.")
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="❌ <b>User Rejected!</b>", parse_mode="HTML")
            bot.answer_callback_query(call.id, "Rejected!")

    except Exception as e:
        bot.answer_callback_query(call.id, f"Error: {e}", show_alert=True)

# Automatic Join Request Acceptor
@bot.chat_join_request_handler()
def handle_join_request(request):
    user_id = request.from_user.id
    
    conn = sqlite3.connect("users_verification.db")
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM verified_users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()

    if result and result[0] == 'APPROVED':
        bot.approve_chat_join_request(request.chat.id, user_id)
        bot.send_message(user_id, "✅ <b>Welcome! Your join request has been automatically accepted.</b>", parse_mode="HTML")
    else:
        bot.decline_chat_join_request(request.chat.id, user_id)
        bot.send_message(user_id, "⚠️ <b>Access Denied!</b> You must complete verification first.", parse_mode="HTML")

# User Left or Kicked -> Data Cleanup
@bot.chat_member_handler()
def handle_chat_member(message):
    status = message.new_chat_member.status
    user_id = message.new_chat_member.user.id
    
    if status in ['left', 'kicked', 'banned']:
        conn = sqlite3.connect("users_verification.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM verified_users WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM pending_users WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()

# Start Bot Loop
print("Bot is running...")
while True:
    try:
        bot.infinity_polling(
            skip_pending=True, 
            timeout=20, 
            long_polling_timeout=20, 
            allowed_updates=['message', 'callback_query', 'chat_member', 'chat_join_request']
        )
    except Exception as e:
        time.sleep(5)
