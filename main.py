import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import config
import database as db
from handlers import *
from admin_handlers import *

async def main():
    # راه‌اندازی دیتابیس
    db.init_db()
    
    # ساخت اپلیکیشن
    app = Application.builder().token(config.TOKEN).build()
    
    # ========== دستورات عمومی ==========
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_receipt))
    
    # ========== دستور مخفی ادمین ==========
    app.add_handler(MessageHandler(
        filters.Regex(r'^hahbyhh555466mamabbbnn$'), 
        admin_panel
    ))
    
    # ========== Callback handlers ==========
    app.add_handler(CallbackQueryHandler(show_products, pattern="^products$"))
    app.add_handler(CallbackQueryHandler(start_purchase, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(approve_transaction, pattern="^approve_"))
    app.add_handler(CallbackQueryHandler(reject_transaction, pattern="^reject_"))
    app.add_handler(CallbackQueryHandler(pending_list, pattern="^pending_list$"))
    app.add_handler(CallbackQueryHandler(back_to_main, pattern="^back$"))
    app.add_handler(CallbackQueryHandler(back_to_admin, pattern="^back_admin$"))
    app.add_handler(CallbackQueryHandler(support, pattern="^support$"))
    app.add_handler(CallbackQueryHandler(status, pattern="^status$"))
    
    # ========== اجرا ==========
    print("🤖 ربات روشن شد!")
    print(f"✅ ادمین اصلی: {config.MASTER_ADMIN}")
    print(f"✅ تعداد ادمین‌ها: {len(config.ADMIN_IDS)}")
    
    # شروع دریافت پیام‌ها با Polling
    await app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    asyncio.run(main())
