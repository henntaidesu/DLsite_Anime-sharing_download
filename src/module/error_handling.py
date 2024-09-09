from src.module.datebase_execution import DateBase, TrimString


class a:
    @staticmethod
    def aaa():
        sql1 = 'SELECT `1` FROM `DLsite`.`test` where `2` is null'
        flag, data = DateBase().select(sql1)
        for i in data:
            aaa = i[0]
            rj = aaa[29:]
            rj = rj[:10]

            name = aaa[len('2024-02-01 23:21:46 - INFO - RJ01078729 - 项目作品名称 - '):]

            name = TrimString(name)
            aaa = TrimString(aaa)
            sql = (f"UPDATE `DLsite`.`test` set `2` = '{rj}', `3` = '{name}' "
                   f"WHERE `1` = '{aaa}'")

            DateBase().update(sql)

            print(aaa)

    @staticmethod
    def bbb():
        sql = 'SELECT * FROM `DLsite`.`test` where `4` is null'
        flag, data = DateBase().select(sql)

        for i in data:
            rj = i[1]
            title = i[2]
            print(f'{rj}   {title}')

            sql1 = f"DELETE FROM `DLsite`.`works` WHERE `work_id` = '{rj}';"
            DateBase().delete(sql1)

            sql2 = f"SELECT work_id FROM `DLsite`.`works` WHERE `work_name` = '{title}'"
            flag, bbb = DateBase().select(sql2)
            bbb = bbb[0][0]
            print(bbb)

            sql3 = f"UPDATE works set `work_id` = '{rj}' WHERE `work_name` = '{title}'"
            print(sql3)
            DateBase().update(sql3)

            sql4 = f"INSERT INTO `DLsite`.`works`(`work_id`) VALUES ('{bbb}')"
            DateBase().insert(sql4)

            sql5 = f"UPDATE `DLsite`.`test` SET `4` = '1' WHERE  `2` = '{rj}' "
            DateBase().insert(sql5)
