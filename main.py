import sys

from src.index import Index
from src.module.create_folder import create_log_folder
import multiprocessing
from PyQt5.QtWidgets import QApplication
from src.QTui.index_UI import IndexWindow


def start_CLI():
    multiprocessing.freeze_support()
    flag = create_log_folder()
    if flag is True:
        while True:
            Index().index()
    else:
        sys.exit()


def start_UI():
    app = QApplication(sys.argv)
    window = IndexWindow()
    window.show()
    app.exec_()


start_UI()

# worksTableuInWork_stateList
# -1：已下载
# -2：已解压
# -3：已归档
# -9：已听过
# 1：未从API中获取到
# 2：已更新works表
# 3：已获取下载URL
# 4：DLWorkAPI存在重复数据
# 5：已经进行爬取 但未获取到
# 6：
# 7：已经更新information表
# 8：更新information表错误
# 9：
# 10：この作品は現在販売されていません、
# 14：未从AS上获取到上传组织URL
# 15：已获取AS上传组织URL


# 20：Tag表存在问题
# 22：AS上所有下载连接已失效
# 23：shine中的ka网盘下载链接失效
# 24
# 30：已下载未归档
# 97：AM&ASMR.ONE中均无法下载
# 98：未从AS上获取到下载URL
# 99：无法获取任何数据
