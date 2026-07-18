from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import config
import database as db

def get_setting(key):
    return db.get_setting(key)

def main_menu():
    keyboard = [
        [InlineKeyboardButton(get_setting('btn_products'), callback_data="products")],
        [InlineKeyboardButton(get_setting('btn_support'), callback_data="support")],
        [InlineKeyboardButton(get_setting('btn_status'), callback_data="status")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome = get_setting('welcome_text').format(first_name=user.first_name)
    
    # ثبت کاربر در دیتابیس
    db.add_user(user.id, user.username, user.first_name)
    db.save_chat_message(user.id, user.username, user.first_name, "/start", True)
    
    await update.message.reply_text(welcome, reply_markup=main_menu())

async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    products = db.get_all_products()
    if not products:
        await query.message.edit_text(
            "😕 متأسفانه محصولی موجود نیست.",
            reply_markup=main_menu()
        )
        return
    keyboard = []
    for p in products:
        keyboard.append([InlineKeyboardButton(
            f"🔹 {p[1]} - {p[2]:,} تومان (موجودی: {p[3]})",
            callback_data=f"buy_{p[0]}"
        )])
    keyboard.append([InlineKeyboardButton(get_setting('btn_back'), callback_data="back")])
    await query.message.edit_text(
        "🛒 **لیست محصولات موجود:**\n\nروی محصول مورد نظر کلیک کن:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def start_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.split("_")[1])
    context.user_data['buying_product'] = product_id
    product = db.get_product(product_id)
    if not product:
        await query.message.edit_text("❌ محصول یافت نشد!", reply_markup=main_menu())
        return
    keyboard = [
        [InlineKeyboardButton(get_setting('btn_buy'), callback_data="send_receipt")],
        [InlineKeyboardButton(get_setting('btn_cancel'), callback_data="back")]
    ]
    await query.message.edit_text(
        f"💳 **اطلاعات واریز:**\n\n"
        f"💰 مبلغ: **{product[2]:,} تومان**\n"
        f"🏦 شماره کارت: `{config.CARD_NUMBER}`\n"
        f"👤 صاحب حساب: {config.CARD_OWNER}\n\n"
        "⬇️ بعد از واریز، رسید رو ارسال کن.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    product_id = context.user_data.get('buying_product')
    if not product_id:
        await update.message.reply_text("❌ لطفاً اول یک محصول رو انتخاب کن!")
        return
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    elif update.message.document:
        file_id = update.message.document.file_id
    else:
        await update.message.reply_text("❌ لطفاً یک عکس یا فایل ارسال کن.")
        return
    product = db.get_product(product_id)
    if not product:
        await update.message.reply_text("❌ محصول یافت نشد!")
        return
    trans_id = db.create_transaction(user.id, product_id, product[2], file_id)
    
    # ذخیره در تاریخچه چت
    db.save_chat_message(user.id, user.username, user.first_name, f"ارسال رسید برای محصول: {product[1]}", True)
    
    await update.message.reply_text(
        "✅ **رسید شما دریافت شد!**\n\n⏳ در حال بررسی توسط ادمین...\nبه محض تأیید، اپل‌آیدی برات ارسال میشه."
    )
    await send_to_admins(update, context, trans_id, user, file_id, product)

async def send_to_admins(update, context, trans_id, user, file_id, product):
    caption = (
        f"🆕 **درخواست خرید جدید**\n\n"
        f"👤 کاربر: [{user.first_name}](tg://user?id={user.id})\n"
        f"🆔 آیدی: `{user.id}`\n"
        f"📦 محصول: {product[1]}\n"
        f"💰 مبلغ: {product[2]:,} تومان\n"
        f"📝 کد تراکنش: `{trans_id}`\n\n"
        "✅ برای تأیید/رد از دکمه‌ها استفاده کن:"
    )
    keyboard = [
        [InlineKeyboardButton("✅ تأیید", callback_data=f"approve_{trans_id}")],
        [InlineKeyboardButton("❌ رد", callback_data=f"reject_{trans_id}")]
    ]
    for admin_id in config.ADMIN_IDS:
        try:
            await context.bot.send_photo(
                chat_id=admin_id,
                photo=file_id,
                caption=caption,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            print(f"❌ ارسال به ادمین ناموفق: {e}")

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.edit_text(
        "🏠 **منوی اصلی**\n\nلطفاً یکی از گزینه‌ها رو انتخاب کن:",
        reply_markup=main_menu()
    )

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.edit_text(
        "📞 **پشتیبانی**\n\nبرای ارتباط با پشتیبانی:\n🆔 @YourSupportUsername\n⏰ پاسخگویی: ۹ صبح تا ۱۲ شب",
        reply_markup=main_menu()
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    transactions = db.get_user_transactions(user_id)
    if not transactions:
        await query.message.edit_text("📊 **وضعیت خرید**\n\nشما هنوز خریدی انجام نداده‌اید.", reply_markup=main_menu())
        return
    text = "📊 **تاریخچه خرید شما:**\n\n"
    for t in transactions[:5]:
        status_emoji = {
            'pending': '⏳ در انتظار', 
            'approved': '✅ تأیید شده', 
            'rejected': '❌ رد شده',
            'delivered': '📦 ارسال شده'
        }.get(t[5], '❓ نامشخص')
        text += f"🔹 تراکنش #{t[0]}\n   مبلغ: {t[3]:,} تومان\n   وضعیت: {status_emoji}\n"
        if t[6]:
            text += f"   🔑 کد: `{t[6]}`\n"
        text += "\n"
    keyboard = [[InlineKeyboardButton(get_setting('btn_back'), callback_data="back")]]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
