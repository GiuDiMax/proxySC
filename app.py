import requests
from dnslib import DNSRecord
from flask import Flask, redirect
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

@app.route("/movie/<int:item_id>")
def go(item_id):
    host = get_hostname()
    if not host:
        return "Errore nella risoluzione dell'host", 500

    #item_id = getId(host, item_id)
    if item_id == 0:
        return "Errore nella ricezione dell'id", 500

    sc = API(f"{host}/it")
    iframe, m3u_playlist_url = sc.get_links(item_id)

    print("Redirect a:", m3u_playlist_url)
    return redirect(m3u_playlist_url, code=302)

# Esempio d'uso
if __name__ == "__main__":
    #sc = API(f"streamingcommunityz.boats/it")
    #iframe, m3u_playlist_url = sc.get_links(10739)
    #print(m3u_playlist_url)
    #10739 dragon trainer
    app.run(host="0.0.0.0", port=5000)
