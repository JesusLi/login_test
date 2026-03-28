"""终端二维码渲染工具。

提供两个公共函数：
- print_qrcode_to_terminal(url): 给定 URL，直接渲染 ASCII 二维码到终端
- extract_qrcode_url(page, selector): 从页面图片元素截图中解码二维码 URL
"""

import io

import qrcode
from PIL import Image

from login_tester.exceptions import ElementNotFoundError


def print_qrcode_to_terminal(url: str) -> None:
    """将 URL 渲染为 ASCII 二维码并打印到终端。"""
    qr = qrcode.QRCode()
    qr.add_data(url)
    qr.make(fit=True)
    qr.print_ascii(invert=True)  # invert=True 在深色终端下效果更佳


async def extract_qrcode_url(page, selector: str) -> str:
    """从页面二维码图片元素中提取 URL。

    Args:
        page: Playwright Page 对象
        selector: 定位二维码图片的 CSS/XPath selector

    Returns:
        二维码中编码的字符串（通常为 URL）

    Raises:
        ElementNotFoundError: 无法从截图中解码二维码内容
    """
    try:
        from pyzbar.pyzbar import decode as pyzbar_decode
    except ImportError as exc:
        raise ImportError(
            "pyzbar 未安装，请执行: pip install pyzbar"
        ) from exc

    img_bytes = await page.locator(selector).screenshot()
    image = Image.open(io.BytesIO(img_bytes))
    results = pyzbar_decode(image)
    if not results:
        raise ElementNotFoundError("无法从二维码图片中解码内容，请确认 selector 正确且二维码可见")
    return results[0].data.decode("utf-8")
