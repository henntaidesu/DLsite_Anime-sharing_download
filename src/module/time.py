import time
from datetime import datetime, timedelta


class Time:
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


