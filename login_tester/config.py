from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse


@dataclass
class LoginConfig:
    base_url: str                        # 登录页面完整 URL
    login_method: str                    # "password" | "qrcode"
    homepage_url: Optional[str] = None  # 登录后访问的主页 URL，默认为 base_url 的域名根路径
    username: Optional[str] = None
    password: Optional[str] = None
    headless: bool = True                # 无头模式（二维码方式强制 False）
    timeout: int = 60000                 # ms，等待超时
    storage_dir: str = "storage/states" # 登录态保存目录

    def get_homepage_url(self) -> str:
        """返回主页 URL，未配置时自动降级为 base_url 的域名根路径"""
        if self.homepage_url:
            return self.homepage_url
        p = urlparse(self.base_url)
        return f"{p.scheme}://{p.netloc}/"
