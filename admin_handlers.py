from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import config
import database as db

# ========== پنل اصلی ادمین ==========
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in config.SECRET_ADMINS:
        await update.message.reply_text("⛔ شما دسترسی ندارید!")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 تراکنش‌های در انتظار", callback_data="pending_list")],
        [InlineKeyboardButton("➕ افزودن محصول", callback_data="add_product")],
        [InlineKeyboardButton("📝 ویرایش محصول", callback_data="edit_product")],
        [InlineKeyboardButton("🗑 حذف محصول", callback_data="delete_product")],
        [InlineKeyboardButton("📈 آمار فروش", callback_data="stats")],
        [InlineKeyboardButton("💬 مشاهده چت کاربران", callback_data="view_chats")],
        [InlineKeyboardButton("✏️ ویرایش ظاهر ربات", callback_data="edit_ui")],
        [InlineKeyboardButton("📢 پیام همگانی", callback_data="broadcast")],
    ]
    await update.message.reply_text(
        "🔐 **پنل مدیریت**\n\n"
        "لطفاً یکی از گزینه‌ها رو انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========== 1. تراکنش‌ها ==========
async def pending_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in config.SECRET_ADMINS:
        await query.message.edit_text("⛔ دسترسی ندارید!")
        return
    
    transactions = db.get_pending_transactions()
    
    if not transactions:
        await query.message.edit_text(
            "📊 **تراکنش‌های در انتظار**\n\n"
            "✅ هیچ تراکنش در انتظاری وجود ندارد.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back_admin")]
            ])
        )
        return
    
    text = "📊 **تراکنش‌های در انتظار:**\n\n"
    for t in transactions[:10]:
        product = db.get_product(t[2])
        product_name = product[1] if product else "نامشخص"
        text += f"🆔 #{t[0]} - {product_name}\n"
        text += f"👤 کاربر: `{t[1]}`\n"
        text += f"💰 {t[3]:,} تومان\n"
        text += f"📅 {t[7][:16]}\n\n"
    
    await query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_admin")]
        ])
    )

# ========== 2. تأیید تراکنش ==========
async def approve_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    admin_id = query.from_user.id
    
    if admin_id not in config.SECRET_ADMINS:
        await query.answer("⛔ شما دسترسی ندارید!", show_alert=True)
        return
    
    trans_id = int(query.data.split("_")[1])
    transaction = db.get_transaction(trans_id)
    
    if not transaction:
        await query.message.edit_caption("❌ تراکنش یافت نشد!")
        return
    
    if transaction[5] != 'pending':
        await query.message.edit_caption("❌ این تراکنش قبلاً پردازش شده!")
        return
    
    db.update_transaction_status(trans_id, 'approved')
    
    await query.message.edit_caption(
        f"✅ **تراکنش #{trans_id} تأیید شد!**\n\n"
        "👤 برای ارسال اپل‌آیدی به کاربر، روی دکمه زیر کلیک کن:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 ارسال پیام به خریدار", callback_data=f"send_product_{trans_id}")]
        ])
    )
    await query.answer("✅ تأیید شد!", show_alert=True)

# ========== 3. رد تراکنش ==========
async def reject_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    admin_id = query.from_user.id
    
    if admin_id not in config.SECRET_ADMINS:
        await query.answer("⛔ شما دسترسی ندارید!", show_alert=True)
        return
    
    trans_id = int(query.data.split("_")[1])
    transaction = db.get_transaction(trans_id)
    
    if not transaction:
        await query.message.edit_caption("❌ تراکنش یافت نشد!")
        return
    
    if transaction[5] != 'pending':
        await query.message.edit_caption("❌ این تراکنش قبلاً پردازش شده!")
        return
    
    db.update_transaction_status(trans_id, 'rejected')
    
    # اطلاع به کاربر
    try:
        await context.bot.send_message(
            chat_id=transaction[1],
            text="❌ متأسفانه رسید شما تأیید نشد.\n"
                 "لطفاً با پشتیبانی تماس بگیرید."
        )
    except:
        pass
    
    await query.message.edit_caption(f"❌ تراکنش {trans_id} رد شد.")
    await query.answer("❌ رد شد!", show_alert=True)

