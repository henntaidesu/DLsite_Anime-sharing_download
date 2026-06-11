# 对 works 表中缺少作品名的记录逐个调用 DL API 补全数据。
# 必须在仓库根目录下执行：python backfill_works.py
from src.module.import_local_works import backfill_works_from_api


def progress(i, total, rj, ok):
    if i % 25 == 0 or not ok:
        print(f"{i}/{total} {rj} {'OK' if ok else '未获取到'}", flush=True)


if __name__ == '__main__':
    filled, missed, total = backfill_works_from_api(delay=0.5, progress=progress)
    print(f"完成：补全 {filled} 个，未获取到 {missed} 个，共 {total} 个")
