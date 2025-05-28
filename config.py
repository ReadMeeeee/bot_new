from os import getenv
from dotenv import load_dotenv
from bot_api import AIModelAPI


load_dotenv()

# model = "Qwen/Qwen2-1.5B-Instruct"

API_TG = getenv("API_TG")
API_DS = getenv("API_DS")

model_url = "https://api.deepseek.com"
model_name = "deepseek-chat"

deepseek_api = AIModelAPI(API_DS, model_url, model_name)
