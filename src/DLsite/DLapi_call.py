import requests
import time
import json
from src.module.conf_operate import Config
from src.module.log import err1


def get_dlsite_work_name(term):
    try:
        OpenProxy, proxies = Config().read_proxy()
        session = requests.Session()
        if OpenProxy is True:
            session.proxies.update(proxies)  # 将代理配置应用于该Session

        site = "adult-jp"
        touch = 0
        # 生成新的时间戳
        timestamp = int(time.time() * 1000)
        timestamp2 = timestamp + 10
        # 构建请求的 URL，包括新的时间戳
        url = f"https://www.dlsite.com/suggest/?term={term}&site={site}&time={timestamp}&touch={touch}&_={timestamp2}"
        # print(url)
        response = session.get(url)
        data = json.loads(response.text)
        works = data.get('work', [])
        makers = data.get('maker', [])
        work_list = []
        maker_list = []

        for work in works:
            work_data = {
                'work_work_name': work.get('work_name', ''),
                'work_workno': work.get('workno', ''),
                'work_maker_name': work.get('maker_name', ''),
                'work_maker_id': work.get('maker_id', ''),
                'work_work_type': work.get('work_type', ''),
                'work_intro_s': work.get('intro_s', ''),
                'work_age_category': work.get('age_category', ''),
                'work_is_ana': work.get('is_ana', '')
            }
            work_list.append(work_data)

        if len(work_list) > 1:
            return "False"

        for maker in makers:
            maker_data = {
                'maker_maker_name': maker.get('maker_name', ''),
                'maker_workno': maker.get('workno', ''),
                'maker_maker_name_kana': maker.get('maker_name_kana', ''),
                'maker_make_id': maker.get('maker_id', ''),
                'maker_age_category': maker.get('age_category', ''),
                'maker_is_ana': maker.get('is_ana', '')
            }
            maker_list.append(maker_data)
        return [work_list, maker_list]
    except ExceptionGroup as e:
        err1(e)


def get_work_data(work_id):
    """调用 DL suggest API，返回该 RJ 号作品的全部数据（dict），未获取到返回 None"""
    try:
        OpenProxy, proxies = Config().read_proxy()
        session = requests.Session()
        if OpenProxy is True:
            session.proxies.update(proxies)  # 将代理配置应用于该Session

        site = "adult-jp"
        touch = 0
        # 生成新的时间戳
        timestamp = int(time.time() * 1000)
        timestamp2 = timestamp + 10
        # 构建请求的 URL，包括新的时间戳
        url = f"https://www.dlsite.com/suggest/?term={work_id}&site={site}&time={timestamp}&touch={touch}&_={timestamp2}"
        response = session.get(url, timeout=15)
        data = json.loads(response.text)
        works = data.get('work', [])
        # 优先返回 workno 完全匹配的作品
        for work in works:
            if str(work.get('workno', '')).upper() == work_id.upper():
                return work
        return works[0] if works else None
    except Exception as e:
        err1(e)
        return None


def get_work_name(work_id):
    try:
        OpenProxy, proxies = Config().read_proxy()
        session = requests.Session()
        if OpenProxy is True:
            session.proxies.update(proxies)  # 将代理配置应用于该Session

        site = "adult-jp"
        touch = 0
        # 生成新的时间戳
        timestamp = int(time.time() * 1000)
        timestamp2 = timestamp + 10
        # 构建请求的 URL，包括新的时间戳
        url = f"https://www.dlsite.com/suggest/?term={work_id}&site={site}&time={timestamp}&touch={touch}&_={timestamp2}"
        # print(url)
        response = session.get(url)
        data = json.loads(response.text)
        works = data.get('work', [])
        makers = data.get('maker', [])
        work_list = []
        maker_list = []

        for work in works:
            work_name = work.get('work_name', '')
            return work_name
    except ExceptionGroup as e:
        err1(e)
