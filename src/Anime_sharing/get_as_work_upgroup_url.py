import requests
from lxml import html
import urllib.parse
from src.module.log import Log, err1, err2
from src.module.time import Time_a
from src.module.conf_operate import Config

logger = Log()


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
        return as_work_url(rj_number)

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

        url = f"https://www.anime-sharing.com/search/52383544/?q={Work_id}&o=relevance"
        response = session.get(url)

        html_content = response.text
        tree = html.fromstring(html_content)
        result_items = tree.cssselect('.block-body .block-row')
        results = []
        # 逐条解析搜索结果列表
        for item in result_items:
            title_a = item.cssselect('.contentRow-title a')
            if not title_a:
                continue
            title_a = title_a[0]
            href = title_a.get('href')
            if not href or '/threads/' not in href:
                continue
            title = ' '.join(title_a.text_content().split())

            # 去掉 ?q= 查询串和 #post 锚点，保留 threads/xxx 相对路径
            href = urllib.parse.unquote(href)
            href = href.split('?')[0].split('#')[0].strip('/')

            # 作者 · 日期 · 回复数 · 版块
            minor_items = [li.text_content().strip()
                           for li in item.cssselect('.contentRow-minor li')]
            minor = ' · '.join(' '.join(x.split()) for x in minor_items if x)

            # 帖子摘要（Title / Brand / Size / Release Date 等详情）
            snippet_el = item.cssselect('.contentRow-snippet')
            snippet = snippet_el[0].text_content().strip() if snippet_el else ''

            # 作品缩略图
            thumb_el = item.cssselect('.structItem-iconContainer img.thread-thumbnail')
            thumb = thumb_el[0].get('src') if thumb_el else ''

            results.append({
                'title': title,
                'url': href,
                'minor': minor,
                'snippet': snippet,
                'thumb': thumb,
            })
        return results

    except Exception as e:
        err1(e)
        return []
