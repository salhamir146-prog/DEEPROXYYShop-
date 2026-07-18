import json
import os
import logging
import random
import zipfile
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# ==================== تنظیمات ====================
TOKEN = "8565413645:AAGm027C1AwMH9ZcaRkvuzwi2IXzfzMGOck"
ADMIN_IDS = [8706836237, 8911508795]  # 👥 هر دو ادمین با دسترسی کامل

# ==================== فایل‌های دیتابیس ====================
APPLE_IDS_FILE = "apple_ids.json"
SETTINGS_FILE = "settings.json"
SALES_FILE = "sales.json"
PENDING_FILE = "pending.json"
WALLETS_FILE = "wallets.json"
CHANNEL_FILE = "channel.json"
START_TEXT_FILE = "start_text.json"
BOT_STATUS_FILE = "bot_status.json"
COUPONS_FILE = "coupons.json"

# ==================== توابع مدیریت دیتابیس ====================
def load_json(file_path, default_data):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f) or default_data
        except:
            return default_data
    save_json(file_path, default_data)
    return default_data

def save_json(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ==================== مقداردهی اولیه ====================
settings = load_json(SETTINGS_FILE, {
    "card_number": "6219861950901305", 
    "card_holder": "محمد مهدی جاودان", 
    "price_per_item": 300000,
    "ref_percent": 10,
    "support_username": "Owner_Admin",
    "min_bonus": 1000,
    "max_bonus": 3000
})
bot_status = load_json(BOT_STATUS_FILE, {"enabled": True})
channel_config = load_json(CHANNEL_FILE, {"channel_id": "", "channel_link": "https://t.me/Nexo_IP", "enabled": False})
apple_ids_list = load_json(APPLE_IDS_FILE, [])
sales = load_json(SALES_FILE, [])
pending_payments = load_json(PENDING_FILE, {})
wallets = load_json(WALLETS_FILE, {})
coupons = load_json(COUPONS_FILE, {})

default_start_text = (
    "🛍 *فروشگاه پیشرفته اپل آیدی*\n\n"
    "💰 موجودی کیف پول: {balance:,} تومان\n"
    "💵 قیمت هر اپل آیدی: {price:,} تومان\n\n"
    "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:"
)
start_text_config = load_json(START_TEXT_FILE, {"text": default_start_text})

# ==================== توابع کیف پول و کاربر ====================
def get_wallet(user_id):
    user_id = str(user_id)
    if user_id not in wallets:
        wallets[user_id] = {
            "balance": 0, "total_deposit": 0, "total_spent": 0,
            "referred_by": None, "last_daily_bonus": None, "is_banned": False,
            "joined_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "chat_logs": []  # 📜 محل ذخیره چت‌های کاربر
        }
        save_json(WALLETS_FILE, wallets)
    return wallets[user_id]

def add_balance(user_id, amount):
    user_id = str(user_id)
    wallet = get_wallet(user_id)
    wallet["balance"] += amount
    save_json(WALLETS_FILE, wallets)
    return wallet["balance"]

def subtract_balance(user_id, amount):
    user_id = str(user_id)
    wallet = get_wallet(user_id)
    if wallet["balance"] < amount: return False
    wallet["balance"] -= amount
    wallet["total_spent"] += amount
    save_json(WALLETS_FILE, wallets)
    return True

# ==================== دکوراتورها و امنیت ربات ====================
def require_user_access(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        wallet = get_wallet(user_id)
        
        if wallet.get("is_banned", False):
            if update.callback_query: await update.callback_query.answer("🚫 شما از سرور ربات مسدود شده‌اید!", show_alert=True)
            else: await update.message.reply_text("🚫 دسترسی شما به ربات مسدود شده است.")
            return
        
        if not bot_status.get("enabled", True) and user_id not in ADMIN_IDS:
            if update.callback_query: await update.callback_query.answer("⛔ ربات در حال آپدیت است!", show_alert=True)
            else: await update.message.reply_text("⛔ ربات در حال آپدیت است! لطفاً چند دقیقه دیگر مجدداً تلاش کنید.")
            return
            
        if channel_config.get("enabled", False) and user_id not in ADMIN_IDS:
            channel_id = channel_config.get("channel_id", "")
            if channel_id:
                try:
                    member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
                    if member.status not in ["member", "administrator", "creator"]: raise Exception()
                except:
                    keyboard = [
                        [InlineKeyboardButton("📢 عضویت در کانال", url=channel_config.get("channel_link"))],
                        [InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership")]
                    ]
                    text = "🔒 *عضویت اجباری*\n\nبرای استفاده از ربات ابتدا باید عضو کانال ما شوید."
                    if update.callback_query:
                        await update.callback_query.answer("🔒 ابتدا عضو کانال شوید!", show_alert=True)
                        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
                    else:
                        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
                    return
                    
        return await func(update, context, *args, **kwargs)
    return wrapper

# ==================== دستورات عمومی و کاربر ====================
@require_user_access
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        user_id = query.from_user.id
        await query.answer()
    else:
        user_id = update.message.from_user.id
        if context.args and context.args[0].startswith("ref_"):
            wallet = get_wallet(user_id)
            ref_id = context.args[0].split("_")[1]
            if ref_id != str(user_id) and str(ref_id) in wallets and not wallet.get("referred_by"):
                wallet["referred_by"] = ref_id
                save_json(WALLETS_FILE, wallets)
                try: await context.bot.send_message(chat_id=int(ref_id), text="🎉 یک کاربر جدید با لینک شما وارد ربات شد!")
                except: pass

    wallet = get_wallet(user_id)
    keyboard = [
        [InlineKeyboardButton("🛒 خرید اپل آیدی", callback_data="buy_apple"), InlineKeyboardButton("📦 خریدهای من", callback_data="my_orders")],
        [InlineKeyboardButton("💰 کیف پول", callback_data="my_wallet"), InlineKeyboardButton("💳 شارژ حساب", callback_data="charge_wallet")],
        [InlineKeyboardButton("🎁 هدیه روزانه", callback_data="daily_bonus"), InlineKeyboardButton("🔗 زیرمجموعه‌گیری", callback_data="referral_menu")],
        [InlineKeyboardButton("📞 پشتیبانی ربات", callback_data="support")],
        [InlineKeyboardButton("🎟 ثبت کد هدیه", callback_data="use_coupon"), InlineKeyboardButton("💸 انتقال موجودی", callback_data="transfer_balance")]
    ]
    if int(user_id) in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("⚙️ پنل مدیریت ادمین", callback_data="admin_panel")])
    
    formatted_text = start_text_config.get("text", default_start_text).format(balance=wallet['balance'], price=settings['price_per_item'])
    if update.callback_query: await query.edit_message_text(formatted_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else: await update.message.reply_text(formatted_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# ==================== قابلیت‌های کاربر ====================
@require_user_access
async def daily_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    wallet = get_wallet(user_id)
    
    now = datetime.now()
    last_bonus = wallet.get("last_daily_bonus")
    if last_bonus and datetime.strptime(last_bonus, "%Y-%m-%d %H:%M:%S") + timedelta(days=1) > now:
        await query.edit_message_text("❌ هدیه امروز رو گرفتی رفیق! ۲۴ ساعت بعد بیا.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")]]))
        return
        
    gift = random.randint(settings.get("min_bonus", 1000), settings.get("max_bonus", 3000))
    add_balance(user_id, gift)
    wallet["last_daily_bonus"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_json(WALLETS_FILE, wallets)
    await query.edit_message_text(f"🎁 *تبریک!*\n\nمبلغ *{gift:,}* تومان شانس‌کی به کیف پولت اضافه شد!", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("دمت گرم 😍", callback_data="back_to_menu")]]))

