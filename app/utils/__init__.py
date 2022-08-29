from sqlalchemy.orm import Query

from .milvus_util import MilvusUtil
from .pagination import paginate

Query.paginate = paginate

milvus = MilvusUtil()
