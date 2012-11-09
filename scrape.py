#!/usr/bin/env python

import requests
import lxml.html
import dumptruck
import time

dt = dumptruck.DumpTruck(dbname="lastfm.sqlite")

url = 'http://ws.audioscrobbler.com/2.0/'
params = {
    'method': 'user.getrecenttracks',
    'user': 'zarino',
    'api_key': '12b5aaf2b0f27b4b9402b391c956a88a',
    'to': int(time.time()),
    'limit': 200
}
page = 1

dt.execute('CREATE TABLE IF NOT EXISTS `tracks` (track, track_mbid, track_url, artist, artist_mbid, album, album_mbid, album_art, date, date_uts)')
dt.create_index(['track_mbid'], 'tracks')
dt.create_index(['artist_mbid'], 'tracks')
dt.create_index(['album_mbid'], 'tracks')
dt.create_index(['date_uts'], 'tracks', unique=True)

#latest = dt.execute('SELECT * FROM tracks ORDER BY date_uts DESC LIMIT 1')
#if latest:
#    params['from'] = latest['date_uts']

while page < 200:
    params['page'] = page
    xml = requests.get(url, params=params).text.replace(' encoding="utf-8"', '')
    dom = lxml.html.fromstring(xml)
    tracks = dom.cssselect('track');
    rows = []
    for track in tracks:
        if not track.get('nowplaying'):
            rows.append({
                'track': track.cssselect('name')[0].text,
                'track_mbid': track.cssselect('mbid')[0].text,
                'track_url': track.cssselect('url')[0].text,
                'artist': track.cssselect('artist')[0].text,
                'artist_mbid': track.cssselect('artist')[0].get('mbid'),
                'album': track.cssselect('album')[0].text,
                'album_mbid': track.cssselect('album')[0].get('mbid'),
                'album_art': track.cssselect('image[size="extralarge"]')[0].text,
                'date': track.cssselect('date')[0].text,
                'date_uts': track.cssselect('date')[0].get('uts')
            })
    dt.insert(rows, "tracks")
    print "scraped", len(tracks), "tracks"
    if len(tracks) < 200:
        break
    else:
        page = page + 1