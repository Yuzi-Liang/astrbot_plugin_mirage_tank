import io
import os
import tempfile
import aiohttp
from PIL import Image

from ..config import TEMP_DIR


async def save_image_as_png(url, save_dir: str = TEMP_DIR):
    """
    从指定 URL 下载图片并保存到本地临时png文件
    返回保存的文件路径
    """
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
    else:
        save_dir = None

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise RuntimeError(f"图片下载失败: HTTP {resp.status}")
            content = await resp.read()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".png", dir=save_dir) as temp_file:
        with Image.open(io.BytesIO(content)) as img:
            img.save(temp_file, format="PNG")
        temp_path = temp_file.name

    return temp_path
