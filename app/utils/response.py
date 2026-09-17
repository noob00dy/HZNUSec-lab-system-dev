"""统一响应格式，兼容旧系统：{"code": "200", "data": ...}。"""
from flask import jsonify

SUCCESS = "200"
UNAUTHORIZED = "399"   # 未登录 / 登录过期
FORBIDDEN = "403"       # 无权限
BAD_REQUEST = "400"
NOT_FOUND = "404"
SERVER_ERROR = "500"


def _make(payload, status=200):
    resp = jsonify(payload)
    resp.status_code = status
    return resp


def success(data=None, msg=None, code=SUCCESS, http_status=200):
    """成功响应。

    旧系统部分接口（如 systemConfig）返回 msg 字段而非 data。
    """
    payload = {"code": code}
    if msg is not None and data is None:
        payload["msg"] = msg
    else:
        payload["data"] = data
        if msg is not None:
            payload["msg"] = msg
    return _make(payload, http_status)


def error(message, code=SERVER_ERROR, http_status=None):
    """失败响应。默认 HTTP 200，仅业务 code 表示错误（与旧前端约定一致）。"""
    if http_status is None:
        http_status = 200
    return _make({"code": code, "message": message or "操作失败"}, http_status)


def paged(items, total, page, size, key):
    """分页响应体。"""
    page_count = (total + size - 1) // size if size else 0
    return {
        key: items,
        "dataCount": total,
        "page": page,
        "size": size,
        "pageCount": page_count,
    }