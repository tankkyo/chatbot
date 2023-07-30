import os
import logging
import openai

logging.basicConfig(level=logging.INFO)

# 是否开启debug模式
DEBUG = True


token = os.environ.get("VERIFY_TOKEN", 'tankkyo_chatbot')
# refer to https://github.com/chatanywhere/GPT_API_free
openai.api_base = os.environ.get(
    "OPENAI_API_BASE", "https://api.chatanywhere.com.cn/v1")
