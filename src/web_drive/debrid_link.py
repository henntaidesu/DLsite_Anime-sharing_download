import os
import shutil
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

# 正在解压作品的实时进度：work_id -> {'state': 'pending'|'extracting', 'pct': 0~100}
# 下载完成后由解压线程写入、下载页 UI 读取，全部分卷已下载完成才会出现在此
UNZIP_PROGRESS = {}

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

CHUNK = 1024 * 64           # 每次读取的块大小

# UI 指定的每作品媒体库目标根目录与所属媒体库名：work_id -> 文件夹路径 / 媒体库名
# 下载/解压都在缓存目录进行，解压完成后再移动到此目标目录
_work_target_paths = {}
_work_target_libs = {}


def set_work_target_path(work_id, path, lib_name=None):
    """由 UI 在入队时设定作品解压完成后要移动到的媒体库目标目录及所属媒体库名。
    除写入内存外立即写入 works 表（works 行须已存在），防止程序重启后丢失。"""
    _work_target_paths[work_id] = path
    _work_target_libs[work_id] = lib_name
    from src.module.datebase_execution import SQLiteDB
    esc_path = str(path).replace("'", "''")
    esc_lib = str(lib_name).replace("'", "''") if lib_name else ''
    SQLiteDB().update(
        f'''UPDATE "main"."works" SET "target" = '{esc_path}', "target_lib" = '{esc_lib}'
            WHERE "work_id" = '{work_id}' ''')


def _folder_leaf_name(work_id):
    """作品子文件夹名：按设置以 RJ号 或 DL API 返回的作品名称命名"""
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
    return folder


def _resolve_work_folder(work_id):
    """按缓存路径（设置中的“缓存路径”）+ 子文件夹名计算作品缓存文件夹完整路径"""
    base = Config().read_file_down_path()
    return f"{base}\\{_folder_leaf_name(work_id)}"


def work_folder_path(work_id):
    """返回作品的缓存文件夹完整路径（下载与解压都在此进行）。
    优先使用 works 表中已持久化的路径，保证同一作品的所有分卷、以及进程重启后的
    续传与解压都落在同一目录；未持久化时再按缓存路径设置计算。"""
    from src.module.datebase_execution import SQLiteDB
    result = SQLiteDB().select(
        f'''SELECT "folder" FROM "main"."works" WHERE "work_id" = '{work_id}' ''')
    if result is not False and result[1] and result[1][0][0]:
        return result[1][0][0]
    return _resolve_work_folder(work_id)


def persist_work_folder(work_id, path):
    """把作品的缓存文件夹完整路径写入 works 表（仅在尚未写入时），
    使重启后的续传、解压都能找到同一目录。"""
    from src.module.datebase_execution import SQLiteDB
    esc = str(path).replace("'", "''")
    SQLiteDB().update(
        f'''UPDATE "main"."works" SET "folder" = '{esc}'
            WHERE "work_id" = '{work_id}' AND ("folder" IS NULL OR "folder" = '') ''')


def read_work_target_lib(work_id):
    """读取作品所属媒体库名：优先本次会话的内存选择，其次 works.target_lib（重启后用）"""
    if _work_target_libs.get(work_id):
        return _work_target_libs[work_id]
    from src.module.datebase_execution import SQLiteDB
    result = SQLiteDB().select(
        f'''SELECT "target_lib" FROM "main"."works" WHERE "work_id" = '{work_id}' ''')
    if result is not False and result[1] and result[1][0][0]:
        return result[1][0][0]
    return None


def _read_work_target(work_id):
    """读取作品的媒体库目标根目录：优先本次会话的内存选择，其次 works.target（重启后续传用）"""
    if _work_target_paths.get(work_id):
        return _work_target_paths[work_id]
    from src.module.datebase_execution import SQLiteDB
    result = SQLiteDB().select(
        f'''SELECT "target" FROM "main"."works" WHERE "work_id" = '{work_id}' ''')
    if result is not False and result[1] and result[1][0][0]:
        return result[1][0][0]
    return None


def _folder_size(folder):
    """目录下所有文件的总字节数（目录不存在时为 0），用于估算移动进度"""
    total = 0
    for root, _dirs, files in os.walk(folder):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
    return total


