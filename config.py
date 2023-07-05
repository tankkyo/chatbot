import os
import logging
import openai

logging.basicConfig(level=logging.INFO)

# 是否开启debug模式
DEBUG = True

# 读取数据库环境变量
username = os.environ.get("MYSQL_USERNAME", 'root')
password = os.environ.get("MYSQL_PASSWORD", 'root')
db_address = os.environ.get("MYSQL_ADDRESS", '127.0.0.1:3306')

token = os.environ.get("VERIFY_TOKEN", 'tankkyo_chatbot')
# refer to https://github.com/chatanywhere/GPT_API_free
openai.api_base = os.environ.get("OPENAI_API_BASE", "https://api.chatanywhere.com.cn/v1")