import re
import psycopg2
import os
import urllib.parse
import requests
from bs4 import BeautifulSoup
from linebot import LineBotApi
from linebot.models import TextSendMessage

DATABASE_URL = os.environ['DATABASE_URL']

BOT_KEY = ""
LINE_BOT_API = LineBotApi(BOT_KEY)

INDEX = 'https://www.ptt.cc/bbs/studyteacher/index.html'
NOT_EXIST = BeautifulSoup('<a>本文已被刪除</a>', 'lxml').a

ALREADY_PUSHED_ARTICLES = list()

def write_record_to_database(link):
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cur = conn.cursor()
    sql = "insert into msg (link) values (\'"+link+"\')"
    cur.execute(sql)
    conn.commit()
    conn.close()

def notification(title, link, registered_users):
    if link[-8:-5] in ALREADY_PUSHED_ARTICLES:
        return
    content = "{}\n{}".format(title, link)

    for user in registered_users:
        LINE_BOT_API.push_message(user, TextSendMessage(text=content))

    write_record_to_database(link[-8:-5])

    return True

def get_posts_on_page(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'lxml')
        #re_gs_title = re.compile(r'(國.*小+.*簡章.*|國.*小+.*(缺額|(教甄|甄選).*名額).*|國.*小+.*試場.*|國.*小+.*榜單.*)$', re.I)
        re_gs_title = re.compile(r'(國.*小+.*簡章.*)$', re.I)
        posts = list()

        for article in soup.find_all('div', 'r-ent'):
            meta = article.find('div', 'title').find('a') or NOT_EXIST
            title = meta.getText().strip()

            if re_gs_title.findall(title):
                print(title)
                posts.append({'title': title, 'link': meta.get('href'),
                              'push': article.find('div', 'nrec').getText(),
                              'date': article.find('div', 'date').getText(),
                              'author': article.find('div', 'author').getText()})

        next_link = soup.find('div', 'btn-group-paging').find_all('a', 'btn')[1].get('href')

        return posts, next_link

    except Exception as ex:
        print(ex)
        return [], INDEX

def get_pages(num):
    page_url = INDEX
    all_posts = list()
    for _ in range(num):
        posts, link = get_posts_on_page(page_url)
        all_posts += posts
        page_url = urllib.parse.urljoin(INDEX, link)

    return all_posts

def start(registered_users):
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cur = conn.cursor()
    cur.execute("select * from msg")
    rows = cur.fetchall()
    for row in rows:
        ALREADY_PUSHED_ARTICLES.append(row[0])
    conn.close()
    pages = 2
    for post in get_pages(pages):
        if isinstance(post['link'], str):
            link = post['link']
            notification(post['title'],
                         'https://www.ptt.cc/'+ link,
                         registered_users)

