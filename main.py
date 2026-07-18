from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import sqlite3
import os
import configparser
import re

# ==================== تنظیمات اولیه ====================
# اگر فایل config.ini ندارید، این مقادیر رو مستقیم وارد کنید
TOKEN = "8536796290:AAHxGy2RdPLO2HXp2V_X6BDXvsWVmH0tDIQ"
MASTER_ADMIN = 8911508795
ADMIN_IDS = [8706836237, 8911508795]
CARD_NUMBER = "621986195090"
CARD_OWNER = "محمد مهدی جاودان"
DB_NAME = "shop.db"

# ==================== دیتابیس ====================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # جدول محصولات
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price INTEGER,
        stock INTEGER,
        codes TEXT
    )''')
    
    # جدول تراکنش‌ها
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_id INTEGER,
        amount INTEGER,
        receipt_file_id TEXT,
        status TEXT,
        assigned_code TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # جدول تنظیمات
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    
    # تنظیمات پیش‌فرض
    defaults = [
        ('welcome_text', '👋 سلام {first_name} عزیز!\nبه فروشگاه خوش آمدی.'),
        ('btn_products', '🛒 لیست محصولات'),
        ('btn_support', '📞 پشتیبانی'),
        ('btn_status', '📊 وضعیت خرید'),
        ('btn_back', '🔙 بازگشت'),
    ]
    c.executemany("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", defaults)
    
    conn.commit()
    conn.close()

def get_setting(key):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else ""

# ==================== توابع کمکی ====================
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton(get_setting('btn_products'), callback_data="products")],
        [InlineKeyboardButton(get_setting('btn_support'), callback_data="support")],
        [InlineKeyboardButton(get_setting('btn_status'), callback_data="status")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_panel():
    keyboard = [
        [InlineKeyboardButton("➕ افزودن محصول", callback_data="add_product")],
        [InlineKeyboardButton("📝 ویرایش محصول", callback_data="edit_product")],
        [InlineKeyboardButton("🗑 حذف محصول", callback_data="delete_product")],
        [InlineKeyboardButton("📊 تراکنش‌ها", callback_data="transactions")],
        [InlineKeyboardButton("📈 آمار", callback_data="stats")],
        [InlineKeyboardButton("💬 چت کاربران", callback_data="view_chats")],
        [InlineKeyboardButton("✏️ ویرایش پیام‌ها", callback_data="edit_msgs")],
        [InlineKeyboardButton("📢 پیام همگانی", callback_data="broadcast")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== دستورات عمومی ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = get_setting('welcome_text').format(first_name=user.first_name)
    await update.message.reply_text(welcome_text, reply_markup=get_main_menu())

# ==================== دکمه‌های منوی اصلی ====================
async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, name, price, stock FROM products WHERE stock > 0")
    products = c.fetchall()
    conn.close()
    
    if not products:
        await query.message.edit_text("😕 محصولی موجود نیست.", reply_markup=get_main_menu())
        return
    
    keyboard = []
    for p in products:
        keyboard.append([InlineKeyboardButton(
            f"🔹 {p[1]} - {p[2]:,} تومان (موجودی: {p[3]})",
            callback_data=f"buy_{p[0]}"
        )])
    keyboard.append([InlineKeyboardButton(get_setting('btn_back'), callback_data="back_to_main")])
    
    await query.message.edit_text("🛒 لیست محصولات:", reply_markup=InlineKeyboardMarkup(keyboard))

async def buy_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    product_id = int(query.data.split("_")[1])
    context.user_data['buying_product'] = product_id
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT name, price FROM products WHERE id=?", (product_id,))
    product = c.fetchone()
    conn.close()
    
    if not product:
        await query.message.edit_text("❌ محصول یافت نشد!", reply_markup=get_main_menu())
        return
    
    keyboard = [
        [InlineKeyboardButton("✅ ارسال رسید", callback_data="send_receipt")],
        [InlineKeyboardButton("🔙 انصراف", callback_data="back_to_main")]
    ]
    
    await query.message.edit_text(
        f"💳 **اطلاعات واریز:**\n\n"
        f"💰 مبلغ: {product[1]:,} تومان\n"
        f"🏦 شماره کارت: `{CARD_NUMBER}`\n"
        f"👤 صاحب حساب: {CARD_OWNER}\n\n"
        "⬇️ بعد از واریز، رسید رو ارسال کن.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    product_id = context.user_data.get('buying_product')
    
    if not product_id:
        await update.message.reply_text("❌ اول محصول رو انتخاب کن!")
        return
    
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    else:
        await update.message.reply_text("❌ فقط عکس ارسال کن!")
        return
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT name, price FROM products WHERE id=?", (product_id,))
    product = c.fetchone()
    
    if not product:
        conn.close()
        await update.message.reply_text("❌ محصول یافت نشد!")
        return
    
    c.execute('''INSERT INTO transactions (user_id, product_id, amount, receipt_file_id, status) 
                 VALUES (?, ?, ?, ?, ?)''', (user.id, product_id, product[1], file_id, 'pending'))
    trans_id = c.lastrowid
    conn.commit()
    conn.close()
    
    await update.message.reply_text("✅ رسید دریافت شد! در حال بررسی...")
    
    # ارسال به ادمین
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_photo(
                chat_id=admin_id,
                photo=file_id,
                caption=f"🆕 درخواست خرید جدید\n🆔 تراکنش: {trans_id}\n👤 کاربر: {user.first_name}\n📦 محصول: {product[0]}\n💰 مبلغ: {product[1]:,} تومان",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ تأیید", callback_data=f"approve_{trans_id}")],
                    [InlineKeyboardButton("❌ رد", callback_data=f"reject_{trans_id}")]
                ])
            )
        except:
            pass

# ==================== دکمه‌های بازگشت ====================
async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.edit_text("🏠 منوی اصلی:", reply_markup=get_main_menu())

async def back_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.edit_text("🔐 پنل مدیریت:", reply_markup=get_admin_panel())

# ==================== پنل ادمین ====================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ دسترسی ندارید!")
        return
    await update.message.reply_text("🔐 پنل مدیریت:", reply_markup=get_admin_panel())

# ==================== مدیریت محصولات ====================
# افزودن محصول
async def add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.edit_text(
        "➕ **افزودن محصول جدید**\n\n"
        "اطلاعات رو به این ترتیب وارد کن (هر خط یک مورد):\n"
        "1️⃣ نام\n2️⃣ قیمت (عدد)\n3️⃣ موجودی (عدد)\n4️⃣ کدها (با کاما جدا کن)\n\n"
        "مثال:\nاپل‌آیدی آمریکا\n15000\n10\nuser1|pass1,user2|pass2",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back_admin")]])
    )
    context.user_data['awaiting_add_product'] = True

async def save_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_add_product'):
        return
    
    lines = update.message.text.strip().split('\n')
    if len(lines) < 4:
        await update.message.reply_text("❌ ۴ خط اطلاعات وارد کن!")
        return
    
    try:
        name = lines[0].strip()
        price = int(lines[1].strip())
        stock = int(lines[2].strip())
        codes = lines[3].strip()
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO products (name, price, stock, codes) VALUES (?, ?, ?, ?)", 
                  (name, price, stock, codes))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(f"✅ محصول '{name}' با موفقیت اضافه شد!")
        context.user_data['awaiting_add_product'] = False
    except:
        await update.message.reply_text("❌ خطا! قیمت و موجودی باید عدد باشن.")

# ویرایش محصول
async def edit_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, name, price, stock FROM products")
    products = c.fetchall()
    conn.close()
    
    if not products:
        await query.message.edit_text("❌ محصولی وجود ندارد.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back_admin")]]))
        return
    
    keyboard = []
    for p in products:
        keyboard.append([InlineKeyboardButton(f"✏️ {p[1]}", callback_data=f"edit_product_{p[0]}")])
    keyboard.append([InlineKeyboardButton("🔙", callback_data="back_admin")])
    
    await query.message.edit_text("📝 محصول رو برای ویرایش انتخاب کن:", reply_markup=InlineKeyboardMarkup(keyboard))

async def edit_product_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    product_id = int(query.data.split("_")[2])
    context.user_data['editing_product'] = product_id
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT name, price, stock, codes FROM products WHERE id=?", (product_id,))
    product = c.fetchone()
    conn.close()
    
    if not product:
        await query.message.edit_text("❌ محصول یافت نشد!")
        return
    
    await query.message.edit_text(
        f"📝 **ویرایش محصول**\n\n"
        f"نام: {product[0]}\n"
        f"قیمت: {product[1]:,} تومان\n"
        f"موجودی: {product[2]}\n"
        f"کدها: {product[3]}\n\n"
        "کدوم قسمت رو می‌خوای عوض کنی؟",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 نام", callback_data=f"edit_field_name_{product_id}")],
            [InlineKeyboardButton("💰 قیمت", callback_data=f"edit_field_price_{product_id}")],
            [InlineKeyboardButton("📦 موجودی", callback_data=f"edit_field_stock_{product_id}")],
            [InlineKeyboardButton("🔑 کدها", callback_data=f"edit_field_codes_{product_id}")],
            [InlineKeyboardButton("🔙", callback_data="edit_product")]
        ])
    )

async def edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    field = parts[2]
    product_id = int(parts[3])
    
    context.user_data['editing_field'] = field
    context.user_data['editing_product_id'] = product_id
    
    await query.message.edit_text(f"✏️ مقدار جدید برای '{field}' رو وارد کن:")

async def save_edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('editing_field'):
        return
    
    product_id = context.user_data['editing_product_id']
    field = context.user_data['editing_field']
    value = update.message.text.strip()
    
    if field in ['price', 'stock']:
        try:
            value = int(value)
        except:
            await update.message.reply_text("❌ باید عدد وارد کنی!")
            return
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(f"UPDATE products SET {field} = ? WHERE id = ?", (value, product_id))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(f"✅ {field} با موفقیت به‌روز شد!")
    context.user_data['editing_field'] = None

# حذف محصول
async def delete_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, name FROM products")
    products = c.fetchall()
    conn.close()
    
    if not products:
        await query.message.edit_text("❌ محصولی وجود ندارد.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back_admin")]]))
        return
    
    keyboard = []
    for p in products:
        keyboard.append([InlineKeyboardButton(f"🗑 {p[1]}", callback_data=f"delete_product_{p[0]}")])
    keyboard.append([InlineKeyboardButton("🔙", callback_data="back_admin")])
    
    await query.message.edit_text("🗑 محصول رو برای حذف انتخاب کن:", reply_markup=InlineKeyboardMarkup(keyboard))

async def delete_product_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    product_id = int(query.data.split("_")[2])
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE id=?", (product_id,))
    conn.commit()
    conn.close()
    
    await query.message.edit_text("✅ محصول با موفقیت حذف شد!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back_admin")]]))

# ==================== تراکنش‌ها ====================
async def transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, user_id, amount, status FROM transactions ORDER BY created_at DESC LIMIT 10")
    trans = c.fetchall()
    conn.close()
    
    if not trans:
        await query.message.edit_text("📊 هیچ تراکنشی وجود ندارد.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back_admin")]]))
        return
    
    text = "📊 **۱۰ تراکنش آخر:**\n\n"
    for t in trans:
        status = {"pending": "⏳ در انتظار", "approved": "✅ تأیید", "rejected": "❌ رد", "delivered": "📦 تحویل"}.get(t[3], "❓")
        text += f"#{t[0]} - کاربر: {t[1]} - {t[2]:,} تومان - {status}\n"
    
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back_admin")]]))

# ==================== تأیید/رد تراکنش ====================
async def approve_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    trans_id = int(query.data.split("_")[1])
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id, product_id FROM transactions WHERE id=?", (trans_id,))
    trans = c.fetchone()
    
    if not trans:
        await query.message.edit_caption("❌ تراکنش یافت نشد!")
        return
    
    # دریافت یک کد از محصول
    c.execute("SELECT codes FROM products WHERE id=?", (trans[1],))
    codes_row = c.fetchone()
    
    if not codes_row or not codes_row[0]:
        await query.message.edit_caption("⚠️ موجودی کد تمام شد!")
        return
    
    codes = codes_row[0].split(',')
    assigned = codes[0].strip()
    remaining = ','.join(codes[1:])
    
    c.execute("UPDATE products SET codes=? WHERE id=?", (remaining, trans[1]))
    c.execute("UPDATE transactions SET status='approved', assigned_code=? WHERE id=?", (assigned, trans_id))
    conn.commit()
    conn.close()
    
    # ارسال کد به کاربر
    await context.bot.send_message(
        chat_id=trans[0],
        text=f"🎉 خرید شما تأیید شد!\n\n🔑 اپل‌آیدی شما:\n`{assigned}`"
    )
    
    await query.message.edit_caption(f"✅ تراکنش #{trans_id} تأیید و کد ارسال شد!")

async def reject_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    trans_id = int(query.data.split("_")[1])
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id FROM transactions WHERE id=?", (trans_id,))
    trans = c.fetchone()
    
    if trans:
        await context.bot.send_message(chat_id=trans[0], text="❌ رسید شما رد شد. لطفاً با پشتیبانی تماس بگیرید.")
    
    c.execute("UPDATE transactions SET status='rejected' WHERE id=?", (trans_id,))
    conn.commit()
    conn.close()
    
    await query.message.edit_caption(f"❌ تراکنش #{trans_id} رد شد!")

# ==================== آمار ====================
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    users = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM transactions")
    total = c.fetchone()[0] or 0
    c.execute("SELECT SUM(amount) FROM transactions WHERE status='approved'")
    sales = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM transactions WHERE status='pending'")
    pending = c.fetchone()[0] or 0
    conn.close()
    
    await query.message.edit_text(
        f"📈 **آمار فروشگاه**\n\n"
        f"👥 کاربران: {users}\n"
        f"📦 تراکنش‌ها: {total}\n"
        f"💰 فروش: {sales:,} تومان\n"
        f"⏳ در انتظار: {pending}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back_admin")]])
    )

# ==================== چت کاربران (ساده شده) ====================
async def view_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.edit_text("💬 این بخش در حال توسعه است.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back_admin")]]))

# ==================== ویرایش پیام‌ها ====================
async def edit_msgs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.edit_text("✏️ این بخش در حال توسعه است.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back_admin")]]))

# ==================== پیام همگانی ====================
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.edit_text("📢 پیام خود رو برای همگانی ارسال کن:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back_admin")]]))
    context.user_data['broadcast_msg'] = True

async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('broadcast_msg'):
        return
    
    msg = update.message.text
    await update.message.reply_text("⏳ در حال ارسال...")
    
    # دریافت لیست کاربران از تراکنش‌ها
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT DISTINCT user_id FROM transactions")
    users = c.fetchall()
    conn.close()
    
    sent = 0
    for u in users:
        try:
            await context.bot.send_message(chat_id=u[0], text=f"📢 پیام اطلاع‌رسانی:\n\n{msg}")
            sent += 1
        except:
            pass
    
    await update.message.reply_text(f"✅ پیام برای {sent} کاربر ارسال شد!")
    context.user_data['broadcast_msg'] = False

# ==================== main ====================
def main():
    init_db()
    
    app = Application.builder().token(TOKEN).build()
    
    # دستورات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex(r'^hahbyhh555466mamabbbnn$'), admin_panel))
    app.add_handler(MessageHandler(filters.PHOTO, handle_receipt))
    
    # هندلرهای ذخیره (با اولویت)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_product), group=1)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_edit_field), group=2)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, send_broadcast), group=3)
    
    # دکمه‌های منو
    app.add_handler(CallbackQueryHandler(show_products, pattern="^products$"))
    app.add_handler(CallbackQueryHandler(buy_product, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(back_to_main, pattern="^back_to_main$"))
    app.add_handler(CallbackQueryHandler(back_to_admin, pattern="^back_admin$"))
    app.add_handler(CallbackQueryHandler(support, pattern="^support$"))
    app.add_handler(CallbackQueryHandler(status, pattern="^status$"))
    
    # دکمه‌های پنل ادمین
    app.add_handler(CallbackQueryHandler(add_product, pattern="^add_product$"))
    app.add_handler(CallbackQueryHandler(edit_product, pattern="^edit_product$"))
    app.add_handler(CallbackQueryHandler(edit_product_form, pattern="^edit_product_"))
    app.add_handler(CallbackQueryHandler(edit_field, pattern="^edit_field_"))
    app.add_handler(CallbackQueryHandler(delete_product, pattern="^delete_product$"))
    app.add_handler(CallbackQueryHandler(delete_product_confirm, pattern="^delete_product_"))
    app.add_handler(CallbackQueryHandler(transactions, pattern="^transactions$"))
    app.add_handler(CallbackQueryHandler(stats, pattern="^stats$"))
    app.add_handler(CallbackQueryHandler(view_chats, pattern="^view_chats$"))
    app.add_handler(CallbackQueryHandler(edit_msgs, pattern="^edit_msgs$"))
    app.add_handler(CallbackQueryHandler(broadcast, pattern="^broadcast$"))
    
    # تأیید/رد تراکنش
    app.add_handler(CallbackQueryHandler(approve_transaction, pattern="^approve_"))
    app.add_handler(CallbackQueryHandler(reject_transaction, pattern="^reject_"))
    
    app.run_polling()

if __name__ == "__main__":
    main()
