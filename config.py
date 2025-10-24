import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

ROOT_DIR = os.path.dirname(os.path.dirname(CURRENT_DIR))

TEMP_DIR = os.path.join(ROOT_DIR, "mirage_tank_cache")  # 自定义临时目录

TIMEOUT_SEC = 10  # 等待用户上传图片的超时
