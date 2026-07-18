from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import config
import database as db
from handlers import *
from admin_handlers import *

def main():
    db.init_db()
    
    app = Application.builder().token(config.TOKEN).build()
    
    # ========== دستورات عمومی ==========
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_receipt))
    
    # ========== دستور مخفی ادمین (برای هر دو ادمین) ==========
    app.add_handler(MessageHandler(
        filters.Regex(r'^hahbyhh555466mamabbbnn$'), 
        admin_panel
    ))
    
    # ========== هندلر پیام از ادمین به کاربر ==========
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_admin_reply
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
    
    # ========== هندلرهای جدید ==========
    app.add_handler(CallbackQueryHandler(view_chats, pattern="^view_chats$"))
    app.add_handler(CallbackQueryHandler(show_user_chat, pattern="^chat_user_"))
    app.add_handler(CallbackQueryHandler(send_message_to_user, pattern="^msg_user_"))
    
    print("🤖 ربات روشن شد!")
    print(f"✅ ادمین‌ها: {config.SECRET_ADMINS}")
    app.run_polling()

if __name__ == "__main__":
    main()
