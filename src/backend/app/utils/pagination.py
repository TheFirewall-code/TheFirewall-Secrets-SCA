from math import ceil
from typing import Any

from pydantic import BaseModel


def paginate(query, total_count: int, page: int, limit: int):
    """
    Applies pagination to a query.

    :param query: SQLAlchemy query object.
    :param total_count: Total number of records.
    :param page: The current page number.
    :param limit: The number of records per page.
    :return: Paginated query, metadata.
    """
    total_pages = ceil(total_count / limit)
    paginated_query = query.offset((page - 1) * limit).limit(limit)

    return {
        "query": paginated_query,
        "meta": {
            "current_page": page,
            "total_pages": total_pages,
            "current_limit": limit,
            "total_count": total_count
        }
    }


class Pagination(BaseModel):
    total: int
    page: int
    page_size: int
    data: Any
