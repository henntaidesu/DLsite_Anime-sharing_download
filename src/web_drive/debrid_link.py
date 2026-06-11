import os
import time

import requests
from tqdm import tqdm

from src.module.conf_operate import Config
from src.module.log import Log, err1

logger = Log()

API_BASE = 'https://debrid-link.fr/api/v2'

# API 不可用（无 key / 网络异常）时的兜底域名列表
FALLBACK_DOMAINS = [
    'katfile.com', 'rapidgator.net', 'rg.to', 'mexa.sh', 'mexashare.com',
    'fikper.com', 'ddownload.com', '1fichier.com', 'turbobit.net',
    'nitroflare.com', 'hitfile.net', 'uploady.io', 'filefactory.com',
    'mega.nz', 'filespayout.com', 'filepv.com',
]

_domain_cache = None


class DebridLink:
    """debrid-link.com 下载中转站 API 客户端"""

    def __init__(self):
        conf = Config()
        self.api_key = conf.read_debrid_api_key()
        open_proxy, proxies = conf.read_proxy()
        self.session = requests.Session()
        if open_proxy is True:
            self.session.proxies.update(proxies)
        if self.api_key:
            self.session.headers['Authorization'] = f'Bearer {self.api_key}'

    def _request(self, method, path, **kwargs):
        kwargs.setdefault('timeout', 30)
        response = self.session.request(method, f'{API_BASE}/{path}', **kwargs)
        data = response.json()
        if not data.get('success'):
            logger.write_log(f"debrid-link API 错误: {path} -> {data.get('error')}", 'error')
            return None
        return data.get('value')

    def account_infos(self):
        return self._request('GET', 'account/infos')

    def get_domains(self):
        """获取 debrid-link 支持解析的网盘域名列表"""
        value = self._request('GET', 'downloader/domains')
        if isinstance(value, dict):
            domains = []
            for item in value.values():
                domains.extend(item if isinstance(item, list) else [item])
            return domains
        return value or []

    def add_download(self, url, password=None):
        """提交网盘链接，返回包含 downloadUrl / name / size 的字典"""
        form = {'url': url}
        if password:
            form['password'] = password
        return self._request('POST', 'downloader/add', data=form)


def supported_domains():
    """返回 debrid-link 支持的域名列表（每次运行只请求一次 API）"""
    global _domain_cache
    if _domain_cache:
        return _domain_cache
    try:
        domains = DebridLink().get_domains()
    except Exception as e:
        err1(e)
        domains = []
    _domain_cache = [d.lower() for d in domains] if domains else FALLBACK_DOMAINS
    return _domain_cache


def QTUI_debrid_down():
    """后台下载线程：轮询 download_list 表，通过 debrid-link 中转下载"""
    from src.module.datebase_execution import SQLiteDB

    open_proxy, proxies = Config().read_proxy()
    session = requests.Session()
    if open_proxy is True:
        session.proxies.update(proxies)

    while True:
        try:
            sql = '''SELECT *,rowid "NAVICAT_ROWID" FROM "main"."download_list" WHERE "status" = '0' LIMIT 0, 1'''
            flag, data = SQLiteDB().select(sql)
            if not data:
                time.sleep(10)
                continue

            data = data[0]
            key = data[0]
            work_id = data[1]
            url = data[2]
            print(f'通过 debrid-link 解析: {url}')

            value = DebridLink().add_download(url)
            if not value or not value.get('downloadUrl'):
                logger.write_log(f"{work_id} debrid-link 解析失败: {url}", 'error')
                sql = f'''UPDATE "main"."download_list" SET "status" = '2' WHERE UUID = '{key}' '''
                SQLiteDB().update(sql)
                continue

            direct_url = value['downloadUrl']
            filename = value.get('name') or direct_url.rstrip('/').rsplit('/', 1)[-1]
            download_path = f"{Config().read_file_down_path()}\\{work_id}"
            os.makedirs(download_path, exist_ok=True)
            file_path = os.path.join(download_path, filename)

            # 断点续传：本地已有部分文件时从断点继续
            headers = {}
            if os.path.exists(file_path):
                headers['Range'] = 'bytes=%d-' % os.path.getsize(file_path)

            response = session.get(direct_url, headers=headers, stream=True, timeout=60)
            if response.status_code == 416:
                # 文件已完整下载
                response.close()
            elif response.status_code in (200, 206):
                total_size = int(response.headers.get('content-length', 0))
                progress_bar = tqdm(total=total_size, unit='B', unit_scale=True, desc=filename)
                mode = 'ab' if response.status_code == 206 else 'wb'
                with open(file_path, mode) as file:
                    for chunk in response.iter_content(1024 * 64):
                        progress_bar.update(len(chunk))
                        file.write(chunk)
                progress_bar.close()
            else:
                logger.write_log(f"{work_id} 下载失败 HTTP {response.status_code}: {direct_url}", 'error')
                time.sleep(5)
                continue

            logger.write_log(f"{work_id}已完成下载", 'info')
            sql = f'''UPDATE "main"."download_list" SET "status" = '1' WHERE UUID = '{key}' '''
            SQLiteDB().update(sql)

        except requests.exceptions.RequestException as e:
            print(f"网络错误: {e}")
            time.sleep(5)
        except Exception as e:
            err1(e)
            time.sleep(5)


_download_thread = None


def start_download_worker():
    """启动后台下载线程；已在运行时不重复启动，返回是否新启动"""
    global _download_thread
    if download_worker_running():
        return False
    import threading
    _download_thread = threading.Thread(target=QTUI_debrid_down, daemon=True)
    _download_thread.start()
    return True


def download_worker_running():
    return _download_thread is not None and _download_thread.is_alive()
