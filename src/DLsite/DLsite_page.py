import os
import requests
from bs4 import BeautifulSoup
from src.module.conf_operate import Config
from src.module.log import Log

logger = Log()

IMAGES_DIR = 'images'  # 无作品文件夹时的图片回退目录：images/<RJ号>/
DATA_SOURCE_DIR = 'DataSource'  # 作品文件夹内存放 DLsite 图片的子文件夹名
DESCRIPTION_TXT = 'description.txt'  # 数据源文件夹内的作品页正文文本
IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.gif', '.webp')

# 作品页 work_outline 表格字段 -> works 表列名
FIELD_MAP = {
    '販売日': 'sell_date',
    'シリーズ名': 'series',
    'シナリオ': 'scenario',
    'イラスト': 'illust',
    '声優': 'voice_actor',
    '年齢指定': 'age_category',
    '作品形式': 'work_type',
    'ジャンル': 'genre',
    'ファイル容量': 'file_size',
}


def _session():
    OpenProxy, proxies = Config().read_proxy()
    session = requests.Session()
    if OpenProxy is True:
        session.proxies.update(proxies)
    session.headers['User-Agent'] = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                     'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36')
    # R18 作品页需要已通过年龄确认
    session.cookies.set('adultchecked', '1', domain='.dlsite.com')
    return session


def get_work_page(work_id):
    """抓取 DLsite 作品页，返回 (字段 dict, 图片 URL 列表, 正文文本)；
    图片列表为轮播图在前、正文图片在后（封面取第一张轮播图）。
    页面不存在或请求失败返回 (None, [], '')"""
    session = _session()
    resp = None
    for shop in ('home', 'maniax'):
        url = f'https://www.dlsite.com/{shop}/work/=/product_id/{work_id}.html'
        try:
            r = session.get(url, timeout=20)
        except requests.RequestException as e:
            logger.write_log(f'作品页请求失败 {work_id}: {e}', 'error')
            return None, [], ''
        if r.status_code == 200:
            resp = r
            break
    if resp is None:
        logger.write_log(f'作品页不存在 {work_id}', 'info')
        return None, [], ''

    soup = BeautifulSoup(resp.text, 'lxml')
    data = {}
    outline = soup.find(id='work_outline')
    if outline:
        for tr in outline.find_all('tr'):
            th, td = tr.find('th'), tr.find('td')
            if th is None or td is None:
                continue
            column = FIELD_MAP.get(th.get_text(strip=True))
            if column:
                data[column] = ' '.join(td.get_text(' ', strip=True).split())
    # 作品名 / 社团名（suggest API 检索不到的作品兜底）
    name = soup.find(id='work_name')
    if name:
        data['work_name'] = name.get_text(strip=True)
    maker = soup.find(class_='maker_name')
    if maker:
        data['maker_name'] = maker.get_text(strip=True)

    urls = []
    slider = soup.find(class_='product-slider-data')
    if slider:
        for div in slider.find_all('div'):
            src = div.get('data-src')
            if src:
                urls.append('https:' + src if src.startswith('//') else src)
    if not urls:
        og = soup.find('meta', property='og:image')
        if og and og.get('content'):
            urls.append(og['content'])

    # 正文（work_parts_container）：文本 + 正文图片
    body_text = ''
    description = (soup.select_one('div[itemprop="description"]')
                   or soup.find(class_='work_parts_container'))
    if description is not None:
        body_text = description.get_text('\n', strip=True)
        for img in description.find_all('img'):
            src = img.get('data-src') or img.get('src')
            if src:
                url = 'https:' + src if src.startswith('//') else src
                if url not in urls:
                    urls.append(url)
    return data, urls, body_text


def download_work_images(work_id, urls, work_folder=None):
    """下载作品全部图片到 <作品文件夹>/DataSource/（无作品文件夹时回退 images/<RJ号>/）。
    数据源文件夹已存在且有图片时不再下载，直接返回其中第一张作为封面；
    否则逐张下载（已存在的文件跳过），返回封面（第一张图片）的路径，没有图片返回 ''"""
    if work_folder and os.path.isdir(work_folder):
        folder = os.path.join(work_folder, DATA_SOURCE_DIR)
    else:
        folder = os.path.join(IMAGES_DIR, work_id)
    if os.path.isdir(folder):
        existing = [f for f in sorted(os.listdir(folder))
                    if os.path.isfile(os.path.join(folder, f)) and f.lower().endswith(IMAGE_EXTS)]
        if existing:
            # 优先用主图做封面（正文图片是哈希文件名，排序会排在主图前面）
            main = [f for f in existing if 'img_main' in f.lower()]
            return os.path.join(folder, (main or existing)[0])
    if not urls:
        return ''
    os.makedirs(folder, exist_ok=True)
    session = _session()
    cover = ''
    for i, url in enumerate(urls):
        filename = url.rsplit('/', 1)[-1].split('?')[0] or f'{work_id}_{i}'
        path = os.path.join(folder, filename)
        if not os.path.exists(path):
            try:
                r = session.get(url, timeout=30)
                if r.status_code != 200:
                    logger.write_log(f'图片下载失败 {url}: HTTP {r.status_code}', 'error')
                    continue
                with open(path, 'wb') as f:
                    f.write(r.content)
            except requests.RequestException as e:
                logger.write_log(f'图片下载失败 {url}: {e}', 'error')
                continue
        if not cover:
            cover = path
    return cover


def save_work_description(work_id, text, work_folder=None):
    """把作品页正文保存为 <作品文件夹>/DataSource/description.txt
    （无作品文件夹时回退 images/<RJ号>/），每次覆盖写入。
    返回 txt 路径，text 为空或写入失败返回 ''"""
    if not text:
        return ''
    if work_folder and os.path.isdir(work_folder):
        folder = os.path.join(work_folder, DATA_SOURCE_DIR)
    else:
        folder = os.path.join(IMAGES_DIR, work_id)
    path = os.path.join(folder, DESCRIPTION_TXT)
    try:
        os.makedirs(folder, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
    except OSError as e:
        logger.write_log(f'正文保存失败 {work_id}: {e}', 'error')
        return ''
    return path
