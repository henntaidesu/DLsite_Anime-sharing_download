import os
import threading
import time

import requests
from tqdm import tqdm

from src.module.conf_operate import Config
from src.module.log import Log, err1

logger = Log()

API_BASE = 'https://debrid-link.fr/api/v2'

# 正在下载任务的实时进度：UUID -> {'downloaded': 字节数, 'total': 总字节数, 'speed': B/s}
# 由下载线程写入、下载页 UI 读取（同进程内共享）
DOWNLOAD_PROGRESS = {}

# 暂停信号：置位后下载线程停止当前文件（保留断点）并退出
_stop_event = threading.Event()

# API 不可用（无 key / 网络异常）时的兜底域名列表
FALLBACK_DOMAINS = [
    'katfile.com', 'rapidgator.net', 'rg.to', 'mexa.sh', 'mexashare.com',
    'fikper.com', 'ddownload.com', '1fichier.com', 'turbobit.net',
    'nitroflare.com', 'hitfile.net', 'uploady.io', 'filefactory.com',
    'mega.nz', 'filespayout.com', 'filepv.com',
]

_domain_cache = None

# 作品名缓存：work_id -> 作品名称（同一作品的多个分卷只调一次 DL API）
_work_name_cache = {}


def work_folder_path(work_id):
    """返回作品的下载文件夹路径，按设置以 RJ号 或 DL API 返回的作品名称命名"""
    folder = work_id
    if Config().read_folder_name() == 'work_name':
        if work_id not in _work_name_cache:
            try:
                from src.DLsite.DLapi_call import get_work_name
                _work_name_cache[work_id] = get_work_name(work_id) or ''
            except Exception as e:
                err1(e)
                _work_name_cache[work_id] = ''
        name = _work_name_cache[work_id]
        # 去掉 Windows 文件夹名中的非法字符；未获取到作品名时回退到 RJ 号
        for ch in '\\/:*?"<>|':
            name = name.replace(ch, ' ')
        name = ' '.join(name.split()).rstrip('.')
        if name:
            folder = name
        else:
            logger.write_log(f'{work_id} 未从 DL API 获取到作品名称，文件夹按 RJ 号命名', 'error')
    return f"{Config().read_file_down_path()}\\{folder}"


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
    """后台下载线程：轮询 download_list 表，通过 debrid-link 中转下载（支持断点续传）"""
    from src.module.datebase_execution import SQLiteDB

    open_proxy, proxies = Config().read_proxy()
    session = requests.Session()
    if open_proxy is True:
        session.proxies.update(proxies)

    def set_status(key, status, progress=None):
        sql = f'''UPDATE "main"."download_list" SET "status" = '{status}' '''
        if progress is not None:
            sql += f''', "long" = '{progress}' '''
        sql += f'''WHERE UUID = '{key}' '''
        SQLiteDB().update(sql)

    # 上次运行中断时遗留的"下载中"任务重新排队，靠断点续传从已下载部分继续
    SQLiteDB().update('''UPDATE "main"."download_list" SET "status" = '0' WHERE "status" = '3' ''')

    while True:
        key = None
        try:
            if _stop_event.is_set():
                return

            sql = '''SELECT *,rowid "NAVICAT_ROWID" FROM "main"."download_list" WHERE "status" = '0' LIMIT 0, 1'''
            flag, data = SQLiteDB().select(sql)
            if not data:
                # 等待期间收到暂停信号时立即退出
                if _stop_event.wait(10):
                    return
                continue

            data = data[0]
            key = data[0]
            work_id = data[1]
            url = data[2]
            print(f'通过 debrid-link 解析: {url}')
            set_status(key, '3', 0)

            value = DebridLink().add_download(url)
            if not value or not value.get('downloadUrl'):
                logger.write_log(f"{work_id} debrid-link 解析失败: {url}", 'error')
                set_status(key, '2')
                continue

            direct_url = value['downloadUrl']
            filename = value.get('name') or direct_url.rstrip('/').rsplit('/', 1)[-1]
            download_path = work_folder_path(work_id)
            os.makedirs(download_path, exist_ok=True)
            file_path = os.path.join(download_path, filename)

            # 断点续传：本地已有部分文件时从断点继续
            headers = {}
            downloaded = 0
            if os.path.exists(file_path):
                downloaded = os.path.getsize(file_path)
                headers['Range'] = 'bytes=%d-' % downloaded

            response = session.get(direct_url, headers=headers, stream=True, timeout=60)
            if response.status_code == 416:
                # 文件已完整下载
                response.close()
            elif response.status_code in (200, 206):
                if response.status_code == 200:
                    downloaded = 0  # 服务器不支持续传，从头下载
                total_size = downloaded + int(response.headers.get('content-length', 0))
                progress_bar = tqdm(total=total_size, initial=downloaded,
                                    unit='B', unit_scale=True, desc=filename)
                mode = 'ab' if response.status_code == 206 else 'wb'
                last_db_write = 0.0
                speed = 0.0
                speed_time, speed_bytes = time.time(), downloaded
                paused = False
                with open(file_path, mode) as file:
                    for chunk in response.iter_content(1024 * 64):
                        if _stop_event.is_set():
                            paused = True
                            break
                        progress_bar.update(len(chunk))
                        file.write(chunk)
                        downloaded += len(chunk)
                        now = time.time()
                        # 每秒计算一次下载速度
                        if now - speed_time >= 1:
                            speed = (downloaded - speed_bytes) / (now - speed_time)
                            speed_time, speed_bytes = now, downloaded
                        DOWNLOAD_PROGRESS[key] = {
                            'downloaded': downloaded, 'total': total_size, 'speed': speed}
                        # 每 2 秒把进度百分比写回数据库（用于断点续传后恢复显示）
                        if total_size and now - last_db_write >= 2:
                            set_status(key, '3', int(downloaded * 100 / total_size))
                            last_db_write = now
                progress_bar.close()
                if paused:
                    # 暂停：已下载部分保留在磁盘上，任务回到等待状态，下次从断点继续
                    response.close()
                    DOWNLOAD_PROGRESS.pop(key, None)
                    pct = int(downloaded * 100 / total_size) if total_size else 0
                    set_status(key, '0', pct)
                    return
            else:
                logger.write_log(f"{work_id} 下载失败 HTTP {response.status_code}: {direct_url}", 'error')
                set_status(key, '0')
                time.sleep(5)
                continue

            logger.write_log(f"{work_id}已完成下载", 'info')
            DOWNLOAD_PROGRESS.pop(key, None)
            set_status(key, '1', 100)
            _mark_work_downloaded(work_id)
            _auto_unzip_if_done(work_id)

        except requests.exceptions.RequestException as e:
            print(f"网络错误: {e}")
            if key:
                DOWNLOAD_PROGRESS.pop(key, None)
                set_status(key, '0')  # 重新排队，下次从断点继续
            time.sleep(5)
        except Exception as e:
            err1(e)
            if key:
                DOWNLOAD_PROGRESS.pop(key, None)
                set_status(key, '0')
            time.sleep(5)