@require_user_access
async def referral_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    bot_info = await context.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    invited_count = sum(1 for u in wallets.values() if u.get("referred_by") == user_id)
    
    text = (
        f"🔗 *سیستم زیرمجموعه‌گیری*\n\n"
        f"لینک رو بفرست برای دوستات. با هر شارژ حساب اونا، *{settings.get('ref_percent', 10)}%* سود واریز میشه به حساب تو!\n\n"
        f"👥 زیرمجموعه‌های تو: {invited_count} نفر\n"
        f"🔗 لینک تو:\n`{ref_link}`"
    )
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")]]))

@require_user_access
async def use_coupon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['user_action'] = 'submit_coupon'
    await query.edit_message_text("🎟 لطفاً کد تخفیف/هدیه خود را وارد کنید:")

# 💸 قابلیت جدید کاربران: انتقال موجودی به رفیق
@require_user_access
async def transfer_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['user_action'] = 'transfer_money'
    await query.edit_message_text("💸 *بخش کارت‌به‌کارت موجودی*\n\nلطفاً آیدی عددی مقصد و مبلغ انتقال را به این فرمت بفرستید:\n`آیدی مقصد:مبلغ`\n\nمثال: `8706836237:25000`", parse_mode="Markdown")

async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    user_sales = [s for s in sales if str(s["user_id"]) == user_id]
    if not user_sales:
        await query.edit_message_text("📦 خریدی نداری رفیق.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")]]))
        return
    text = "📦 *لیست خریدهای شما:*\n\n"
    for idx, sale in enumerate(user_sales, 1):
        text += f"🛒 *خرید {idx}* ({sale.get('count')} عدد):\n"
        for item in sale.get("items", []): text += f"🔑 `{item}`\n"
        text += "—" * 12 + "\n"
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")]]))

