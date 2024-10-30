import sys
from src.module.datebase_execution import MySQLDB
from src.module.time import Time_a
from src.module.conf_operate import Config


def RJ():
    sql = f"SELECT work_id FROM works WHERE id_type = 1 ORDER BY insert_time desc LIMIT 1;"
    flag, WorkList = MySQLDB().select(sql)
    rj_number = int(str(WorkList[0][0])[2:]) + 1
    max_RJ = Config().read_max_RJ()

    count = 0
    while True:
        rj_number += 1

        if rj_number > max_RJ:
            break
        new_Num = f"RJ{rj_number:08d}"
        count += 1
        if count > 100000:
            break
        print(f"{new_Num} Now: {count}")
        sql = (f"INSERT INTO `DLsite`.`works`(`work_id`, `insert_time`, `query_count`, `id_type`) "
               f"VALUES ('{new_Num}','{Time_a().now_time3()}', 0, 1);")
        MySQLDB().insert(sql)

    sys.exit()

def VJ():
    sql = f"SELECT work_id FROM works WHERE id_type = 2 ORDER BY insert_time desc LIMIT 1;"
    flag, WorkList = MySQLDB().select(sql)
    vj_number = int(str(WorkList[0][0])[2:]) + 1

    count = 0
    while True:
        vj_number += 1
        new_Num = f"VJ{vj_number:08d}"
        count += 1
        if count > 1000:
            break
        print(f"{new_Num} Now: {count}")
        sql = (f"INSERT INTO `DLsite`.`works`(`work_id`, `insert_time`, `query_count`, `id_type`) "
               f"VALUES ('{new_Num}','{Time_a().now_time3()}', 0, 1);")
        MySQLDB().insert(sql)


# def RjIdGenerateOLD():
#     RJ = "RJ"
#     Num = "899550"

#     for i in range(1, 1000000):
#         num_value = int(Num)
#         num_value += 1
#         Num = num_value
#         new_Num = f"{num_value:06d}"
#         if Num > 1000000:
#             break
#         rj_number = RJ + new_Num
#         print(f"{rj_number}")
#         sql = f"INSERT INTO `DLsite`.`works`(`work_id`, `insert_time`) VALUES ('{rj_number}','{Time_a().now_time3()}');"
#         MySQLDB().insert(sql)