def move_to_target_folder(work_id, cache_folder):
    """解压完成后把作品从缓存目录移动到媒体库目标目录，并更新 works.folder，返回最终目录路径。
    未设置目标、目标即缓存、或移动失败时，保持在缓存目录。
    移动期间把进度写入 UNZIP_PROGRESS（state='moving'）供下载页显示。"""
    from src.module.datebase_execution import SQLiteDB
    target_root = _read_work_target(work_id)
    if not target_root:
        # 入队时未选择媒体库目标（如当时无媒体库配置）：明确记录而不是静默跳过
        logger.write_log(f'{work_id} 未设置媒体库目标目录，保留在缓存目录: {cache_folder}', 'warning')
        return cache_folder
    leaf = os.path.basename(os.path.normpath(cache_folder))
    dest = os.path.join(target_root, leaf)
    if os.path.abspath(dest) == os.path.abspath(cache_folder):
        return cache_folder  # 缓存路径就是媒体库目录，无需移动

    # 移动进度：跨盘移动是复制+删除，用目标目录已写入字节数 / 源目录总字节数估算；
    # 同盘移动是瞬时改名，监控线程来不及跑也无妨
    total = _folder_size(cache_folder) or 1
    UNZIP_PROGRESS[work_id] = {'state': 'moving', 'pct': 0}
    stop = threading.Event()

    def _monitor():
        while not stop.wait(1):
            try:
                pct = min(99, int(_folder_size(dest) * 100 / total))
            except OSError:
                continue
            # 大目录遍历可能耗时数秒：移动若已结束，绝不能再写回进度，
            # 否则会把已被弹出的 UNZIP_PROGRESS 条目"复活"，状态永远卡在移动中 99%
            if stop.is_set():
                break
            UNZIP_PROGRESS[work_id] = {'state': 'moving', 'pct': pct}

    monitor = threading.Thread(target=_monitor, daemon=True, name=f'move-mon-{work_id}')
    monitor.start()
    try:
        os.makedirs(target_root, exist_ok=True)
        if os.path.exists(dest):
            logger.write_log(f'{work_id} 媒体库已存在同名目录，先删除再移动: {dest}', 'warning')
            shutil.rmtree(dest)
        logger.write_log(f'{work_id} 开始移动到媒体库: {dest}', 'info')
        shutil.move(cache_folder, dest)
    except Exception as e:
        err1(e)
        logger.write_log(f'{work_id} 移动到媒体库失败，保留在缓存目录: {cache_folder}', 'error')
        return cache_folder
    finally:
        stop.set()
        monitor.join()  # 等监控线程退出，确保返回后不会再写 UNZIP_PROGRESS
    esc = str(dest).replace("'", "''")
    SQLiteDB().update(
        f'''UPDATE "main"."works" SET "folder" = '{esc}' WHERE "work_id" = '{work_id}' ''')
    logger.write_log(f'{work_id} 解压完成，已移动到媒体库: {dest}', 'info')
    return dest


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

    def download_limits(self):
        """获取下载流量使用情况，返回 {'usagePercent': {'current', 'value'},
        'nextResetSeconds': {'current', 'value'}, 'hosters': [...]}"""
        return self._request('GET', 'downloader/limits')

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


def _probe_size(session, url):
    """探测文件总大小与是否支持 Range；返回 (total_size, supports_range)"""
    try:
        response = session.get(url, headers={'Range': 'bytes=0-0'}, stream=True, timeout=30)
        try:
            if response.status_code == 206:
                content_range = response.headers.get('Content-Range', '')
                if '/' in content_range:
                    tail = content_range.rsplit('/', 1)[1]
                    if tail.isdigit():
                        return int(tail), True
            if response.status_code == 200:
                length = response.headers.get('Content-Length')
                return (int(length) if length and length.isdigit() else 0), False
        finally:
            response.close()
    except requests.exceptions.RequestException:
        pass
    return 0, False


def _meta_path(file_path):
    return file_path + '.dlmeta'


def _clear_meta(file_path):
    try:
        os.remove(_meta_path(file_path))
    except OSError:
        pass


