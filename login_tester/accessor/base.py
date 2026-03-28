from abc import ABC, abstractmethod

from login_tester.config import LoginConfig


class PageAccessor(ABC):
    """基于已保存登录态访问页面的基类（供后续扩展）。

    目标 URL 统一通过 ``self.config.get_homepage_url()`` 取得，
    遵循单一数据源原则，子类不应自行维护 target_url。
    """

    def __init__(self, storage_state_path: str, config: LoginConfig) -> None:
        self.storage_state_path = storage_state_path
        self.config = config

    @abstractmethod
    async def fetch(self) -> dict:
        """访问目标页面，返回结构化数据。"""
        ...
