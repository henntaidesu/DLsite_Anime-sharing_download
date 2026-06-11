import requests

from src.module.conf_operate import Config
from src.module.log import Log

logger = Log()

USER_AGENT = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')

# 个别网盘（如 rapidgator）对失效文件返回 200 + 错误页而非 404，
# 需要用页面中明确的死链提示语兜底（统一小写匹配）
DEAD_MARKERS = [
    'file not found',
    '404 file',
    'file was deleted',
    'file has expired',
    'file does not exist',
]


def make_session():
    """创建带统一代理配置的会话，供批量检测复用"""
    open_proxy, proxies = Config().read_proxy()
    session = requests.Session()
    if open_proxy is True:
        session.proxies.update(proxies)
    session.headers['User-Agent'] = USER_AGENT
    return session


def check_url(url, session=None):
    """直连访问下载链接判断是否有效（不经过下载中转站）

    判定规则：
    1. HTTP 404 等 4xx/5xx 状态 → 失效（网盘对已删除/过期文件通常返回 404，katfile 返回 500）
    2. 返回 200 但页面是明确的"文件不存在"错误页 → 失效（rapidgator 等不返回 404 的网盘）
    3. 其余 → 有效
    返回 True=有效，False=失效或无法访问
    """
    if session is None:
        session = make_session()
    try:
        response = session.get(url, timeout=20, allow_redirects=True)
    except requests.exceptions.RequestException:
        return False

    if response.status_code >= 400:
        return False

    text = response.text.lower()
    return not any(marker in text for marker in DEAD_MARKERS)
