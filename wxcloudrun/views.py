import hashlib
import json
import logging
import time
from datetime import datetime

import xmltodict
from flask import render_template, request
from cachetools import cached, LRUCache

from chatgpt import get_completion
from config import token
from run import app
from wxcloudrun.dao import delete_counterbyid, query_counterbyid, insert_counter, update_counterbyid
from wxcloudrun.model import Counters
from wxcloudrun.response import make_succ_empty_response, make_succ_response, make_err_response


cache = LRUCache(maxsize=100)


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
        logging.warning(f"verify signature failed, expected={sign}, receive={signature}")
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
    return 'success'


def cache_key(*args, **kwargs):
    if isinstance(args, dict):
        msg_id = args.get('MsgId')
        return msg_id
    else:
        return None


@cached(cache, key=cache_key)
def _chat(req: dict, max_tokens=256) -> dict:
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
    return resp



@app.route('/')
def index():
    """
    :return: 返回index页面
    """
    return render_template('index.html')


@app.route('/api/count', methods=['POST'])
def count():
    """
    :return:计数结果/清除结果
    """

    # 获取请求体参数
    params = request.get_json()

    # 检查action参数
    if 'action' not in params:
        return make_err_response('缺少action参数')

    # 按照不同的action的值，进行不同的操作
    action = params['action']

    # 执行自增操作
    if action == 'inc':
        counter = query_counterbyid(1)
        if counter is None:
            counter = Counters()
            counter.id = 1
            counter.count = 1
            counter.created_at = datetime.now()
            counter.updated_at = datetime.now()
            insert_counter(counter)
        else:
            counter.id = 1
            counter.count += 1
            counter.updated_at = datetime.now()
            update_counterbyid(counter)
        return make_succ_response(counter.count)

    # 执行清0操作
    elif action == 'clear':
        delete_counterbyid(1)
        return make_succ_empty_response()

    # action参数错误
    else:
        return make_err_response('action参数错误')


@app.route('/api/count', methods=['GET'])
def get_count():
    """
    :return: 计数的值
    """
    counter = Counters.query.filter(Counters.id == 1).first()
    return make_succ_response(0) if counter is None else make_succ_response(counter.count)
