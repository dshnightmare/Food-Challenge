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
options.add_argument("--disable-extensions")
options.add_argument("--proxy-server=socks5://127.0.0.1:1080")
titles = []
abstracts = []
urls = []
newsurl = []


def run(start, end, file):
    with open("../data/{} Set for Competition.txt".format(file), encoding='UTF-8') as f:  # read url from txt
        data = f.readlines()
    data = data[1:]
    if end == -1:
        end = len(data)
    print(start, end)
    with open('../data/{}_download{}-{}.csv'.format(file, start, end), 'w', encoding='UTF-8') as csvfile,\
            open('../data/{}_untreated{}-{}'.format(file, start, end), 'w', encoding='UTF-8') as undo:
        fieldnames = ['title', 'url', 'newsurl', 'abstract', 'text_body']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()

        driver = webdriver.Chrome(chrome_options=options, executable_path='../bin/chromedriver.exe')
        # driver = driver = webdriver.Firefox(options=options, executable_path='C:\pythonpath\geckodriver.exe')
        for index, lines in enumerate(data[start:end]):
            csvfile.flush()
            undo.flush()
            # if index < 24:
            #     continue
            if file == 'Train':
                _, _, _, _, title, url, abstract = lines.split('\t')
            elif file == 'Test':
                _, _, _, title, url, abstract = lines.split('\t')
            else:
                raise  ValueError
            '''
            1. twitter url + news url already converted to short url
            2. twitter url + news url not handle
            3. twitter url + text only ()
            4. news url
            '''
            print('{}: {}'.format(start + index, url))
            pattern1 = re.compile('https://twitter.com/.+/status/[0-9]+')
            newsurl = None
            if pattern1.match(url):
                # 不使用提供的短网址
                # pattern2 = re.compile('https://t.co/[a-zA-Z0-9]+')
                # result = re.search(pattern2, abstract)
                # Quote Tweet
                while True:
                    try:
                        driver.get(url)
                        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "html")))
                        tweet = driver.find_elements_by_class_name('QuoteTweet')
                        media = tweet.find_element_by_class_name('js-media-container')
                        item = media.get_attribute('href')
                        assert item is not None
                        _url = 'https://twitter.com{}'.format(item)
                        print(_url)
                        if url.split('/')[-1] == _url.split('/')[-1]:
                            break
                        url = _url
                    except Exception as e:
                        break
                try:
                    text = driver.find_element_by_class_name('js-tweet-text-container')
                except Exception as e:
                    print('invalid tweet: {}'.format(str(e)))
                    writer.writerow({
                        'title': title,

                        'url': url,

                        'newsurl': "none",

                        'abstract': abstract,

                        'text_body': "none"
                    })
                    undo.write('invalid tweet:{}\n'.format(index))
                    continue
                # find card
                try:
                    media = driver.find_element_by_class_name('js-media-container')
                    type = media.get_attribute('data-card2-name')
                    if type in ['summary_large_image', 'summary']:
                        newsurl = media.find_element_by_tag_name('div').get_attribute('data-card-url')
                    elif type in ['player', None]:
                        raise NoSuchElementException
                    elif type.find('choice_text_only'):
                        raise NoSuchElementException
                    elif type.find('message_me') != -1:
                        raise NoSuchElementException
                    elif type.find('moment') != -1:
                        raise NoSuchElementException
                    else:
                        raise ValueError
                except ValueError as e:
                    raise
                except NoSuchElementException as e:
                    print('no card element: {}'.format(str(e)))
                    # find link in text
                    links = text.find_elements_by_class_name('twitter-timeline-link')
                    hides = text.find_elements_by_class_name('u-hidden')
                    for link in links:
                        if link not in hides:
                            newsurl = link.get_attribute('href')
                            break
                    if newsurl is None:
                        print('no link in text: {}'.format(str(e)))
                        writer.writerow({
                            'title': title,

                            'url': url,

                            'newsurl': "none",

                            'abstract': text.text,

                            'text_body': "none"
                        })
                        continue
            else:
                newsurl = url
            print(newsurl)
            # load the page, max three times
            num = 0
            while True:
                try:
                    driver.get(newsurl)
                    print("<<<<<<<<<<<<Waiting>>>>>>>>>>>")
                    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.TAG_NAME, "html")))
                except Exception as e:
                    num += 1
                    print("<<<<<<<<<<<<loading error {}>>>>>>>>>>>".format(num))
                    if num < 3:
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
            # if pattern1.match(longurl):
            #     print("<<<<<<<<<<<<Quete Tweet>>>>>>>>>>>")
            #     assert longurl.split('/')[-1] == url.split('/')[-1]
            #     try:
            #         container = driver.find_element_by_class_name('permalink-tweet-container')
            #         text = container.find_element_by_class_name('js-tweet-text-container')
            #     except NoSuchElementException as e:
            #         raise
            #     writer.writerow({
            #         'title': title,
            #
            #         'url': url,
            #
            #         'newsurl': newsurl,
            #
            #         'abstract': abstract,
            #
            #         'text_body': text.text
            #     })
            #     # undo.write('quote tweet:{}\n'.format(index))
            #     continue
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
    parser.add_argument('--end', type=int, default=-1, help='end by this index')
    parser.add_argument('--file', type=str, default='Training', help='Training or test')
    args = parser.parse_args()
    run(args.start, args.end, args.file)