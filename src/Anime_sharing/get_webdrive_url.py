import urllib.parse

import requests
from lxml import html

from src.module.log import Log, err1, err2
from src.web_drive.debrid_link import supported_domains

logger = Log()


def _is_supported(url):
    """链接所属域名是否被 debrid-link 支持"""
    try:
        netloc = urllib.parse.urlparse(url).netloc.lower()
    except Exception:
        return False
    if not netloc:
        return False
    if netloc.startswith('www.'):
        netloc = netloc[4:]
    for domain in supported_domains():
        if netloc == domain or netloc.endswith('.' + domain):
            return True
    return False


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
        href_list = []
        for span_elements in [L1, L2]:
            if not span_elements or None in span_elements:
                continue
            for span in span_elements:
                for a in span.xpath(".//a"):
                    href = a.get("href")
                    if href and _is_supported(href):
                        href_list.append(href)

        # 去重并保持原始顺序
        href_list = list(dict.fromkeys(href_list))

        if not href_list:
            return [], AS_title

        if len(href_list) > 1:
            not_mp3_list = [href for href in href_list if 'mp3' not in href]
            return not_mp3_list or href_list, AS_title
        return href_list, AS_title

    except Exception as e:
        err1(e)
        return [], None
