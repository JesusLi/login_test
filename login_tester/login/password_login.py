"""账号密码登录策略。

元素定位优先级：
  1. aria-label / role（国际化友好）
  2. placeholder 属性
  3. type 属性（input[type=password]）
  4. 通用 CSS Selector 兜底
"""

import re

from playwright.async_api import BrowserContext, Page

from login_tester.config import LoginConfig
from login_tester.exceptions import ElementNotFoundError, LoginError
from login_tester.login.base import LoginStrategy
from login_tester.utils.logger import get_logger

logger = get_logger()

# 用于匹配用户名/密码/按钮的正则
_USERNAME_RE = re.compile(r"用户名|username|账号|email|邮箱", re.I)
_PASSWORD_RE = re.compile(r"密码|password", re.I)
_LOGIN_BTN_RE = re.compile(r"^(登录|登 录|login|sign[\s\-]?in)$", re.I)


class PasswordLoginStrategy(LoginStrategy):
    """账号密码登录实现。"""

    async def login(self, context: BrowserContext, config: LoginConfig) -> bool:
        page = await context.new_page()
        try:
            logger.info("打开登录页面: %s", config.base_url)
            await page.goto(config.base_url, timeout=config.timeout)
            await page.wait_for_load_state("domcontentloaded")

            await self._fill_username(page, config)
            await self._fill_password(page, config)
            await self._click_login_button(page, config)

            await page.wait_for_load_state("networkidle", timeout=config.timeout)
            return await self.verify_login(context)
        except LoginError:
            raise
        except Exception as exc:
            raise LoginError(f"登录过程发生异常: {exc}") from exc
        finally:
            await page.close()

    async def verify_login(self, context: BrowserContext) -> bool:
        """简单验证：确认当前页面不再是登录页（URL 已跳转）。"""
        pages = context.pages
        if not pages:
            return False
        current_url = pages[-1].url
        # 若 URL 中仍含 login/signin 等关键词，则认为未登录成功
        if re.search(r"login|signin|sign-in", current_url, re.I):
            logger.warning("登录后 URL 仍含登录关键词，可能登录失败: %s", current_url)
            return False
        logger.info("登录成功，当前 URL: %s", current_url)
        return True

    # ------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------

    async def _fill_username(self, page: Page, config: LoginConfig) -> None:
        locator = (
            page.get_by_role("textbox", name=_USERNAME_RE)
            .or_(page.locator("input[type=text][placeholder]").filter(has_text=""))
            .first
        )
        # 逐级尝试定位
        candidates = [
            page.get_by_role("textbox", name=_USERNAME_RE).first,
            page.locator("input[autocomplete='username']"),
            page.locator("input[type='email']"),
            page.locator("input[type='text']").first,
        ]
        filled = False
        for loc in candidates:
            try:
                if await loc.is_visible(timeout=2000):
                    await loc.fill(config.username)
                    logger.debug("已填写用户名")
                    filled = True
                    break
            except Exception:
                continue
        if not filled:
            raise ElementNotFoundError("无法定位用户名输入框")

    async def _fill_password(self, page: Page, config: LoginConfig) -> None:
        candidates = [
            page.get_by_role("textbox", name=_PASSWORD_RE).first,
            page.locator("input[type='password']").first,
        ]
        filled = False
        for loc in candidates:
            try:
                if await loc.is_visible(timeout=2000):
                    await loc.fill(config.password)
                    logger.debug("已填写密码")
                    filled = True
                    break
            except Exception:
                continue
        if not filled:
            raise ElementNotFoundError("无法定位密码输入框")

    async def _click_login_button(self, page: Page, config: LoginConfig) -> None:
        candidates = [
            page.get_by_role("button", name=_LOGIN_BTN_RE).first,
            page.locator("button[type='submit']").first,
            page.locator("input[type='submit']").first,
        ]
        clicked = False
        for loc in candidates:
            try:
                if await loc.is_visible(timeout=2000):
                    await loc.click()
                    logger.debug("已点击登录按钮")
                    clicked = True
                    break
            except Exception:
                continue
        if not clicked:
            raise ElementNotFoundError("无法定位登录按钮")
