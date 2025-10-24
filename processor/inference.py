import asyncio

from PIL import Image
import numpy as np
import tempfile


WHITE_RGBA = np.array([255, 255, 255, 255], dtype=np.uint8)
BLACK_RGBA = np.array([0, 0, 0, 0], dtype=np.uint8)


async def generate_mirage(front_img_path, back_img_path, mode="gray", a=12, b=7):
    """
    合成幻影坦克图片（灰度模式）
    支持模式：
        - gray  : 黑白模式
        - color : 彩色模式
    """
    if mode == "gray":
        return await _generate_gray_tank(front_img_path, back_img_path)
    else:
        return await _generate_color_tank(front_img_path, back_img_path, a, b)


async def _generate_gray_tank(front_img_path, back_img_path):
    """
    生成灰度幻影坦克
    """
    wimg = Image.open(front_img_path).convert("L")
    bimg = Image.open(back_img_path).convert("L").resize(wimg.size)

    wpix = np.array(wimg).astype("float64")
    bpix = np.array(bimg).astype("float64")

    wpix = wpix * 0.5 + 128
    bpix *= 0.5

    a = 1.0 - wpix / 255.0 + bpix / 255.0
    r = np.where(abs(a) > 1e-6, bpix / a, 255.0)

    pixels = np.dstack((r, r, r, a * 255.0))
    pixels[pixels > 255] = 255

    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
        Image.fromarray(pixels.astype("uint8"), "RGBA").save(temp_file, format="PNG")
        return temp_file.name


async def _generate_color_tank(front_img_path, back_img_path, wlight=1.0, blight=0.25, wcolor=0.5, bcolor=0.7):
    """
    生成彩色幻影坦克
    wlight: 表图亮度调节因子 (推荐 1.0~1.3)
    blight: 里图亮度调节因子 (推荐 0.15~0.3)
    wcolor: 表图色彩保留比例 (推荐 0.4~0.6)
    bcolor: 里图色彩保留比例 (推荐 0.6~0.8)
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        _generate_color_tank_sync,
        front_img_path, back_img_path,
        wlight, blight, wcolor, bcolor
    )


def _generate_color_tank_sync(front_img_path, back_img_path, wlight=1.0, blight=0.25, wcolor=0.5, bcolor=0.7):
    """同步核心算法"""

    # 打开图片并统一尺寸
    image_f = Image.open(front_img_path).convert("RGB")
    image_b = Image.open(back_img_path).convert("RGB")

    w, h = min(image_f.width, image_b.width), min(image_f.height, image_b.height)
    image_f = image_f.resize((w, h), Image.Resampling.CATMULLROM)
    image_b = image_b.resize((w, h), Image.Resampling.CATMULLROM)

    # 转为 numpy 数组 (0~1)
    wpix = np.array(image_f, dtype=np.float32) / 255.0
    bpix = np.array(image_b, dtype=np.float32) / 255.0

    # 调整亮度
    wpix *= wlight
    bpix *= blight

    # 计算灰度
    wgray = np.minimum(np.mean(wpix, axis=2, keepdims=True), 1.0)
    bgray = np.minimum(np.mean(bpix, axis=2, keepdims=True), 1.0)

    # 调整色彩保真度
    wpix = wpix * wcolor + wgray * (1.0 - wcolor)
    bpix = bpix * bcolor + bgray * (1.0 - bcolor)

    # 幻影坦克公式
    drgb = 1.0 - wpix + bpix

    # alpha = min( max(luma(d), max(brgb)), 1.0 )
    a_lum = drgb[:, :, 0] * 0.2126 + drgb[:, :, 1] * 0.7152 + drgb[:, :, 2] * 0.0722
    bmax = np.max(bpix, axis=2)
    a = np.minimum(np.maximum(a_lum, bmax), 1.0)

    # 输出 RGB = brgb / a
    denom = np.maximum(a[:, :, None], 1e-6)
    out_rgb = np.clip((bpix / denom) * 255.0, 0.0, 255.0).astype(np.uint8)
    out_alpha = np.clip(a * 255.0, 0.0, 255.0).astype(np.uint8)

    rgba = np.concatenate([out_rgb, out_alpha[:, :, None]], axis=2)
    img = Image.fromarray(rgba, mode="RGBA")

    # 保存临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
        img.save(temp_file.name, format="PNG")
        return temp_file.name