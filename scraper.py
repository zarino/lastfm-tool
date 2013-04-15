#!/usr/bin/env python

# This Python script takes one command line argument: a lastfm username.
# It then saves the user's entire scrobble history to a sqlite file.

from __future__ import division
import requests
import lxml.html
import sqlite3
import dumptruck
import time
import optparse

parser = optparse.OptionParser()
(options, args) = parser.parse_args()

# Settings
user = args[0] if args else 'zarino'
api_key = '12b5aaf2b0f27b4b9402b391c956a88a'
per_page = 200

tracks_to_scrape = 0
tracks_scraped = 0

dt = dumptruck.DumpTruck(dbname="scraperwiki.sqlite")

def main():
    status("Scraping %s's history..." % user)
    setUpDatabase()
    getInfo()
    getRecentTracks()

def status(message, type='ok'):
    requests.post("https://x.scraperwiki.com/api/status", data={'type': type, 'message': message})
    print "%s: %s" % (type, message)

def percent(x,y):
    p = x / y * 100
    if p < 0.1:
        return '<0.1%'
    else:
        return str(round(p, 1)).replace('.0', '') + '%'

def setUpDatabase():
    dt.execute("CREATE TABLE IF NOT EXISTS recenttracks (datetime TEXT, user TEXT, track TEXT, track_mbid TEXT, track_url TEXT, track_artwork TEXT, artist TEXT, artist_mbid TEXT, album TEXT, album_mbid TEXT, _updated TEXT)")
    dt.execute("CREATE UNIQUE INDEX IF NOT EXISTS datetime_user_index ON recenttracks (datetime, user)")
    dt.execute("CREATE TABLE IF NOT EXISTS userinfo (user TEXT, id INT, realname TEXT, url TEXT, image TEXT, country TEXT, age INT, gender TEXT, subscriber INT, playcount INT, playlists INT, bootstrap INT, registered TEXT, _updated TEXT)")
    dt.execute("CREATE UNIQUE INDEX IF NOT EXISTS user_index ON userinfo (user)")

def getLatestScrobble():
    # Before we start scraping, we want to find out where
    # to start from. Are there already tracks in the database?
    try:
        r = dt.execute("SELECT strftime('%%s', datetime) as timestamp FROM recenttracks WHERE user='%s' ORDER BY datetime DESC LIMIT 1" % user)
        # Try selecting the most recently scraped track from the database
    except sqlite3.OperationalError as e:
        # Oh! Unexpected error. Pass it on.
        status("Unexpected SQL error: %s" % str(e), 'error')
        raise
    else:
        if r:
            # Great! We've got the most recently scraped track.
            latest_scrobble = int(r[0]['timestamp'])
        else:
            # Aha! The table exists but it's empty. Ignore.
            latest_scrobble = 0

    return latest_scrobble

def getRecentTracks():
    while True:
        # We scrape *backwards*, from the past to the present - where are we up to?
        latest_scrobble = getLatestScrobble()

        # Get the last page - going back to the timestamp we have (there'll be
        # one scrobble overlapping between each request)
        params = {
            'method': 'user.getrecenttracks',
            'user': user,
            'api_key': api_key,
            'from': latest_scrobble,
            'limit': per_page,
            'page': 9999999 # get the last page always
        }
        #print "get with params", params
        req = requests.get('http://ws.audioscrobbler.com/2.0/', params=params)
        xml = req.text.replace(' encoding="utf-8"', '') # Stop lxml complaining about encodings
        #print "got", xml
        dom = lxml.html.fromstring(xml)

        if dom.cssselect('error'):
            status("Unexpected error from Last.fm API: %s" % dom.cssselect('error')[0].text, 'error')
            raise Exception(dom.cssselect('error')[0].text)
            exit()

        recentTracks = []

        for item in dom.cssselect('track'):
            if item.get('nowplaying'):
                # Skip 'now playing' tracks because
                # they don't have a timestamp
                continue
            uts = int(item.cssselect('date')[0].get('uts'))
            recentTracks.append({
                'datetime': time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(uts)),
                'user': user,
                'track': item.cssselect('name')[0].text,
                'track_mbid': item.cssselect('mbid')[0].text,
                'track_url': item.cssselect('url')[0].text,
                'track_mbid': item.cssselect('mbid')[0].text,
                'track_artwork': item.cssselect('image[size="extralarge"]')[0].text,
                'artist': item.cssselect('artist')[0].text,
                'artist_mbid': item.cssselect('artist')[0].get('mbid'),
                'album': item.cssselect('album')[0].text,
                'album_mbid': item.cssselect('album')[0].get('mbid'),
                '_updated': time.strftime('%Y-%m-%dT%H:%M:%S')
            })
        dt.upsert(recentTracks, "recenttracks")
        global tracks_scraped
        tracks_scraped += len(recentTracks)
        status("Imported %s of %s tracks (%s)" % (tracks_scraped, tracks_to_scrape, percent(tracks_scraped, tracks_to_scrape)))

        if len(recentTracks) == 0:
            status("Up to date")
            break

def getInfo():
    # Save the user's metadata to a separate table.
    # We specifically don't store historical states here: just the latest info.

    params = {
        'method': 'user.getinfo',
        'user': user,
        'api_key': api_key
    }
    req = requests.get('http://ws.audioscrobbler.com/2.0/', params=params)
    xml = req.text.replace(' encoding="utf-8"', '') # Stop lxml complaining about encodings
    dom = lxml.html.fromstring(xml)

    if dom.cssselect('error'):
        status("Unexpected error from Last.fm API: %s" % dom.cssselect('error')[0].text, 'error')
        raise Exception(dom.cssselect('error')[0].text)
        exit()

    global tracks_to_scrape
    tracks_to_scrape = int(dom.cssselect('playcount')[0].text)
    registered = int(dom.cssselect('registered')[0].get('unixtime'))

    dt.upsert({
        'user': user,
        'id': dom.cssselect('id')[0].text,
        'realname': dom.cssselect('realname')[0].text,
        'url': dom.cssselect('url')[0].text,
        'image': dom.cssselect('image[size="extralarge"]')[0].text,
        'country': dom.cssselect('country')[0].text,
        'age': dom.cssselect('age')[0].text,
        'gender': dom.cssselect('gender')[0].text,
        'subscriber': dom.cssselect('subscriber')[0].text,
        'playcount': tracks_to_scrape,
        'playlists': dom.cssselect('playlists')[0].text,
        'bootstrap': dom.cssselect('bootstrap')[0].text,
        'registered': time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(registered)),
        '_updated': time.strftime('%Y-%m-%dT%H:%M:%S')
    }, "userinfo")

main()