class _RateLimiter:
    """全局下载限速器（令牌桶）：所有下载线程共享同一总速度上限，0 表示不限速。"""

    def __init__(self):
        self._lock = threading.Lock()
        self._rate = 0          # 字节/秒，0=不限速
        self._allowance = 0.0   # 当前可用令牌（字节）
        self._last = None

    def set_rate(self, bytes_per_sec):
        with self._lock:
            self._rate = max(0, bytes_per_sec)
            if self._rate == 0:
                self._allowance = 0.0
                self._last = None

    def consume(self, nbytes):
        """登记本次已下载 nbytes，返回需要 sleep 的秒数（计算在锁内，睡眠在锁外）"""
        if self._rate <= 0:
            return 0.0
        with self._lock:
            now = time.time()
            if self._last is None:
                self._last = now
            self._allowance += (now - self._last) * self._rate
            self._last = now
            if self._allowance > self._rate:   # 突发上限：最多积累 1 秒额度
                self._allowance = self._rate
            self._allowance -= nbytes
            if self._allowance >= 0:
                return 0.0
            return -self._allowance / self._rate


_rate_limiter = _RateLimiter()


def _download_single(session, url, file_path, filename, key, set_status):
    """单连接下载（断点续传 + 暂停 + 低速重试），返回 done/paused/slow/failed"""
    headers = {}
    downloaded = 0
    if os.path.exists(file_path):
        downloaded = os.path.getsize(file_path)
        headers['Range'] = 'bytes=%d-' % downloaded

    response = session.get(url, headers=headers, stream=True, timeout=60)
    if response.status_code == 416:
        response.close()
        return 'done'  # 文件已完整
    if response.status_code not in (200, 206):
        response.close()
        logger.write_log(f"{filename} 下载失败 HTTP {response.status_code}", 'error')
        set_status(key, '0')
        return 'failed'
    if response.status_code == 200:
        downloaded = 0  # 服务器不支持续传，从头下载

    total_size = downloaded + int(response.headers.get('content-length', 0))
    progress_bar = tqdm(total=total_size, initial=downloaded, unit='B', unit_scale=True, desc=filename)
    mode = 'ab' if response.status_code == 206 else 'wb'
    last_db_write = 0.0
    speed = 0.0
    speed_time, speed_bytes = time.time(), downloaded
    low_speed_start = None
    min_speed_bytes = Config().read_min_speed() * 1024
    # 全局限速：所有下载线程共享同一总上限；限速时关闭低速重试，避免被限的速度误判为卡死
    speed_limited = Config().read_speed_limit() > 0
    _rate_limiter.set_rate(Config().read_speed_limit() * 1024)
    result = 'done'
    with open(file_path, mode) as file:
        for chunk in response.iter_content(CHUNK):
            if _stop_event.is_set():
                result = 'paused'
                break
            progress_bar.update(len(chunk))
            file.write(chunk)
            downloaded += len(chunk)
            sleep_for = _rate_limiter.consume(len(chunk))
            if sleep_for > 0:
                time.sleep(sleep_for)
            now = time.time()
            if now - speed_time >= 1:
                speed = (downloaded - speed_bytes) / (now - speed_time)
                speed_time, speed_bytes = now, downloaded
                if min_speed_bytes > 0 and speed > 0 and not speed_limited:
                    if speed < min_speed_bytes:
                        if low_speed_start is None:
                            low_speed_start = now
                        elif now - low_speed_start >= 30:
                            result = 'slow'
                            break
                    else:
                        low_speed_start = None
            DOWNLOAD_PROGRESS[key] = {'downloaded': downloaded, 'total': total_size, 'speed': speed}
            if total_size and now - last_db_write >= 2:
                set_status(key, '3', int(downloaded * 100 / total_size))
                last_db_write = now
    progress_bar.close()
    response.close()
    if result in ('paused', 'slow'):
        pct = int(downloaded * 100 / total_size) if total_size else 0
        set_status(key, '0', pct)
        if result == 'slow':
            logger.write_log(f"{filename} 速度持续低于 {min_speed_bytes // 1024} KB/s，重新排队", 'warning')
    return result


def _download_file(session, direct_url, file_path, filename, key, set_status):
    """下载单个文件：统一单连接下载（断点续传 + 暂停 + 低速重试）。
    返回 done/paused/slow/failed，过程中负责写回数据库进度与状态。"""
    total_size, _ = _probe_size(session, direct_url)

    # 旧版分段下载遗留的元数据：其预分配的整文件内容不可信，连同文件一起清掉后单连接重下
    if os.path.exists(_meta_path(file_path)):
        _clear_meta(file_path)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass

    # 已完整下载
    if (total_size > 0 and os.path.exists(file_path)
            and os.path.getsize(file_path) == total_size):
        return 'done'

    return _download_single(session, direct_url, file_path, filename, key, set_status)


