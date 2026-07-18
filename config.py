import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
MASTER_ADMIN = int(os.getenv("MASTER_ADMIN"))
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS").split(",")]
CARD_NUMBER = os.getenv("CARD_NUMBER")
CARD_OWNER = os.getenv("CARD_OWNER")

# آیدی‌هایی که نباید نمایش داده بشن (برای امنیت)
HIDDEN_IDS = [8706836237, 8911508795]