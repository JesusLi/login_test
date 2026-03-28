from abc import ABC, abstractmethod

from playwright.async_api import BrowserContext

from login_tester.config import LoginConfig


class LoginStrategy(ABC):
    """所有登录方式的统一接口。"""

    @abstractmethod
    async def login(self, context: BrowserContext, config: LoginConfig) -> bool:
        """执行登录，成功返回 True，失败抛出 LoginError。"""
        ...

    @abstractmethod
    async def verify_login(self, context: BrowserContext) -> bool:
        """验证当前页面是否已处于登录态。"""
        ...