def _set_status(key, status, progress=None):
    from src.module.datebase_execution import SQLiteDB
    sql = f'''UPDATE "main"."download_list" SET "status" = '{status}' '''
    if progress is not None:
        sql += f''', "long" = '{progress}' '''
    sql += f'''WHERE UUID = '{key}' '''
    SQLiteDB().update(sql)


# 领取任务与占位需原子进行，避免多个下载线程领到同一条记录
_claim_lock = threading.Lock()


def _claim_next():
    """从队列原子地领取一条待下载任务并立即标记为下载中，返回该行；无任务时返回 None"""
    from src.module.datebase_execution import SQLiteDB
    with _claim_lock:
        sql = '''SELECT *,rowid "NAVICAT_ROWID" FROM "main"."download_list" WHERE "status" = '0' LIMIT 0, 1'''
        flag, data = SQLiteDB().select(sql)
        if not data:
            return None
        row = data[0]
        _set_status(row[0], '3', 0)  # 立即占位，其它线程不会重复领取
        return row


def _worker_count():
    """并发下载文件数，取自“下载线程数”设置，限制在 1~16"""
    try:
        _, n = Config().read_download_list()
        return max(1, min(16, int(n)))
    except (TypeError, ValueError):
        return 1


def _download_worker_loop(session):
    """单个下载线程：不断领取队列任务，通过 debrid-link 中转下载一个文件（支持断点续传）"""
    while True:
        key = None
        try:
            if _stop_event.is_set():
                return

            row = _claim_next()
            if row is None:
                # 队列空，等待新任务；期间收到暂停信号立即退出
                if _stop_event.wait(10):
                    return
                continue

            key = row[0]
            work_id = row[1]
            url = row[2]
            print(f'通过 debrid-link 解析: {url}')

            value = DebridLink().add_download(url)
            if not value or not value.get('downloadUrl'):
                logger.write_log(f"{work_id} debrid-link 解析失败: {url}", 'error')
                _set_status(key, '2')
                continue

            direct_url = value['downloadUrl']
            filename = value.get('name') or direct_url.rstrip('/').rsplit('/', 1)[-1]
            download_path = work_folder_path(work_id)
            # 首个分卷处理时落库缓存目录，保证后续分卷、以及重启续传后的解压都用同一目录
            # （媒体库目标目录已在入队时由 set_work_target_path 落库）
            persist_work_folder(work_id, download_path)
            os.makedirs(download_path, exist_ok=True)
            file_path = os.path.join(download_path, filename)

            result = _download_file(session, direct_url, file_path, filename, key, _set_status)
            DOWNLOAD_PROGRESS.pop(key, None)
            if result == 'paused':
                # 暂停：部分文件保留在磁盘上，下次从断点续传
                return
            if result in ('slow', 'failed'):
                time.sleep(5)
                continue

            logger.write_log(f"{work_id}已完成下载", 'info')
            _set_status(key, '1', 100)
            _mark_work_downloaded(work_id)
            _auto_unzip_if_done(work_id)

        except requests.exceptions.RequestException as e:
            print(f"网络错误: {e}")
            if key:
                DOWNLOAD_PROGRESS.pop(key, None)
                _set_status(key, '0')  # 重新排队，下次从断点继续
            time.sleep(5)
        except Exception as e:
            err1(e)
            if key:
                DOWNLOAD_PROGRESS.pop(key, None)
                _set_status(key, '0')
            time.sleep(5)


