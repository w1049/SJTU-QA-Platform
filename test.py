import time

import requests

s = [i for i in range(1, 5001)]


def aq():
    corpus_file = 'qa_pair.csv'
    nq = []
    na = []
    with open(corpus_file, 'r', encoding='utf-8') as f:
        cnt = 0
        total = 0
        title = []
        content = []
        for line in f:
            q, a = line.split('\t')
            title.append(q.rstrip())
            content.append(a.rstrip())
            cnt += 1
            total += 1
            if cnt == 500:
                # print("total:{}".format(total))
                requests.post('http://127.0.0.1:5000/api/question', json={'many': 1,
                                                                          'title': title, 'content': content})
                cnt = 0
                title = []
                content = []


def add_set():
    requests.post('http://127.0.0.1:5000/api/question_set', json={'name': '政务'})


def insert():
    requests.put('http://127.0.0.1:5000/api/question_set/1', json={'op': 'append', 'questions': s})


if __name__ == '__main__':
    start = time.time()
    aq()
    end = time.time()
    print("add questions: {}s".format(end - start))
    start = time.time()
    add_set()
    end = time.time()
    print("add set: {}s".format(end - start))
    start = time.time()
    insert()
    end = time.time()
    print("insert questions to set: {}s".format(end - start))
