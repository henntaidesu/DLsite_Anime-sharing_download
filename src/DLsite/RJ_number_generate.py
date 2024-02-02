import sys

from src.module.datebase_execution import DateBase
from src.module.time import Time
import time
import re


def rjnumber_generate():
    sql = f"SELECT work_id FROM works ORDER BY insert_time desc LIMIT 1;"
    flag, WorkList = DateBase().select_all(sql)

    rj_number = int(str(WorkList[0][0])[2:]) + 1

    flag = 0
    while True:
        rj_number += 1
        Num = rj_number
        new_Num = f"RJ{rj_number:08d}"
        flag += 1
        if flag > 100000:
            break
        print(f"{new_Num} Now: {flag}")
        sql = f"INSERT INTO `DLsite`.`works`(`work_id`, `insert_time`) VALUES ('{new_Num}','{Time().now_time3()}');"
        DateBase().insert_all(sql)


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
        sql = f"INSERT INTO `DLsite`.`works`(`work_id`, `insert_time`) VALUES ('{rj_number}','{Time().now_time3()}');"
        DateBase().insert_all(sql)