# ========== 4. ارسال دستی محصول ==========
async def send_product_manually(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    trans_id = int(query.data.split("_")[2])
    transaction = db.get_transaction(trans_id)
    
    if not transaction:
        await query.message.edit_text("❌ تراکنش یافت نشد!")
        return
    
    user_id = transaction[1]
    product = db.get_product(transaction[2])
    product_name = product[1] if product else "نامشخص"
    
    context.user_data['manual_reply_user'] = user_id
    context.user_data['manual_trans_id'] = trans_id
    
    await query.message.edit_text(
        f"✏️ **ارسال اطلاعات به خریدار**\n\n"
        f"👤 کاربر: `{user_id}`\n"
        f"📦 محصول: {product_name}\n\n"
        "📩 **لطفاً پیام حاوی اپل‌آیدی و رمز را ارسال کنید.**"
    )

# ========== 5. افزودن محصول ==========
async def add_product_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in config.SECRET_ADMINS:
        await query.message.edit_text("⛔ دسترسی ندارید!")
        return
    
    await query.message.edit_text(
        "➕ **افزودن محصول جدید**\n\n"
        "لطفاً اطلاعات محصول رو به این ترتیب وارد کن (هر خط یک مورد):\n\n"
        "1️⃣ نام محصول\n"
        "2️⃣ قیمت (تومان - فقط عدد)\n"
        "3️⃣ تعداد موجودی (عدد)\n"
        "4️⃣ لیست کدها (با کاما جدا کن)\n\n"
        "📌 مثال:\n"
        "اپل‌آیدی آمریکا\n"
        "15000\n"
        "10\n"
        "user1|pass1,user2|pass2,user3|pass3"
    )
    context.user_data['awaiting_add_product'] = True

async def save_new_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in config.SECRET_ADMINS or not context.user_data.get('awaiting_add_product'):
        return
    
    lines = update.message.text.strip().split('\n')
    if len(lines) < 4:
        await update.message.reply_text(
            "❌ فرمت اشتباه! ۴ خط اطلاعات وارد کن:\n"
            "نام\nقیمت\nتعداد\nکدها"
        )
        return
    
    try:
        name = lines[0].strip()
        price = int(lines[1].strip())
        stock = int(lines[2].strip())
        codes = lines[3].strip()
        
        product_id = db.add_product(name, price, stock, codes)
        await update.message.reply_text(
            f"✅ **محصول با موفقیت اضافه شد!**\n\n"
            f"🆔 شناسه: {product_id}\n"
            f"📦 نام: {name}\n"
            f"💰 قیمت: {price:,} تومان\n"
            f"📊 موجودی: {stock}"
        )
        context.user_data['awaiting_add_product'] = False
        
    except ValueError:
        await update.message.reply_text("❌ قیمت و تعداد باید عدد باشند!")

# ========== 6. ویرایش محصول ==========
async def edit_product_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in config.SECRET_ADMINS:
        await query.message.edit_text("⛔ دسترسی ندارید!")
        return
    
    products = db.get_all_products()
    if not products:
        await query.message.edit_text("❌ هیچ محصولی برای ویرایش وجود ندارد!")
        return
    
    keyboard = []
    for p in products:
        keyboard.append([InlineKeyboardButton(
            f"📝 {p[1]} - {p[2]:,} تومان", 
            callback_data=f"edit_product_{p[0]}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_admin")])
    
    await query.message.edit_text(
        "📝 **انتخاب محصول برای ویرایش:**",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def edit_product_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    product_id = int(query.data.split("_")[2])
    product = db.get_product(product_id)
    
    if not product:
        await query.message.edit_text("❌ محصول یافت نشد!")
        return
    
    context.user_data['editing_product_id'] = product_id
    
    await query.message.edit_text(
        f"📝 **ویرایش محصول: {product[1]}**\n\n"
        f"🆔 شناسه: {product[0]}\n"
        f"📦 نام: {product[1]}\n"
        f"💰 قیمت: {product[2]:,} تومان\n"
        f"📊 موجودی: {product[3]}\n\n"
        "❓ کدام بخش رو می‌خوای ویرایش کنی؟",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 نام", callback_data=f"edit_field_name_{product_id}")],
            [InlineKeyboardButton("💰 قیمت", callback_data=f"edit_field_price_{product_id}")],
            [InlineKeyboardButton("📊 موجودی", callback_data=f"edit_field_stock_{product_id}")],
            [InlineKeyboardButton("🔑 کدها", callback_data=f"edit_field_codes_{product_id}")],
            [InlineKeyboardButton("🔙 انصراف", callback_data="back_admin")]
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
    
    field_names = {
        'name': 'نام جدید',
        'price': 'قیمت جدید (عدد)',
        'stock': 'موجودی جدید (عدد)',
        'codes': 'کدهای جدید (با کاما جدا کن)'
    }
    
    await query.message.edit_text(
        f"✏️ **ویرایش {field_names[field]}**\n\n"
        f"مقدار جدید رو وارد کن:"
    )

async def save_edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in config.SECRET_ADMINS:
        return
    
    product_id = context.user_data.get('editing_product_id')
    field = context.user_data.get('editing_field')
    
    if not product_id or not field:
        return
    
    new_value = update.message.text.strip()
    
    if field in ['price', 'stock']:
        try:
            new_value = int(new_value)
        except ValueError:
            await update.message.reply_text("❌ مقدار باید عدد باشد!")
            return
    
    db.update_product(product_id, **{field: new_value})
    
    await update.message.reply_text(
        f"✅ **فیلد با موفقیت به‌روز شد!**\n"
        f"مقدار جدید: `{new_value}`"
    )
    
    context.user_data['editing_field'] = None
    context.user_data['editing_product_id'] = None

# ========== 7. حذف محصول ==========
async def delete_product_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in config.SECRET_ADMINS:
        await query.message.edit_text("⛔ دسترسی ندارید!")
        return
    
    products = db.get_all_products()
    if not products:
        await query.message.edit_text("❌ هیچ محصولی برای حذف وجود ندارد!")
        return
    
    keyboard = []
    for p in products:
        keyboard.append([InlineKeyboardButton(
            f"🗑 {p[1]} - {p[2]:,} تومان", 
            callback_data=f"delete_product_{p[0]}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_admin")])
    
    await query.message.edit_text(
        "🗑 **انتخاب محصول برای حذف:**",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def confirm_delete_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    product_id = int(query.data.split("_")[2])
    product = db.get_product(product_id)
    
    if not product:
        await query.message.edit_text("❌ محصول یافت نشد!")
        return
    
    await query.message.edit_text(
        f"⚠️ **آیا مطمئنی؟**\n\n"
        f"📦 محصول: {product[1]}\n"
        f"💰 قیمت: {product[2]:,} تومان\n"
        f"📊 موجودی: {product[3]}\n\n"
        "این عملیات غیرقابل بازگشت است!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ بله، حذف کن", callback_data=f"delete_confirm_{product_id}")],
            [InlineKeyboardButton("❌ لغو", callback_data="delete_product")]
        ])
    )

