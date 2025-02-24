import sys
import time

from src.module.datebase_execution import MySQLDB
from src.module.time import Time_a
from src.module.conf_operate import Config
import bs4
import requests
from lxml import etree

conf = Config()
API_address = conf.read_HOME_API()

def API_new_RJ():
    URL = r'''https://www.dlsite.com/maniax/works/type/=/language/jp/sex_category%5B0%5D/male/work_category%5B0%5D/doujin/work_type%5B0%5D/SOU/work_type_name%5B0%5D/%E3%83%9C%E3%82%A4%E3%82%B9%E3%83%BBASMR/options_and_or/and/options%5B0%5D/JPN/options%5B1%5D/NM/options_name%5B0%5D/%E6%97%A5%E6%9C%AC%E8%AA%9E%E4%BD%9C%E5%93%81/options_name%5B1%5D/%E8%A8%80%E8%AA%9E%E4%B8%8D%E5%95%8F%E4%BD%9C%E5%93%81/per_page/100/page/1/show_type/3/lang_options%5B0%5D/%E6%97%A5%E6%9C%AC%E8%AA%9E/lang_options%5B1%5D/%E8%A8%80%E8%AA%9E%E4%B8%8D%E8%A6%81/without_order/1/order/release_d'''
    XPATH = f'//*[@id="search_result_img_box"]/li[1]/dl/dd[2]/div[2]/a/@href'
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(URL, headers=headers)
    html = etree.HTML(response.text)
    href = html.xpath('//*[@id="search_result_img_box"]/li[1]/dl/dd[2]/div[2]/a/@href')
    RJ = int(href[0][href[0].find('RJ') + 2:].replace('.html', '').strip())
    api_url = f'{API_address}/dlsite/index/write_new_RJ/{RJ}'
    state = requests.get(api_url).status_code
    if state != 200:
        print("出现错误")
    Config().write_max_RJ(RJ)
    return True


def RJ():
    # sql = f"SELECT work_id FROM works WHERE id_type = 1 ORDER BY insert_time desc LIMIT 1;"
    # flag, WorkList = MySQLDB().select(sql)
    # rj_number = int(str(WorkList[0][0])[2:]) + 1
    max_RJ = API_new_RJ()
    api_url = f'{API_address}/dlsite/index/max_RJ'
    rj_number = int(requests.get(api_url).text)

    count = 0
    while True:
        rj_number += 1

        if rj_number > max_RJ:
            break
        new_Num = f"RJ{rj_number:08d}"
        count += 1
        if count > 100000:
            break
        print(f"{new_Num} Now: {count}")
        sql = (f"INSERT INTO `DLsite`.`works`(`work_id`, `insert_time`, `query_count`, `id_type`) "
               f"VALUES ('{new_Num}','{Time_a().now_time3()}', 0, 1);")
        MySQLDB().insert(sql)
        api_url = f'{API_address}/dlsite/index/write_new_RJ/{new_Num}'
        state = requests.get(api_url).status_code
        while True:
            if state == 200:
                break
            elif state == 400:
                time.sleep(1)
                continue


    sys.exit()

def VJ():
    sql = f"SELECT work_id FROM works WHERE id_type = 2 ORDER BY insert_time desc LIMIT 1;"
    flag, WorkList = MySQLDB().select(sql)
    vj_number = int(str(WorkList[0][0])[2:]) + 1

    count = 0
    while True:
        vj_number += 1
        new_Num = f"VJ{vj_number:08d}"
        count += 1
        if count > 1000:
            break
        print(f"{new_Num} Now: {count}")
        sql = (f"INSERT INTO `DLsite`.`works`(`work_id`, `insert_time`, `query_count`, `id_type`) "
               f"VALUES ('{new_Num}','{Time_a().now_time3()}', 0, 1);")
        MySQLDB().insert(sql)


# def RjIdGenerateOLD():
#     RJ = "RJ"
#     Num = "899550"

#     for i in range(1, 1000000):
#         num_value = int(Num)
#         num_value += 1
#         Num = num_value
#         new_Num = f"{num_value:06d}"
#         if Num > 1000000:
#             break
#         rj_number = RJ + new_Num
#         print(f"{rj_number}")
#         sql = f"INSERT INTO `DLsite`.`works`(`work_id`, `insert_time`) VALUES ('{rj_number}','{Time_a().now_time3()}');"
#         MySQLDB().insert(sql)
