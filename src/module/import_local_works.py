import os
import re
import shutil
import time
from src.module.datebase_execution import SQLiteDB
from src.module.time import Time_a
from src.module.log import Log, err2

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
    """只读取目录下的全部一级文件夹，返回 {RJ号: 文件夹绝对路径}"""
    rj_map = {}
    try:
        for name in os.listdir(root):
            path = os.path.join(root, name)
            if not os.path.isdir(path):
                continue
            match = RJ_PATTERN.search(name)
            if match:
                rj_map[match.group(0).upper()] = os.path.abspath(path)
    except OSError as e:
        logger.write_log(f'媒体库目录读取失败 {root}: {e}', 'error')
    return rj_map


def _import_rj_list(rj_list, state, library=None, folders=None):
    """把 RJ 号列表写入 works 表并标记状态（可附带所属媒体库名与
    folders 提供的 {RJ号: 作品文件夹路径}），返回新增数"""
    db = SQLiteDB()
    result = db.select('SELECT "work_id" FROM "main"."works"')
    existing = {row[0] for row in result[1]} if result is not False else set()
    now = Time_a().now_time()
    folders = folders or {}
    set_lib = ''
    lib_value = 'NULL'
    if library is not None:
        lib_value = "'" + str(library).replace("'", "''") + "'"
        set_lib = f', "library" = {lib_value}'
    added = 0
    for rj in rj_list:
        folder_value = 'NULL'
        set_folder = ''
        if folders.get(rj):
            folder_value = "'" + folders[rj].replace("'", "''") + "'"
            set_folder = f', "folder" = {folder_value}'
        if rj in existing:
            db.update(f'''UPDATE "main"."works" SET "state" = '{state}'{set_lib}{set_folder}
                          WHERE "work_id" = '{rj}' ''')
        else:
            db.insert(f'''INSERT INTO "main"."works" ("work_id", "state", "library", "folder", "down_time")
                          VALUES ('{rj}', '{state}', {lib_value}, {folder_value}, '{now}')''')
            added += 1
    return added


def move_work_to_library(work_id, target_lib, target_folder):
    """把作品文件夹移动到目标媒体库文件夹，并把 works 表的 library/folder 改为新库，
    旧库因 library 列被改写而自动不再包含该作品。移动成功后补全(同步)该作品元数据。
    返回 (是否成功, 新路径 或 失败原因)。"""
    db = SQLiteDB()
    result = db.select(f'''SELECT "folder" FROM "main"."works" WHERE "work_id" = '{work_id}' ''')
    if result is False or not result[1] or not result[1][0][0]:
        return False, '作品当前文件夹未知，无法移动'
    src = result[1][0][0]
    if not os.path.isdir(src):
        return False, f'作品文件夹不存在: {src}'
    leaf = os.path.basename(os.path.normpath(src))
    dest = os.path.join(target_folder, leaf)
    if os.path.abspath(dest) == os.path.abspath(src):
        return False, '目标位置与当前位置相同'
    if os.path.exists(dest):
        return False, f'目标媒体库已存在同名文件夹: {dest}'
    try:
        os.makedirs(target_folder, exist_ok=True)
        shutil.move(src, dest)
    except Exception as e:
        err2(e)
        return False, str(e)

    lib_esc = str(target_lib).replace("'", "''")
    dest_esc = dest.replace("'", "''")
    db.update(f'''UPDATE "main"."works" SET "library" = '{lib_esc}', "folder" = '{dest_esc}'
                  WHERE "work_id" = '{work_id}' ''')
    logger.write_log(f'{work_id} 已移动到媒体库 {target_lib}: {dest}', 'info')

    # 新媒体库自动同步元数据：缺失时补全(图片已随文件夹一并移动)
    try:
        backfill_works_from_api(delay=0.0, work_ids=[work_id])
        backfill_work_pages(delay=0.0, work_ids=[work_id])
    except Exception as e:
        err2(e)
    return True, dest


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
    rj_map = scan_top_rj_folders(root)
    rj_list = sorted(rj_map)
    added = _import_rj_list(rj_list, '已品悦', lib_name, rj_map)
    logger.write_log(f'媒体库导入完成 {root}: 扫描到 {len(rj_list)} 个，新增 {added} 个', 'info')
    return added, len(rj_list)


def _work_ids_cond(work_ids):
    """把限定的 work_id 列表转成 SQL 条件；传入空列表时返回永假条件"""
    if work_ids is None:
        return ''
    ids = ','.join("'" + str(w).replace("'", "''") + "'" for w in work_ids)
    return f''' AND "work_id" IN ({ids})''' if ids else ' AND 1=0'


