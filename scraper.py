#!/usr/bin/env python

# This Python script takes one command line argument: a lastfm username.
# It then saves the user's entire scrobble history to a sqlite file.

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

def main():
    now = int(time.time())
    dt = dumptruck.DumpTruck(dbname="scraperwiki.sqlite")

    status("Scraping %s's history..." % user)

    getInfo()
    getRecentTracks()

def status(message, type='ok'):
    requests.post("https://x.scraperwiki.com/api/status", data={'type': type, 'message': message})
    print "%s: %s" % (type, message)

def getRecentTracks():
    # Before we start scraping, we want to find out where
    # to start from. Are there already tracks in the database?
    try:
        r = dt.execute("SELECT date FROM recenttracks WHERE user='%s' ORDER BY date DESC LIMIT 1" % user)
        # Try selecting the most recently scraped track from the database
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            # Aha! First time the scraper's run. create the table.
            dt.execute("CREATE TABLE recenttracks (date INT, user TEXT, track TEXT, track_mbid TEXT, track_url TEXT, track_image TEXT, artist TEXT, artist_mbid TEXT, album TEXT, album_mbid TEXT)")
            dt.create_index(['date','user'], 'recenttracks', unique=True)
            latest_scrobble = 0
        else:
            # Oh! Unexpected error. Pass it on.
            status("Unexpected SQL error: %s" % str(e), 'error')
            raise
    else:
        if r:
            # Great! We've got the most recently scraped track.
            latest_scrobble = int(r[0]['date'])
            t = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(latest_scrobble))
            status("Scraping %s's tracks since %s" %  (user, t))
        else:
            # Aha! The table exists but it's empty. Ignore.
            latest_scrobble = 0

    # This next bit is a little over-complicated because
    # we scrape *backwards*, from the past to the present

    # We first request the most recent page, to work out
    # how many pages there are in total. Then we start from
    # the end and work back to the present.

    # This way, if we bail halfway, we know we've *always* got
    # historical data, and we just have to scrape everything
    # *more recent* than the last row in our database.

    page = 1
    totalPages = 0

    while True:
        params = {
            'method': 'user.getrecenttracks',
            'user': user,
            'api_key': api_key,
            'to': now,
            'from': latest_scrobble,
            'limit': per_page,
            'page': page
        }
        req = requests.get('http://ws.audioscrobbler.com/2.0/', params=params)
        xml = req.text.replace(' encoding="utf-8"', '') # Stop lxml complaining about encodings
        dom = lxml.html.fromstring(xml)

        if dom.cssselect('error'):
            status("Unexpected error from Last.fm API: %s" % dom.cssselect('error')[0].text, 'error')
            raise Exception(dom.cssselect('error')[0].text)
            exit()

        if totalPages:
            # This is at least our second time round the While loop.
            # Parse scrobbles out of the API response, then decrement the counter.

            status("%s%% complete: scraping page %s of %s" % (totalPages/page, page, totalPages))
            recentTracks = []

            for item in dom.cssselect('track'):
                if item.get('nowplaying'):
                    # Skip 'now playing' tracks because
                    # they don't have a timestamp
                    continue
                recentTracks.append({
                    'date': item.cssselect('date')[0].get('uts'),
                    'user': user,
                    'track': item.cssselect('name')[0].text,
                    'track_mbid': item.cssselect('mbid')[0].text,
                    'track_url': item.cssselect('url')[0].text,
                    'track_mbid': item.cssselect('mbid')[0].text,
                    'track_artwork': item.cssselect('image[size="extralarge"]')[0].text,
                    'artist': item.cssselect('artist')[0].text,
                    'artist_mbid': item.cssselect('artist')[0].get('mbid'),
                    'album': item.cssselect('album')[0].text,
                    'album_mbid': item.cssselect('album')[0].get('mbid')
                })

            dt.upsert(recentTracks, "recenttracks")

            if page == 1:
                # Done! Break out of the While loop.
                break
            else:
                page -= 1

        else:
            # This is our first time round the While loop.
            # Set an upper bound for the total number of API calls we need to make,
            # then continue with the next loop.
            totalPages = int(dom.cssselect('recenttracks')[0].get('totalpages'))
            page = totalPages
            continue


def getInfo():
    # Save the user's metadata to a separate table.
    # We specifically don't store historical states here: just the latest info.

    dt.execute("CREATE TABLE IF NOT EXISTS info (date INT, user TEXT, id INT, realname TEXT, url TEXT, image TEXT, country TEXT, age INT, gender TEXT, subscriber INT, playcount INT, playlists INT, bootstrap INT, registered INT)")
    dt.create_index(['user'], 'info', unique=True)

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

    dt.upsert({
        'date': now,
        'user': user,
        'id': dom.cssselect('id')[0].text,
        'realname': dom.cssselect('realname')[0].text,
        'url': dom.cssselect('url')[0].text,
        'image': dom.cssselect('image[size="extralarge"]')[0].text,
        'country': dom.cssselect('country')[0].text,
        'age': dom.cssselect('age')[0].text,
        'gender': dom.cssselect('gender')[0].text,
        'subscriber': dom.cssselect('subscriber')[0].text,
        'playcount': dom.cssselect('playcount')[0].text,
        'playlists': dom.cssselect('playlists')[0].text,
        'bootstrap': dom.cssselect('bootstrap')[0].text,
        'registered': dom.cssselect('registered')[0].get('unixtime')
    }, "info")

main()
