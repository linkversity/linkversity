from bs4 import BeautifulSoup
import requests as r

req = r.get("https://emoji-css.afeld.me")
soup = BeautifulSoup(req.content, 'html.parser')
names = soup.find_all("span", class_="name")
names = (n.text for n in names)

with open('data/emoji.txt', 'w+') as f:
    for name in list(names):
        f.write('\n'+'em-'+name)