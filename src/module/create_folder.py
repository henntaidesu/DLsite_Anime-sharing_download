import os
from src.module.log import err1, Log
from src.module.conf_operate import Config


def create_log_folder():
    root_directory = os.getcwd()  # 获取当前工作目录，即根目录
    print(root_directory)
    log_folder_path = os.path.join(root_directory, "log")

    if not os.path.exists(log_folder_path):
        try:
            os.makedirs(log_folder_path)
            Log().write_log("创建log文件夹成功", 'info')
            return True
        except OSError as e:
            err1(e)
            return False
    else:
        return True


def create_folder(folder_name):
    folder_path = Config().read_file_down_path()

    folder_path = folder_path + folder_name
    # 使用os.makedirs()创建文件夹，如果文件夹已存在则不会引发错误
    os.makedirs(folder_path, exist_ok=True)
    print(f"Folder created at: {folder_path}")
    return folder_path
