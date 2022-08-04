import json

import requests

from config import ROCKETQA_URL


def get_embedding(query):
    input_data = {'step': 1, 'query': [query]}
    result = requests.post(ROCKETQA_URL, json=input_data)
    res_json = json.loads(result.text)
    return res_json['result'][0]


def get_para(title, para):
    input_data = {'step': 3, 'title': title, 'para': para}
    result = requests.post(ROCKETQA_URL, json=input_data)
    res_json = json.loads(result.text)
    return res_json['result'][0]


def get_embeddings(queries):
    input_data = {'step': 1, 'query': queries}
    result = requests.post(ROCKETQA_URL, json=input_data)
    res_json = json.loads(result.text)
    return res_json['result']


def matching(query, titles):
    input_data = {'step': 2, 'query': query, 'titles': titles, 'paras': ['-' for i in range(len(titles))]}
    result = requests.post(ROCKETQA_URL, json=input_data)
    res_json = json.loads(result.text)
    scores = res_json['score']

    final_result = {}
    for i in range(len(scores)):
        final_result[titles[i]] = scores[i]
    sort_res = sorted(final_result.items(), key=lambda a: a[1], reverse=True)
    return sort_res
