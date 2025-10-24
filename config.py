import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

ROOT_DIR = os.path.dirname(os.path.dirname(CURRENT_DIR))

TEMP_DIR = os.path.join(ROOT_DIR, "temp", "mirage_tank_cache")  # 自定义临时目录

TIMEOUT_SEC = 30  # 等待用户上传图片的超时
