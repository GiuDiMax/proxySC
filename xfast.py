import re
import requests
from urllib.parse import quote, urljoin, unquote
from dnslib import DNSRecord
from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import RedirectResponse, Response, PlainTextResponse, StreamingResponse
from scuapi import API

app = FastAPI()

def resolve_hostname() -> str:
    url = "https://cloudflare-dns.com/dns-query"
    headers = {"accept": "application/dns-message"}
    query_param = "AAABAAABAAAAAAAAE3N0cmVhbWluZ2NvbW11bml0eXoFYm9hdHMAABwAAQ"
    resp = requests.get(f"{url}?dns={query_param}", headers=headers)
    if resp.status_code != 200:
        raise HTTPException(status_code=500, detail="Errore nella risoluzione DNS")
    record = DNSRecord.parse(resp.content)
    return str(record.questions[0].qname).rstrip(".")


def proxify_playlist(playlist: str, base_url: str) -> str:
    def proxify(line: str) -> str:
        # intercetta URI in #EXT-X-KEY o simili
        if 'URI="' in line:
            # estrai URI e trasformalo in proxy URL
            return re.sub(
                r'URI="([^"]+)"',
                lambda m: f'URI="/proxy?url={quote(urljoin(base_url + "/", m.group(1)))}"',
                line
            )
        # riga che inizia con http
        if line.startswith("http"):
            return f"/proxy?url={quote(line)}"
        # riga non commento e non vuota
        if line and not line.startswith("#"):
            return f"/proxy?url={quote(urljoin(base_url + '/', line))}"
        return line

@app.get("/movie/{item_id}")
def get_movie(item_id: int):
    host = resolve_hostname()
    if item_id == 0:
        raise HTTPException(status_code=400, detail="ID mancante o non valido")
    sc = API(f"{host}/it")
    _, playlist_url = sc.get_links(item_id)
    resp = requests.get(playlist_url)
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Errore nel download della playlist")
    base_url = playlist_url.rsplit("/", 1)[0]
    return Response(proxify_playlist(resp.text, base_url), media_type="application/vnd.apple.mpegurl")


@app.get("/serie/{item_id}/{episode_id}")
def get_serie(item_id: int, episode_id: int):
    host = resolve_hostname()
    if item_id == 0:
        raise HTTPException(status_code=400, detail="ID mancante o non valido")
    sc = API(f"{host}/it")
    _, playlist_url = sc.get_links(item_id, episode_id=episode_id)
    resp = requests.get(playlist_url)
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Errore nel download della playlist")
    base_url = playlist_url.rsplit("/", 1)[0]
    return Response(proxify_playlist(resp.text, base_url), media_type="application/vnd.apple.mpegurl")


@app.get("/redirect/movie/{item_id}")
def redirect_movie(item_id: int):
    host = resolve_hostname()
    if item_id == 0:
        raise HTTPException(status_code=400, detail="ID mancante o non valido")
    sc = API(f"{host}/it")
    _, playlist_url = sc.get_links(item_id)
    return RedirectResponse(playlist_url)

@app.get("/proxy")
def proxy(url: str):
    decoded_url = unquote(url)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/115.0 Safari/537.36"
    }
    try:
        resp = requests.get(decoded_url, headers=headers, timeout=15, stream=True, verify=True)
        return StreamingResponse(
            resp.iter_content(chunk_size=8192),
            status_code=resp.status_code,
            media_type=resp.headers.get("Content-Type"),
        )
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Bad Gateway: {e}")