# ==================== سیستم خرید و مالی ====================
@require_user_access
async def buy_apple(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    wallet = get_wallet(user_id)
    total_apple = len(apple_ids_list)
    if total_apple == 0:
        await query.edit_message_text("❌ موجودی انبار صفره! به زودی شارژ میشه.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")]]))
        return
    keyboard = []
    for i in range(1, min(total_apple, 10) + 1):
        price = i * settings['price_per_item']
        keyboard.append([InlineKeyboardButton(f"📱 {i} عدد - {price:,} تومان", callback_data=f"buy_{i}")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")])
    await query.edit_message_text(f"📱 *انتخاب تعداد خرید:*\n\n💰 موجودی تو: {wallet['balance']:,} تومان\n📦 انبار ربات: {total_apple} عدد\n💵 قیمت هر عدد: {settings['price_per_item']:,} تومان", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

@require_user_access
async def buy_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    count = int(query.data.split("_")[1])
    total_price = count * settings['price_per_item']
    wallet = get_wallet(user_id)
    
    global apple_ids_list
    if len(apple_ids_list) < count:
        await query.edit_message_text("❌ موجودی انبار تغییر کرد!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="buy_apple")]]))
        return
    if wallet['balance'] < total_price:
        await query.edit_message_text(f"❌ موجودی کافی نیست!\n💰 موجودی: {wallet['balance']:,} تومان\n💵 هزینه: {total_price:,} تومان", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 شارژ حساب", callback_data="charge_wallet")], [InlineKeyboardButton("🔙 بازگشت", callback_data="buy_apple")]]))
        return
        
    subtract_balance(user_id, total_price)
    selected_accounts = apple_ids_list[:count]
    apple_ids_list = apple_ids_list[count:]
    save_json(APPLE_IDS_FILE, apple_ids_list)
    
    sales.append({"user_id": user_id, "count": count, "total_price": total_price, "items": selected_accounts, "date": str(datetime.now())})
    save_json(SALES_FILE, sales)
    
    text = "🎉 *خرید موفق!*\n\n📧 اطلاعات اکانت‌ها:\n━━━━━━━━━━━━━━━━\n"
    for i, acc in enumerate(selected_accounts, 1): text += f"{i}. `{acc}`\n"
    text += "━━━━━━━━━━━━━━━━\n🔒 رفیق حتماً رمز عبور اکانت رو تغییر بده!"
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back_to_menu")]]))
    for adm in ADMIN_IDS:
        try: await context.bot.send_message(chat_id=adm, text=f"🛒 *فروش جدید!*\n👤 کاربر: {user_id}\n📦 تعداد: {count} عدد\n💰 مبلغ: {total_price:,} تومان")
        except: pass

@require_user_access
async def my_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    wallet = get_wallet(user_id)
    await query.edit_message_text(f"💰 *وضعیت حساب شما:*\n\n💵 موجودی فعلی: {wallet['balance']:,} تومان\n💳 کارت واریز:\n`{settings['card_number']}`\n👤 بنام: {settings['card_holder']}", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 شارژ حساب", callback_data="charge_wallet")], [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")]]))

@require_user_access
async def charge_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("💳 ۵۰,۰۰۰", callback_data="charge_50000"), InlineKeyboardButton("💳 ۱۰۰,۰۰۰", callback_data="charge_100000")],
        [InlineKeyboardButton("💳 ۲۰۰,۰۰۰", callback_data="charge_200000"), InlineKeyboardButton("💳 ۵۰۰,۰۰۰", callback_data="charge_500000")],
        [InlineKeyboardButton("✏️ ورود مبلغ دلخواه", callback_data="charge_custom")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")]
    ]
    await query.edit_message_text("💳 مبلغ شارژ رو انتخاب کن:", reply_markup=InlineKeyboardMarkup(keyboard))

@require_user_access
async def charge_custom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['user_action'] = 'charge_custom'
    await query.edit_message_text("✏️ مبلغ مورد نظر رو به عدد و به *تومان* بفرست:")

@require_user_access
async def charge_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    amount = int(query.data.split("_")[1])
    await initiate_payment(query.from_user.id, amount, context, query)

