from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
import getpass


def download(download_path):
    user_profile_path = f"C:\\Users\\{getpass.getuser()}\\AppData\\Local\\Google\\Chrome\\Selenium User Data"
    print(user_profile_path)

    # 配置 Chrome 选项
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument(f"--user-data-dir={user_profile_path}")  # 使用指定的用户数据目录
    prefs = {
        "download.default_directory": download_path,  # 设置默认下载路径
        # "download.prompt_for_download": False,  # 禁用下载提示
        "directory_upgrade": True,  # 允许覆盖已有的下载路径
        "safebrowsing.enabled": True  # 启用安全浏览
    }
    chrome_options.add_experimental_option("prefs", prefs)

    # 设置 ChromeDriver 服务
    service = Service('chromedriver.exe')  # 替换为你的 ChromeDriver 路径
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver
