"""主页信息访问器。

使用已保存的登录态打开主页，返回页面标题、URL 和完整 HTML。
"""

from login_tester.accessor.base import PageAccessor
from login_tester.browser_session import BrowserSession
from login_tester.utils.logger import get_logger

logger = get_logger()


class HomepageAccessor(PageAccessor):
    """访问登录后的主页，提取标题、URL 和 HTML 内容。"""

    async def fetch(self) -> dict:
        target_url = self.config.get_homepage_url()
        logger.info("正在访问主页: %s", target_url)

        async with BrowserSession(headless=True) as session:
            context = await session.new_context(self.storage_state_path)
            page = await context.new_page()
            await page.goto(target_url, timeout=self.config.timeout)
            await page.wait_for_load_state("networkidle", timeout=self.config.timeout)

            result = {
                "title": await page.title(),
                "url": page.url,
                "content": await page.content(),
            }
            await page.close()

        logger.info("主页标题: %s", result["title"])
        logger.info("主页 URL: %s", result["url"])
        return result
