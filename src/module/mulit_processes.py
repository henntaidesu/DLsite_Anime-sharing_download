import time
from src.module.datebase_execution import MySQLDB
import multiprocessing
from src.module.conf_operate import Config
from src.module.log import Log
from src.module.log import err1


class Process:
    def __init__(self):
        self.conf = Config()

    @staticmethod
    def split_list(input_list, num_parts):
        avg = len(input_list) // num_parts
        remainder = len(input_list) % num_parts
        chunks = []
        current_idx = 0

        for i in range(num_parts):
            chunk_size = avg + 1 if i < remainder else avg
            chunks.append(input_list[current_idx:current_idx + chunk_size])
            current_idx += chunk_size

        return chunks

    def multi_process_as_up_group(self, sql, func):
        try:
            processes = int(self.conf.read_processes())
            flag, work_list = MySQLDB().select(sql)
            if len(work_list) == 0:
                print("已完成获取AS UPGroup")
                return False
            chunks = self.split_list(work_list, processes)
            # 创建进程池
            pool = multiprocessing.Pool(processes=processes)
            pool.imap_unordered(func, chunks)
            pool.close()
            pool.join()

        except ExceptionGroup as e:
            err1(e)
