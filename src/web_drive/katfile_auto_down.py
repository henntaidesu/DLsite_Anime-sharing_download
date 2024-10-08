import sys
from lxml import html
import time
import os
import requests
from tqdm import tqdm
from src.module.log import Log, err1, err2
from src.module.conf_operate import Config, WriteConf
from src.module.datebase_execution import DateBase
from src.module.time import Time_a
from src.module.create_folder import create_folder

logger = Log()


def GETXFSS():
    user, pass_wd, xfss = Config().read_katfile_use()
    url = "https://katfile.com/?op=forgot_pass"

    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-encoding": "gzip, deflate, br, zstd",
         "accept-language": "zh-CN,zh;q=0.9,ja-JP;q=0.8,ja;q=0.7,en;q=0.6,zh-TW;q=0.5",
        "cache-control": "max-age=0",
        # "content-length": "92",
        "content-type": "application/x-www-form-urlencoded",
        "cookie": "lang=taiwan; _ga=GA1.1.756764407.1725778738; login=; ads=-1; msg=; xfss=; _ga_TKFXMGCJEH=GS1.1.1728277646.10.1.1728277675.0.0.0",
        "origin": "https://katfile.com",
        "priority": "u=0, i",
        # "referer": "https://katfile.com/",
        # "sec-ch-ua": '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
        # "sec-ch-ua-mobile": "?0",
        # "sec-ch-ua-platform": "Windows",
        # "sec-fetch-dest": "document",
        # "sec-fetch-mode": "navigate",
        # "sec-fetch-site": "same-origin",
        # "sec-fetch-user": "?1",
        # "upgrade-insecure-requests": "1",
        # "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
    }

    response = requests.post(url, headers=headers)
    try:
        data = response.headers
        print(data)

        cf_headers = {'Date': 'Mon, 07 Oct 2024 05:05:56 GMT', 'Content-Type': 'text/html ; charset=UTF-8', 'Transfer-Encoding': 'chunked', 'Connection': 'keep-alive', 'Expires': 'Sun, 06 Oct 2024 05:05:56 GMT', 'CF-Cache-Status': 'DYNAMIC', 'Report-To': '{"endpoints":[{"url":"https:\\/\\/a.nel.cloudflare.com\\/report\\/v4?s=RDYoYKqLhu00diW3UNCCHMVPLAqMruVFZiwZJVRd0wp6udXQp4NQTIKtGPIItpU9t6ZyScXasbAsLKyff9p3ix%2Byqw%2FS6mI0kqKPlKvMKrMBNhbJWpmW3PFmSbnO"}],"group":"cf-nel","max_age":604800}', 'NEL': '{"success_fraction":0,"report_to":"cf-nel","max_age":604800}', 'Server': 'cloudflare', 'CF-RAY': '8ceb5be4ee3e2623-NRT'}
        login_data = {
            'op': 'login',
            'token': '',
            'rand': '',
            'redirect': '',
            'login': user,
            'password': pass_wd,
            'submit': '',
        }

        response = requests.post(url, headers=cf_headers, data=login_data)
        data = response.headers
        print(data)

        SetCookie = data['Set-Cookie']
        SetCookie = str(SetCookie)
        StartIndex = SetCookie.find('xfss=')
        # 找到下一个分号的位置
        EndIndex = SetCookie.find(';', StartIndex)
        # 提取 'xfss' 的值
        XFSS_code = SetCookie[StartIndex + len('xfss='):EndIndex]
        print("已获取最新Cookie:")
        Config().write_katfile_xfss(XFSS_code)
        return XFSS_code
    except ExceptionGroup as e:
        err1(e)
        logger.write_log("Katfile账号或密码错误,注意密码连续错误三次以上，需要手动获取Cookie", 'error')
        sys.exit()


