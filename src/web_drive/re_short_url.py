from src.module.time import Time
from src.module.datebase_execution import DateBase
from src.module.log import Log
import requests

logger = Log()


def TrimString(Str):
    if "'" in Str:
        Str = Str.replace("'", "\\'")
    if '"' in Str:
        Str = Str.replace('"', '\\"')
    return Str


def re_down_table_short_url(work_list, i=0):
    try:
        while True:
            if i >= len(work_list):
                return
            Id = work_list[i][0]
            ShortURL = work_list[i][1]

            i += 1

            time = Time().now_time()
            LongURL = resolve_short_url(ShortURL)
            if 'https' in LongURL[:8]:
                LongURL = LongURL[8:]
            else:
                LongURL = LongURL[7:]
            Name = LongURL.split('.')[0]
            LongURL = TrimString(LongURL)
            Name = TrimString(Name)
            if len(Name) > 12:
                Name = Name[:12]

            sql = f"UPDATE `DLsite`.`AS_work_down_URL` " \
                  f"SET `work_down_url` = '{LongURL}', `url_state` = '0', `down_web_name` = '{Name}', " \
                  f"`update_time` = '{time}' WHERE `id` = {Id};"

            Flag = DateBase().update_all(sql)

            if Flag is True:
                logger.write_log(f"Update Short ID:{Id} New DownName:{Name}", 'info')
            if Flag is False:
                logger.write_log(f"Update Short ID:{Id}", 'error')
    except Exception as e:
        if type(e).__name__ == 'SSLError' or type(e).__name__ == 'NameError' or type(e).__name__ == 'TypeError':
            re_down_table_short_url(work_list, i)


def resolve_short_url(short_url):
    short_url = str(short_url)
    url = "https://" + short_url
    # print(url)
    with requests.head(url, allow_redirects=True) as response:
        final_url = response.url

    return final_url