def backfill_works_from_api(delay=0.5, progress=None, library=None, force=False, work_ids=None):
    """对 works 表中缺少作品名的记录逐个调用 DL API 补全字段，
    返回 (补全数, 未获取到数, 总数)。delay 为每次调用间隔秒数（限速）。
    library 限定只处理该媒体库的作品；work_ids 限定只处理这些作品；
    force 为 True 时无视已有数据强制重新获取。"""
    from src.DLsite.DLapi_call import get_work_data

    db = SQLiteDB()
    lib_cond = ''
    if library is not None:
        lib_cond = f''' AND "library" = '{str(library).replace("'", "''")}' '''
    id_cond = _work_ids_cond(work_ids)
    if force:
        sql = f'''SELECT "work_id" FROM "main"."works" WHERE "state" = '已品悦'{lib_cond}{id_cond}'''
    else:
        # 已扫描过元数据（meta_scanned = '1'）的作品不再重新获取
        sql = f'''SELECT "work_id" FROM "main"."works"
                  WHERE ("work_name" IS NULL OR "work_name" = '')
                  AND COALESCE("meta_scanned", '') != '1'{lib_cond}{id_cond}'''
    result = db.select(sql)
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


# 作品页抓取可补全的 works 表列
PAGE_COLUMNS = ('work_name', 'maker_name', 'sell_date', 'series', 'scenario', 'illust',
                'voice_actor', 'age_category', 'work_type', 'genre', 'file_size')


def backfill_work_pages(delay=1.0, progress=None, library=None, force=False, work_ids=None):
    """对未标记 meta_scanned 的已品悦作品逐个抓取 DLsite 作品页，
    补全字段、保存正文与标签，并下载全部图片到作品文件夹的数据源目录。
    抓取成功的作品标记 meta_scanned = '1'，下次扫描不再重新获取。
    返回 (补全数, 失败数, 总数)。delay 为每次抓取间隔秒数（限速）。
    library 限定只处理该媒体库的作品；work_ids 限定只处理这些作品；
    force 为 True 时无视标记选取全部作品：
    作品页仍可访问的删除旧数据源后全量重新下载，获取不到的保留原有元数据。"""
    from src.DLsite.DLsite_page import (get_work_page, download_work_images,
                                        save_work_description, remove_work_data_source)

    db = SQLiteDB()
    lib_cond = ''
    if library is not None:
        lib_cond = f''' AND "library" = '{str(library).replace("'", "''")}' '''
    id_cond = _work_ids_cond(work_ids)
    if force:
        sql = f'''SELECT "work_id", "folder" FROM "main"."works" WHERE "state" = '已品悦'{lib_cond}{id_cond}'''
    else:
        # meta_scanned 是"已完整扫描"（字段+图片+正文+标签）的唯一标记：
        # 旧版扫描过、字段已齐但缺正文/标签的作品也会被选中补全
        sql = f'''SELECT "work_id", "folder" FROM "main"."works" WHERE "state" = '已品悦'
                  AND COALESCE("meta_scanned", '') != '1'{lib_cond}{id_cond}'''
    result = db.select(sql)
    if result is False:
        return 0, 0, 0
    rj_list = result[1]

    def esc(value):
        return str(value if value is not None else '').replace("'", "''")

    filled = missed = 0
    for i, (rj, work_folder) in enumerate(rj_list, 1):
        data, image_urls, body_text = get_work_page(rj)
        if data:
            if force:
                # 作品页仍可访问：删除旧数据源后全量重新下载；
                # 获取不到的作品走 else 分支，原有元数据保持不动
                remove_work_data_source(rj, work_folder)
            cover = download_work_images(rj, image_urls, work_folder)
            save_work_description(rj, body_text, work_folder)
            genres = data.pop('genres', [])
            if genres:
                db.delete(f'''DELETE FROM "main"."work_genres" WHERE "work_id" = '{rj}' ''')
                for genre in genres:
                    db.insert(f'''INSERT OR IGNORE INTO "main"."work_genres" ("work_id", "genre")
                                  VALUES ('{rj}', '{esc(genre)}')''')
            sets = [f'''"{col}" = '{esc(data[col])}' ''' for col in PAGE_COLUMNS if data.get(col)]
            if cover:
                sets.append(f'''"cover" = '{esc(cover)}' ''')
            sets.append('''"meta_scanned" = '1' ''')
            db.update(f'''UPDATE "main"."works" SET {', '.join(sets)} WHERE "work_id" = '{rj}' ''')
            filled += 1
        else:
            missed += 1
        if progress:
            progress(i, len(rj_list), rj, bool(data))
        if i % 50 == 0:
            logger.write_log(f'作品页元数据补全进度: {i}/{len(rj_list)}（成功 {filled}）', 'info')
        time.sleep(delay)

    logger.write_log(
        f'作品页元数据补全完成: 补全 {filled} 个，失败 {missed} 个，共 {len(rj_list)} 个', 'info')
    return filled, missed, len(rj_list)
