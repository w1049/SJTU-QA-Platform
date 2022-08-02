import requests


def add_question():
    corpus_file = 'qa_pair.csv'
    nq = []
    na = []
    with open(corpus_file, 'r', encoding='utf-8') as f:
        for line in f:
            q, a = line.split('\t')
            q = q.rstrip()
            a = a.rstrip()
            requests.post('http://127.0.0.1:5000/api/question', json={'title': q, 'content': a})


def add_set():
    requests.post('http://127.0.0.1:5000/api/question_set',
                  json={'name': '政务', 'questions': [i for i in range(1, 5000)]})
