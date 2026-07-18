from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import config
import database as db

# ... (همون کدهای قبلی)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # ثبت کاربر در تاریخچه
    conn = db.get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  username TEXT,
                  first_name TEXT,
                  message TEXT,
                  is_from_user BOOLEAN,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''INSERT INTO chat_history (user_id, username, first_name, message, is_from_user) 
                 VALUES (?, ?, ?, ?, ?)''',
              (user.id, user.username, user.first_name, "/start", True))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        f"👋 سلام {user.first_name} عزیز!\n\n"
        "به فروشگاه اپل‌آیدی خوش آمدی.\n"
        "لطفاً از منوی زیر یکی از گزینه‌ها رو انتخاب کن:",
        reply_markup=main_menu()
    )

# همچنین تابع handle_receipt و بقیه رو آپدیت کن تا چت رو ذخیره کنن
