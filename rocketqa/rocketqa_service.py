# 修改自
# https://github.com/PaddlePaddle/RocketQA/blob/main/examples/faiss_example/rocketqa_service.py
import json
import time

from tornado import ioloop, web, httpserver

import rocketqa


class RocketQAServer(web.RequestHandler):

    def __init__(self, application, request, **kwargs):
        web.RequestHandler.__init__(self, application, request)
        self._dual_encoder = kwargs["dual_encoder"]

    def post(self):
        input_request = self.request.body
        output = {'error_code': 0, 'error_message': ''}
        if input_request is None:
            output['error_code'] = 1
            output['error_message'] = "Input is empty"
            self.write(json.dumps(output))
            return

        try:
            input_data = json.loads(input_request)
        except:
            output['error_code'] = 2
            output['error_message'] = "Load input request error"
            self.write(json.dumps(output))
            return

        if input_data['step'] == 1:
            # encode query
            query = input_data['query']
            start = time.time()
            q_embs = self._dual_encoder.encode_query(query=query)
            q_embs = [x.tolist() for x in list(q_embs)]
            end = time.time()
            print('encode query: {}s'.format(end - start))
            output['result'] = q_embs

        elif input_data['step'] == 3:
            titles = input_data['titles']
            paras = input_data['paras']
            start = time.time()
            q_embs = self._dual_encoder.encode_para(title=titles, para=paras)
            q_embs = [x.tolist() for x in list(q_embs)]
            end = time.time()
            print('encode para: {}s'.format(end - start))
            output['result'] = q_embs

        result_str = json.dumps(output, ensure_ascii=False)
        self.write(result_str)


def create_rocketqa_app(sub_address, rocketqa_server):
    de_conf = {
        "model": 'zh_dureader_de_v2',
        "use_cuda": False,
        "device_id": 0,
        "batch_size": 32
    }
    dual_encoder = rocketqa.load_model(**de_conf)
    return web.Application([(sub_address, rocketqa_server, dict(dual_encoder=dual_encoder))])


if __name__ == "__main__":
    sub_address = r'/rocketqa'
    port = 25565
    app = create_rocketqa_app(sub_address, RocketQAServer)
    server = httpserver.HTTPServer(app)
    server.bind(port)
    server.start(0)
    ioloop.IOLoop.current().start()
