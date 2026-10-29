"""
生产环境入口 — 用 Waitress 替代 Flask 开发服务器
启动: python wsgi.py
"""
from waitress import serve
from app import app
import socket

def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

if __name__ == "__main__":
    port = 5000
    print(f"""
+==============================================+
|   Live Stream Control Panel v1.0              |
|   Production Mode (Waitress)                  |
|   http://0.0.0.0:{port}                       |
+==============================================+
    """)
    serve(app, host="0.0.0.0", port=port, threads=4)
