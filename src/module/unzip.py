import os
import sys
import time
import shutil
import subprocess
import threading
from tqdm import tqdm
import patoolib
from src.module.conf_operate import Config
from src.module.log import Log, err1, err2

logger = Log()

# Bandizip 命令行工具，用于解压 rar 等格式（patool 不支持 Bandizip）
BANDIZIP_BZ = r"C:\Program Files\Bandizip\bz.exe"


def rename(work_path):  # 输入一个目录，解决该目录下所有文件名的乱码。
    try:
        encode = Config().read_sys_encoding()
        decode = "Shift_JIS"
        CurrentPath = os.getcwd()
        os.chdir(work_path)
        for path in os.listdir():
            if os.path.isdir(path):
                rename(path)
            os.rename(path, path.encode(encode).decode(encoding=decode, errors="ignore"))
        os.chdir(CurrentPath)
        return True
    except Exception as e:
        if type(e).__name__ == 'UnicodeEncodeError':
            return False
        else:
            err2(e)


def extract_rar(file_path, extract_path):
    # if patoolib.test_archive(file_path):
    try:
        if os.path.exists(BANDIZIP_BZ):
            # bz 返回非 0 多为输出文件被杀软/索引器临时占用（0x20 共享冲突），
            # -aoa 会覆盖已解出的部分，因此可安全重试，等占用释放后再来
            last_code = 0
            for attempt in range(1, 4):
                result = subprocess.run([BANDIZIP_BZ, 'x', f'-o:{extract_path}', '-aoa', '-y', file_path])
                if result.returncode == 0:
                    break
                last_code = result.returncode
                if attempt < 3:
                    logger.write_log(
                        f'bz.exe 解压返回码 {last_code}，可能文件被占用，{attempt}/3 次后重试', 'warning')
                    time.sleep(10)
            else:
                raise Exception(f'bz.exe 解压失败，返回码 {last_code}')
        else:
            patoolib.extract_archive(file_path, outdir=extract_path)
    except Exception as e:
        print(e)
        err2(e)
        return False

    # else:
    #     logger.write_log('压缩包不完整', 'error')
    #     return False


def delete_file(file_path):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
        else:
            print(f"The file {file_path} does not exist.")
    except Exception as e:
        err2(e)


def get_file_names(folder_path):
    files = os.listdir(folder_path)
    files = [file for file in files if os.path.isfile(os.path.join(folder_path, file))]
    return files


def get_all_archive_files(folder_path):
    archive_files = []
    # 遍历当前目录下的所有文件和文件夹
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            _, extension = os.path.splitext(file_path)

            # 判断文件是否为压缩文件（你可以根据需要添加其他压缩文件格式）
            if extension.lower() in ['.zip', '.rar', '.exe']:
                archive_files.append(file_path)
    # print(archive_files)
    return archive_files


def move_to_root(work_id, folder_path):
    # 解压后内容常被多包一层或多层目录（如 RJxxx\RJxxx\RJxxx），
    # 沿“只有一个子目录”的链找到最终内容目录，把其内容移到根目录，并删除嵌套路径文件夹
    try:
        final_path = folder_path
        while True:
            dirs = [d for d in os.listdir(final_path) if os.path.isdir(os.path.join(final_path, d))]
            if len(dirs) != 1:
                break
            final_path = os.path.join(final_path, dirs[0])
        if final_path == folder_path:
            return
        top_name = os.path.relpath(final_path, folder_path).split(os.sep)[0]
        top_path = os.path.join(folder_path, top_name)
        pending = []  # 与嵌套路径目录重名的内容先用临时名，删除嵌套目录后再改回
        for name in os.listdir(final_path):
            src = os.path.join(final_path, name)
            dst = os.path.join(folder_path, name)
            if os.path.exists(dst):
                tmp = dst + '_moving_tmp'
                shutil.move(src, tmp)
                pending.append((tmp, dst))
            else:
                shutil.move(src, dst)
        shutil.rmtree(top_path)
        for tmp, dst in pending:
            os.rename(tmp, dst)
        logger.write_log(f'{work_id} 已将最终目录内容移动到根目录', 'info')
    except Exception as e:
        err2(e)


def _post_extract(work_id, folder_path):
    """解压成功后：将作品标记为已品悦，关联所属媒体库和文件夹，然后后台补全详细元数据"""
    from src.module.import_local_works import (_import_rj_list, backfill_works_from_api,
                                               backfill_work_pages)
    # 通过父目录匹配媒体库文件夹
    lib_name = None
    parent = os.path.dirname(os.path.abspath(folder_path))
    for lib in Config().read_media_libs():
        for lib_folder in lib.get('folders', []):
            try:
                if os.path.abspath(lib_folder) == parent:
                    lib_name = lib['name']
                    break
            except OSError:
                pass
        if lib_name:
            break

    _import_rj_list([work_id], '已品悦', lib_name, {work_id: os.path.abspath(folder_path)})
    logger.write_log(f'{work_id} 已标记为已品悦，媒体库: {lib_name or "未关联"}', 'info')

    def _backfill():
        try:
            backfill_works_from_api(delay=0.5)
            backfill_work_pages(delay=1.0)
        except Exception as e:
            err2(e)

    threading.Thread(target=_backfill, daemon=True, name=f'backfill-{work_id}').start()


def unzip(work_id):
    try:
        # 与下载逻辑保持同一文件夹命名方式（RJ号 / 作品名称）
        from src.web_drive.debrid_link import work_folder_path
        folder_path = work_folder_path(work_id)
        logger.write_log(f'{work_id} 正在解压', 'info')
        while True:
            file_name_list = get_all_archive_files(folder_path)

            if len(file_name_list) == 0:
                move_to_root(work_id, folder_path)
                un_flag = rename(folder_path)
                logger.write_log(f'{work_id} 解压成功', 'info')
                if un_flag is True:
                    logger.write_log(f'{work_id} 转码成功', 'info')
                else:
                    logger.write_log(f'{work_id} 无需转码', 'info')
                _post_extract(work_id, folder_path)
                return False
            file_name = file_name_list[0]
            if 'exe' in file_name:
                file_name = file_name_list[1]
            flag1 = extract_rar(file_name, folder_path)
            if flag1 is False:
                return

            time.sleep(3)
            # 删除所有压缩文件
            for archive_file in file_name_list:
                delete_file(archive_file)
    except Exception as e:
        err2(e)


def auto_down_to_unzip(work_id):
    # sql = f"select work_id from works where work_state = '-1' limit 1"
    # flag, work_id = DateBase().select_all(sql)
    # print(work_id)
    # work_id = work_id[0][0]
    # print(work_id)
    while True:
        # WorkId = 'RJ01018336'
        folder_path = f"{Config().read_file_down_path()}\\{work_id}"
        print(folder_path)
        file_name_list = get_all_archive_files(folder_path)

        if len(file_name_list) == 0:
            un_flag = rename(folder_path)
            logger.write_log(f'{work_id} 解压成功', 'info')
            if un_flag is True:
                logger.write_log(f'{work_id} 转码成功', 'info')
            else:
                logger.write_log(f'{work_id} 无需转码', 'info')
            return False
        file_name = file_name_list[0]
        if 'exe' in file_name:
            file_name = file_name_list[1]
        print(file_name)
        extract_rar(file_name, folder_path)

        # 删除所有压缩文件
        for archive_file in file_name_list:
            delete_file(archive_file)
