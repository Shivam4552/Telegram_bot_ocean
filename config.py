import os
from dotenv import load_dotenv
from typing import List

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()]
    CHANNEL_ID = int(os.getenv('CHANNEL_ID', '0'))
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    VULGAR_WORDS = [
        # Vulgar and inappropriate content
        "chutiya", "mc", "gandu", "lodu", "pagal", "lund", "chut", "fuck",
        "bsdk", "madrchod", "madrchd", "nudes", "hot pic", "takla", "sexy",
        "handjob", "mutthi", "masturbation", "pussy", "dick", "randi", "rand",
        "gand", "gaand", "gaandu", "Doglapan", "dogla", "bhosdike", "bhosdika",
        "bhosdiki", "bhosdike", "bhosdiki", "chu*iya", "ch*tiya", "chut1ya", 
        "m@derch0d", "b$dk", "g@ndu", "g@ndu", "gandu", "gandu", "gandu",
        "f-uck", "f**k", "ph*ck", "f*ck", "fuk", "fuker", "fuking",
        "l0du", "r@ndi", "r@nd", "randi", "randi", "randi", "randi",
        "delete this group", "report this channel", "waste channel", "useless channel",
        "useless group", "fake channel", "fake group", "scam channel",
        "bhenchod", "sisterfucker", "madarchod variations",
        "rakshas", "harami", "kameena", "badtameez"
        "chodu", "lavde", "bhosadi", "bhosadi ke", "bhosadi ki", "bhosadi ka",
        "bhosadi wale", "bhosadi wale", "bhosadi wale",

    ]
    
    COMPETITOR_KEYWORDS = [
        # Major National Coaching Brands
        "allen", "ellen", "alen", "aleen", "alenn", "allleen", "alien",
        "akash", "aakash", "aksh", "aaksh", "pw", "physics wallaha", 
        "physics wallah", "coaching"
    ]
    
    SCREENSHOT_INDICATORS = [
        #"report admin", "report channel", "scam", "fraud", 
        #"false report", "ban channel", "shut down", "report group"
    ]