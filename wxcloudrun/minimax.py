import requests
import os

from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv())

group_id = os.getenv('MINIMAX_GROUP_ID')
api_key = os.getenv('MINIMAX_API_KEY')
endpoint = os.getenv('MINIMAX_ENDPOINT', 'https://api.minimax.chat/v1/text/chatcompletion')


def get_completion(prompt, model="abab5.5-chat", max_tokens=512):
    url = f"{endpoint}?GroupId={group_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "tokens_to_generate": max_tokens,
        "messages": [
            {
                "sender_type": "USER",
                "text": prompt
            }
        ]
    }
    response = requests.post(url, headers=headers, json=payload, stream=True)
    return response.json()['reply']


if __name__ == '__main__':
    print(get_completions("大模型的资料有哪些"))