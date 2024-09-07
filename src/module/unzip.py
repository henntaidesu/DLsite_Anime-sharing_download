import os
import sys
import time
from tqdm import tqdm
import patoolib
from src.module.time import Time
from src.module.datebase_execution import DateBase
from src.module.conf_operate import Config
from src.module.log import Log, err1, err2

logger = Log()


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


def unzip(work_id):
    try:
        folder_path = f"{Config().read_file_down_path()}\\{work_id}"
        logger.write_log(f'{work_id} 正在解压', 'info')
        while True:
            # print(folder_path)
            file_name_list = get_all_archive_files(folder_path)

            if len(file_name_list) == 0:
                now_time = Time().now_time()
                sql = (f"UPDATE `DLsite`.`works` SET `update_time` = '{now_time}', "
                       f"`work_state` = '-2' WHERE `work_id` = '{work_id}';")
                DateBase().update_all(sql)
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
            # print(file_name)
            flag1 = extract_rar(file_name, folder_path)
            if flag1 is False:
                now_time = Time().now_time()
                sql = (f"UPDATE `DLsite`.`works` SET `update_time` = '{now_time}', "
                       f"`work_state` = '-0' WHERE `work_id` = '{work_id}';")
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
            now_time = Time().now_time()
            sql = f"UPDATE `DLsite`.`works` SET `updata_time` = '{now_time}', `work_state` = '-2' WHERE `work_id` = '{work_id}';"
            DateBase().update_all(sql)
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
