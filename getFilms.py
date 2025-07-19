from main import get_hostname
import requests
import json
import html
from bs4 import BeautifulSoup

def getFilms():
    results = []
    url = f"https://{get_hostname()}/it/browse/trending?type=movie"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    app_div = soup.find("div", {"id": "app"})
    if not app_div:
        return results
    data_page_raw = app_div.get("data-page")
    if not data_page_raw:
        return results
    data_page_unescaped = html.unescape(data_page_raw)
    try:
        data = json.loads(data_page_unescaped)
        films = data['props']['titles']
        for f in films:
            print(f)
            exit()
    except:
        return results

if __name__ == "__main__":
    getFilms()
