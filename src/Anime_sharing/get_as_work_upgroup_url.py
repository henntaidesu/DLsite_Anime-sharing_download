import requests
from lxml import html
import urllib.parse
from src.module.log import Log, err1, err2
from src.module.time import Time_a
from src.module.datebase_execution import MySQLDB
from src.module.conf_operate import Config

logger = Log()
db = MySQLDB()


def get_as_work_upgroup_url(rj_number, i=0):
    try:
        # while True:
        #     if i >= len(work_list):
        #         print(111)
        #         return
        #
        #     rj_number = work_list[i][0]
        #
        #     i += 1
        #
        #     if len(rj_number) < 9:
        #         logger.write_log(rj_number, 'info')
        #         now_time = Time().now_time()
        #         sql = f"Update works set work_state = '98', update_time = '{now_time}' WHERE work_id = '{rj_number}' ;"
        #         db.update_all(sql)
        #         continue
        #     else:
        #         print(11111)
        #         continue
        group_list, url_list = as_work_url(rj_number)
        return group_list, url_list

        # print(Data)
        # if Data:
        #     for j in Data:
        #         sql = f"INSERT INTO AS_work_updata_group(`work_id`, `group_name`, `url`, `url_state`) " \
        #               f"VALUES ('{rj_number}', '{j[0]}', '{j[1]}', '0');"
        #         flag = DateBase().insert_all(sql)
        #         if flag is True:
        #             logger.write_log(f"{rj_number} 已获取AS上传组织URL数据", 'info')
        #         else:
        #             logger.write_log(f'{rj_number}error', 'error')
        #
        #     now_time = Time().now_time()
        #     sql = f"Update works set work_state = '15', update_time = '{now_time}' WHERE work_id = '{rj_number}' ;"
        #     flag = DateBase().insert_all(sql)
        #     if flag is True:
        #         logger.write_log(f"{rj_number}已更新works表", 'info')
        #     else:
        #         logger.write_log(f'{rj_number}error', 'error')
        #
        # else:
        #     now_time = Time().now_time()
        #     sql = f"UPDATE `works` SET `work_state` = '14', update_time = '{now_time}' WHERE `work_id` ='{rj_number}';"
        #     DateBase().insert_all(sql)
        #     logger.write_log(f"{rj_number}无法从AS中获取数据", 'error')
    except Exception as e:
        if type(e).__name__ == 'SSLError' or type(e).__name__ == 'NameError' or type(e).__name__ == 'TypeError':
            pass
        err2(e)


def as_work_url(Work_id):
    try:
        # 设置代理
        OpenProxy, proxy_url = Config().read_proxy()

        session = requests.Session()  # 创建一个Session对象
        if OpenProxy is True:
            session.proxies.update(proxy_url)  # 将代理配置应用于该Session

        url = f"https://www.anime-sharing.com/search/7017202/?q={Work_id}&o=relevance"
        response = session.get(url)

        html_content = response.text
        tree = html.fromstring(html_content)
        title_elements = tree.cssselect('.block-body')
        group_list = []
        url_list = []
        # 遍历并处理找到的元素
        for title_element in title_elements:
            li_elements = title_element.findall('.//li')
            for li in li_elements:
                group = li.get('data-author')
                if group is None:
                    continue
                else:
                    a_element = li.find('.//a')
                    if a_element is not None:
                        url = a_element.get('href')
                        url = urllib.parse.unquote(url)

                        group_str = str(group)

                        # print(groupStr)
                        group_str = group_str.lower()
                        group_str_long = len(group_str)
                        if group_str == url[:group_str_long]:
                            continue

                        group_list.append(group)
                        url_list.append(url)
        print(group_list)
        if not group_list:
            group_list = ['NULL']
            url_list = None
        return group_list, url_list



    except ExceptionGroup as e:
        err1(e)