def auto_katfile():
    Id = None
    WorkId = None
    WorkName = None
    try:
        GN = 'Shine'
        maker_id = "RG49556"
        LimitData = '2022-01-01'
        sql1 = f"SELECT AS_work_updata_group.id ,works_full_information.work_id, works.work_name " \
               f"FROM works_full_information, AS_work_updata_group, works " \
               f"WHERE works_full_information.work_id = AS_work_updata_group.work_id " \
               f"AND works.work_id = works_full_information.work_id " \
               f"AND works_full_information.Release_data > '{LimitData}' " \
               f"AND works_full_information.work_type = 'SOU' " \
               f"AND works_full_information.tag like '%耳かき%' " \
               f"AND AS_work_updata_group.group_name = '{GN}' " \
               f"AND AS_work_updata_group.url_state IN ('1', '2', '3', '4') " \
               f"AND works.work_state = '15'  " \
               f"GROUP BY works.work_name,  works_full_information.work_id, AS_work_updata_group.id " \
               f"Limit 1"
        Work = DateBase().select(sql1)
        Work = Work[0]
        Id = Work[0]
        WorkId = Work[1]
        WorkName = Work[2]
        sql2 = f"SELECT * FROM AS_work_down_URL WHERE group_table_id = {Id} AND dowm_web_name = 'katfile'"
        down_list = DateBase().select(sql2)
        down_url_list = []
        IDList = []
        url_id_list = []
        if len(down_list) < 1:
            ("无数据")
        if len(down_list) == 1:
            DownListTemp = down_list[0]
            UrlId = DownListTemp[0]
            url_id_list.append(UrlId)
            downurl = DownListTemp[2]
            down_url_list.append(downurl)
            state = DownListTemp[3]
            if state == '9':
                now_time = Time_a().now_time()
                sql = f"update works set work_state = '22',`update_time`= '{now_time}' where work_id = '{WorkId}'"
                DateBase().update(sql)
                logger.write_log('AS上有下载连接已失效', 'error')
                return False, downurl, WorkId
            return url_id_list, down_url_list, WorkId

        for i in down_list:
            UrlId = i[0]
            downurl = i[2]
            state = i[3]
            if 'mp3' in downurl:
                continue
            if state == "5":
                continue
            if state == "9":
                now_time = Time_a().now_time()
                sql2 = f"update works set work_state = '23',`updata_time`='{now_time}' where work_id = '{WorkId}'"
                DateBase().update(sql2)
                logger.write_log('Katfile的Shine上有部分下载连接已失效', 'error')
                print(state + '   ' + downurl)
                return False, downurl, WorkId
            down_url_list.append(downurl)
            IDList.append(UrlId)
            print(state + '   ' + downurl)
            if len(down_list) == 0:
                now_time = Time_a().now_time()
                sql = f"UPDATE `works`SET `updata_time` = '{now_time}', `work_state` = '-1' WHERE `work_id` = '{WorkId}';"
                DateBase().update(sql)
                logger.write_log(f"{WorkId}已完成下载", 'info')

                return True, downurl, WorkId
        return IDList, down_url_list, WorkId

    except ExceptionGroup as e:
        logger.write_log(f'{Id}, {WorkId}, {WorkName}', 'error')
        err1(e)


def auto_katfile_down():
    try:
        # 设置代理
        open_proxy, proxy_url = Config().read_proxy()
        Cookie = Config().read_katfile_cookie()
        headers = {
            'Cookie': Cookie,
        }
        url_id_list, downurl_list, WorkId = auto_katfile()
        if url_id_list is False:
            return False
        if url_id_list is True:
            return True
        flag = 0
        flag = int(flag)
        for i in downurl_list:
            time.sleep(3)
            UrlId = url_id_list[flag]
            flag += 1
            OriginalURL = i
            url = 'https://' + OriginalURL
            session = requests.Session()  # 创建一个Session对象
            if open_proxy is True:
                session.proxies.update(proxy_url)  # 将代理配置应用于该Session

            response = session.get(url, headers=headers, allow_redirects=False)  # allow_redirects=False不进行重定向

            print("Redirected Code:", response.status_code)
            if response.status_code == 200:
                WebData = response.text
                if 'Login' in WebData:
                    print("Cookie错误 开始自动获取Cookie")
                    Flag = GETXFSS()
                    if Flag:
                        print("已获取最新Cookie将开始自动下载")
                        auto_katfile_down()

                elif 'reCAPTCHA' in WebData:
                    print("请确保改账户为Premium")
                    print("或者未开启Direct downloads，请前往个人中心开启")
                    print("https://katfile.com/?op=my_account")
                    sys.exit()
            down_path = create_folder(WorkId)
            os.makedirs(down_path, exist_ok=True)  # 确保下载路径存在
            if response.is_redirect:
                # 获取重定向后的 URL
                redirected_url = response.headers.get('location')
                print(f'Redirected URL: {redirected_url}')

                URLstring = str(redirected_url)
                last_slash_index = URLstring.rfind('/')
                filename = URLstring[last_slash_index + 1:]
                print("filename:" + filename)

                # 检查本地文件是否存在
                file_path = os.path.join(down_path, filename)
                if os.path.exists(file_path):
                    # 如果文件已存在，获取已下载的文件大小
                    resume_header = {'Range': 'bytes=%d-' % os.path.getsize(file_path)}
                    response = session.get(redirected_url, headers=resume_header, stream=True)
                else:
                    response = session.get(redirected_url, stream=True)

                download_complete = False
                while not download_complete:

                    try:
                        if response.status_code == 416:
                            print(response.status_code)
                            print("检查代理设置或删除最近一个下载的文件")
                            sys.exit()
                        if response.status_code == 200 or response.status_code == 206:  # 206表示部分内容
                            total_size = int(response.headers.get('content-length', 0))
                            block_size = 1024  # 1 KB
                            progress_bar = tqdm(total=total_size, unit='B', unit_scale=True)

                            with open(file_path, 'ab') as file:  # 使用追加模式打开文件
                                for data in response.iter_content(block_size):
                                    progress_bar.update(len(data))
                                    file.write(data)

                            progress_bar.close()
                            now_time = Time_a().now_time()
                            sql = (f"UPDATE `AS_work_down_URL` SET  `url_state` = '5' ,`updata_time` = '{now_time}' "
                                   f"WHERE `id` = '{UrlId}';")
                            DateBase().update(sql)
                            download_complete = True  # 下载完成

                        else:
                            # 处理非200和206状态码，可以根据需要进行处理
                            print(f"Error: {response.status_code}")
                            time.sleep(3)

                    except requests.exceptions.RequestException as e:
                        print(f"网络错误: {e}")
                        time.sleep(3)
                        auto_katfile_down()
            else:
                # 处理非200状态码，可以根据需要进行处理
                print(f"处理非200状态码，Error: {response.status_code}")

        now_time = Time_a().now_time()
        sql = f"UPDATE `works`SET `updata_time` = '{now_time}', `work_state` = '-1' WHERE `work_id` = '{WorkId}';"
        DateBase().update(sql)
        logger.write_log(f"{WorkId}已完成下载", 'info')

        # AutoDowmToUnzip(WorkId)
        # logger.write_log(f"{WorkId}已完成解压", 'info')

    except ExceptionGroup as e:
        err1(e)


