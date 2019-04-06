from __future__ import print_function
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup
import os, time
import re
import random
from bs4.element import Comment
import csv
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


def tag_visible(element):
    if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
        return False
    if isinstance(element, Comment):
        return False
    return True


def text_from_html(body):
    soup = BeautifulSoup(body, 'html.parser')
    texts = soup.findAll(text=True)
    visible_texts = filter(tag_visible, texts)
    return u" ".join(t.strip() for t in visible_texts)


def wait_for_page_load(self, timeout=30):
    old_page = self.driver.find_element_by_tag_name('html')
    yield
    WebDriverWait(self.browser, timeout).until(EC.staleness_of(old_page))


# options = Options()
# options.headless = True
titles = []
abstracts = []
urls = []
newsurl = []

with open("..\data\Training Set for Competition.txt", encoding='UTF-8') as f:  # read url from txt
    data = f.readlines()
data = data[1:]
with open('..\data\download.csv', 'w', encoding='UTF-8') as csvfile:
    fieldnames = ['title', 'url', 'newsurl', 'abstract', 'text_body']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()

    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(chrome_options=options, executable_path='../bin/chromedriver.exe')
    for index, lines in enumerate(data):
        # if index < 80:
        #     continue
        title = lines.split('\t')[4]
        url = lines.split('\t')[5]
        abstract = lines.split('\t')[6]
        '''
        1. twitter url + news url already converted to short url
        2. twitter url + news url not handle
        3. twitter url + text only ()
        4. news url
        '''
        print('{}: {}'.format(index, url))
        pattern = re.compile('https://twitter.com/tweet/status/[0-9]+')
        if pattern.match(url):
            pattern = re.compile('https://t.co/[a-zA-Z0-9]+')
            result = re.search(pattern, abstract)
            if result != None:
                newsurl = result.group(0)
            else:
                try:
                    driver.get(url)
                    try:
                        text = driver.find_element_by_class_name('js-tweet-text-container')
                        link = text.find_element_by_class_name('twitter-timeline-link')
                        newsurl = link.get_attribute('href')
                    except NoSuchElementException as e:
                        print('no link in text: {}'.format(str(e)))
                        try:
                            media = driver.find_element_by_class_name('card2 js-media-container')
                            link = media.find_element_by_tag_name('a')
                            newsurl = link.get_attribute('href')
                        except NoSuchElementException as e:
                            print('no card link: {}'.format(str(e)))
                            print("<<<<<<<<<<<<no newsurl>>>>>>>>>>>")
                            writer.writerow({
                                'title': title,

                                'url': url,

                                'newsurl': "none",

                                'abstract': abstract,

                                'text_body': "none"
                            })
                            continue
                except Exception as e:
                    print(e)
        else:
            newsurl = url
        print(newsurl)
        # try:
        #     driver.get(newsurl)
        #     print("<<<<<<<<<<<<Waiting>>>>>>>>>>>")
        #     WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "html")))
        # except:
        #     print("<<<<<<<<<<<<???????>>>>>>>>>>>")
        # text_body = text_from_html(driver.page_source)
        # print(text_body)
        # print("<<<<<<<<<<<<Writing>>>>>>>>>>>")
        # writer.writerow({
        #     'title': title,
        #
        #     'url': url,
        #
        #     'newsurl': newsurl,
        #
        #     'abstract': abstract,
        #
        #     'text_body': text_body
        # })
