import gc
from src.module.time import Time_a
from src.module.datebase_execution import MySQLDB
from src.DLsite.DLapi_call import get_dlsite_work_name
from src.module.log import Log, err1

logger = Log()


def craw_dlsite_works(work_list, i=0):
    try:
        while True:
            if i >= len(work_list):
                return
            formatted_date = Time_a().now_time()
            gc.collect()
            rj_number = work_list[i][0]
            query_count = work_list[i][1]
            i += 1
            query_count += 1

            Data = get_dlsite_work_name(rj_number)

            # if len(rj_number) < 9:
            #     LogPrint(rj_number + "旧数据")
            #     sql = f"UPDATE `works` SET  `work_state` = '99', `updata_time` = '{formatted_date}' " \
            #           f" WHERE `work_id` = '{rj_number}'"
            #     InsertALL(sql)
            #     continue
            #
            # if len(rj_number) > 9:
            #     LogPrint(wrj_number + "New")
            #     continue

            if not Data[0] or not Data[1]:
                sql = f"UPDATE `works` SET  `work_state` = '1', `update_time` = '{formatted_date}' , " \
                      f"`query_count` = {query_count} WHERE `work_id` = '{rj_number}'"
                MySQLDB().insert(sql)
                logger.write_log(f"{rj_number} - 接口无返回值", "warning")
                continue
            if Data == "False":
                logger.write_log(f"{rj_number} - 接口存在重复数据", "error")
                sql = f"UPDATE `works` SET  `work_state` = '4', `update_time` = '{formatted_date}' " \
                      f"`query_count` = {query_count}  WHERE `work_id` = '{rj_number}'"
                MySQLDB().insert(sql)
                continue
            else:
                maker_id = Data[0][0]['work_maker_id']
                if "'" in maker_id:
                    maker_id = maker_id.replace("'", "\\'")

                WorkName = Data[0][0]['work_work_name']
                if "'" in WorkName:
                    WorkName = WorkName.replace("'", "\\'")

                try:
                    maker_name_kana = Data[1][0]['maker_maker_name_kana']
                    if "'" in maker_name_kana:
                        maker_name_kana = maker_name_kana.replace("'", "\\'")
                except:
                    maker_name_kana = "NULL"
                intro_s = Data[0][0]['work_intro_s']
                if "'" in intro_s:
                    intro_s = intro_s.replace("'", "\\'")

                work_type = Data[0][0]['work_work_type']
                if "'" in work_type:
                    work_type = work_type.replace("'", "\\'")

                work_workno = Data[0][0]['work_workno']

                if len(WorkName) > 128:
                    WorkName = WorkName[:128]

                sql1 = (f"UPDATE `works` SET "
                        f"`maker_id` = '{maker_id}', "
                        f"`work_name` = '{WorkName}', "
                        f"`age_category` = {Data[0][0]['work_age_category']}, "
                        f"`maker_name_kana` = '{maker_name_kana}', "
                        f"`intro_s` = '{intro_s}', "
                        f"`work_type` = '{work_type}',"
                        f"`update_time` = '{formatted_date}', "
                        f"`work_state` = '2' "
                        f"`query_count` = {query_count}  "
                        f"WHERE `work_id` = '{rj_number}' ;")
                # print(work_workno, "项目作品名称", Data[0][0]['work_work_name'])
                logger.write_log(f"{work_workno} - 项目作品名称 - {Data[0][0]['work_work_name']}", 'info')
                # print(sql1)
                MySQLDB().insert(sql1)
                sql = f"SELECT maker_id FROM `maker` WHERE maker_id = '{Data[0][0]['work_maker_id']}' "
                result = MySQLDB().select(sql)
                if result is True:
                    continue
                else:
                    TempMakerName = Data[0][0]['work_maker_name']
                    if "'" in TempMakerName:
                        TempMakerName = TempMakerName.replace("'", "\\'")
                    sql2 = f"INSERT INTO `maker`" \
                           f"(`maker_id`, `maker_name`, `age_category`, `is_ana`) " \
                           f"VALUES " \
                           f"('{Data[0][0]['work_maker_id']}', " \
                           f"'{TempMakerName}'," \
                           f" '{Data[1][0]['maker_age_category']}', " \
                           f"'{Data[1][0]['maker_is_ana']}');"
                    # print(sql)
                    MySQLDB().insert(sql2)

        # random_float = random.uniform(0, 2)
        # print(random_float)
        # time.sleep(random_float)

    except Exception as e:
        if type(e).__name__ == 'SSLError' or type(e).__name__ == 'NameError':
            craw_dlsite_works(work_list, i)
        else:
            err1(e)


