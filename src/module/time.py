import time
from datetime import datetime, timedelta


class Time_a:
    @staticmethod
    def now_time3():
        now_time = time.time()
        datetime_obj = datetime.fromtimestamp(now_time)
        formatted_date = datetime_obj.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        return formatted_date

    @staticmethod
    def now_time():
        now_time = time.time()
        datetime_obj = datetime.fromtimestamp(now_time)
        formatted_date = datetime_obj.strftime("%Y-%m-%d %H:%M:%S.%f")
        return formatted_date

    @staticmethod
    def tow_days_ago():
        # 获取当前日期和时间
        current_datetime = datetime.now()
        # 计算三天前的日期
        three_days_ago = current_datetime - timedelta(days=2)
        # 格式化日期
        formatted_date = three_days_ago.strftime("%Y-%m-%d")
        return formatted_date

    @staticmethod
    def today():
        now_time = time.time()
        datetime_obj = datetime.fromtimestamp(now_time)
        formatted_date = datetime_obj.strftime("%Y-%m-%d")
        return formatted_date


def TT():
    Time = time.time()
    datetime_obj = datetime.fromtimestamp(Time)
    formatted_date = datetime_obj.strftime("%H:%M:%S")
    return formatted_date

def now_time():
    Time = time.time()
    datetime_obj = datetime.fromtimestamp(Time)
    formatted_date = datetime_obj.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    return formatted_date


def proxy_time():
    current_time = time.time()
    next_minute_time = current_time + 30  # 秒
    datetime_obj = datetime.fromtimestamp(next_minute_time)
    formatted_date = datetime_obj.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    return formatted_date


def today():
    Time = time.time()
    datetime_obj = datetime.fromtimestamp(Time)
    formatted_date = datetime_obj.strftime("%Y-%m-%d")
    return formatted_date


def day():
    Time = time.time()
    datetime_obj = datetime.fromtimestamp(Time)
    formatted_date = datetime_obj.strftime("%d")
    return formatted_date


def year():
    Time = time.time()
    datetime_obj = datetime.fromtimestamp(Time)
    formatted_date = datetime_obj.strftime("%Y")
    return formatted_date


def moon():
    Time = time.time()
    datetime_obj = datetime.fromtimestamp(Time)
    formatted_date = datetime_obj.strftime("%m")
    return formatted_date