async def initiate_payment(user_id, amount, context, query=None):
    user_id = str(user_id)
    pending_payments[user_id] = {"amount": amount, "status": "waiting"}
    save_json(PENDING_FILE, pending_payments)
    text = f"💳 *درخواست شارژ*\n\n💰 مبلغ: *{amount:,}* تومان\n📌 کارت:\n`{settings['card_number']}`\n👤 بنام: {settings['card_holder']}\n\n✅ پس از واریز، *عکس رسید* رو توی همین چت بفرست."
    if query: await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 انصراف", callback_data="back_to_menu")]]))
    else: await context.bot.send_message(chat_id=int(user_id), text=text, parse_mode="Markdown")

async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id not in pending_payments or pending_payments[user_id]["status"] != "waiting":
        await update.message.reply_text("❌ رفیق فاکتور فعالی نداری.")
        return
    photo_file = update.message.photo[-1].file_id
    pending_payments[user_id].update({"photo": photo_file, "status": "pending"})
    save_json(PENDING_FILE, pending_payments)
    
    keyboard = [[InlineKeyboardButton("✅ تایید رسید", callback_data=f"approve_{user_id}"), InlineKeyboardButton("❌ رد رسید", callback_data=f"reject_{user_id}")]]
    for adm in ADMIN_IDS:
        try: await context.bot.send_photo(chat_id=adm, photo=photo_file, caption=f"📩 *رسید جدید!*\n👤 کاربر: `{user_id}`\n💰 مبلغ: {pending_payments[user_id]['amount']:,} تومان", reply_markup=InlineKeyboardMarkup(keyboard))
        except: pass
    await update.message.reply_text("✅ رسید برای ادمین‌ها ارسال شد.")

async def approve_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in ADMIN_IDS: return
    user_id = query.data.split("_")[1]
    if user_id not in pending_payments: return
    
    amount = pending_payments[user_id]["amount"]
    new_balance = add_balance(user_id, amount)
    
    ref_id = get_wallet(user_id).get("referred_by")
    if ref_id and str(ref_id) in wallets:
        bonus = int(amount * settings.get('ref_percent', 10) / 100)
        add_balance(ref_id, bonus)
        try: await context.bot.send_message(chat_id=int(ref_id), text=f"💰 *سود دعوت!*\nمبلغ *{bonus:,}* تومان پورسانت واریز شد!")
        except: pass

    try: await context.bot.send_message(chat_id=int(user_id), text=f"✅ *رسید تایید شد!*\n💰 مبلغ {amount:,} تومان هدیه به حسابت اضافه شد.")
    except: pass
    del pending_payments[user_id]
    save_json(PENDING_FILE, pending_payments)
    await query.edit_message_text(f"✅ رسید کاربر {user_id} تایید شد.")

async def reject_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in ADMIN_IDS: return
    user_id = query.data.split("_")[1]
    if user_id not in pending_payments: return
    try: await context.bot.send_message(chat_id=int(user_id), text="❌ رسید واریزی شما رد شد!")
    except: pass
    del pending_payments[user_id]
    save_json(PENDING_FILE, pending_payments)
    await query.edit_message_text("❌ رسید رد شد.")

