"""
中控台配置文件
"""
import os

# 访问密码 — 设为空字符串则局域网内无需密码
# 设置方式: 环境变量 LIVE_DB_PASSWORD=你的密码
# 或在下面直接修改
ACCESS_PASSWORD = os.environ.get("LIVE_DB_PASSWORD", "")

# 自动化插件目录（未来扩展）
PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "plugins")
