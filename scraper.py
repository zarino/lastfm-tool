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
    xml = req.text.replace(' encoding="utf-8"', '') # stop lxml complaining about encodings
    dom = lxml.html.fromstring(xml)

    if dom.cssselect('error'):
        raise Exception(dom.cssselect('error')[0].text)
        exit()

    if page:
        print 'Scraping page #%s' % page
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
        dt.upsert(artists, "artist")
        dt.upsert(albums, "album")
        dt.upsert(tracks, "track")
        dt.upsert(scrobbles, "scrobble")
        min = time.strftime('%Y-%m-%d %H:%I', time.gmtime(float(scrobbles[0]['date'])))
        max = time.strftime('%Y-%m-%d %H:%I', time.gmtime(float(scrobbles[-1]['date'])))
        print 'Saved', len(scrobbles), 'scrobbles:', min , 'to', max
        if page > 1:
            get_scrobbles(page - 1)
        else:
            print 'Done!'

    else:
        # we didn't ask for a page - start from the end
        i = int(dom.cssselect('recenttracks')[0].get('totalpages'))
        t = int(dom.cssselect('recenttracks')[0].get('total'))
        if i > 0:
            print t, 'new tracks since', time.strftime('%Y-%m-%d %H:%I', time.gmtime(latest))
            get_scrobbles(i)
        else:
            print 'No new tracks since', time.strftime('%Y-%m-%d %H:%I', time.gmtime(latest))

# settings
user = 'zarino'
api_key = '12b5aaf2b0f27b4b9402b391c956a88a'
per_page = 200
now = int(time.time())

dt = dumptruck.DumpTruck(dbname="lastfm.sqlite")
create_tables(dt)

latest = get_latest_scrobble(dt)

get_scrobbles()
