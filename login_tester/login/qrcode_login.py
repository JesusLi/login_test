"""二维码登录策略。

支持两种二维码获取方式：
  1. 截图裁剪：定位页面中的二维码图片元素 → pyzbar 解码 → 终端渲染
  2. 接口拦截：监听网络响应，从 API JSON 中提取二维码 URL → 终端渲染

二维码获取策略通过构造参数 `strategy` 指定：
  - "screenshot"（默认）：截图裁剪
  - "intercept"：接口拦截
"""

import asyncio
import re
from typing import Optional

from playwright.async_api import BrowserContext, Page, Response

from login_tester.config import LoginConfig
from login_tester.exceptions import ElementNotFoundError, LoginError, QRCodeExpiredError
from login_tester.login.base import LoginStrategy
from login_tester.utils.logger import get_logger
from login_tester.utils.qr_renderer import extract_qrcode_url, print_qrcode_to_terminal

logger = get_logger()

# 常见二维码图片 CSS selector（覆盖主流网站）
_QR_IMG_SELECTORS = [
    "img.qrcode",
    "img[class*='qr']",
    "img[class*='QR']",
    "img[class*='qrCode']",
    "canvas[class*='qr']",
    ".qrcode img",
    ".qr-code img",
    "[data-testid*='qr'] img",
]

# 切换到二维码 Tab 的常见文字
_QR_TAB_TEXT_RE = re.compile(r"二维码|扫码|QR\s*Code|scan", re.I)


class QRCodeLoginStrategy(LoginStrategy):
    """二维码登录实现。"""

    def __init__(self, strategy: str = "screenshot") -> None:
        if strategy not in ("screenshot", "intercept"):
            raise ValueError(f"不支持的二维码策略: {strategy}")
        self._strategy = strategy
        self._intercepted_url: Optional[str] = None

    async def login(self, context: BrowserContext, config: LoginConfig) -> bool:
        page = await context.new_page()
        try:
            logger.info("打开登录页面: %s", config.base_url)
            await page.goto(config.base_url, timeout=config.timeout)
            await page.wait_for_load_state("domcontentloaded")

            # 尝试切换到二维码 Tab
            await self._switch_to_qr_tab(page)

            if self._strategy == "screenshot":
                qr_url = await self._get_qr_url_by_screenshot(page)
            else:
                qr_url = await self._get_qr_url_by_intercept(page, config)

            logger.info("请使用手机扫描以下二维码：")
            print_qrcode_to_terminal(qr_url)

            # 轮询等待登录态变化
            await self._wait_for_login(page, config)
            return await self.verify_login(context)
        except (LoginError, QRCodeExpiredError):
            raise
        except Exception as exc:
            raise LoginError(f"二维码登录过程发生异常: {exc}") from exc
        finally:
            await page.close()

    async def verify_login(self, context: BrowserContext) -> bool:
        pages = context.pages
        if not pages:
            return False
        current_url = pages[-1].url
        if re.search(r"login|signin|sign-in", current_url, re.I):
            logger.warning("二维码扫码后 URL 仍含登录关键词，可能未成功: %s", current_url)
            return False
        logger.info("二维码登录成功，当前 URL: %s", current_url)
        return True

    # ------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------

    async def _switch_to_qr_tab(self, page: Page) -> None:
        """尝试点击二维码登录 Tab，不存在时静默跳过。"""
        try:
            tab = page.get_by_text(_QR_TAB_TEXT_RE).first
            if await tab.is_visible(timeout=3000):
                await tab.click()
                await asyncio.sleep(0.5)
                logger.debug("已切换到二维码登录 Tab")
        except Exception:
            logger.debug("未发现二维码 Tab，直接使用当前页面")

    async def _get_qr_url_by_screenshot(self, page: Page) -> str:
        """截图裁剪策略：遍历常见 selector，找到可见的二维码图片并解码。"""
        for selector in _QR_IMG_SELECTORS:
            try:
                loc = page.locator(selector).first
                if await loc.is_visible(timeout=2000):
                    url = await extract_qrcode_url(page, selector)
                    logger.debug("截图解码二维码成功，selector: %s", selector)
                    return url
            except ElementNotFoundError:
                continue
            except Exception:
                continue
        raise ElementNotFoundError(
            "无法通过截图方式找到并解码二维码，"
            "请尝试使用 strategy='intercept' 或手动指定 selector"
        )

    async def _get_qr_url_by_intercept(self, page: Page, config: LoginConfig) -> str:
        """接口拦截策略：监听响应，从 JSON 中提取二维码 URL。"""
        self._intercepted_url = None

        async def _on_response(response: Response) -> None:
            if self._intercepted_url:
                return
            content_type = response.headers.get("content-type", "")
            if "json" not in content_type:
                return
            try:
                body = await response.json()
                url = self._extract_qr_from_json(body)
                if url:
                    self._intercepted_url = url
            except Exception:
                pass

        page.on("response", _on_response)
        await page.reload()
        await page.wait_for_load_state("networkidle")

        deadline = config.timeout / 1000  # 转为秒
        elapsed = 0.0
        while not self._intercepted_url and elapsed < deadline:
            await asyncio.sleep(0.5)
            elapsed += 0.5

        if not self._intercepted_url:
            raise ElementNotFoundError("接口拦截策略未能捕获到二维码 URL")
        return self._intercepted_url

    def _extract_qr_from_json(self, data, _depth: int = 0) -> Optional[str]:
        """递归从 JSON 对象中查找疑似二维码 URL 的字段值。"""
        if _depth > 5:
            return None
        if isinstance(data, dict):
            for key, val in data.items():
                if re.search(r"qr|qrcode|qr_url|ticket", key, re.I) and isinstance(val, str):
                    return val
                result = self._extract_qr_from_json(val, _depth + 1)
                if result:
                    return result
        elif isinstance(data, list):
            for item in data:
                result = self._extract_qr_from_json(item, _depth + 1)
                if result:
                    return result
        return None

    async def _wait_for_login(self, page: Page, config: LoginConfig) -> None:
        """轮询等待 URL 跳转或登录 DOM 消失，超时则抛出 QRCodeExpiredError。"""
        logger.info("等待扫码确认（最多 %d 秒）...", config.timeout // 1000)
        deadline = config.timeout / 1000
        elapsed = 0.0
        original_url = page.url

        while elapsed < deadline:
            await asyncio.sleep(1)
            elapsed += 1
            current_url = page.url
            if current_url != original_url and not re.search(r"login|signin", current_url, re.I):
                logger.info("检测到 URL 跳转，扫码成功")
                return
            # 也检测二维码元素是否消失（扫码后通常会消失或变化）
            for selector in _QR_IMG_SELECTORS:
                try:
                    if not await page.locator(selector).first.is_visible(timeout=500):
                        logger.info("二维码元素已消失，扫码可能成功")
                        return
                except Exception:
                    pass

        raise QRCodeExpiredError(
            f"等待 {config.timeout // 1000} 秒后二维码仍未扫描，请重试"
        )
