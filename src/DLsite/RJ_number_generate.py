import sys

from src.module.datebase_execution import MySQLDB
from src.module.time import Time_a
from src.module.conf_operate import Config


def RJ():
    sql = f"SELECT work_id FROM works ORDER BY insert_time desc LIMIT 1;"
    flag, WorkList = MySQLDB().select(sql)
    rj_number = int(str(WorkList[0][0])[2:]) + 1
    max_RJ = Config().read_max_RJ()

    flag = 0
    while True:
        rj_number += 1

        if rj_number > max_RJ:
            break
        Num = rj_number
        new_Num = f"RJ{rj_number:08d}"
        flag += 1
        if flag > 100000:
            break
        print(f"{new_Num} Now: {flag}")
        sql = (f"INSERT INTO `DLsite`.`works`(`work_id`, `insert_time`, `query_count`, `id_type`) "
               f"VALUES ('{new_Num}','{Time_a().now_time3()}', 0, 2);")
        MySQLDB().insert(sql)

    sys.exit()


def RjIdGenerateOLD():
    RJ = "RJ"
    Num = "899550"

    for i in range(1, 1000000):
        num_value = int(Num)
        num_value += 1
        Num = num_value
        new_Num = f"{num_value:06d}"
        if Num > 1000000:
            break
        rj_number = RJ + new_Num
        print(f"{rj_number}")
        sql = f"INSERT INTO `DLsite`.`works`(`work_id`, `insert_time`) VALUES ('{rj_number}','{Time_a().now_time3()}');"
        MySQLDB().insert(sql)


def VJ():
    key = "VJ"
    Num = "000000"
    for i in range(1, 500000):
        num_value = int(Num)
        num_value += 1
        Num = num_value
        new_Num = f"{num_value:06d}"
        rj_number = key + new_Num
        print(f"{rj_number}")
        sql = (f"INSERT INTO `DLsite`.`works`(`work_id`, `insert_time`, `query_count`, `id_type`) "
               f"VALUES ('{rj_number}','{Time_a().now_time3()}', 0, 2);")
        MySQLDB().insert(sql)