@require_user_access
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(f"📞 *پشتیبانی فروشگاه:*\n\n👤 @{settings.get('support_username', 'Owner_Admin')}", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")]]))

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

# ==================== پنل مدیریت طبقه‌بندی شده ====================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in ADMIN_IDS: return
    keyboard = [
        [InlineKeyboardButton("📦 انبار و محصولات", callback_data="admin_m_prod"), InlineKeyboardButton("👥 مدیریت اعضا", callback_data="admin_m_user")],
        [InlineKeyboardButton("🎨 شخصی‌سازی ربات", callback_data="admin_m_config"), InlineKeyboardButton("📊 آمار و سیستم", callback_data="admin_m_sys")],
        [InlineKeyboardButton("🔙 بازگشت به منوی کاربر", callback_data="back_to_menu")]
    ]
    await query.edit_message_text("⚙️ *به پنل مدیریت چندگانه ارشد خوش آمدید رفیق!*\nدسته‌بندی مورد نظر رو انتخاب کن:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def menu_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ افزودن اپل آیدی", callback_data="admin_add_ids"), InlineKeyboardButton("📋 مشاهده انبار", callback_data="admin_list_ids")],
        [InlineKeyboardButton("💰 تغییر قیمت اکانت", callback_data="admin_change_price"), InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
    ]
    await update.callback_query.edit_message_text("📦 *بخش مدیریت محصولات و انبار:*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def menu_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔍 رادار و جستجوی کاربر", callback_data="admin_search_user")],
        [InlineKeyboardButton("🎟 ساخت کد تخفیف/هدیه", callback_data="admin_add_coupon")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
    ]
    await update.callback_query.edit_message_text("👥 *بخش مدیریت و رادار کاربران:*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def menu_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💳 تغییر کارت و صاحب حساب", callback_data="admin_change_card")],
        [InlineKeyboardButton("📞 تغییر آیدی پشتیبانی", callback_data="admin_set_support")],
        [InlineKeyboardButton("🔗 تغییر درصد زیرمجموعه", callback_data="admin_set_ref")],
        [InlineKeyboardButton("🎁 تغییر بازه هدیه روزانه", callback_data="admin_set_bonus")],
        [InlineKeyboardButton("📝 تغییر متن استارت", callback_data="admin_change_start")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
    ]
    await update.callback_query.edit_message_text("🎨 *تنظیمات اتمی و شخصی‌سازی ربات:*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def menu_system(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📢 پیام همگانی", callback_data="admin_broadcast"), InlineKeyboardButton("📊 آمار مالی", callback_data="admin_stats")],
        [InlineKeyboardButton("📢 کانال جوین اجباری", callback_data="admin_channel"), InlineKeyboardButton("🔄 سوئیچ آپدیت ربات", callback_data="admin_toggle_bot")],
        [InlineKeyboardButton("💾 پشتیبان‌گیری جادویی (Backup)", callback_data="admin_backup")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
    ]
    await update.callback_query.edit_message_text("📊 *بخش آمار و ابزارهای سیستم:*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# ==================== هندلرهای توابع ادمین ====================
async def admin_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    zip_name = "database_backup.zip"
    files = [APPLE_IDS_FILE, SETTINGS_FILE, SALES_FILE, PENDING_FILE, WALLETS_FILE, CHANNEL_FILE, START_TEXT_FILE, BOT_STATUS_FILE, COUPONS_FILE]
    with zipfile.ZipFile(zip_name, 'w') as zipf:
        for f in files:
            if os.path.exists(f): zipf.write(f)
    with open(zip_name, 'rb') as f:
        await context.bot.send_document(chat_id=query.from_user.id, document=f, filename=f"Backup_{datetime.now().strftime('%Y%m%d_%H%M')}.zip", caption="💾 بکاپ کامل سیستم صادر شد رفیق.")
    os.remove(zip_name)

async def admin_search_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['admin_action'] = 'search_user'
    await update.callback_query.edit_message_text("🔍 آیدی عددی کاربر هدف را ارسال کنید:")

async def admin_add_coupon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['admin_action'] = 'add_coupon'
    await update.callback_query.edit_message_text("🎟 کد تخفیف و مبلغ را بفرستید.\nفرمت: `کد:مبلغ`\nمثال: `عيدانه:50000`")

# ==================== مدیریت ورودی‌های متنی و لاگ چت ====================
async def handle_text_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    
    if text == '/cancel':
        context.user_data.clear()
        await update.message.reply_text("❌ عملیات لغو شد.")
        return

    # 📜 لاگ کردن پیام کاربر (مخصوص قابلیت جاسوسی مجاز!)
    if user_id not in ADMIN_IDS:
        wallet = get_wallet(user_id)
        if "chat_logs" not in wallet: wallet["chat_logs"] = []
        time_str = datetime.now().strftime("%m-%d %H:%M")
        wallet["chat_logs"].append(f"[{time_str}] 👤: {text}")
        if len(wallet["chat_logs"]) > 15: wallet["chat_logs"].pop(0)  # ذخیره حداکثر ۱۵ چت آخر
        save_json(WALLETS_FILE, wallets)

    # منطق کاربر عادی
    if user_id not in ADMIN_IDS:
        u_action = context.user_data.get('user_action')
        if u_action == 'charge_custom':
            try:
                amt = int(text)
                if amt < 10000: raise Exception()
                context.user_data.clear()
                await initiate_payment(user_id, amt, context)
            except: await update.message.reply_text("❌ عدد معتبر بزرگتر از ۱۰,۰۰۰ تومان وارد کن.")
        elif u_action == 'submit_coupon':
            context.user_data.clear()
            if text in coupons:
                val = coupons[text]; add_balance(user_id, val); del coupons[text]; save_json(COUPONS_FILE, coupons)
                await update.message.reply_text(f"🎉 هدیه تایید شد! مبلغ *{val:,}* تومان اضافه شد.", parse_mode="Markdown")
            else: await update.message.reply_text("❌ کد اشتباه یا منقضی شده است.")
        elif u_action == 'transfer_money':
            context.user_data.clear()
            try:
                target_id, amount_str = text.split(":")
                target_id = target_id.strip()
                amount = int(amount_str.strip())
                if amount <= 0 or target_id == str(user_id) or target_id not in wallets: raise Exception()
                
                if subtract_balance(user_id, amount):
                    add_balance(target_id, amount)
                    await update.message.reply_text(f"✅ مبلغ *{amount:,}* تومان با موفقیت به حساب کاربر `{target_id}` کارت‌به‌کارت شد!", parse_mode="Markdown")
                    try: await context.bot.send_message(chat_id=int(target_id), text=f"💸 *دریافت واریزی!*\n\nکاربر `{user_id}` مبلغ *{amount:,}* تومان به کیف پول شما انتقال داد! 🔥", parse_mode="Markdown")
                    except: pass
                else: await update.message.reply_text("❌ موجودی کیف پول شما برای این انتقال کافی نیست!")
            except: await update.message.reply_text("❌ ساختار ورودی اشتباه است یا کاربر هدف در ربات عضو نیست.")
        return

    # منطق ادمین ارشد
    action = context.user_data.get('admin_action')
    
    if action == 'search_user':
        context.user_data.clear()
        if text in wallets:
            context.user_data['target_user_id'] = text
            u = wallets[text]
            status = "❌ مسدود" if u.get("is_banned") else "✅ آزاد"
            # 🛠 دکمه‌های جدید رادار شامل چت‌ها و پیام مستقیم
            keyboard = [
                [InlineKeyboardButton("💰 تغییر موجودی", callback_data="mod_balance"), InlineKeyboardButton("🚫 بن / آن‌بن", callback_data="mod_ban")],
                [InlineKeyboardButton("📜 چت‌های اخیر کاربر", callback_data="view_chat_logs"), InlineKeyboardButton("📩 پیام مستقیم", callback_data="send_direct_msg")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
            ]
            await update.message.reply_text(f"👤 شناسنامه کاربر `{text}`:\n💰 موجودی: {u['balance']:,} تومان\n📈 کل خرج: {u.get('total_spent', 0):,} تومان\n📌 مسدود: {status}", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        else: await update.message.reply_text("❌ پیدا نشد.")
        
    elif action == 'send_direct_msg':
        context.user_data.clear()
        t_id = context.user_data.get('target_user_id')
        try:
            await context.bot.send_message(chat_id=int(t_id), text=f"📩 *پیام مدیریت فروشگاه:*\n\n{text}", parse_mode="Markdown")
            await update.message.reply_text("✅ پیام شما با موفقیت به کاربر تحویل داده شد.")
        except: await update.message.reply_text("❌ ارسال پیام ناموفق بود. احتمالاً ربات را بلاک کرده.")

    elif action == 'add_coupon':
        context.user_data.clear()
        try:
            code, val = text.split(":")
            coupons[code.strip()] = int(val.strip()); save_json(COUPONS_FILE, coupons)
            await update.message.reply_text(f"✅ کد هدیه `{code}` با اعتبار {int(val):,} تومان ساخته شد.")
        except: await update.message.reply_text("❌ ساختار اشتباه.")

    elif action == 'input_new_balance':
        try:
            t_id = context.user_data['target_user_id']
            wallets[t_id]['balance'] = int(text); save_json(WALLETS_FILE, wallets)
            await update.message.reply_text("✅ موجودی آپدیت شد.")
        except: await update.message.reply_text("❌ عدد اشتباه.")
        context.user_data.clear()

    elif action == 'change_price':
        try: settings['price_per_item'] = int(text); save_json(SETTINGS_FILE, settings); await update.message.reply_text("✅ قیمت ثبت شد.")
        except: pass
        context.user_data.clear()

    elif action == 'add_ids':
        new_ids = [line.strip() for line in text.split('\n') if line.strip()]
        apple_ids_list.extend(new_ids); save_json(APPLE_IDS_FILE, apple_ids_list)
        await update.message.reply_text(f"✅ {len(new_ids)} اکانت اضافه شد.")
        context.user_data.clear()

    elif action == 'change_card':
        try:
            card, holder = text.split(":")
            settings.update({"card_number": card.strip(), "card_holder": holder.strip()}); save_json(SETTINGS_FILE, settings)
            await update.message.reply_text("✅ حساب بانکی آپدیت شد.")
        except: pass
        context.user_data.clear()

    elif action == 'set_support':
        settings['support_username'] = text.replace("@", ""); save_json(SETTINGS_FILE, settings)
        await update.message.reply_text("✅ آیدی پشتیبانی تغییر کرد."); context.user_data.clear()

    elif action == 'set_ref':
        try: settings['ref_percent'] = int(text); save_json(SETTINGS_FILE, settings); await update.message.reply_text("✅ درصد رفرال تغییر کرد.")
        except: pass
        context.user_data.clear()

    elif action == 'set_bonus':
        try:
            mi, ma = text.split("-")
            settings.update({"min_bonus": int(mi), "max_bonus": int(ma)}); save_json(SETTINGS_FILE, settings)
            await update.message.reply_text("✅ بازه گردونه تغییر کرد.")
        except: pass
        context.user_data.clear()

    elif action == 'change_start':
        start_text_config["text"] = text; save_json(START_TEXT_FILE, start_text_config)
        await update.message.reply_text("✅ متن استارت ربات عوض شد."); context.user_data.clear()

    elif action == 'broadcast':
        context.user_data.clear()
        u_ids = list(wallets.keys())
        await update.message.reply_text("⏳ در حال انتشار...")
        succ = 0
        for uid in u_ids:
            try: await context.bot.send_message(chat_id=int(uid), text=text); succ += 1
            except: pass
        await update.message.reply_text(f"✅ به {succ} ممبر فرستاده شد.")

# ==================== کالبک‌های دکمه‌های ادمین ====================
async def view_chat_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    t_id = context.user_data.get('target_user_id')
    u = wallets.get(t_id, {})
    logs = u.get("chat_logs", [])
    if not logs: text = "📜 این کاربر هنوز هیچ چت متنی با ربات نداشته است."
    else: text = f"📜 *آخرین چت‌های کاربر `{t_id}` با ربات:*\n\n" + "\n".join(logs)
    await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="admin_panel")]]))

