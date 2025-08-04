import re
import requests
from urllib.parse import quote, urlparse, urljoin
from flask import Flask, redirect, Response, request, jsonify
from dnslib import DNSRecord
from scuapi import API
import m3u8
app = Flask(__name__)
DNS_QUERY_URL = "https://cloudflare-dns.com/dns-query"
DNS_QUERY_PARAM = "AAABAAABAAAAAAAAE3N0cmVhbWluZ2NvbW11bml0eXoFYm9hdHMAABwAAQ"

def get_hostname():
    """Risolvi l'host tramite DNS-over-HTTPS."""
    headers = {"accept": "application/dns-message"}
    try:
        response = requests.get(f"{DNS_QUERY_URL}?dns={DNS_QUERY_PARAM}", headers=headers, timeout=5)
        response.raise_for_status()
        dns_response = DNSRecord.parse(response.content)
        return str(dns_response.questions[0].qname).rstrip('.')
    except Exception as e:
        app.logger.error(f"Errore DNS: {e}")
        return None

def proxify_line(line, base_url):
    """Modifica le righe della playlist per farle passare tramite il proxy."""
    if 'URI="' in line:
        return re.sub(r'URI="([^"]+)"', lambda m: f'URI="/proxy?url={quote(urljoin(base_url + "/", m.group(1)))}"' if not m.group(1).startswith('http') else f'URI="/proxy?url={quote(m.group(1))}"', line)
    if line.startswith("http"):
        return f"/proxy?url={quote(line)}"
    if line and not line.startswith("#"):
        return f"/proxy?url={quote(urljoin(base_url + '/', line))}"
    return line

def proxy_stream(url):
    """Proxy diretto per contenuti non-m3u8."""
    try:
        resp = requests.get(url, stream=True, timeout=10)
        return Response(resp.iter_content(chunk_size=4096),
                        status=resp.status_code,
                        content_type=resp.headers.get('Content-Type'))
    except Exception as e:
        app.logger.error(f"Proxy error: {e}")
        return f"Errore durante il proxy: {e}", 500

@app.route("/proxy")
def go_proxy():
    url = request.args.get("url")
    if not url:
        return "Missing 'url' parameter", 400

    if "vixcloud.co" not in url and "scws-content.net" in url:
        return proxy_stream(url)

    try:
        resp = requests.get(url, timeout=10)
        content_type = resp.headers.get('Content-Type', '')
        if 'application/vnd.apple.mpegurl' in content_type or url.endswith('.m3u8'):
            base_url = url.rsplit("/", 1)[0]
            playlist = "\n".join(proxify_line(line, base_url) for line in resp.text.splitlines())
            return Response(playlist, content_type="application/vnd.apple.mpegurl")
        return proxy_stream(url)
    except Exception as e:
        app.logger.error(f"Errore nel proxy della playlist: {e}")
        return f"Errore nel download: {e}", 500

def fetch_playlist(item_id, episode_id=None):
    host = get_hostname()
    if not host:
        return None, "Errore nella risoluzione dell'host"
    if not item_id:
        return None, "ID non valido"
    sc = API(f"{host}/it")
    try:
        iframe, m3u_playlist_url = sc.get_links(item_id, episode_id=episode_id)
        resp = requests.get(m3u_playlist_url, timeout=10)
        if resp.status_code != 200:
            return None, "Errore nel download della playlist"
        base_url = m3u_playlist_url.rsplit("/", 1)[0]
        playlist = "\n".join(proxify_line(line, base_url) for line in resp.text.splitlines())
        return playlist, None
    except Exception as e:
        app.logger.error(f"Errore ottenendo playlist: {e}")
        return None, str(e)

@app.route("/movie/<int:item_id>")
def go_movie(item_id):
    playlist, error = fetch_playlist(item_id)
    if error:
        return error, 500
    return Response(playlist, content_type="application/vnd.apple.mpegurl")

@app.route("/serie/<int:item_id>/<int:episode_id>")
def go_serie(item_id, episode_id):
    playlist, error = fetch_playlist(item_id, episode_id)
    if error:
        return error, 500
    return Response(playlist, content_type="application/vnd.apple.mpegurl")

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

@app.route("/send/movie/<int:item_id>")
def sendMovie(item_id):
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
    #http://127.0.0.1:5000/movie/10739