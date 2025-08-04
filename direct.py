import requests
from dnslib import DNSRecord
from flask import Flask, redirect, Response
from scuapi import API
app = Flask(__name__)

def get_hostname():
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
    #item_id = getId(host, item_id)
    if item_id == 0:
        return "Errore nella ricezione dell'id", 500
    sc = API(f"{host}/it")
    iframe, m3u_playlist_url = sc.get_links(item_id)
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
    #http://127.0.0.1:5000/movie/10739
    #http://127.0.0.1:5000/serie/5334/34065
    app.run(host="0.0.0.0", port=5000)