async def delete_product_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    product_id = int(query.data.split("_")[2])
    product = db.get_product(product_id)
    
    if product:
        db.delete_product(product_id)
        await query.message.edit_text(
            f"✅ **محصول '{product[1]}' با موفقیت حذف شد!**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="back_admin")]
            ])
        )
    else:
        await query.message.edit_text("❌ محصول یافت نشد!")

# ========== 8. آمار ==========
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in config.SECRET_ADMINS:
        await query.message.edit_text("⛔ دسترسی ندارید!")
        return
    
    stats = db.get_stats()
    text = (
        f"📈 **آمار فروشگاه**\n\n"
        f"👥 تعداد کاربران: {stats['total_users']}\n"
        f"📦 تعداد تراکنش‌ها: {stats['total_transactions']}\n"
        f"💰 مجموع فروش: {stats['total_sales']:,} تومان\n"
        f"⏳ در انتظار تأیید: {stats['pending']}"
    )
    await query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_admin")]
        ])
    )

# ========== 9. مشاهده چت کاربران ==========
async def view_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in config.SECRET_ADMINS:
        await query.message.edit_text("⛔ دسترسی ندارید!")
        return
    
    users = db.get_all_users()
    if not users:
        await query.message.edit_text(
            "💬 **چت کاربران**\n\n"
            "هیچ کاربری هنوز چت نکرده.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back_admin")]
            ])
        )
        return
    
    keyboard = []
    for u in users:
        user_id, username, first_name, _ = u
        label = f"👤 {first_name or 'کاربر'}" + (f" (@{username})" if username else "")
        keyboard.append([InlineKeyboardButton(label, callback_data=f"chat_user_{user_id}")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_admin")])
    
    await query.message.edit_text(
        "💬 **انتخاب کاربر:**\n\n"
        "روی هر کاربر کلیک کن تا تاریخچه چتش رو ببینی.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_user_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in config.SECRET_ADMINS:
        await query.message.edit_text("⛔ دسترسی ندارید!")
        return
    
    target_user_id = int(query.data.split("_")[2])
    user_info = db.get_user_info(target_user_id)
    messages = db.get_user_chat_history(target_user_id, 20)
    
    if not messages:
        await query.message.edit_text("❌ این کاربر پیامی نداشته.")
        return
    
    name = user_info[1] or "کاربر"
    username = f" (@{user_info[0]})" if user_info[0] else ""
    
    text = f"💬 **چت با {name}{username}**\n\n"
    text += f"🆔 آیدی: `{target_user_id}`\n\n"
    
    for msg in reversed(messages):
        sender = "👤 **کاربر:**" if msg[1] else "🤖 **ربات:**"
        text += f"{sender}\n`{msg[0][:100]}`\n"
        text += f"_🕐 {msg[2][:16]}_\n\n"
        if len(text) > 3500:
            break
    
    keyboard = [
        [InlineKeyboardButton("📥 ارسال پیام", callback_data=f"msg_user_{target_user_id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="view_chats")]
    ]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ========== 10. ارسال پیام به کاربر ==========
async def send_message_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in config.SECRET_ADMINS:
        await query.message.edit_text("⛔ دسترسی ندارید!")
        return
    
    target_user_id = int(query.data.split("_")[2])
    context.user_data['reply_to_user'] = target_user_id
    
    await query.message.edit_text(
        f"✏️ **ارسال پیام به کاربر**\n\n"
        f"🆔 آیدی: `{target_user_id}`\n\n"
        "📝 پیام خود را ارسال کن."
    )

async def handle_reply_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in config.SECRET_ADMINS:
        return
    
    target_user_id = context.user_data.get('reply_to_user')
    if not target_user_id:
        return
    
    message_text = update.message.text
    
    try:
        await context.bot.send_message(
            chat_id=target_user_id,
            text=f"📩 **پیام از ادمین:**\n\n{message_text}"
        )
        await update.message.reply_text("✅ پیام با موفقیت ارسال شد!")
        db.save_chat_message(target_user_id, None, None, f"[ادمین] {message_text}", False)
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}")
    
    context.user_data['reply_to_user'] = None

# ========== 11. ویرایش ظاهر ربات ==========
async def edit_ui_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in config.SECRET_ADMINS:
        await query.message.edit_text("⛔ دسترسی ندارید!")
        return
    
    keyboard = [
        [InlineKeyboardButton("📝 پیام خوش‌آمدگویی", callback_data="edit_setting_welcome_text")],
        [InlineKeyboardButton("🔹 دکمه محصولات", callback_data="edit_setting_btn_products")],
        [InlineKeyboardButton("🔹 دکمه پشتیبانی", callback_data="edit_setting_btn_support")],
        [InlineKeyboardButton("🔹 دکمه وضعیت خرید", callback_data="edit_setting_btn_status")],
        [InlineKeyboardButton("🔹 دکمه بازگشت", callback_data="edit_setting_btn_back")],
        [InlineKeyboardButton("🔹 دکمه ارسال رسید", callback_data="edit_setting_btn_buy")],
        [InlineKeyboardButton("🔹 دکمه انصراف", callback_data="edit_setting_btn_cancel")],
        [InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="back_admin")],
    ]
    await query.message.edit_text(
        "✏️ **ویرایش ظاهر ربات**\n\n"
        "روی هر گزینه کلیک کن تا متن جدید رو وارد کنی:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def edit_setting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    key = query.data.replace("edit_setting_", "")
    context.user_data['editing_key'] = key
    current_text = db.get_setting(key)
    
    await query.message.edit_text(
        f"✏️ **ویرایش**\n\n"
        f"🆔 کلید: `{key}`\n"
        f"📝 متن فعلی:\n`{current_text}`\n\n"
        "📩 **متن جدید رو تایپ و ارسال کن.**"
    )

async def save_ui_setting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in config.SECRET_ADMINS:
        return
    
    key = context.user_data.get('editing_key')
    if not key:
        return
    
    new_value = update.message.text
    db.update_setting(key, new_value)
    
    await update.message.reply_text(f"✅ **متن '{key}' با موفقیت به‌روز شد!**")
    context.user_data['editing_key'] = None

# ========== 12. پیام همگانی ==========
async def broadcast_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in config.SECRET_ADMINS:
        await query.message.edit_text("⛔ دسترسی ندارید!")
        return
    
    await query.message.edit_text(
        "📢 **ارسال پیام همگانی**\n\n"
        "لطفاً پیامی که می‌خواید برای **همه کاربران** ارسال بشه رو تایپ کنید.\n"
        "⏳ ممکنه چند دقیقه طول بکشه."
    )
    context.user_data['awaiting_broadcast'] = True

async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in config.SECRET_ADMINS or not context.user_data.get('awaiting_broadcast'):
        return
    
    text = update.message.text
    await update.message.reply_text("⏳ در حال ارسال پیام به همه کاربران...")
    
    users = db.get_all_users_for_broadcast()
    success_count = 0
    fail_count = 0
    
    for uid in users:
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=f"📢 **پیام اطلاع‌رسانی:**\n\n{text}"
            )
            success_count += 1
        except Exception:
            fail_count += 1
    
    context.user_data['awaiting_broadcast'] = False
    await update.message.reply_text(
        f"✅ **پیام همگانی ارسال شد!**\n\n"
        f"📨 ارسال موفق: {success_count}\n"
        f"❌ ارسال ناموفق: {fail_count}"
    )

# ========== 13. بازگشت به پنل ==========
async def back_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await admin_panel(update, context)

# ========== 14. هندلر پیام ادمین (ارسال دستی محصول) ==========
async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in config.SECRET_ADMINS:
        return
    
    target_user_id = context.user_data.get('manual_reply_user')
    trans_id = context.user_data.get('manual_trans_id')
    
    if not target_user_id:
        return
    
    message_text = update.message.text
    
    try:
        await context.bot.send_message(
            chat_id=target_user_id,
            text=f"🎉 **خرید شما تأیید شد!**\n\n"
                 f"🔑 اطلاعات محصول شما:\n"
                 f"`{message_text}`\n\n"
                 "📌 لطفاً رمز را تغییر دهید.\n"
                 "🙏 ممنون از خرید شما!"
        )
        await update.message.reply_text("✅ اطلاعات با موفقیت برای کاربر ارسال شد!")
        db.update_transaction_status(trans_id, 'delivered')
        db.save_chat_message(target_user_id, None, None, f"[ادمین] {message_text}", False)
        
        context.user_data['manual_reply_user'] = None
        context.user_data['manual_trans_id'] = None
        
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در ارسال: {str(e)}")
