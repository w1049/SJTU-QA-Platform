from sqlalchemy.orm import Query

from .pagination import paginate

Query.paginate = paginate
