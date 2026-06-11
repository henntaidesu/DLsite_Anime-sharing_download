import time
from src.module.time import Time_a
from src.module.log import Log, err1
from src.module.mulit_processes import Process
from src.module.unzip import unzip
from src.web_drive.katfile_auto_down import QTUI_katfile_down
import threading
from src.module.conf_operate import Config
import sys
import requests


conf = Config()
API_address = conf.read_HOME_API()

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
                from src.QTui.style.theme import apply_dark_theme
                import sys
                import asyncio
                from qasync import QEventLoop
                app = QApplication(sys.argv)
                apply_dark_theme(app)
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
            print("8:解压文件")

            flag = '2'

            if flag == '1':
                from src.DLsite.RJ_number_generate import RJ, API_new_RJ
                RJ()

            elif flag == '2':
                from src.DLsite.craw_dlsite_works_name import craw_dlsite_works
                from src.DLsite.RJ_number_generate import RJ, API_new_RJ
                API_new_RJ()
                URL = f'{API_address}/dlsite/status1'
                print(URL)
                # sql = (f"SELECT work_id , query_count FROM `works` WHERE work_state is NULL or work_state = '1' "
                #        f"and update_time < '{Time_a().tow_days_ago()} 00:00:00' and query_count < 5")'
                while True:
                    work_list = requests.get(URL).json()
                    if work_list:
                        Process().multi_process_as_up_group(work_list, craw_dlsite_works)
                    else:
                        break

            # elif flag == '8':
                # rj = 'RJ01053406'
                # unzip(rj)

            days = 10
            pause_duration = 3600 * 24 * days
            print(f'暂停{days}天')
            time.sleep(pause_duration)
