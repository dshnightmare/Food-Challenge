from __future__ import print_function
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import re
from argparse import ArgumentParser
from bs4.element import Comment
import csv
import json
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from newspaper import Article

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
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_argument('--log-level=3')
titles = []
abstracts = []
urls = []
newsurl = []

with open("../data/Training Set for Competition.txt", encoding='UTF-8') as f:  # read url from txt
    data = f.readlines()
data = data[1:]

def run(start, end):
    with open('../data/download{}-{}.csv'.format(start, end), 'w', encoding='UTF-8') as csvfile,\
            open('../data/untreated{}-{}'.format(start, end), 'w', encoding='UTF-8') as undo:
        fieldnames = ['title', 'url', 'newsurl', 'abstract', 'text_body']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()

        driver = webdriver.Chrome(chrome_options=options, executable_path='../bin/chromedriver.exe')
        # driver = driver = webdriver.Firefox(options=options, executable_path='C:\pythonpath\geckodriver.exe')
        print(start, end)
        for index, lines in enumerate(data[start:end]):
            title = lines.split('\t')[4]
            url = lines.split('\t')[5]
            abstract = lines.split('\t')[6]
            '''
            1. twitter url + news url already converted to short url
            2. twitter url + news url not handle
            3. twitter url + text only ()
            4. news url
            '''
            print('{}: {}'.format(start + index, url))
            pattern1 = re.compile('https://twitter.com/.+/status/[0-9]+')
            if pattern1.match(url):
                pattern2 = re.compile('https://t.co/[a-zA-Z0-9]+')
                result = re.search(pattern2, abstract)
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
                                type = media.get_attribute('data-card2-name')
                                if type in []:
                                    raise ValueError
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
                                undo.write('pure text:{}\n'.format(index))
                                continue
                    except Exception as e:
                        print(e)
            else:
                newsurl = url
            print(newsurl)
            # load the page, max three times
            num = 0
            while True:
                try:
                    driver.get(newsurl)
                    print("<<<<<<<<<<<<Waiting>>>>>>>>>>>")
                    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "html")))
                except TimeoutException as e:
                    num += 1
                    print("<<<<<<<<<<<<loading error {}>>>>>>>>>>>".format(num))
                    if num <= 3:
                        continue
                    else:
                        writer.writerow({
                            'title': title,

                            'url': url,

                            'newsurl': newsurl,

                            'abstract': abstract,

                            'text_body': "none"
                        })
                        undo.write('loading error:{}\n'.format(index))
                        break
                else:
                    break
            if num == 3:
                continue
            longurl = driver.current_url
            print(longurl)
            if pattern1.match(longurl):
                print("<<<<<<<<<<<<Quete Tweet>>>>>>>>>>>")
                writer.writerow({
                    'title': title,

                    'url': url,

                    'newsurl': newsurl,

                    'abstract': abstract,

                    'text_body': "none"
                })
                undo.write('quote tweet:{}\n'.format(index))
                continue
            try:
                article = Article(longurl)
                article.download()
            except:
                print("<<<<<<<<<<<<download fail>>>>>>>>>>>")
                writer.writerow({
                    'title': title,

                    'url': url,

                    'newsurl': newsurl,

                    'abstract': abstract,

                    'text_body': "none"
                })
                undo.write('download fail:{}\n'.format(index))
            else:
                try:
                    article.parse()
                    print(article.text)
                    writer.writerow({
                        'title': title,

                        'url': url,

                        'newsurl': newsurl,

                        'abstract': abstract,

                        'text_body': json.dumps({'title': article.title, 'authors': article.authors, 'text': article.text, 'image': article.top_img})
                    })
                except:
                    print("<<<<<<<<<<<parsing fail>>>>>>>>>>>")
                    writer.writerow({
                        'title': title,

                        'url': url,

                        'newsurl': newsurl,

                        'abstract': abstract,

                        'text_body': "none"
                    })
                    undo.write('parsing fail:{}\n'.format(index))

if __name__ == '__main__':
    # run in range
    parser = ArgumentParser()
    parser.add_argument('--start',  type=int, default=0, help='start from this index')
    parser.add_argument('--end', type=int, default=len(data), help='end by this index')
    args = parser.parse_args()
    run(args.start, args.end)