"""
应用日志配置
统一日志格式：时间 | 级别 | 请求ID | 模块 | 消息
"""
import logging
import sys

LOG_FORMAT = (
    "%(asctime)s | %(levelname)-5s | %(name)s | %(message)s"
)
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: int = logging.INFO):
    """初始化全局日志配置，输出到 stdout"""
    root = logging.getLogger()
    root.setLevel(level)
    # 清除已有 handler（避免重复）
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    root.addHandler(handler)

    # 为项目自身设置级别
    logging.getLogger("student_management").setLevel(level)
    # 降低第三方库日志噪音
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("aiomysql").setLevel(logging.WARNING)

    logging.getLogger("student_management").info("Logging initialized at level %s", logging.getLevelName(level))
