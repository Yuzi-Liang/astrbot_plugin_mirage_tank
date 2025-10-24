import asyncio
import os

from PIL import Image
import numpy as np
import tempfile

from ..config import TEMP_DIR


async def generate_mirage(front_img_path, back_img_path, save_dir: str = TEMP_DIR, mode="gray"):
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
        return await _generate_color_tank(front_img_path, back_img_path, save_dir)


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


async def _generate_color_tank(front_img_path, back_img_path, save_dir):
    """
    生成彩色幻影坦克
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        _generate_color_tank_sync,
        front_img_path, back_img_path, save_dir,
    )


def _generate_color_tank_sync(front_img_path, back_img_path, save_dir, a=12, b=7):
    """
    同步核心算法（改写自 CSDN colorful_shio）
    """
    with Image.open(front_img_path) as f_img, Image.open(back_img_path) as b_img:
        image_f = f_img.convert("RGB")
        image_b = b_img.convert("RGB")

        # 尺寸对齐
        w, h = min(image_f.width, image_b.width), min(image_f.height, image_b.height)
        image_f = image_f.resize((w, h), Image.Resampling.LANCZOS)
        image_b = image_b.resize((w, h), Image.Resampling.LANCZOS)

        array_f = np.array(image_f, dtype=np.float64)
        array_b = np.array(image_b, dtype=np.float64)
        new_pixels = np.zeros((h, w, 4), dtype=np.uint8)

        # 核心公式（LAB近似）
        Rf, Gf, Bf = array_f[:, :, 0] * a / 10, array_f[:, :, 1] * a / 10, array_f[:, :, 2] * a / 10
        Rb, Gb, Bb = array_b[:, :, 0] * b / 10, array_b[:, :, 1] * b / 10, array_b[:, :, 2] * b / 10

        delta_r = Rb - Rf
        delta_g = Gb - Gf
        delta_b = Bb - Bf
        coe_a = 8 + 255 / 256 + (delta_r - delta_b) / 256
        coe_b = 4 * delta_r + 8 * delta_g + 6 * delta_b + ((delta_r - delta_b) * (Rb + Rf)) / 256 + (delta_r ** 2 - delta_b ** 2) / 512
        A_new = 255 + coe_b / (2 * coe_a)

        A_new = np.clip(A_new, 0, 255)
        # 防止除 0
        A_safe = np.where(A_new < 1, 1, A_new)
        R_new = np.clip((255 * Rb * b / 10) / A_safe, 0, 255)
        G_new = np.clip((255 * Gb * b / 10) / A_safe, 0, 255)
        B_new = np.clip((255 * Bb * b / 10) / A_safe, 0, 255)

        new_pixels[:, :, 0] = R_new.astype(np.uint8)
        new_pixels[:, :, 1] = G_new.astype(np.uint8)
        new_pixels[:, :, 2] = B_new.astype(np.uint8)
        new_pixels[:, :, 3] = A_new.astype(np.uint8)

        img = Image.fromarray(new_pixels, mode="RGBA")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png", dir=save_dir) as temp_file:
            img.save(temp_file, format="PNG")
            return temp_file.name
