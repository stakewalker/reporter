ver = '1.1.1'

import requests
import json
from config import chavecrypcomp, wp_blog, wp_website, tl_pk
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods.posts import GetPosts, NewPost
from datetime import datetime
from time import sleep
from python_translator import Translator
import pyshorteners
import link_preview
from random import randint

tl_pk = tl_pk[::-1]
wp = Client(wp_website+'xmlrpc2.php', wp_blog[0], wp_blog[1][::-1])
cache_file = "~/reporter/cache.data"  # Assuming it's a Linux/Unix OS
# cache_file = "cache.data"  # Uncomment for testing
last_id = int(open(cache_file).read())  # Specify full path
translator = Translator()

special_terms = [
    ('binance','https://bit.ly/3PWFkpR'),
    ('bybit','https://bit.ly/3z44nAB'),
    ('kucoin','https://bit.ly/3z9temv'),
    ('exchange','https://bit.ly/3PBf0Su'),
    ('negocia','https://bit.ly/3OA4c5Z'),
    ('telegram','https://bit.ly/3RXGTWx'),
    ('instagram','https://bit.ly/3vabGFV'),
    ('linkedin','https://bit.ly/3zwT85f'),
    ('twitter','https://bit.ly/3zwrCF3'),
    ('mercado','https://bit.ly/3zwWQMc'),
    ('satoshi','https://bit.ly/3OGIU6Q'),
    ('bitcoin','https://bit.ly/3vdzQ2a'),
    ('criptomoeda','https://bit.ly/3RXD7fL')
    ]
def cook_description(content):
    description = translate(content).replace('. ','.\n')  #Deal with paragraphs
    description = description.split('[')[0]  # Remove bugs ( [&#8230;] )
    added_links = []
    for word in description.split(' '):  # Add hyperlinks
        if len(word) >= 5:  # and word.lower() not in added_links:
            for item in special_terms:
                if item[0] in word.lower() and item[1] not in added_links:
                    print(f'[ Added hyperlink for {word}]')
                    description = description.replace(word,f'<a href={item[1]} target="_blank">{word}</a>', 1)
                    added_links.append(item[1])
    return description

def translate(text):  # Traduz coisas
    print('Traduzindo...')
    return str(translator.translate(text, "portuguese"))

def get_thumbnail(url,terms):  # Busca o thumbnail original
    print(terms)
    print('Procurando thumbnail...')
    sleep(1)
    try:
        img_url = link_preview.generate_dict(url)['image']
        return short_url(img_url, False)
    except:
        rnum = randint(6,10)
        return f"https://source.unsplash.com/random/{rnum}00x{rnum}00/?"+terms.replace('|',',')

def short_url(url, bool):  # Encurta links
    if bool == True:  # if True short and translate
        print('Shorting URL & translating...')
        google_translator = 'http://translate.google.com/translate?js=n&sl=en&tl=pt&u='
        return google_translator+pyshorteners.Shortener().tinyurl.short(url)
    elif bool == False:  # if False just short url
        print('Shorting URL...')
        return pyshorteners.Shortener().tinyurl.short(url)

def upd_db():  # Prepara as notícias e inverte a ordem
    new_db = []
    news = requests.get(f'https://min-api.cryptocompare.com/data/v2/news/?lang=EN&api_key={chavecrypcomp[::-1]}').json()['Data']
    for i in news:
        if int(i['id']) > last_id:
            try:
                new_db.append(editor(i))
                print(i['id'],'OK\n')
            except:
                print('\n<< Error >>\n')
    new_db = list(reversed(new_db))
    return new_db

def editor(news_obj):  # Formata as manchetes
    print(f"Editando manchete {news_obj['id']}...")
    blacklist = ['sponsored','analysis']
    for i in blacklist:
        if i in str(news_obj).lower():
            raise Exception  # Desiste da manchete se conter palavras da blacklist
    thumbnail = get_thumbnail(news_obj['url'],news_obj['categories'])
    sleep(1)
    date = datetime.fromtimestamp(news_obj['published_on'])
    title = translate(news_obj['title']).replace('criptografia','cripto')
    description = cook_description(news_obj['body'])
    tags = translate(news_obj['tags']).upper().replace('|',',').replace(' ','')
    categories = translate(news_obj['categories']).replace('|',',')
    original_url = short_url(news_obj['url'], False)
    sleep(1)
    minute = date.minute if len(str(date.minute)) >= 2 else '00'
    content = f"""
    <a href="{wp_website}?p=wpid"> <img src={thumbnail} alt={categories}> </a>
    <p style="text-align:center;">
    <a href="{original_url}" target="_blank">Copyright © {news_obj['source'].title()}</a></p>
    <!--more-->
    <p style="font-size:120%;">
    {description}
    <p><span style="color: #008000;"><a style="color: #008000;" href="{short_url(news_obj['url'], True)}" target="_blank"><strong>(Continuar lendo...)</strong></a></span></p>
    </p>


    <small>Esta é apenas uma tradução em português e este conteúdo não reflete a opinião do site Satoshi da Silva.
    A <a href="{original_url}" target="_blank">notícia original</a> foi publicada por {
    news_obj['source'].title()}, no dia {date.day}/{date.month}/{date.year}, às {
    date.hour}:{minute} (Horário de Brasília).</small>
    """
    return {
        'id': news_obj['id'],
        'title': title,
        'content': content,
        'tags': [i for i in tags.split(',') if i != ''],
        'categories': categories.split(','),
        'thumbnail': thumbnail
        }

def publish2wp(headline):  # Publica no WordPress
    print(f"Publicando #{headline['id']} no WP...")
    post = WordPressPost()
    wpid = int(wp.call(GetPosts())[0].id) + 2
    post.slug = wpid
    post.title = headline['title']
    post.content = headline['content'].replace('wpid',str(wpid))  # fix broken links
    post.terms_names = {
    'post_tag': headline['tags'],  # Must be list type
    'category': headline['categories']  # Same here
    }
    post.post_status = 'publish'
    wp.call(NewPost(post))  #Finish and post
    return open(cache_file, 'w').write(headline['id'])  # Save id to file

def publish2tl(headline):
    print('Postando no Telegram...')
    last_wpid = wp.call(GetPosts())[0].id  # Gets the last WP post ID
    sleep(1)
    the_url = str(short_url(f"{wp_website}?p={last_wpid}", False)).split('//')[1]
    msg = f'''**{headline['title']}**: {the_url}'''
    return requests.get("https://api.telegram.org/bot"+tl_pk+"/sendMessage?chat_id=-1001575989033"+"&parse_mode=Markdown&text="+msg)

### Rodando o programa!
print(f'Rodando Reporter {ver} \n')
new_db = upd_db()
for i in new_db:
    publish2wp(i)
    print(f'WordPress OK')
    publish2tl(i)
    print('Telegram OK\n')
    sleep(10)
print('\nOK COMPUTER\n')