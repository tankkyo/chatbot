import hashlib
import json
import logging
import time
from datetime import datetime

import cachetools
import xmltodict
from flask import render_template, request

# TODO add new chatbot class and put into config later
from wxcloudrun.minimax import get_completion
from config import token
from run import app
from wxcloudrun.response import make_succ_empty_response, make_succ_response, make_err_response

cache = cachetools.LRUCache(maxsize=100)


@app.route('/handle', methods=["GET", "POST"])
def handle():
    if request.method == "GET":
        # 处理服务器的验证消息
        data = request.args
        return verify_signature(signature=data.get('signature'),
                                timestamp=data.get('timestamp'),
                                nonce=data.get('nonce'),
                                echostr=data.get('echostr'))
    if request.method == "POST":
        try:
            # 处理公众号推送消息
            if request.content_type == "application/json":
                return handle_json_msg(request.json)
            else:
                return handle_xml_msg(request.data)
        except Exception as e:
            logging.error(e)
            return 'error', 403


def verify_signature(signature: str, timestamp: str, nonce: str, echostr: str):
    # 对参数进行字典排序，拼接字符串
    temp = [timestamp, nonce, token]
    temp.sort()
    temp = ''.join(temp)
    # 加密
    sign = hashlib.sha1(temp.encode('utf8')).hexdigest()
    if sign == signature:
        logging.info("verify signature success!")
        return echostr
    else:
        logging.warning(
            f"verify signature failed, expected={sign}, receive={signature}")
        return 'error', 403


def handle_xml_msg(xml: bytes):
    req = xmltodict.parse(xml)['xml']
    logging.info("receive xml message: %s" % req)
    if 'text' == req.get('MsgType'):
        msg: str = req.get('Content')
        if msg.startswith("@chatbot"):
            resp = _chat(req)
            xml = """<xml>
                        <ToUserName><![CDATA[{ToUserName}]]></ToUserName>
                        <FromUserName><![CDATA[{FromUserName}]]></FromUserName>
                        <CreateTime>{CreateTime}</CreateTime>
                        <MsgType><![CDATA[text]]></MsgType>
                        <Content><![CDATA[{Content}]]></Content>
                    </xml>"""
            return xml.format(**resp), 200, {'Content-Type': 'application/xml'}
    # 对于其他的消息，一概不予响应
    return 'success'


def handle_json_msg(req: dict):
    logging.info("receive json message: %s" % req)
    if req.get('MsgType') == 'text':
        msg: str = req.get('Content')
        if msg.startswith("@chatbot"):
            resp = _chat(req)
            return json.dumps(resp, ensure_ascii=False), 200, {'Content-Type': 'application/json'}
    elif req.get('action') == 'CheckContainerPath':
        return 'success', 200
    return 'success', 200


def _chat(req: dict, max_tokens=256) -> dict:
    msg_id = req.get('MsgId')
    resp = cache.get(msg_id)
    if resp:
        logging.info(
            f"found response for msg_id={msg_id} in cache, return {resp}")
        return resp

    prompt = f"{req.get('Content')[8:]}, 请将回复控制在{max_tokens - 10}字以内"
    start = time.time()
    logging.debug(f"send prompt: {prompt}")
    reply = get_completion(prompt, max_tokens=max_tokens)
    t = time.time() - start
    logging.info(f"send prompt: {prompt}, reply={reply}, time={t:.2f}s")
    resp = {
        'ToUserName': req.get('FromUserName'),
        'FromUserName': req.get('ToUserName'),
        'CreateTime': int(time.time()),
        'MsgType': 'text',
        'Content': reply
    }
    cache.setdefault(msg_id, resp)
    return resp


@app.route('/')
def index():
    """
    测试用接口
    """
    return 'Hello, Chatbot!'
