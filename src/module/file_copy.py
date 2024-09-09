import sys

from src.module.time import Time_a
from src.module.datebase_execution import DateBase
from src.module.log import Log,err2
from src.module.create_folder import create_folder
import shutil


def file_copy():
    sql = f"SELECT * FROM `test_copy1` where `2` is null "
    flag, data = DateBase().select_all(sql)
    for i in data:
        rj = i[0]
        print(rj)
        try:
            print(f'正在复制{rj}')
            source_folder = f'Y:\\Works\\{rj}'
            destination_folder = f'D:\\耳かき\\{rj}'
            # 使用 shutil.copytree() 进行文件夹复制
            shutil.copytree(source_folder, destination_folder)
            Log().write_log(f"文件夹 '{source_folder}' 已成功复制到 '{destination_folder}'。", 'info')
            sql1 = f"UPDATE `DLsite`.`test_copy1` SET `2` = '1' WHERE `1` = '{rj}';"
            DateBase().update_all(sql1)
        except Exception as e:
            err2(e)
            Log().write_log(f"复制文件夹失败: {rj}", 'error')