def _mark_work_downloaded(work_id):
    """该番号的所有任务都下载完成后，works 表状态从 下载中 改为 已下载"""
    from src.module.datebase_execution import SQLiteDB

    sql = f'''SELECT COUNT(*) FROM "main"."download_list"
              WHERE "work_id" = '{work_id}' AND "status" != '1' '''
    result = SQLiteDB().select(sql)
    if result is False or not result[1] or result[1][0][0] != 0:
        return  # 还有未完成的分卷
    SQLiteDB().update(f'''UPDATE "main"."works" SET "state" = '已下载'
                          WHERE "work_id" = '{work_id}' AND "state" = '下载中' ''')


def _auto_unzip_if_done(work_id):
    """开启自动解压时，该番号的所有任务都下载完成后在后台线程解压"""
    from src.module.datebase_execution import SQLiteDB

    if not Config().read_auto_unzip():
        return
    sql = f'''SELECT COUNT(*) FROM "main"."download_list"
              WHERE "work_id" = '{work_id}' AND "status" != '1' '''
    result = SQLiteDB().select(sql)
    if result is False or not result[1] or result[1][0][0] != 0:
        return  # 还有未完成的分卷，等全部下载完再解压

    from src.module.unzip import unzip
    logger.write_log(f'{work_id} 下载完成，开始自动解压', 'info')
    threading.Thread(target=unzip, args=(work_id,), daemon=True).start()


_download_thread = None


def start_download_worker():
    """启动后台下载线程；已在运行时不重复启动，返回是否新启动"""
    global _download_thread
    if download_worker_running():
        return False
    _stop_event.clear()
    _download_thread = threading.Thread(target=QTUI_debrid_down, daemon=True)
    _download_thread.start()
    return True


def stop_download_worker():
    """请求暂停下载：当前文件停到断点后线程退出，再次开始时续传"""
    _stop_event.set()


def stop_requested():
    return _stop_event.is_set()


def download_worker_running():
    return _download_thread is not None and _download_thread.is_alive()
