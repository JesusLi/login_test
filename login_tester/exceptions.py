class LoginError(Exception):
    """登录失败（账密错误、验证码拦截、超时等）"""


class ElementNotFoundError(LoginError):
    """无法定位登录表单元素（Selector 不匹配）"""


class QRCodeExpiredError(LoginError):
    """二维码超时未扫码"""


class SessionExpiredError(Exception):
    """复用已保存的登录态时，服务端会话已失效"""
