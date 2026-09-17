"""分页与查询辅助。"""
from flask import request


def get_page_args(default_size=10, max_size=200):
    page = request.args.get("page") or request.form.get("page")
    size = request.args.get("size") or request.form.get("size")
    return normalize_page(page, size, default_size, max_size)


def normalize_page(page, size, default_size=10, max_size=200):
    try:
        page = int(page)
    except (TypeError, ValueError):
        page = 1
    try:
        size = int(size)
    except (TypeError, ValueError):
        size = default_size
    page = max(1, page)
    size = min(max_size, max(1, size))
    return page, size


def paginate(query, page, size, serializer):
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    return [serializer(i) for i in items], total