#!/usr/bin/env python

import requests
import lxml.html
import sqlite3
import dumptruck
import time

requests.defaults.defaults['max_retries'] = 5

# Settings
user = 'zarino'
api_key = '12b5aaf2b0f27b4b9402b391c956a88a'
per_page = 200

def getRecentTracks():
    print "Scraping %s.getRecentTracks..." % user

    # Before we start scraping, we want to find out where
    # to start from. Are there already tracks in the database?

    try:
        r = dt.execute("SELECT date FROM recenttracks WHERE user='%s' ORDER BY date DESC LIMIT 1" % user)
        # Try selecting the most recently scraped track from the database
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            # Aha! First time the scraper's run. create the table.
            print '  First run: Creating database table'
            dt.execute("CREATE TABLE recenttracks (date INT, user TEXT, track TEXT, track_mbid TEXT, track_url TEXT, track_image TEXT, artist TEXT, artist_mbid TEXT, album TEXT, album_mbid TEXT)")
            dt.create_index(['date','user'], 'recenttracks', unique=True)
            latest_scrobble = 0
            print "  First run: Scraping entire history"
        else:
            # Oh! Unexpected error. Pass it on.
            raise
    else:
        if r:
            # Great! We've got the most recently scraped track.
            latest_scrobble = int(r[0]['date'])
            t = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(latest_scrobble))
            print "  Scraping %s's tracks since %s" %  (user, t)
        else:
            # Aha! The table exists but it's empty. Ignore.
            latest_scrobble = 0
            print "  First run for %s: Scraping entire history" % user

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
            raise Exception(dom.cssselect('error')[0].text)
            exit()

        if totalPages:
            print '  Scraping page %s of %s' % (page, totalPages)
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
            min = time.strftime('%Y-%m-%d %H:%I', time.gmtime(float(recentTracks[0]['date'])))
            max = time.strftime('%Y-%m-%d %H:%I', time.gmtime(float(recentTracks[-1]['date'])))
            print '  Saved %s scrobbles: %s to %s' % (len(recentTracks), max, min)

            if page == 1:
                print '  All done!'
                break
            else:
                page -= 1

        else:
            totalPages = int(dom.cssselect('recenttracks')[0].get('totalpages'))
            print '  %s pages to scrape' % totalPages
            page = totalPages
            continue


now = int(time.time())
dt = dumptruck.DumpTruck(dbname="lastfm.sqlite")

print '----- START %s -----' % time.strftime('%Y-%m-%d %H:%I:%S', time.gmtime())

getRecentTracks()

print '----- END %s -----' % time.strftime('%Y-%m-%d %H:%I:%S', time.gmtime())