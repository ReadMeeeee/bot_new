from os import getenv
from dotenv import load_dotenv

load_dotenv()

# model = "Qwen/Qwen2-1.5B-Instruct"

API_TG = getenv("API_TG")
API_AI = getenv("API_AI")

model_url = "https://api.deepseek.com"
model_name = "deepseek-chat"