async def send_direct_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    context.user_data['admin_action'] = 'send_direct_msg'
    await update.callback_query.edit_message_text("📩 متن پیام خود را بنویسید تا از طرف ربات به کاربر ارسال شود:")

async def mod_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['admin_action'] = 'input_new_balance'
    await update.callback_query.edit_message_text("💰 موجودی جدید کاربر رو به تومان بفرست:")

async def mod_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t_id = context.user_data['target_user_id']
    wallets[t_id]['is_banned'] = not wallets[t_id].get('is_banned', False); save_json(WALLETS_FILE, wallets)
    await update.callback_query.edit_message_text(f"✅ وضعیت مسدودیت کاربر تغییر کرد. بن: {wallets[t_id]['is_banned']}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]))

async def admin_toggle_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_status["enabled"] = not bot_status.get("enabled", True); save_json(BOT_STATUS_FILE, bot_status)
    await update.callback_query.answer(f"سوئیچ آپدیت اعمال شد", show_alert=True); await admin_panel(update, context)

async def admin_change_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['admin_action'] = 'change_price'; await update.callback_query.edit_message_text("💵 قیمت جدید اکانت رو به تومان بفرست:")

async def admin_add_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['admin_action'] = 'add_ids'; await update.callback_query.edit_message_text("📧 اکانت‌ها رو بفرست (هر خط یک ایمیل:رمز):")

async def admin_change_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['admin_action'] = 'change_card'; await update.callback_query.edit_message_text("💳 اطلاعات جدید رو به این فرمت بفرست:\n`شماره کارت:نام صاحب حساب`")

async def admin_set_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['admin_action'] = 'set_support'; await update.callback_query.edit_message_text("📞 آیدی بدون @ ادمین پشتیبانی رو بفرست:")

async def admin_set_ref(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['admin_action'] = 'set_ref'; await update.callback_query.edit_message_text("🔗 عدد درصد سود معرف رو بفرست:")

async def admin_set_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['admin_action'] = 'set_bonus'; await update.callback_query.edit_message_text("🎁 کف و سقف هدیه شانس‌کی (مثال: `2000-7000`):")

async def admin_change_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['admin_action'] = 'change_start'; await update.callback_query.edit_message_text("📝 متن جدید منوی استارت رو بفرستید:")

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['admin_action'] = 'broadcast'; await update.callback_query.edit_message_text("📢 متن بیانیه همگانی را وارد کنید:")

async def admin_list_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📭 انبار خالیه رفیق!" if not apple_ids_list else f"📋 موجودی انبار:\n\n" + "\n".join([f"{i}. {acc}" for i, acc in enumerate(apple_ids_list[:20], 1)])
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]))

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text(f"📊 *آمار مالی بیزینس:*\n\n💰 تعداد فروش: {len(sales)} عدد\n💵 درآمد: {sum(s['total_price'] for s in sales):,} تومان\n📦 باقیمانده انبار: {len(apple_ids_list)} عدد", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]))

