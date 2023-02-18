import re
import os
import time
import threading
from queue import Queue
from urllib3.exceptions import ProtocolError

from selenium import webdriver
from selenium.common.exceptions import *
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webelement import WebElement
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd

from utils.utils import *
from utils import Logger

class FCCScraper:
    """Scrapes content from https://www.youtube.com/@freecodecamp/videos"""

    def __init__(self) -> None:
        self.videos, self.video_count = [], 0
        
        self.date_regx = re.compile(r"\d+\s+[A-Za-z]+\s+ago\b")
        self.views_regex = re.compile(r"\b\d+(?:,\d+)?(?:,\d+)?\s(view[s]?)$")
        self.date_views = re.compile(r"\b\d+.+(view[s]?)$")

        self.queue = Queue()
        self.logger = Logger(__class__.__name__)

        self.logger.info("*******FCCScraper started*******")

        self.browser = self.__init_browser()

    def __init_browser(self) -> webdriver.Chrome:
        """Initializes the browser to be used in scraping  content"""
        options = webdriver.ChromeOptions()

        options.add_argument("--headless")
        options.add_argument("--incognito")
        options.add_argument("--no-sandbox")
        options.add_argument("--disabe-extensions")
        options.add_argument("--log-level=3")
        options.add_argument("--start-maximized")
        options.add_argument("--single-process")
        options.add_argument("--ignore-gpu-blocklist")
        options.add_argument("--disable-dev-shm-usage")

        options.add_experimental_option("useAutomationExtension", False)
        options.add_experimental_option("excludeSwitches", 
                                        ["enable-automation"])

        caps = DesiredCapabilities.CHROME
        caps["pageLoadStrategy"] = "none"

        service = Service(ChromeDriverManager().install())

        return webdriver.Chrome(service=service, options=options, 
                                desired_capabilities=caps)
    
    def __fetch_video_container(self) -> WebElement:
        """Fetches the videos from the current page"""
        self.browser.get(ROOT_URL)

        return WebDriverWait(self.browser, 20).until(
                    EC.presence_of_element_located(
                        (
                            By.CSS_SELECTOR, CONTAINER
                        )
                    )
                )

    def __test_content_loaded(self, container:WebElement) -> list:
        """Tests if new videos have been loaded on current page"""
        for _ in range(5):
            videos = container.find_elements(By.CSS_SELECTOR, VIDEO)

            if len(videos) > self.video_count: break

            time.sleep(2)

        return videos
    
    def __extract_video_slugs(self, element:WebElement) -> None:
        """Extracts the video slugs from a given webelement

            :param element: a webelement representing a single YT video
        """
        while True:
            try:
                a_tag = element.find_element(By.ID, "video-title-link")
                label_text = a_tag.get_attribute("aria-label")

                date_views = self.date_views.search(label_text, re.I).group()

                video_length = element.find_element(By.CSS_SELECTOR, 
                                                    VIDEO_LENGTH_CSS)

                data = {
                    "title":a_tag.get_attribute("title"),
                    "views":self.views_regex.search(date_views, re.I).group(),
                    "video_length": video_length.get_attribute("aria-label"),
                    "date_posted":self.date_regx.search(date_views).group(),
                    "link":a_tag.get_attribute("href")}

                self.videos.append(data)

                self.logger.info(f"Data extracted: {len(self.videos)}")

                break

            except ProtocolError:
                self.logger.warn("Error in %s. Retrying..." % \
                                 threading.current_thread().name)
    
    def __save_to_csv(self) -> None:
        """Save resulting data to csv"""
        if not os.path.exists("./data/"): os.makedirs("./data/")

        self.logger.info("Saving to csv...")

        df = pd.DataFrame.from_dict(self.videos)
        df = df.drop_duplicates()

        df.to_csv("./data/videos.csv", index=False)

        self.logger.info("Done!")
    
    def __create_work(self, elements:list) -> None:
        """Creates thread jobs
        
            :param elements: a list of elements from which video slugs 
             are to be extracted
        """
        [self.queue.put((element, elements)) for element in elements]
        self.queue.join()
    
    def __work(self) -> None:
        """Work to be done by the threads"""
        while True:
            element, elements = self.queue.get()

            self.__extract_video_slugs(element)

            elements.remove(element)

            self.queue.task_done()

    def scrape(self) -> None:
        """Entry point to the scraper"""
        self.logger.info("Loading all videos...")

        video_container = self.__fetch_video_container()

        videos = video_container.find_elements(By.CSS_SELECTOR, VIDEO)

        body = self.browser.find_element(By.TAG_NAME, "body")

        while True:
            if len(videos) == self.video_count:
                break

            self.video_count = len(videos)
            body.send_keys(Keys.END)

            videos = self.__test_content_loaded(video_container)
        
        if not len(videos):
            self.logger.error("Failed to scrape videos!")
        else:
            self.logger.info(f"{len(videos)} found. Extracting video slugs...")

        [threading.Thread(target=self.__work, daemon=True).start() 
                                                for _ in range(100)]

        self.__create_work(videos)

        self.__save_to_csv()
    
if __name__ == "__main__":
    scraper = FCCScraper()
    scraper.scrape()