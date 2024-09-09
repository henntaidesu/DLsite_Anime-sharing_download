import requests
from lxml import html

from src.module.time import Time_a
from src.module.datebase_execution import DateBase, TrimString
from src.module.log import Log, err1, err2

logger = Log()


def as_work_down_url(work_list, i=0):
    try:
        while True:
            if i >= len(work_list):
                return
            down_url_list = []
            Id = work_list[i][0]
            work_id = work_list[i][1]
            group_url = work_list[i][2]
            # Id = '37022'
            # work_id = 'RJ01000686'
            # group_url = '230103-みにょって-【マゾ向け実演】エロ意地悪低音声優に絶頂管理される寸止めドスケベオナニー【バイノーラル】-rj01000686.1264875'

            i += 1

            try:
                flag, down_url_set = get_work_down_url(group_url)
                if down_url_set:
                    for index in down_url_set:
                        if index is None:
                            flag = 4
                            continue
                        url = index[8:]
                        down_url_list.append(url)
                    insert_down_url(down_url_list, Id, work_id, flag)
                else:
                    logger.write_log(f"groupID - {Id} - 作品 - {work_id} - 未获取到下载连接", 'error')
                    sql = (f"UPDATE `AS_work_updata_group` SET  `url_state` = '8', "
                           f"`update_time` = '{Time_a().now_time()}' WHERE `id` = {Id};")
                    DateBase().update_all(sql)
            except Exception as e:
                sql = (f"UPDATE `AS_work_updata_group` SET  `url_state` = '8', `update_time` = '{Time_a().now_time()}'"
                       f" WHERE `id` = {Id};")
                DateBase().update_all(sql)
                logger.write_log(f"groupID - {Id} - 作品 - {work_id} - 源HTML错误", 'error')
                if type(e).__name__ == 'SSLError' or type(e).__name__ == 'NameError' or type(e).__name__ == 'TypeError':
                    as_work_down_url(work_list, i)
    except Exception as e:
        err2(e)
        if type(e).__name__ == 'SSLError' or type(e).__name__ == 'NameError' or type(e).__name__ == 'TypeError':
            as_work_down_url(work_list, i)


def insert_down_url(down_url_set, Id, WorkId, URLState):
    unique_urls = list(set(down_url_set))
    # print(unique_urls)
    for URL in unique_urls:
        time = Time_a().now_time()
        text = URL
        index = text.find(".")
        WebName = text[:index]
        # or WebName == "pixhost"
        if WebName[:3] == "www" or WebName[:2] == "ww" or WebName == "imagetwist":
            continue
        if WebName == "estpublic:guestpublic@bishoujo":
            # estpublic:guestpublic@bishoujo.moe:666
            WebName = "mikoconFTP"
        if "xt=urn" in WebName:
            WebName = "xt=urn"
        if len(WebName) > 12:
            WebName = WebName[:12]

        URL = TrimString(URL)
        WebName = TrimString(WebName)

        sql = f"INSERT INTO `AS_work_down_URL` (`group_table_id`, `work_down_url`, `url_state`,`down_web_name`, " \
              f"`update_time`)VALUES ({Id}, '{URL}', '0', '{WebName}', '{time}');"
        DateBase().insert_all(sql)

    sql = (f"UPDATE `AS_work_updata_group` SET  `url_state` = '{URLState}', `update_time` = '{Time_a().now_time()}"
           f" WHERE `id` = {Id};")
    Flag = DateBase().update_all(sql)
    if Flag is True:
        LenData = len(unique_urls)  # 使用去重后的集合长度
        logger.write_log(f"已查询到groupID - {Id} - 作品 - {WorkId} - 有{LenData}个下载连接，"
                         f"已更新AS_work_updata_group表 HTMLType:{URLState}", 'info')
    if Flag is False:
        logger.write_log(f"{WorkId}", 'error')


def get_work_down_url(URL):
    try:
        url = f"https://www.anime-sharing.com/{URL}/"
        print(url)

        response = requests.get(url)
        html_data = response.text
        tree = html.fromstring(html_data)

        AS_title = tree.xpath('//h1[@class="p-title-value"]')
        AS_title = AS_title[0].text_content().strip()

        if len(AS_title) > 40:
            AS_title = AS_title[:40] + '\n' + AS_title[40:]

        L1 = tree.xpath('//span[contains(@class, "bbcode-box-content")]')
        L2 = tree.xpath('//div[contains(@class, "bbWrapper")]')
        # L3 = tree.xpath('//span[contains(@class, "bbcode-box")]')
        List = [L1, L2]
        Flag = 0
        href_list = []
        for i in List:
            span_elements = i
            Flag += 1
            if None in span_elements:
                continue
            if span_elements:
                for span in span_elements:
                    # 获取span元素的文本内容
                    span_text = span.text_content()
                    # 获取span元素内的所有a标签的href属性
                    a_elements = span.xpath(".//a")
                    for a in a_elements:
                        url = a.get("href")
                        try:
                            if 'katfile' not in url:
                                continue
                            else:
                                href_list.append(url)
                        except TypeError:
                            continue

        print(type(href_list))

        href_list = list(set(href_list))

        if href_list == '':
            return []

        not_mp3_list = []
        if len(href_list) > 1:
            for href in href_list:
                if 'mp3' in href:
                    continue
                else:
                    not_mp3_list.append(href)
            print(href_list)
            return not_mp3_list, AS_title
        else:
            return href_list, AS_title

    except ExceptionGroup as e:
        err1(e)