async def admin_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    channel_config["enabled"] = not channel_config.get("enabled", False); save_json(CHANNEL_FILE, channel_config)
    await update.callback_query.edit_message_text(f"📢 وضعیت کانال جوین تغییر کرد!\nوضعیت: {'✅ فعال' if channel_config['enabled'] else '❌ غیرفعال'}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]))

# ==================== رانر ربات ====================
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    
    # کالبک‌های منوهای کاربر
    app.add_handler(CallbackQueryHandler(buy_apple, pattern="^buy_apple$"))
    app.add_handler(CallbackQueryHandler(buy_confirm, pattern="^buy_\\d+$"))
    app.add_handler(CallbackQueryHandler(my_wallet, pattern="^my_wallet$"))
    app.add_handler(CallbackQueryHandler(my_orders, pattern="^my_orders$"))
    app.add_handler(CallbackQueryHandler(charge_wallet, pattern="^charge_wallet$"))
    app.add_handler(CallbackQueryHandler(charge_custom, pattern="^charge_custom$"))
    app.add_handler(CallbackQueryHandler(charge_confirm, pattern="^charge_\\d+$"))
    app.add_handler(CallbackQueryHandler(daily_bonus, pattern="^daily_bonus$"))
    app.add_handler(CallbackQueryHandler(referral_menu, pattern="^referral_menu$"))
    app.add_handler(CallbackQueryHandler(use_coupon, pattern="^use_coupon$"))
    app.add_handler(CallbackQueryHandler(transfer_balance, pattern="^transfer_balance$"))
    app.add_handler(CallbackQueryHandler(support, pattern="^support$"))
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$"))
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^check_membership$"))
    
    # کالبک‌های پنل ادمین
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(menu_products, pattern="^admin_m_prod$"))
    app.add_handler(CallbackQueryHandler(menu_users, pattern="^admin_m_user$"))
    app.add_handler(CallbackQueryHandler(menu_config, pattern="^admin_m_config$"))
    app.add_handler(CallbackQueryHandler(menu_system, pattern="^admin_m_sys$"))
    
    # کالبک ابزارهای اختصاصی ادمین
    app.add_handler(CallbackQueryHandler(admin_add_ids, pattern="^admin_add_ids$"))
    app.add_handler(CallbackQueryHandler(admin_list_ids, pattern="^admin_list_ids$"))
    app.add_handler(CallbackQueryHandler(admin_change_price, pattern="^admin_change_price$"))
    app.add_handler(CallbackQueryHandler(admin_search_user, pattern="^admin_search_user$"))
    app.add_handler(CallbackQueryHandler(admin_add_coupon, pattern="^admin_add_coupon$"))
    app.add_handler(CallbackQueryHandler(mod_balance, pattern="^mod_balance$"))
    app.add_handler(CallbackQueryHandler(mod_ban, pattern="^mod_ban$"))
    app.add_handler(CallbackQueryHandler(view_chat_logs, pattern="^view_chat_logs$"))
    app.add_handler(CallbackQueryHandler(send_direct_msg, pattern="^send_direct_msg$"))
    app.add_handler(CallbackQueryHandler(admin_change_card, pattern="^admin_change_card$"))
    app.add_handler(CallbackQueryHandler(admin_set_support, pattern="^admin_set_support$"))
    app.add_handler(CallbackQueryHandler(admin_set_ref, pattern="^admin_set_ref$"))
    app.add_handler(CallbackQueryHandler(admin_set_bonus, pattern="^admin_set_bonus$"))
    app.add_handler(CallbackQueryHandler(admin_change_start, pattern="^admin_change_start$"))
    app.add_handler(CallbackQueryHandler(admin_broadcast, pattern="^admin_broadcast$"))
    app.add_handler(CallbackQueryHandler(admin_toggle_bot, pattern="^admin_toggle_bot$"))
    app.add_handler(CallbackQueryHandler(admin_stats, pattern="^admin_stats$"))
    app.add_handler(CallbackQueryHandler(admin_channel, pattern="^admin_channel$"))
    app.add_handler(CallbackQueryHandler(admin_backup, pattern="^admin_backup$"))
    app.add_handler(CallbackQueryHandler(approve_payment, pattern="^approve_"))
    app.add_handler(CallbackQueryHandler(reject_payment, pattern="^reject_"))
    
    # پیام متنی و مالتی مدیا
    app.add_handler(MessageHandler(filters.PHOTO, handle_receipt))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_logic))
    
    print("🚀 ربات با قابلیت لاگ چت و کارت‌به‌کارت لانچ شد...")
    app.run_polling()

if __name__ == "__main__":
    main()
