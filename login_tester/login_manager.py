"""登录流程协调器。

负责：
- 路由到对应的 LoginStrategy
- 调用 BrowserSession 执行登录
- 保存 / 复用 storageState 文件
"""

import hashlib
import os
import time
from typing import Optional

from login_tester.browser_session import BrowserSession
from login_tester.config import LoginConfig
from login_tester.exceptions import LoginError
from login_tester.login.password_login import PasswordLoginStrategy
from login_tester.login.qrcode_login import QRCodeLoginStrategy
from login_tester.utils.logger import get_logger

logger = get_logger()


class LoginManager:
    STRATEGIES = {
        "password": PasswordLoginStrategy,
        "qrcode": QRCodeLoginStrategy,
    }

    async def run(self, config: LoginConfig) -> str:
        """执行完整登录流程，返回 storage_state 文件路径。

        若已存在有效的登录态文件（TTL 内），直接跳过登录步骤复用。
        """
        state_path = self._resolve_state_path(config)

        # 尝试复用已有登录态
        reused = self._find_valid_state(state_path, ttl_hours=8)
        if reused:
            logger.info("复用已有登录态: %s", reused)
            return reused

        strategy_cls = self.STRATEGIES.get(config.login_method)
        if strategy_cls is None:
            raise ValueError(f"不支持的登录方式: {config.login_method}")

        strategy = strategy_cls()
        # 二维码方式强制非无头模式
        headless = config.headless if config.login_method != "qrcode" else False

        async with BrowserSession(headless=headless) as session:
            context = await session.new_context(storage_state_path=None)
            logger.info("正在执行 [%s] 登录...", config.login_method)
            success = await strategy.login(context, config)
            if not success:
                raise LoginError("登录验证失败，请检查账号密码或重新扫码")
            await session.save_state(context, state_path)

        return state_path

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _resolve_state_path(self, config: LoginConfig) -> str:
        """生成登录态文件路径：<storage_dir>/<domain>_<method>_<date>.json"""
        from urllib.parse import urlparse
        domain = urlparse(config.base_url).netloc.replace(":", "_")
        date_str = time.strftime("%Y%m%d")
        filename = f"{domain}_{config.login_method}_{date_str}.json"
        return os.path.join(config.storage_dir, filename)

    def _find_valid_state(self, path: str, ttl_hours: int = 8) -> Optional[str]:
        """若文件存在且在 TTL 内，返回路径；否则返回 None。"""
        if not os.path.exists(path):
            return None
        age_seconds = time.time() - os.path.getmtime(path)
        if age_seconds < ttl_hours * 3600:
            return path
        logger.info("已有登录态文件超过 TTL（%dh），将重新登录", ttl_hours)
        return None
