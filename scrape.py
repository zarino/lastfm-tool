#!/usr/bin/env python

import requests
import lxml.html
import dumptruck
import time

def create_tables(dt):
    dt.execute('CREATE TABLE IF NOT EXISTS `artist` (`mbid` TEXT PRIMARY KEY, `name` TEXT)')
    dt.execute('CREATE TABLE IF NOT EXISTS `album` (`mbid` TEXT PRIMARY KEY, `name` TEXT, `artwork` TEXT)')
    dt.execute('CREATE TABLE IF NOT EXISTS `track` (`mbid` TEXT PRIMARY KEY, `name` TEXT, `url` TEXT, `artist_mbid` TEXT, `album_mbid` TEXT)')
    dt.execute('CREATE TABLE IF NOT EXISTS `scrobble` (`date` INT, `user` TEXT, `track_mbid` TEXT)')
    dt.create_index(['date','user'], 'scrobble', unique=True)

def get_latest_scrobble(dt):
    r = dt.execute('SELECT `date` FROM `scrobble` ORDER BY `date` DESC LIMIT 1')
    if r:
        return r[0]['date']
    else:
        return 0

def get_scrobbles(page=None):
    params = {
        'method': 'user.getrecenttracks',
        'user': user,
        'api_key': api_key,
        'to': now,
        'from': latest,
        'limit': per_page
    }
    if page:
        params['page'] = page
    req = requests.get('http://ws.audioscrobbler.com/2.0/', params=params)
    print 'GET', req.url
    xml = req.text.replace(' encoding="utf-8"', '') # stop lxml complaining about encodings
    for l in xml.splitlines()[:4]:
        print '\033[22;37m   ', l.strip(), '\033[0m'
    dom = lxml.html.fromstring(xml)

    if dom.cssselect('error'):
        raise Exception(dom.cssselect('error')[0].text)
        exit()

    if page:
        print 'scraping page', page
        # we asked for a particular page - get all the tracks
        artists = []
        albums = []
        tracks = []
        scrobbles = []
        for item in dom.cssselect('track'):
            if item.get('nowplaying'): # skip 'now playing' track
                continue
            artists.append({
                'mbid': item.cssselect('artist')[0].get('mbid'),
                'name': item.cssselect('artist')[0].text
            })
            albums.append({
                'mbid': item.cssselect('album')[0].get('mbid'),
                'name': item.cssselect('album')[0].text,
                'artwork': item.cssselect('image[size="extralarge"]')[0].text,
            })
            tracks.append({
                'mbid': item.cssselect('mbid')[0].text,
                'name': item.cssselect('name')[0].text,
                'url': item.cssselect('url')[0].text,
                'artist_mbid': item.cssselect('artist')[0].get('mbid'),
                'album_mbid': item.cssselect('album')[0].get('mbid')
            })
            scrobbles.append({
                'date': item.cssselect('date')[0].get('uts'),
                'user': user,
                'track_mbid': item.cssselect('mbid')[0].text
            })
        print 'saving', len(artists), 'artists,', len(albums), 'albums,', len(tracks), 'tracks,', len(scrobbles), 'scrobbles...'
        dt.upsert(artists, "artist")
        dt.upsert(albums, "album")
        dt.upsert(tracks, "track")
        dt.upsert(scrobbles, "scrobble")
        if page > 1:
            get_scrobbles(page - 1)
        else:
            print 'done!'

    else:
        # we didn't ask for a page - start from the end
        i = dom.cssselect('recenttracks')[0].get('totalpages')
        print i, 'pages to scrape'
        get_scrobbles(int(i))

# settings
user = 'zarino'
api_key = '12b5aaf2b0f27b4b9402b391c956a88a'
per_page = 200
now = int(time.time())

dt = dumptruck.DumpTruck(dbname="lastfm.sqlite")
create_tables(dt)

latest = get_latest_scrobble(dt)

get_scrobbles()