def UI_A_craw_dlsite_works(rj_number):
    try:
        from src.module.time import now_time
        formatted_date = now_time()
        Data = get_dlsite_work_name(rj_number)

        # if len(rj_number) < 9:
        #     LogPrint(rj_number + "旧数据")
        #     sql = f"UPDATE `works` SET  `work_state` = '99', `updata_time` = '{formatted_date}' " \
        #           f" WHERE `work_id` = '{rj_number}'"
        #     InsertALL(sql)
        #     continue
        #
        # if len(rj_number) > 9:
        #     LogPrint(wrj_number + "New")
        #     continue
        if not Data[0] or not Data[1]:
            sql = f"UPDATE `works` SET  `work_state` = '1', `update_time` = '{formatted_date}' " \
                  f" WHERE `work_id` = '{rj_number}'"
            MySQLDB().insert(sql)
            logger.write_log(f"{rj_number} - 接口无返回值", "warning")

        if Data == "False":
            logger.write_log(f"{rj_number} - 接口存在重复数据", "error")
            sql = f"UPDATE `works` SET  `work_state` = '4', `update_time` = '{formatted_date}' " \
                  f" WHERE `work_id` = '{rj_number}'"
            MySQLDB().insert(sql)

        else:
            maker_id = Data[0][0]['work_maker_id']
            if "'" in maker_id:
                maker_id = maker_id.replace("'", "\\'")

            WorkName = Data[0][0]['work_work_name']
            if "'" in WorkName:
                WorkName = WorkName.replace("'", "\\'")

            try:
                maker_name_kana = Data[1][0]['maker_maker_name_kana']
                if "'" in maker_name_kana:
                    maker_name_kana = maker_name_kana.replace("'", "\\'")
            except:
                maker_name_kana = "NULL"
            intro_s = Data[0][0]['work_intro_s']
            if "'" in intro_s:
                intro_s = intro_s.replace("'", "\\'")

            work_type = Data[0][0]['work_work_type']
            if "'" in work_type:
                work_type = work_type.replace("'", "\\'")

            work_workno = Data[0][0]['work_workno']

            if len(WorkName) > 128:
                WorkName = WorkName[:128]

            sql1 = f"UPDATE `works` SET " \
                   f"`maker_id` = '{maker_id}', " \
                   f"`work_name` = '{WorkName}', " \
                   f"`age_category` = {Data[0][0]['work_age_category']}, " \
                   f"`maker_name_kana` = '{maker_name_kana}', " \
                   f"`intro_s` = '{intro_s}', " \
                   f"`work_type` = '{work_type}', `update_time` = '{formatted_date}', `work_state` = '2'  " \
                   f"WHERE `work_id` = '{rj_number}' ;"
            # print(work_workno, "项目作品名称", Data[0][0]['work_work_name'])
            logger.write_log(f"{work_workno} - 项目作品名称 - {Data[0][0]['work_work_name']}", 'info')
            # print(sql1)
            MySQLDB().insert(sql1)
            sql = f"SELECT maker_id FROM `maker` WHERE maker_id = '{Data[0][0]['work_maker_id']}' "
            result = MySQLDB().select(sql)
            if result is True:
                pass
            else:
                TempMakerName = Data[0][0]['work_maker_name']
                if "'" in TempMakerName:
                    TempMakerName = TempMakerName.replace("'", "\\'")
                sql2 = f"INSERT INTO `maker`" \
                       f"(`maker_id`, `maker_name`, `age_category`, `is_ana`) " \
                       f"VALUES " \
                       f"('{Data[0][0]['work_maker_id']}', " \
                       f"'{TempMakerName}'," \
                       f" '{Data[1][0]['maker_age_category']}', " \
                       f"'{Data[1][0]['maker_is_ana']}');"
                # print(sql)
                MySQLDB().insert(sql2)

        # random_float = random.uniform(0, 2)
        # print(random_float)
        # time.sleep(random_float)

    except Exception as e:
        if type(e).__name__ == 'SSLError' or type(e).__name__ == 'NameError':
            UI_A_craw_dlsite_works(rj_number)
        else:
            err1(e)
