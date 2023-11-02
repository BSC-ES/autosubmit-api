import os
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.environ.get("SECRET_KEY", "M87;Z$,o5?MSC(/@#-LbzgE3PH-5ki.ZvS}N.s09v>I#v8I'00THrA-:ykh3HX?") # WARNING: Always provide a SECRET_KEY for production
JWT_ALGORITHM = "HS256"
JWT_EXP_DELTA_SECONDS = 84000*5  # 5 days

RUN_BACKGROUND_TASKS_ON_START = True if os.environ.get("RUN_BACKGROUND_TASKS_ON_START") in ["True", "T", "true"] else False # Default dalse

# CAS Stuff
CAS_LOGIN_URL = os.environ.get("CAS_LOGIN_URL") # e.g: 'https://cas.bsc.es/cas/login'
CAS_VERIFY_URL = os.environ.get("CAS_VERIFY_URL") # e.g: 'https://cas.bsc.es/cas/serviceValidate'

