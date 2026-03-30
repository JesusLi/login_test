# login_tester

基于 [Playwright](https://playwright.dev/python/) 的网页登录自动化工具，支持账号密码和二维码两种登录方式，登录成功后自动保存会话状态并抓取主页内容。

## 功能

- **账号密码登录**：自动定位用户名、密码输入框及登录按钮，兼容中英文页面
- **二维码登录**：支持截图解码和接口拦截两种方式提取二维码，并在终端渲染供手机扫描
- **登录态复用**：将 `storageState`（Cookie + LocalStorage）保存为 JSON 文件，8 小时内自动复用，无需重复登录
- **主页抓取**：登录成功后访问目标主页，保存页面标题、URL 和完整 HTML 到 `storage/pages/`

## 目录结构

```
login_test/
├── main.py                        # CLI 入口
├── requirements.txt
├── storage/
│   ├── states/                    # 登录态 JSON 文件（自动生成）
│   └── pages/                     # 主页 HTML 快照（自动生成）
└── login_tester/
    ├── config.py                  # LoginConfig 配置类
    ├── login_manager.py           # 登录流程协调器（策略路由 + TTL 复用）
    ├── browser_session.py         # Playwright 浏览器会话封装
    ├── exceptions.py              # 自定义异常
    ├── login/
    │   ├── base.py                # LoginStrategy 抽象基类
    │   ├── password_login.py      # 账号密码登录策略
    │   └── qrcode_login.py        # 二维码登录策略
    ├── accessor/
    │   ├── base.py                # PageAccessor 抽象基类
    │   └── homepage_accessor.py   # 主页内容访问器
    └── utils/
        ├── logger.py              # 日志工具
        └── qr_renderer.py         # 二维码终端渲染
```

## 安装

**Python 版本要求**：3.10+

```bash
pip install -r requirements.txt
playwright install chromium
```

## 使用

```bash
python main.py
```

按照交互提示依次输入：

1. 登录页面地址（如 `https://example.com/login`）
2. 登录后主页地址（可留空，自动使用域名根路径）
3. 登录方式：`[1]` 账号密码 / `[2]` 二维码
4. 账号密码（二维码方式跳过，选账号密码后在终端扫描二维码）

登录完成后，终端输出：

```
========================================
主页标题 : 示例系统
主页 URL  : https://example.com/dashboard
登录态文件: storage/states/example.com_password_20260330.json
主页 HTML : storage/pages/example.com_20260330_120000.html
========================================
```

## 登录态文件

登录成功后，会话状态保存为：

```
storage/states/<domain>_<method>_<date>.json
```

8 小时内再次运行时会自动复用，无需重新登录。

## 依赖

| 包 | 用途 |
|---|---|
| playwright | 浏览器自动化 |
| qrcode[pil] | 终端二维码渲染 |
| Pillow | 图像处理 |
| pyzbar | 二维码图像解码 |
