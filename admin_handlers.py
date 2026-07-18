from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import config
import database as db

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پنل مدیریت - فقط برای ادمین اصلی (8911508795)"""
    user_id = update.effective_user.id
    
    # فقط ادمین اصلی می‌تونه پنل رو ببینه
    if user_id != config.MASTER_ADMIN:
        await update.message.reply_text("⛔ شما دسترسی ندارید!")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 تراکنش‌های در انتظار", callback_data="pending_list")],
        [InlineKeyboardButton("➕ افزودن محصول", callback_data="add_product")],
        [InlineKeyboardButton("📝 ویرایش محصول", callback_data="edit_product")],
        [InlineKeyboardButton("🗑 حذف محصول", callback_data="delete_product")],
        [InlineKeyboardButton("📈 آمار", callback_data="stats")],
        [InlineKeyboardButton("👥 مدیریت ادمین‌ها", callback_data="manage_admins")],
    ]
    
    await update.message.reply_text(
        "🔐 **پنل مدیریت**\n\n"
        "لطفاً یکی از گزینه‌ها رو انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def approve_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تأیید تراکنش - هر دو ادمین می‌تونن"""
    query = update.callback_query
    admin_id = query.from_user.id
    
    if admin_id not in config.ADMIN_IDS:
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
    
    assigned_code = db.use_product_code(transaction[2])
    
    if not assigned_code:
        await query.message.edit_caption("⚠️ موجودی اپل‌آیدی تمام شده!")
        return
    
    db.update_transaction_status(trans_id, 'approved', assigned_code)
    
    try:
        await context.bot.send_message(
            chat_id=transaction[1],
            text=f"🎉 **خرید شما تأیید شد!**\n\n"
                 f"🔑 اپل‌آیدی شما:\n"
                 f"`{assigned_code}`\n\n"
                 "📌 لطفاً رمز رو تغییر بدید.\n"
                 "🙏 ممنون از خرید شما!"
        )
    except:
        pass
    
    # مخفی کردن آیدی ادمین در پیام
    await query.message.edit_caption(
        f"✅ **تراکنش {trans_id} تأیید شد**\n"
        f"🔑 کد ارسال شد: `{assigned_code}`"
    )
    
    await query.answer("✅ تأیید شد!", show_alert=True)

async def reject_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رد تراکنش - هر دو ادمین می‌تونن"""
    query = update.callback_query
    admin_id = query.from_user.id
    
    if admin_id not in config.ADMIN_IDS:
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

async def pending_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش لیست تراکنش‌های در انتظار"""
    query = update.callback_query
    if query.from_user.id not in config.ADMIN_IDS:
        await query.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    
    await query.answer()
    
    transactions = db.get_pending_transactions()
    
    if not transactions:
        await query.message.edit_text(
            "📊 **تراکنش‌های در انتظار**\n\n"
            "هیچ تراکنش در انتظاری وجود ندارد.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back_admin")]
            ])
        )
        return
    
    text = "📊 **تراکنش‌های در انتظار:**\n\n"
    for t in transactions[:10]:
        text += f"🆔 #{t[0]} - کاربر: {t[1]}\n"
        text += f"💰 {t[3]:,} تومان - 📅 {t[7]}\n\n"
    
    text += "برای تأیید/رد، از پیام‌های ارسال شده استفاده کنید."
    
    await query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_admin")]
        ])
    )

# دکمه بازگشت به پنل
async def back_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await admin_panel(update, context)