import os
import re
import time
from src.module.datebase_execution import SQLiteDB
from src.module.time import Time_a
from src.module.log import Log

logger = Log()

RJ_PATTERN = re.compile(r'RJ\d{6,}', re.IGNORECASE)


def scan_rj_folders(root):
    """递归扫描目录，返回文件夹名中包含的 RJ 号集合（匹配到的文件夹不再深入）"""
    rj_set = set()
    for dirpath, dirnames, _ in os.walk(root):
        keep = []
        for name in dirnames:
            match = RJ_PATTERN.search(name)
            if match:
                rj_set.add(match.group(0).upper())
            else:
                keep.append(name)
        dirnames[:] = keep
    return rj_set


def scan_top_rj_folders(root):
    """只读取目录下的全部一级文件夹，返回文件夹名中包含的 RJ 号集合"""
    rj_set = set()
    try:
        for name in os.listdir(root):
            if not os.path.isdir(os.path.join(root, name)):
                continue
            match = RJ_PATTERN.search(name)
            if match:
                rj_set.add(match.group(0).upper())
    except OSError as e:
        logger.write_log(f'媒体库目录读取失败 {root}: {e}', 'error')
    return rj_set


def _import_rj_list(rj_list, state, library=None):
    """把 RJ 号列表写入 works 表并标记状态（可附带所属媒体库名），返回新增数"""
    db = SQLiteDB()
    result = db.select('SELECT "work_id" FROM "main"."works"')
    existing = {row[0] for row in result[1]} if result is not False else set()
    now = Time_a().now_time()
    set_lib = ''
    lib_value = 'NULL'
    if library is not None:
        lib_value = "'" + str(library).replace("'", "''") + "'"
        set_lib = f', "library" = {lib_value}'
    added = 0
    for rj in rj_list:
        if rj in existing:
            db.update(f'''UPDATE "main"."works" SET "state" = '{state}'{set_lib} WHERE "work_id" = '{rj}' ''')
        else:
            db.insert(f'''INSERT INTO "main"."works" ("work_id", "state", "library", "down_time")
                          VALUES ('{rj}', '{state}', {lib_value}, '{now}')''')
            added += 1
    return added


def import_local_works(root):
    """递归扫描本地已下载作品目录写入 works 表并标记为已品悦，返回 (新增数, 扫描到的总数)"""
    if not os.path.isdir(root):
        logger.write_log(f'本地作品导入失败，目录不存在: {root}', 'error')
        return 0, 0
    rj_list = sorted(scan_rj_folders(root))
    added = _import_rj_list(rj_list, '已品悦')
    logger.write_log(f'本地作品导入完成: 扫描到 {len(rj_list)} 个，新增 {added} 个', 'info')
    return added, len(rj_list)


def import_media_lib(root, lib_name=None):
    """导入一个媒体库文件夹：读取一级文件夹的 RJ 号写入 works 表并标记为已品悦，
    lib_name 为所属媒体库名称。返回 (新增数, 扫描到的总数)"""
    if not os.path.isdir(root):
        logger.write_log(f'媒体库导入失败，目录不存在: {root}', 'error')
        return 0, 0
    rj_list = sorted(scan_top_rj_folders(root))
    added = _import_rj_list(rj_list, '已品悦', lib_name)
    logger.write_log(f'媒体库导入完成 {root}: 扫描到 {len(rj_list)} 个，新增 {added} 个', 'info')
    return added, len(rj_list)


def backfill_works_from_api(delay=0.5, progress=None):
    """对 works 表中缺少作品名的记录逐个调用 DL API 补全字段，
    返回 (补全数, 未获取到数, 总数)。delay 为每次调用间隔秒数（限速）。"""
    from src.DLsite.DLapi_call import get_work_data

    db = SQLiteDB()
    result = db.select(
        '''SELECT "work_id" FROM "main"."works" WHERE "work_name" IS NULL OR "work_name" = '' ''')
    if result is False:
        return 0, 0, 0
    rj_list = [row[0] for row in result[1]]

    def esc(value):
        return str(value if value is not None else '').replace("'", "''")

    filled = missed = 0
    for i, rj in enumerate(rj_list, 1):
        work = get_work_data(rj)
        if work:
            sql = (f'UPDATE "main"."works" SET '
                   f'''"work_name" = '{esc(work.get("work_name"))}', '''
                   f'''"maker_id" = '{esc(work.get("maker_id"))}', '''
                   f'''"maker_name" = '{esc(work.get("maker_name"))}', '''
                   f'''"work_type" = '{esc(work.get("work_type"))}', '''
                   f'''"intro_s" = '{esc(work.get("intro_s"))}', '''
                   f'''"age_category" = '{esc(work.get("age_category"))}', '''
                   f'''"is_ana" = '{esc(work.get("is_ana"))}' '''
                   f'''WHERE "work_id" = '{rj}' ''')
            db.update(sql)
            filled += 1
        else:
            # DLsite 已下架或检索不到的作品，保持原样
            missed += 1
        if progress:
            progress(i, len(rj_list), rj, bool(work))
        if i % 50 == 0:
            logger.write_log(f'DL API 数据补全进度: {i}/{len(rj_list)}（成功 {filled}）', 'info')
        time.sleep(delay)

    logger.write_log(
        f'DL API 数据补全完成: 补全 {filled} 个，未获取到 {missed} 个，共 {len(rj_list)} 个', 'info')
    return filled, missed, len(rj_list)
