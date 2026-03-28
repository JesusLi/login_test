"""Playwright 浏览器会话管理。

以 async context manager 方式使用，保证浏览器资源正确释放。

用法::

    async with BrowserSession(headless=True) as session:
        context = await session.new_context(storage_state_path=None)
        ...
        await session.save_state(context, "storage/states/example.json")
"""

from __future__ import annotations

from typing import Optional

from playwright.async_api import (
    Browser,
    BrowserContext,
    Playwright,
    async_playwright,
)

from login_tester.utils.logger import get_logger

logger = get_logger()


class BrowserSession:
    """封装 Playwright Browser + BrowserContext 生命周期。"""

    def __init__(self, headless: bool = True) -> None:
        self.headless = headless
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None

    async def __aenter__(self) -> "BrowserSession":
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)
        logger.info("浏览器已启动（headless=%s）", self.headless)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("浏览器已关闭")

    async def new_context(self, storage_state_path: Optional[str] = None) -> BrowserContext:
        """创建新的 BrowserContext。

        Args:
            storage_state_path: 已保存登录态文件路径；为 None 时创建全新会话。
        """
        if storage_state_path:
            logger.info("加载已有登录态: %s", storage_state_path)
            context = await self._browser.new_context(storage_state=storage_state_path)
        else:
            context = await self._browser.new_context()
        return context

    async def save_state(self, context: BrowserContext, path: str) -> None:
        """将当前会话的 Cookie + Storage 保存到文件。"""
        import os
        os.makedirs(os.path.dirname(path), exist_ok=True)
        await context.storage_state(path=path)
        logger.info("登录态已保存至 %s", path)
