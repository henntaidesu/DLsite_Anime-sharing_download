import requests
from lxml import html

from src.module.time import Time_a
from src.module.datebase_execution import MySQLDB
from src.module.log import Log

logger = Log()


def down_url_test(WorkList):
    for i in WorkList:
        sql = None
        Flag = None
        Id = i[0]
        URL = i[1]
        DownName = i[2]
        time = Time_a().now_time()

        if DownName == 'katfile':
            Flag = katfile(URL)
            if Flag is False:
                sql = f"UPDATE `AS_work_down_URL` SET  `url_state` = '9', `updata_time` = '{time}' WHERE `id` = {Id};"
            elif Flag is True:
                sql = f"UPDATE `AS_work_down_URL` SET  `url_state` = '1', `updata_time` = '{time}' WHERE `id` = {Id};"

        elif DownName == 'mexa' or DownName == 'mx-sh':
            Flag = mexa(URL)
            if Flag is False:
                sql = f"UPDATE `AS_work_down_URL` SET  `url_state` = '9', `updata_time` = '{time}' WHERE `id` = {Id};"
            elif Flag is True:
                sql = f"UPDATE `AS_work_down_URL` SET  `url_state` = '1', `updata_time` = '{time}' WHERE `id` = {Id};"

        elif DownName == 'rapidgator' or DownName == 'rg':
            Flag = rapidgator(URL)
            if Flag is False:
                sql = f"UPDATE `AS_work_down_URL` SET  `url_state` = '9', `updata_time` = '{time}' WHERE `id` = {Id};"
            elif Flag is True:
                sql = f"UPDATE `AS_work_down_URL` SET  `url_state` = '1', `updata_time` = '{time}' WHERE `id` = {Id};"

        elif DownName == 'rosefile':
            Flag = rosefile(URL)
            if Flag is False:
                sql = f"UPDATE `AS_work_down_URL` SET  `url_state` = '9', `updata_time` = '{time}' WHERE `id` = {Id};"
            elif Flag is True:
                sql = f"UPDATE `AS_work_down_URL` SET  `url_state` = '1', `updata_time` = '{time}' WHERE `id` = {Id};"

        elif DownName == 'ddownload':
            Flag = ddownload(URL)
            if Flag is False:
                sql = f"UPDATE `AS_work_down_URL` SET  `url_state` = '9', `updata_time` = '{time}' WHERE `id` = {Id};"
            elif Flag is True:
                sql = f"UPDATE `AS_work_down_URL` SET  `url_state` = '1', `updata_time` = '{time}' WHERE `id` = {Id};"

        elif DownName == 'fikper':
            Flag = fikper(URL)
            if Flag is False:
                sql = f"UPDATE `AS_work_down_URL` SET  `url_state` = '9', `updata_time` = '{time}' WHERE `id` = {Id};"
            elif Flag is True:
                sql = f"UPDATE `AS_work_down_URL` SET  `url_state` = '1', `updata_time` = '{time}' WHERE `id` = {Id};"
        flag = MySQLDB().update(sql)

        if flag is True:
            logger.write_log(f"UPDATE AS_work_down_URL URLStare:{Flag} ID:{Id} DownName:{DownName}", 'info')
        if flag is False:
            logger.write_log(f"UPDATE AS_work_down_URL URLStare:{Flag} ID:{Id} DownName", 'error')


def resolve_short_url(short_url):
    # 发起GET请求以获取重定向信息
    url = "https://" + short_url
    with requests.head(url, allow_redirects=True) as response:
        # 提取最终的URL
        final_url = response.url

    return final_url


def katfile(url):
    try:
        # url = "https://" + url
        # print(url)
        response = requests.get(url)
        html_data = response.text
        tree = html.fromstring(html_data)

        span_elements = tree.xpath('//*[@id="container"]')
        for span in span_elements:
            # span_text = span.text_content()
            a_elements = span.xpath(".//img")
            href_list = [a.get("src") for a in a_elements]
            href_list = str(href_list)
            # print(type(href_list))
            if "404" in href_list:
                return False
            else:
                return True
    except ExceptionGroup as e:
        print(e)


def mexa(url):
    try:
        text_content = None
        url = "https://" + url
        # print(url)
        response = requests.get(url)
        html_data = response.text
        tree = html.fromstring(html_data)

        span_elements = tree.xpath('//*[@id="page"]/center/div/p[1]/b')

        if span_elements:
            text_content = span_elements[0].text
            text_content = str(text_content)

        if "File Not Found" in text_content:
            return False
    except:
        return True


def rapidgator(url):
    try:
        text_content = None
        url = "https://" + url
        # print(url)
        response = requests.get(url)
        html_data = response.text
        tree = html.fromstring(html_data)

        span_elements = tree.xpath('/html/body/div[1]/div[3]/div/div/center/h3')

        if span_elements:
            text_content = span_elements[0].text
            text_content = str(text_content)

        if "404 File not found" in text_content:
            return False
    except:
        return True


def rosefile(url):
    url = "https://" + url
    # print(url)
    response = requests.get(url)
    html_data = response.text
    if "404 File does not exist" in html_data:
        return False
    else:
        return True


def atfile(url):
    try:
        text_content = None
        url = "http://" + url
        # print(url)
        response = requests.get(url)
        html_data = response.text
        tree = html.fromstring(html_data)

        span_elements = tree.xpath('/html/body/h1')

        if span_elements:
            text_content = span_elements[0].text
            text_content = str(text_content)

        if "Not Found" in text_content:
            print(False)
            return False
    except:
        print(True)
        return True


def fikper(url):
    try:
        text_content = None
        url = "https://" + url
        print(url)
        response = requests.get(url)
        html_data = response.text
        print(html_data)
        tree = html.fromstring(html_data)

        span_elements = tree.xpath('/html/body')

        if span_elements:
            text_content = span_elements[0].text
            text_content = str(text_content)
        print(text_content)
        if "Not Found" in text_content:
            return False
    except:
        return True


def ddownload(url):
    try:
        text_content = None
        url = "https://" + url
        # print(url)
        response = requests.get(url)
        html_data = response.text
        tree = html.fromstring(html_data)

        span_elements = tree.xpath('/html/body/div[1]/div[3]/div/div/center/h3')

        if span_elements:
            text_content = span_elements[0].text
            text_content = str(text_content)

        if "404 File not found" in text_content:
            return False
    except:
        return True