def QTUI_debrid_down():
    """下载调度线程：把上次遗留的“下载中”任务重新排队，再按设置启动 N 个下载线程并发下载多个文件"""
    from src.module.datebase_execution import SQLiteDB

    # 上次运行中断时遗留的"下载中"任务重新排队，靠断点续传从已下载部分继续
    SQLiteDB().update('''UPDATE "main"."download_list" SET "status" = '0' WHERE "status" = '3' ''')

    # 上次解压中途中断（崩溃/异常）的作品：分卷已全部下载完但还未解压入库（状态仍为
    # 下载中/已下载，未到已品悦），重新触发解压 → 移动 → 入库流程
    result = SQLiteDB().select('''
        SELECT w."work_id" FROM "main"."works" w
        WHERE w."state" IN ('下载中', '已下载')
        AND EXISTS (SELECT 1 FROM "main"."download_list" d WHERE d."work_id" = w."work_id")
        AND NOT EXISTS (SELECT 1 FROM "main"."download_list" d
                        WHERE d."work_id" = w."work_id" AND d."status" != '1')''')
    if result is not False:
        for (stuck_id,) in result[1]:
            logger.write_log(f'{stuck_id} 分卷已全部下载但未完成解压入库，重新触发解压', 'info')
            _mark_work_downloaded(stuck_id)
            _auto_unzip_if_done(stuck_id)

    open_proxy, proxies = Config().read_proxy()
    workers = []
    for _ in range(_worker_count()):
        session = requests.Session()  # 每个下载线程独立 session，避免并发请求互相干扰
        if open_proxy is True:
            session.proxies.update(proxies)
        thread = threading.Thread(target=_download_worker_loop, args=(session,), daemon=True)
        thread.start()
        workers.append(thread)
    for thread in workers:
        thread.join()


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


# 正在解压的番号，避免并发下载下多个分卷同时完成时对同一目录重复解压
_unzip_lock = threading.Lock()
_unzipping = set()


def _extracted_size(folder):
    """目录下所有非压缩包文件的总字节数，作为解压产出量估算解压进度"""
    total = 0
    for root, _dirs, files in os.walk(folder):
        for name in files:
            if os.path.splitext(name)[1].lower() in ('.zip', '.rar', '.exe'):
                continue
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
    return total


def _auto_unzip_if_done(work_id):
    """开启自动解压时，该番号的所有任务都下载完成后在后台线程解压（每个番号只解压一次）。
    解压期间把进度写入 UNZIP_PROGRESS 供下载页显示：待解压 -> 解压中(X%) -> 解压完成移除。"""
    from src.module.datebase_execution import SQLiteDB

    if not Config().read_auto_unzip():
        return
    sql = f'''SELECT COUNT(*) FROM "main"."download_list"
              WHERE "work_id" = '{work_id}' AND "status" != '1' '''
    result = SQLiteDB().select(sql)
    if result is False or not result[1] or result[1][0][0] != 0:
        return  # 还有未完成的分卷，等全部下载完再解压

    with _unzip_lock:
        if work_id in _unzipping:
            return  # 已有线程在解压该番号（并发完成时去重）
        _unzipping.add(work_id)

    # 立即置为“待解压”，避免下载完成到解压线程启动之间 UI 短暂显示“已完成”
    UNZIP_PROGRESS[work_id] = {'state': 'pending', 'pct': 0}
    logger.write_log(f'{work_id} 下载完成，开始自动解压', 'info')
    threading.Thread(target=_run_unzip, args=(work_id,), daemon=True, name=f'unzip-{work_id}').start()


def _run_unzip(work_id):
    """在后台解压一个作品，并用独立线程按解压产出量估算进度写入 UNZIP_PROGRESS"""
    from src.module.unzip import unzip, get_all_archive_files

    folder = work_folder_path(work_id)
    archives = get_all_archive_files(folder)
    total = sum(os.path.getsize(f) for f in archives if os.path.exists(f)) or 1
    stop = threading.Event()

    def _monitor():
        while not stop.wait(1):
            current = UNZIP_PROGRESS.get(work_id)
            if current and current.get('state') == 'moving':
                continue  # 已进入移动阶段，进度改由移动逻辑维护
            if not os.path.isdir(folder):
                continue  # 解压完成后已移动到媒体库，保持上次进度直到解压线程收尾
            try:
                pct = min(99, int(_extracted_size(folder) * 100 / total))
            except OSError:
                pct = UNZIP_PROGRESS.get(work_id, {}).get('pct', 0)
            # 目录遍历可能耗时较久：解压流程若已收尾，不能把弹出的条目再写回去
            if stop.is_set():
                break
            UNZIP_PROGRESS[work_id] = {'state': 'extracting', 'pct': pct}

    UNZIP_PROGRESS[work_id] = {'state': 'extracting', 'pct': 0}
    monitor = threading.Thread(target=_monitor, daemon=True, name=f'unzip-mon-{work_id}')
    monitor.start()
    try:
        unzip(work_id)
    finally:
        stop.set()
        monitor.join()  # 先等监控线程退出再弹出条目，避免条目被"复活"卡在解压中
        UNZIP_PROGRESS.pop(work_id, None)
        with _unzip_lock:
            _unzipping.discard(work_id)


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
