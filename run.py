"""PyCharm 调试启动脚本
用法：在 PyCharm 中右键此文件 → Debug 'run'
注意：调试时禁用了 reload，修改代码后需手动重新启动
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",   # 允许局域网其他设备访问
        port=8000,
        reload=False,
        log_level="info",
    )
