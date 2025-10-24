import asyncio
import io
import os
import tempfile
import aiohttp
from PIL import Image

from ..config import TEMP_DIR


async def save_image_as_png(url, save_dir: str = TEMP_DIR, timeout_sec: int = 30):
    """
    从指定 URL 下载图片并保存到本地临时png文件
    返回保存的文件路径
    """
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
    else:
        save_dir = None
    timeout = aiohttp.ClientTimeout(total=timeout_sec)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"图片下载失败: HTTP {resp.status}")
                content = await resp.read()
        except asyncio.TimeoutError:
            raise TimeoutError(f"下载图片超时（>{timeout_sec}秒）: {url}")
        except aiohttp.ClientError as e:
            raise RuntimeError(f"图片下载异常: {e}")

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _save_image_sync, content, save_dir)


def _save_image_sync(content: bytes, save_dir: str | None) -> str:
    """
    在独立线程中执行同步图像操作，避免阻塞事件循环
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png", dir=save_dir) as temp_file:
        with Image.open(io.BytesIO(content)) as img:
            img.save(temp_file, format="PNG")
        return temp_file.name
