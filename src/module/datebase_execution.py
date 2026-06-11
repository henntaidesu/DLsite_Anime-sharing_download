import sys
import sqlite3


class SQLiteDB:
    def __init__(self):
        self._print_log = None
        self.db = None
        self.db_path = "DASD.db"
        self.connect_db()
        self.create_tables()

    @property
    def print_log(self):
        # 延迟创建 Log，避免 datebase_execution -> log -> conf_operate -> datebase_execution 循环导入
        if self._print_log is None:
            from src.module.log import Log
            self._print_log = Log()
        return self._print_log

    def connect_db(self):
        """连接SQLite数据库（文件不存在时自动创建）"""
        try:
            self.db = sqlite3.connect(self.db_path)
        except sqlite3.Error as e:
            print(f"数据库连接失败: {str(e)}")
            sys.exit()

    def create_tables(self):
        """创建数据表（不存在时）"""
        try:
            cursor = self.db.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS "conf" (
                "section" TEXT NOT NULL,
                "key" TEXT NOT NULL,
                "value" TEXT,
                PRIMARY KEY ("section", "key")
            )''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS "download_list" (
                "UUID" text,
                "work_id" text,
                "url" TEXT NOT NULL,
                "status" text,
                "long" text,
                "delete" text,
                PRIMARY KEY ("url")
            )''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS "works" (
                "work_id" text,
                "work_name" TEXT,
                "maker_id" text,
                "maker_name" TEXT,
                "work_type" text,
                "intro_s" TEXT,
                "age_category" text,
                "is_ana" text,
                "state" text,
                "down_time" text,
                PRIMARY KEY ("work_id")
            )''')
            # 旧版 works 表没有 state 列时补加
            columns = [row[1] for row in cursor.execute('PRAGMA table_info("works")').fetchall()]
            if 'state' not in columns:
                cursor.execute('ALTER TABLE "works" ADD COLUMN "state" text')
            self.db.commit()
            cursor.close()
        except sqlite3.Error as e:
            # 此处不用 Log（配置加载期间 Log 尚不可用），直接输出
            print(f"数据表创建失败: {str(e)}")

    def execute_query(self, sql, query_type='select'):
        """
        执行SQL查询，根据类型返回不同的结果。
        query_type: select, insert, update, delete
        """
        try:
            cursor = self.db.cursor()
            cursor.execute(sql)

            if query_type == 'select':
                result = cursor.fetchall()
                return True, result
            elif query_type in ['insert', 'update', 'delete']:
                self.db.commit()  # 对于修改操作，提交更改
                return True
        except sqlite3.Error as e:
            self.print_log.write_log(f"数据库操作失败: {str(e)}", 'error')
            self.print_log.write_log(sql, 'error')
            return False
        finally:
            if hasattr(cursor, 'close'):
                cursor.close()

    def insert(self, sql):
        return self.execute_query(sql, 'insert')

    def update(self, sql):
        return self.execute_query(sql, 'update')

    def select(self, sql):
        return self.execute_query(sql, 'select')

    def delete(self, sql):
        return self.execute_query(sql, 'delete')

    def close_connection(self):
        if hasattr(self, 'db') and self.db:
            self.db.close()
