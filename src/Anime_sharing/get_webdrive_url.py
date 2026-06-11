import requests
from lxml import html

from src.module.log import Log, err1, err2

logger = Log()


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
