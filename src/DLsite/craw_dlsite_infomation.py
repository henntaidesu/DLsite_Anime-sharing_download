from src.DLsite.DLapi_call import call_works_web_ui
from src.module.time import Time_a
from src.module.datebase_execution import DateBase
from src.module.log import Log, err1

logger = Log()


def crawl_work_web_information(work_list, i=0):
    len_works_list = len(work_list)
    try:
        while True:
            if i >= len_works_list:
                return

            RJNumber = work_list[i][0]
            WorkType = work_list[i][1]

            i += 1

            IfRelease, sql = call_works_web_ui(RJNumber, WorkType)
            if sql == "ERROR":
                sql = f"UPDATE `DLsite`.`works` SET  `work_state` = '10' , `update_time` = '{Time_a().now_time()}' " \
                      f"WHERE `work_id` = '{RJNumber}';"
                DateBase().update(sql)

                logger.write_log(f"{RJNumber} - この作品は現在販売されていません", 'info')
                continue
            # print(sql)
            if IfRelease is False:
                Flag1 = DateBase().insert(sql)
                if Flag1 is True:
                    sql = f"UPDATE `DLsite`.`works` SET  `work_state` = '7' , `update_time` = '{Time_a().now_time()}' " \
                          f"WHERE `work_id` = '{RJNumber}';"
                    DateBase().update(sql)
                    # print(f"更新表works,information中作品{RJNumber}成功")
                    logger.write_log(f"更新表works,information中作品 - {RJNumber} - 成功", 'info')
                else:
                    sql = f"UPDATE `DLsite`.`works` SET  `work_state` = '8' , `update_time` = '{Time_a().now_time()}' " \
                          f"WHERE `work_id` = '{RJNumber}';"
                    DateBase().update(sql)
                    logger.write_log(f"{RJNumber}:ERROR", 'error')
            if IfRelease is True:
                Flag1 = DateBase().insert(sql)
                if Flag1 is True:
                    sql = f"UPDATE `DLsite`.`works` SET  `work_state` = '9' , `update_time` = '{Time_a().now_time()}' " \
                          f"WHERE `work_id` = '{RJNumber}';"
                    DateBase().update(sql)
                    # print(f"更新表works,information中作品{RJNumber}成功，作品处于待发售状态")
                    logger.write_log(f"更新表works,information中作品 - {RJNumber} - 成功，作品处于待发售状态", 'info')
                else:
                    sql = f"UPDATE `DLsite`.`works` SET  `work_state` = '8' , `update_time` = '{Time_a().now_time()}' " \
                          f"WHERE `work_id` = '{RJNumber}';"
                    DateBase().update(sql)
                    logger.write_log(f"{RJNumber}:更新", 'info')
    except Exception as e:
        if type(e).__name__ == 'SSLError' or type(e).__name__ == 'NameError':
            crawl_work_web_information(work_list, i)
        else:
            err1(e)


def UI_A_crawl_work_web_information(RJNumber, WorkType):
    try:
        IfRelease, sql = call_works_web_ui(RJNumber, WorkType)
        if sql == "ERROR":
            sql = f"UPDATE `DLsite`.`works` SET  `work_state` = '10' , `update_time` = '{Time_a().now_time()}' " \
                  f"WHERE `work_id` = '{RJNumber}';"
            DateBase().update(sql)

            logger.write_log(f"{RJNumber} - この作品は現在販売されていません", 'info')

        # print(sql)
        if IfRelease is False:
            Flag1 = DateBase().insert(sql)
            if Flag1 is True:
                sql = f"UPDATE `DLsite`.`works` SET  `work_state` = '7' , `update_time` = '{Time_a().now_time()}' " \
                      f"WHERE `work_id` = '{RJNumber}';"
                DateBase().update(sql)
                # print(f"更新表works,information中作品{RJNumber}成功")
                logger.write_log(f"更新表works,information中作品 - {RJNumber} - 成功", 'info')
            else:
                sql = f"UPDATE `DLsite`.`works` SET  `work_state` = '8' , `update_time` = '{Time_a().now_time()}' " \
                      f"WHERE `work_id` = '{RJNumber}';"
                DateBase().update(sql)
                logger.write_log(f"{RJNumber}:ERROR", 'error')
        if IfRelease is True:
            Flag1 = DateBase().insert(sql)
            if Flag1 is True:
                sql = f"UPDATE `DLsite`.`works` SET  `work_state` = '9' , `update_time` = '{Time_a().now_time()}' " \
                      f"WHERE `work_id` = '{RJNumber}';"
                DateBase().update(sql)
                # print(f"更新表works,information中作品{RJNumber}成功，作品处于待发售状态")
                logger.write_log(f"更新表works,information中作品 - {RJNumber} - 成功，作品处于待发售状态", 'info')
            else:
                sql = f"UPDATE `DLsite`.`works` SET  `work_state` = '8' , `update_time` = '{Time_a().now_time()}' " \
                      f"WHERE `work_id` = '{RJNumber}';"
                DateBase().update(sql)
                logger.write_log(f"{RJNumber}:更新", 'info')
    except Exception as e:
        if type(e).__name__ == 'SSLError' or type(e).__name__ == 'NameError':
            pass
        else:
            err1(e)

