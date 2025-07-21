import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
HR_CHAT_ID = int(os.getenv("HR_CHAT_ID", "0"))
