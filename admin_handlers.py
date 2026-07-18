from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import config
import database as db

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پنل مدیریت - برای هر دو ادمین"""
    user_id = update.effective_user.id
    
    # هر دو ادمین می‌تونن وارد بشن
    if user_id not in config.SECRET_ADMINS:
        await update.message.reply_text("⛔ شما دسترسی ندارید!")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 تراکنش‌های در انتظار", callback_data="pending_list")],
        [InlineKeyboardButton("➕ افزودن محصول", callback_data="add_product")],
        [InlineKeyboardButton("📝 ویرایش محصول", callback_data="edit_product")],
        [InlineKeyboardButton("🗑 حذف محصول", callback_data="delete_product")],
        [InlineKeyboardButton("📈 آمار", callback_data="stats")],
        [InlineKeyboardButton("💬 مشاهده چت کاربران", callback_data="view_chats")],  # جدید
    ]
    
    await update.message.reply_text(
        "🔐 **پنل مدیریت**\n\n"
        "لطفاً یکی از گزینه‌ها رو انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========== بخش جدید: مشاهده چت کاربران ==========

async def view_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش لیست کاربرانی که با ربات چت کردن"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id not in config.SECRET_ADMINS:
        await query.message.edit_text("⛔ دسترسی ندارید!")
        return
    
    # دریافت لیست کاربرانی که با ربات چت کردن
    conn = db.get_db()
    c = conn.cursor()
    
    # جدول چت‌ها رو می‌سازیم (اگه وجود نداشته باشه)
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  username TEXT,
                  first_name TEXT,
                  message TEXT,
                  is_from_user BOOLEAN,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    
    # دریافت کاربران فعال
    c.execute('''SELECT DISTINCT user_id, username, first_name, MAX(timestamp) as last_msg
                 FROM chat_history 
                 GROUP BY user_id 
                 ORDER BY last_msg DESC LIMIT 50''')
    users = c.fetchall()
    conn.close()
    
    if not users:
        await query.message.edit_text(
            "💬 **چت کاربران**\n\n"
            "هنوز هیچ کاربری با ربات چت نکرده.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back_admin")]
            ])
        )
        return
    
    keyboard = []
    for u in users:
        user_id_db, username, first_name, last_msg = u
        label = f"👤 {first_name or 'کاربر'}" + (f" (@{username})" if username else "")
        keyboard.append([InlineKeyboardButton(
            label,
            callback_data=f"chat_user_{user_id_db}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_admin")])
    
    await query.message.edit_text(
        "💬 **انتخاب کاربر برای مشاهده چت:**\n\n"
        "روی هر کاربر کلیک کن تا تاریخچه چتش رو ببینی.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_user_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش چت یک کاربر خاص"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id not in config.SECRET_ADMINS:
        await query.message.edit_text("⛔ دسترسی ندارید!")
        return
    
    target_user_id = int(query.data.split("_")[2])
    
    conn = db.get_db()
    c = conn.cursor()
    
    # دریافت اطلاعات کاربر
    c.execute('''SELECT username, first_name FROM chat_history 
                 WHERE user_id = ? LIMIT 1''', (target_user_id,))
    user_info = c.fetchone()
    
    # دریافت ۲۰ پیام آخر
    c.execute('''SELECT message, is_from_user, timestamp 
                 FROM chat_history 
                 WHERE user_id = ? 
                 ORDER BY timestamp DESC LIMIT 20''', (target_user_id,))
    messages = c.fetchall()
    conn.close()
    
    if not messages:
        await query.message.edit_text(
            "❌ این کاربر هنوز پیامی نداشته.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data="view_chats")]
            ])
        )
        return
    
    name = user_info[1] or "کاربر"
    username = f" (@{user_info[0]})" if user_info[0] else ""
    
    text = f"💬 **چت با {name}{username}**\n\n"
    text += f"🆔 آیدی: `{target_user_id}`\n"
    text += "─" * 20 + "\n\n"
    
    for msg in reversed(messages):
        sender = "👤 **کاربر:**" if msg[1] else "🤖 **ربات:**"
        time = msg[2][:16] if msg[2] else ""
        text += f"{sender}\n`{msg[0][:100]}`\n"
        text += f"_🕐 {time}_\n\n"
        if len(text) > 3500:  # محدودیت طول پیام تلگرام
            break
    
    keyboard = [
        [InlineKeyboardButton("📥 ارسال پیام به کاربر", callback_data=f"msg_user_{target_user_id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="view_chats")]
    ]
    
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def send_message_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارسال پیام به کاربر از طریق ادمین"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id not in config.SECRET_ADMINS:
        await query.message.edit_text("⛔ دسترسی ندارید!")
        return
    
    target_user_id = int(query.data.split("_")[2])
    context.user_data['reply_to_user'] = target_user_id
    
    await query.message.edit_text(
        f"✏️ **ارسال پیام به کاربر**\n\n"
        f"🆔 آیدی کاربر: `{target_user_id}`\n\n"
        "📝 پیام خود را به‌صورت متن ارسال کن.\n"
        "🔙 برای انصراف، /cancel رو بزن.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 انصراف", callback_data="view_chats")]
        ])
    )

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارسال پیام از ادمین به کاربر"""
    user_id = update.effective_user.id
    
    if user_id not in config.SECRET_ADMINS:
        await update.message.reply_text("⛔ شما دسترسی ندارید!")
        return
    
    target_user_id = context.user_data.get('reply_to_user')
    if not target_user_id:
        await update.message.reply_text("❌ ابتدا از پنل مدیریت یک کاربر رو انتخاب کن!")
        return
    
    message_text = update.message.text
    
    # ارسال به کاربر
    try:
        await context.bot.send_message(
            chat_id=target_user_id,
            text=f"📩 **پیام از ادمین:**\n\n{message_text}"
        )
        await update.message.reply_text("✅ پیام با موفقیت ارسال شد!")
        
        # ثبت در تاریخچه
        conn = db.get_db()
        c = conn.cursor()
        c.execute('''INSERT INTO chat_history (user_id, username, first_name, message, is_from_user) 
                     VALUES (?, ?, ?, ?, ?)''',
                  (target_user_id, None, None, f"[ادمین] {message_text}", False))
        conn.commit()
        conn.close()
        
    except Exception as e:
        await update.message.reply_text(f"❌ ارسال پیام ناموفق: {str(e)}")
    
    context.user_data['reply_to_user'] = None

# ========== بقیه کدهای قبلی ==========

async def approve_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (همون کد قبلی)
    pass

async def reject_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (همون کد قبلی)
    pass

async def pending_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (همون کد قبلی)
    pass

async def back_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await admin_panel(update, context)
