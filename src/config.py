import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.environ["BOT_TOKEN"]
    DATABASE_URL = os.environ["DATABASE_URL"]
    FREEBIE_URL = os.getenv("FREEBIE_URL","")
    NEXT_MATERIAL_URL = os.getenv("NEXT_MATERIAL_URL","")
    COURSE_URL = os.getenv("COURSE_URL","")
    INSTAGRAM_URL = os.getenv("INSTAGRAM_URL","")
    BASE_WEBAPP_URL = os.getenv("BASE_WEBAPP_URL","")
    
    YOUTUBE_URL = os.getenv("YOUTUBE_URL", "https://youtu.be/k1jWhdNtnKc")
    
    DIASTASIS_PHOTO_ID = os.getenv("DIASTASIS_PHOTO_ID","")
    
    TZ = os.getenv("TIMEZONE","Asia/Almaty")
    TEST_MODE = os.getenv("TEST_MODE","").strip() == "1"
    WEBHOOK_URL = os.getenv("WEBHOOK_URL","")