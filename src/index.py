import time
from src.module.time import Time_a
from src.module.log import Log, err1
from src.module.mulit_processes import Process
from src.module.datebase_execution import MySQLDB, TrimString
from src.module.file_copy import file_copy
from src.module.unzip import unzip
from src.web_drive.katfile_auto_down import QTUI_katfile_down
import threading
from src.module.conf_operate import Config
import sys


class Index:
    def __init__(self):
        self.logger = Log()
        self.process = Process()

    def choose(self):

        if Config().read_start_type():
            thread1 = threading.Thread(target=self.open_GUI)
            thread2 = threading.Thread(target=QTUI_katfile_down)
            thread1.start()
            thread2.start()
        else:
            self.open_CLI()

    @staticmethod
    def open_GUI():
        while True:
            try:
                from PyQt5.QtWidgets import QApplication
                from src.QTui.index_UI import IndexWindow
                import sys
                import asyncio
                from qasync import QEventLoop
                app = QApplication(sys.argv)
                loop = QEventLoop(app)
                asyncio.set_event_loop(loop)

                window = IndexWindow()
                window.show()

                with loop:  # 确保 asyncio 和 Qt 的事件循环兼容
                    loop.run_forever()

                # app = QApplication(sys.argv)
                # window = IndexWindow()
                # window.show()
                # app.exec_()
            except Exception as e:
                print(f"An error occurred: {e}")
            else:
                raise ValueError('未知错误')

    def open_CLI(self):
        while True:
            print("\n")
            print("1:生成RJ数据")
            print("2:调用DL SELECT API更新works")
            print("3:更新information表")
            print("4:获取AS UPGroup")
            print("5:获取AS Down URL")
            print("6:转换Short URL")
            print("7:测试Down URL if Ture")
            print("8:解压文件")

            flag = '2'

            if flag == '1':
                from src.DLsite.RJ_number_generate import rjnumber_generate
                rjnumber_generate()

            elif flag == '2':
                from src.DLsite.craw_dlsite_works_name import craw_dlsite_works
                from src.DLsite.craw_dlsite_infomation import crawl_work_web_information
                sql = (f"SELECT work_id FROM `works` WHERE work_state is NULL or work_state = '1' "
                       f"and update_time < '{Time_a().tow_days_ago()} 00:00:00'")
                Process().multi_process_as_up_group(sql, craw_dlsite_works)
                # elif flag == '3':
                sql = f"SELECT work_id, work_type FROM works WHERE work_state in ('2')"
                Process().multi_process_as_up_group(sql, crawl_work_web_information)

            # elif flag == '4':
            #     from src.Anime_sharing.get_as_work_upgroup_url import get_as_work_upgroup_url
            #     sql = (f"SELECT work_id, work_type FROM works WHERE  work_state in {'7', '14'} "
            #            f"and update_time < '{Time_a().tow_days_ago()} 00:00:00' ")
            #     self.process.multi_process_as_up_group(sql, get_as_work_upgroup_url)
            #
            # elif flag == '5':
            #     from src.Anime_sharing.get_webdrive_url import as_work_down_url
            #     sql = (f"SELECT id, work_id, url FROM AS_work_updata_group WHERE url_state = '0'"
            #            f"and update_time < '{Time_a().tow_days_ago()} 00:00:00' LIMIT 20000")
            #     self.process.multi_process_as_up_group(sql, as_work_down_url)
            #
            # elif flag == '6':
            #     from src.web_drive.re_short_url import re_down_table_short_url
            #     short_name = "('bit')"
            #     sql = f"SELECT id, work_down_url, down_web_name FROM AS_work_down_URL " \
            #           f"WHERE url_state = '0' and down_web_name in {short_name} "
            #     self.process.multi_process_as_up_group(sql, re_down_table_short_url)
            #
            # elif flag == '7':
            #     from src.web_drive.doun_url_test import down_url_test
            #     down_name = "('katfile', 'mexa', 'mx-sh', 'rapidgator', 'rg', 'rosefile', 'ddownload')"
            #     sql = f"SELECT id, work_down_url, down_web_name FROM AS_work_down_URL " \
            #           f"WHERE url_state = '0' and down_web_name IN {down_name}  limit 10000"
            #     self.process.multi_process_as_up_group(sql, down_url_test)

            # elif flag == '8':

                # sql = f"SELECT * FROM `DLsite`.`test_copy1` where `2` is null"
                # flag, data = DateBase().select_all(sql)
                # for i in data:
                # rj = 'RJ01053406'
                # unzip(rj)

            # elif flag == '9':
            #     file_copy()

            days = 10
            pause_duration = 86400 * days
            print(f'暂停{days}天')
            time.sleep(pause_duration)
