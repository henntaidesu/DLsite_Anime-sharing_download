import sys
from src.module.log import Log
from src.module.conf_operate import ReadConf
from src.module.log import err1


def TrimString(Str):
    # if '\n' in Str:
    #     Str = Str.replace('\n', ' ')
    # if ' ' in Str:
    #     Str = Str.replace(' ', '')
    # if '/' in Str:
    #     Str = Str.replace('/', ' ')
    if "'" in Str:
        Str = Str.replace("'", "\\'")
    if '"' in Str:
        Str = Str.replace('"', '\\"')
    return Str


class DateBase:
    print_log = Log()

    def __init__(self):
        read_db_conf = ReadConf()
        self.db = read_db_conf.database()

    def insert_all(self, sql):
        try:
            cursor = self.db.cursor()
            cursor.execute(sql)
            self.db.commit()
            self.db.close()
            return True
        except Exception as e:
            if "index.PRIMARY" in str(e):
                self.print_log.write_log(f"重复数据 : {sql} ", "warning")
                return '重复数据'
            elif "timed out" in str(e):
                self.print_log.write_log("连接数据库超时", 'error')
                sys.exit()
            else:
                err1(e)
                self.print_log.write_log(sql, 'error')
                return False

    def update_all(self, sql):
        try:
            cursor = self.db.cursor()
            cursor.execute(sql)
            self.db.commit()
            cursor.close()
            return True
        except Exception as e:
            err1(e)
            if "timed out" in str(e):
                self.print_log.write_log("连接数据库超时", 'error')
            self.print_log.write_log(sql, 'error')
            return False
        finally:
            if hasattr(self, 'db') and self.db:
                self.db.close()

    def select_all(self, sql):
        try:
            cursor = self.db.cursor()
            cursor.execute(sql)
            result = cursor.fetchall()
            cursor.close()
            return True, result
        except Exception as e:
            err1(e)
            if "timed out" in str(e):
                self.print_log.write_log("连接数据库超时", 'error')
            self.print_log.write_log(sql, 'error')
        finally:
            if hasattr(self, 'db') and self.db:
                self.db.close()

    def delete_all(self, sql):
        try:
            cursor = self.db.cursor()
            cursor.execute(sql)
            self.db.commit()  # 提交事务，保存删除操作
            cursor.close()
        except Exception as e:
            err1(e)
            if "timed out" in str(e):
                self.print_log.write_log("连接数据库超时", 'error')
            self.print_log.write_log(sql)
            self.db.rollback()  # 回滚事务，撤销删除操作
        finally:
            if hasattr(self, 'db') and self.db:
                self.db.close()