def QTUI_katfile_down(download_url_list, WorkId):
    try:
        # 设置代理
        open_proxy, proxy_url = Config().read_proxy()
        Cookie = Config().read_katfile_cookie()
        headers = {
            'Cookie': Cookie,
        }

        flag = 0
        flag = int(flag)
        for i in download_url_list:
            time.sleep(3)

            flag += 1
            url = i
            session = requests.Session()  # 创建一个Session对象
            if open_proxy is True:
                session.proxies.update(proxy_url)  # 将代理配置应用于该Session

            response = session.get(url, headers=headers, allow_redirects=False)  # allow_redirects=False不进行重定向

            print("Redirected Code:", response.status_code)
            if response.status_code == 200:
                WebData = response.text
                if 'Login' in WebData:
                    print("Cookie错误 开始自动获取Cookie")
                    Flag = GETXFSS()
                    if Flag:
                        print("已获取最新Cookie将开始自动下载")
                        auto_katfile_down()

                elif 'reCAPTCHA' in WebData:
                    print("请确保改账户为Premium")
                    print("或者未开启Direct downloads，请前往个人中心开启")
                    print("https://katfile.com/?op=my_account")
                    sys.exit()
            down_path = create_folder(WorkId)
            os.makedirs(down_path, exist_ok=True)  # 确保下载路径存在
            if response.is_redirect:
                # 获取重定向后的 URL
                redirected_url = response.headers.get('location')
                print(f'Redirected URL: {redirected_url}')

                ur_lstring = str(redirected_url)
                last_slash_index = ur_lstring.rfind('/')
                filename = ur_lstring[last_slash_index + 1:]
                print("filename:" + filename)

                # 检查本地文件是否存在
                file_path = os.path.join(down_path, filename)
                if os.path.exists(file_path):
                    # 如果文件已存在，获取已下载的文件大小
                    resume_header = {'Range': 'bytes=%d-' % os.path.getsize(file_path)}
                    response = session.get(redirected_url, headers=resume_header, stream=True)
                else:
                    response = session.get(redirected_url, stream=True)

                download_complete = False
                while not download_complete:

                    try:
                        if response.status_code == 416:
                            print(response.status_code)
                            print("检查代理设置或删除最近一个下载的文件")
                            sys.exit()
                        if response.status_code == 200 or response.status_code == 206:  # 206表示部分内容
                            total_size = int(response.headers.get('content-length', 0))
                            block_size = 1024  # 1 KB
                            progress_bar = tqdm(total=total_size, unit='B', unit_scale=True)

                            with open(file_path, 'ab') as file:  # 使用追加模式打开文件
                                for data in response.iter_content(block_size):
                                    progress_bar.update(len(data))
                                    file.write(data)

                            progress_bar.close()
                            now_time = Time_a().now_time()
                            download_complete = True  # 下载完成

                        else:
                            # 处理非200和206状态码，可以根据需要进行处理
                            print(f"Error: {response.status_code}")
                            time.sleep(3)

                    except requests.exceptions.RequestException as e:
                        print(f"网络错误: {e}")
                        time.sleep(3)
                        auto_katfile_down()
            else:
                # 处理非200状态码，可以根据需要进行处理
                print(f"处理非200状态码，Error: {response.status_code}")

        logger.write_log(f"{WorkId}已完成下载", 'info')



    except ExceptionGroup as e:
        err1(e)
