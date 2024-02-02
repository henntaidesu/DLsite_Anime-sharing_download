import time
from src.module.time import Time
from src.module.log import Log, err1
from src.module.mulit_processes import Process
from src.DLsite.RJ_number_generate import rjnumber_generate
from src.DLsite.craw_dlsite_works_name import craw_dlsite_works
from src.DLsite.craw_dlsite_infomation import crawl_work_web_information
from src.Anime_sharing.get_as_work_upgroup_url import get_as_work_upgroup_url
from src.Anime_sharing.get_webdrive_url import as_work_down_url
from src.web_drive.doun_url_test import down_url_test
from src.web_drive.re_short_url import re_down_table_short_url
from src.module.datebase_execution import DateBase, TrimString
from src.module.file_copy import file_copy
from src.module.unzip import unzip


class Index:
    def __init__(self):
        self.logger = Log()
        self.process = Process()

    def index(self):
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

            flag = '9'

            if flag == '1':
                rjnumber_generate()

            elif flag == '2':
                sql = (f"SELECT work_id FROM `works` WHERE work_state is NULL or work_state = '1' "
                       f"and update_time < '{Time().tow_days_ago()} 00:00:00'")
                self.process.multi_process_as_up_group(sql, craw_dlsite_works)

            elif flag == '3':
                sql = f"SELECT work_id, work_type FROM works WHERE work_state = '2'"
                self.process.multi_process_as_up_group(sql, crawl_work_web_information)

            elif flag == '4':
                sql = (f"SELECT work_id, work_type FROM works WHERE  work_state in {'7', '14'} "
                       f"and update_time < '{Time().tow_days_ago()} 00:00:00' LIMIT 5000")
                self.process.multi_process_as_up_group(sql, get_as_work_upgroup_url)

            elif flag == '5':
                sql = (f"SELECT id, work_id, url FROM AS_work_updata_group WHERE url_state = '0'"
                       f"and update_time < '{Time().tow_days_ago()} 00:00:00' LIMIT 20000")
                self.process.multi_process_as_up_group(sql, as_work_down_url)

            elif flag == '6':
                short_name = "('bit')"
                sql = f"SELECT id, work_down_url, down_web_name FROM AS_work_down_URL " \
                      f"WHERE url_state = '0' and down_web_name in {short_name} "
                self.process.multi_process_as_up_group(sql, re_down_table_short_url)

            elif flag == '7':
                down_name = "('katfile', 'mexa', 'mx-sh', 'rapidgator', 'rg', 'rosefile', 'ddownload')"
                sql = f"SELECT id, work_down_url, down_web_name FROM AS_work_down_URL " \
                      f"WHERE url_state = '0' and down_web_name IN {down_name}  limit 10000"
                self.process.multi_process_as_up_group(sql, down_url_test)

            elif flag == '8':

                # sql = f"SELECT * FROM `DLsite`.`test_copy1` where `2` is null"
                # flag, data = DateBase().select_all(sql)
                # for i in data:
                # rj = 'RJ01053406'
                # unzip(rj)
                pass

            elif flag == '9':
                file_copy()

            pause_duration = 86400 * 3
            print('休眠3天')
            time.sleep(pause_duration)
