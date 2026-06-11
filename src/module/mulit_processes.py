import time
import multiprocessing
from src.module.conf_operate import Config
from src.module.log import Log
from src.module.log import err1
import requests


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

    def multi_process_as_up_group(self, work_list, func):
        try:
            processes = int(self.conf.read_processes())
            chunks = self.split_list(work_list, processes)
            # 创建进程池
            pool = multiprocessing.Pool(processes=processes)
            pool.imap_unordered(func, chunks)
            pool.close()
            pool.join()

        except ExceptionGroup as e:
            err1(e)
