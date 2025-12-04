import asyncio
import os

from PIL import Image
import numpy as np
import tempfile

from ..config import TEMP_DIR


async def generate_mirage(front_img_path, back_img_path, save_dir: str = TEMP_DIR, mode="gray", a=0.5, b=20, w=0.1):
    """
    合成幻影坦克图片（灰度模式）
    支持模式：
        - gray  : 黑白模式
        - color : 彩色模式
    """
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
    else:
        save_dir = None

    if mode == "gray":
        return await _generate_gray_tank(front_img_path, back_img_path, save_dir)
    elif mode == "color":
        return await _generate_color_tank(front_img_path, back_img_path, save_dir, a, b, w)


async def _generate_gray_tank(front_img_path, back_img_path, save_dir):
    """
    生成灰色幻影坦克
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        _generate_gray_tank_sync,
        front_img_path, back_img_path, save_dir,
    )


def _generate_gray_tank_sync(front_img_path, back_img_path, save_dir, a=5, b=5):
    """
    同步核心算法
    """
    with Image.open(front_img_path) as f_img, Image.open(back_img_path) as b_img:
        image_f = f_img.convert("L")
        image_b = b_img.convert("L")

        # 尺寸对齐
        w, h = min(image_f.width, image_b.width), min(image_f.height, image_b.height)
        image_f = image_f.resize((w, h), Image.Resampling.LANCZOS)
        image_b = image_b.resize((w, h), Image.Resampling.LANCZOS)

        array_f = np.array(image_f, dtype=np.float64)
        array_b = np.array(image_b, dtype=np.float64)
        new_pixels = np.zeros((h, w, 4), dtype=np.uint8)

        # 灰度公式（简化版）
        wf = array_f * a / 10 + 128
        wb = array_b * b / 10
        alpha = 1.0 - wf / 255.0 + wb / 255.0
        R_new = np.where(np.abs(alpha) > 1e-6, wb / alpha, 255.0)

        # 拼接RGBA通道
        new_pixels[:, :, 0] = np.clip(R_new, 0, 255).astype(np.uint8)
        new_pixels[:, :, 1] = new_pixels[:, :, 0]
        new_pixels[:, :, 2] = new_pixels[:, :, 0]
        new_pixels[:, :, 3] = np.clip(alpha * 255.0, 0, 255).astype(np.uint8)

        img = Image.fromarray(new_pixels, mode="RGBA")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png", dir=save_dir) as temp_file:
            img.save(temp_file, format="PNG")
            return temp_file.name


async def _generate_color_tank(front_img_path, back_img_path, save_dir, a, b, w):
    """
    生成彩色幻影坦克
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        _generate_color_tank_sync,
        front_img_path, back_img_path, save_dir, a, b, w
    )


def _generate_color_tank_sync(front_img_path, back_img_path, save_dir, a, b, w):
    """
    同步核心算法
    """

    # 读取图片
    with Image.open(front_img_path) as A_img_raw, Image.open(back_img_path) as B_img_raw:
        A_img = A_img_raw.convert("RGB")
        B_img = B_img_raw.convert("RGB")

        w_img, h_img = A_img.size
        B_img = B_img.resize((w_img, h_img), Image.LANCZOS)

        # 转 numpy 数组
        A_arr = np.array(A_img, dtype=np.float32)  # H,W,3
        B_arr = np.array(B_img, dtype=np.float32)

    # 灰度转换
    A_gray = (
            0.299 * A_arr[:, :, 0] +
            0.587 * A_arr[:, :, 1] +
            0.114 * A_arr[:, :, 2]
    )

    B_gray = (
            0.299 * B_arr[:, :, 0] +
            0.587 * B_arr[:, :, 1] +
            0.114 * B_arr[:, :, 2]
    )

    # 调整 B 亮度（控制里图存在感）
    B_gray = a * B_gray + b

    # alpha 计算
    alpha = 255.0 - A_gray + B_gray
    alpha = np.clip(alpha, 1, 255).astype(np.uint8)
    alpha_3d = alpha.reshape(h_img, w_img, 1)

    # 计算 P（改成 A/B 混合）
    alpha_f = alpha_3d.astype(np.float32)
    A_f = A_arr
    B_f = B_arr

    # w 越大，越偏向里图 B
    base = (1.0 - w) * A_f + w * B_f

    P = (base - (255.0 - alpha_f)) / (alpha_f / 255.0)
    P = np.clip(P, 0, 255).astype(np.uint8)

    # 拼 RGBA
    rgba = np.concatenate([P, alpha_3d], axis=2)
    img_out = Image.fromarray(rgba, mode="RGBA")

    # 保存临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png", dir=save_dir) as tmp:
        img_out.save(tmp.name, format="PNG")
        return tmp.name
