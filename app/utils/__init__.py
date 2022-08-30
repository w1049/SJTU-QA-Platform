from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy.orm import Query
from starlette.templating import Jinja2Templates

from .milvus_util import MilvusUtil
from .pagination import paginate

Query.paginate = paginate

milvus = MilvusUtil()

templates = Jinja2Templates(directory='templates')

instrumentator = Instrumentator()
