"""
速率限制器模块
独立于 main.py 以避免循环导入（auth.py 需要导入 limiter）
使用内存存储，避免读取 .env 时的编码问题
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
