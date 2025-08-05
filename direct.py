import requests
from dnslib import DNSRecord
from flask import Flask, redirect, Response, request
from scuapi import API
import m3u8
app = Flask(__name__)

def get_hostname():
    return "https://streamingunity.co/"
    url = "https://cloudflare-dns.com/dns-query"
    headers = {
        "accept": "application/dns-message"
    }
    query_param = "AAABAAABAAAAAAAAE3N0cmVhbWluZ2NvbW11bml0eXoFYm9hdHMAABwAAQ"
    response = requests.get(f"{url}?dns={query_param}", headers=headers)
    if response.status_code != 200:
        raise Exception("Errore nella richiesta DNS")
    dns_response = DNSRecord.parse(response.content)
    qname = dns_response.questions[0].qname
    hostname = str(qname).rstrip('.')
    return hostname

def getId(host, id):
    url = f"https://{host}/it/titles/{id}"
    return id

@app.route("/redirect/movie/<int:item_id>")
def redirectMovie(item_id):
    host = get_hostname()
    if not host:
        return "Errore nella risoluzione dell'host", 500
    #item_id = getId(host, item_id)
    if item_id == 0:
        return "Errore nella ricezione dell'id", 500
    sc = API(f"{host}/it")
    iframe, m3u_playlist_url = sc.get_links(item_id)
    return redirect(m3u_playlist_url)

@app.route("/movie/<int:item_id>")
def goMovie(item_id):
    host = get_hostname()
    if not host:
        return "Errore nella risoluzione dell'host", 500
    if item_id == 0:
        return "Errore nella ricezione dell'id", 500
    sc = API(f"{host}/it")
    iframe, m3u_playlist_url = sc.get_links(item_id)
    print(m3u_playlist_url)
    try:
        response = requests.get(m3u_playlist_url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        return f"Errore nella richiesta: {e}", 500

    if request.args.get("max") == "1":
        master_playlist = m3u8.loads(response.text)
        if not master_playlist.playlists:
            return "Nessun flusso disponibile nella playlist", 500
        best_stream = max(master_playlist.playlists, key=lambda p: p.stream_info.bandwidth)
        lines = ['#EXTM3U']
        for media in master_playlist.media:
            attrs = [
                f'URI="{media.uri}"',
                f'TYPE={media.type}',
                f'GROUP-ID="{media.group_id}"',
                f'LANGUAGE="{media.language}"',
                f'NAME="{media.name}"',
                f'DEFAULT={"YES" if media.default else "NO"}',
                f'AUTOSELECT={"YES" if media.autoselect else "NO"}',
                f'FORCED={"YES" if media.forced else "NO"}',
            ]
            lines.append(f'#EXT-X-MEDIA:{",".join(attrs)}')

        info = best_stream.stream_info
        attrs = [
            f'BANDWIDTH={info.bandwidth}',
            f'CODECS="{info.codecs}"' if info.codecs else '',
            f'RESOLUTION={info.resolution[0]}x{info.resolution[1]}' if info.resolution else '',
            f'AUDIO="{info.audio}"' if info.audio else '',
            f'SUBTITLES="{info.subtitles}"' if info.subtitles else '',
        ]
        attrs_str = ",".join(filter(None, attrs))
        lines.append(f'#EXT-X-STREAM-INF:{attrs_str}')
        lines.append(best_stream.uri)

        playlist_str = '\n'.join(lines)
        return Response(playlist_str, mimetype="application/vnd.apple.mpegurl")

    headers = {
        "Content-Type": response.headers.get("Content-Type", "application/vnd.apple.mpegurl")
    }
    return Response(response.content, status=response.status_code, headers=headers)

@app.route("/serie/<int:item_id>/<int:episode_id>")
def goSerie(item_id, episode_id):
    host = get_hostname()
    if not host:
        return "Errore nella risoluzione dell'host", 500
    if item_id == 0:
        return "Errore nella ricezione dell'id", 500
    sc = API(f"{host}/it")
    iframe, m3u_playlist_url = sc.get_links(item_id, episode_id=episode_id)
    try:
        proxied_response = requests.get(m3u_playlist_url, timeout=10)
    except requests.RequestException as e:
        return f"Errore nella richiesta: {e}", 500
    headers = {
        "Content-Type": proxied_response.headers.get("Content-Type", "application/octet-stream")
    }
    if "Content-Length" in proxied_response.headers:
        headers["Content-Length"] = proxied_response.headers["Content-Length"]
    if "Content-Disposition" in proxied_response.headers:
        headers["Content-Disposition"] = proxied_response.headers["Content-Disposition"]
    return Response(proxied_response.content, status=proxied_response.status_code, headers=headers)

# Esempio d'uso
if __name__ == "__main__":
    #sc = API(f"streamingcommunityz.boats/it")
    #iframe, m3u_playlist_url = sc.get_links(10739)
    #print(m3u_playlist_url)
    #10739 dragon trainer
    #http://127.0.0.1:5000/movie/10810
    #http://127.0.0.1:5000/serie/5334/34065
    app.run(host="0.0.0.0", port=5000)