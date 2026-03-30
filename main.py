#!/usr/bin/env python3
"""登录测试工具 — CLI 入口。

运行方式::

    python main.py

或直接执行（需 chmod +x）::

    ./main.py
"""

import asyncio
import getpass
import os
import sys
import time

from login_tester.accessor.homepage_accessor import HomepageAccessor
from login_tester.config import LoginConfig
from login_tester.exceptions import LoginError, QRCodeExpiredError, SessionExpiredError
from login_tester.login_manager import LoginManager
from login_tester.utils.logger import get_logger

logger = get_logger()


def _prompt(msg: str, default: str = "") -> str:
    value = input(msg).strip()
    return value if value else default


def _collect_config() -> LoginConfig:
    print("\n欢迎使用登录测试工具\n" + "=" * 40)

    base_url = _prompt("请输入登录地址（如 https://example.com/login）: ")
    if not base_url:
        print("[ERROR] 登录地址不能为空")
        sys.exit(1)

    homepage_url = _prompt(
        "请输入登录后的主页地址（留空则使用域名根路径）: "
    ) or None

    print("\n请选择登录方式:")
    print("  [1] 账号密码")
    print("  [2] 二维码（自动识别，失败时降级到接口拦截）")
    print("  [3] 二维码（直接使用接口拦截）")
    method_input = _prompt("请输入选项 [1/2/3]: ", default="1")

    login_method = "password"
    qr_strategy = "screenshot"
    if method_input == "2":
        login_method = "qrcode"
        qr_strategy = "screenshot"
    elif method_input == "3":
        login_method = "qrcode"
        qr_strategy = "intercept"

    username = password = None
    if login_method == "password":
        username = _prompt("请输入用户名: ")
        password = getpass.getpass("请输入密码: ")
        if not username or not password:
            print("[ERROR] 用户名和密码不能为空")
            sys.exit(1)

    return LoginConfig(
        base_url=base_url,
        login_method=login_method,
        homepage_url=homepage_url,
        username=username,
        password=password,
        headless=True,  # 始终无头模式，CLI 环境无需显示浏览器窗口
        qr_strategy=qr_strategy,
    )


async def _run(config: LoginConfig) -> None:
    manager = LoginManager()

    # Step 1: 登录并获取 storageState 路径
    logger.info("正在启动浏览器...")
    state_path = await manager.run(config)

    # Step 2: 使用登录态访问主页
    accessor = HomepageAccessor(storage_state_path=state_path, config=config)
    result = await accessor.fetch()

    # 保存 HTML 到 storage/pages/
    html_path = _save_html(result, config)

    print("\n" + "=" * 40)
    print(f"主页标题 : {result['title']}")
    print(f"主页 URL  : {result['url']}")
    print(f"登录态文件: {state_path}")
    print(f"主页 HTML : {html_path}")
    print("=" * 40)


def _save_html(result: dict, config: LoginConfig) -> str:
    """将主页 HTML 内容保存到 storage/pages/ 目录，返回文件路径。"""
    from urllib.parse import urlparse
    domain = urlparse(config.base_url).netloc.replace(":", "_")
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    pages_dir = os.path.join(config.storage_dir.rsplit("/", 1)[0], "pages")
    os.makedirs(pages_dir, exist_ok=True)
    html_path = os.path.join(pages_dir, f"{domain}_{timestamp}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(result["content"])
    logger.info("主页 HTML 已保存至 %s", html_path)
    return html_path


def main() -> None:
    config = _collect_config()
    try:
        asyncio.run(_run(config))
    except KeyboardInterrupt:
        print("\n已取消")
    except QRCodeExpiredError as exc:
        print(f"\n[ERROR] 二维码超时: {exc}")
        sys.exit(1)
    except LoginError as exc:
        print(f"\n[ERROR] 登录失败: {exc}")
        sys.exit(1)
    except SessionExpiredError as exc:
        print(f"\n[ERROR] 登录态已过期: {exc}")
        sys.exit(1)
    except Exception as exc:
        logger.exception("未预期的错误: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
