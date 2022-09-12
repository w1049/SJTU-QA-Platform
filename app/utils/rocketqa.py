import json

import httpx
from loguru import logger

from ..config import settings


def get_embedding(query):
    input_data = {'step': 1, 'query': [query]}
    result = httpx.post(settings.rocketqa_url, json=input_data, timeout=30.0)
    res_json = json.loads(result.text)
    return res_json['result'][0]


def get_para(title, para):
    input_data = {'step': 3, 'title': title, 'para': para}
    result = httpx.post(settings.rocketqa_url, json=input_data, timeout=30.0)
    res_json = json.loads(result.text)
    return res_json['result'][0]


async def async_get_para(title, para):
    input_data = {'step': 3, 'titles': [title], 'paras': [para]}
    async with httpx.AsyncClient() as client:
        result = await client.post(settings.rocketqa_url, json=input_data, timeout=30.0)
        res_json = json.loads(result.text)
        return res_json['result'][0]


async def async_get_paras(titles, paras):
    input_data = {'step': 3, 'titles': titles, 'paras': paras}
    async with httpx.AsyncClient() as client:
        result = await client.post(settings.rocketqa_url, json=input_data, timeout=None)
        logger.debug(result)
        res_json = json.loads(result.text)
        return res_json['result']

# def matching(query, titles):
#     input_data = {'step': 2, 'query': query, 'titles': titles, 'paras': ['-' for i in range(len(titles))]}
#     result = httpx.post(settings.rocketqa_url, json=input_data, timeout=30.0)
#     res_json = json.loads(result.text)
#     scores = res_json['score']
#
#     final_result = {}
#     for i in range(len(scores)):
#         final_result[titles[i]] = scores[i]
#     sort_res = sorted(final_result.items(), key=lambda a: a[1], reverse=True)
#     return sort_res
