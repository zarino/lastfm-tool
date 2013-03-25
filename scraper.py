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

now = int(time.time())
dt = dumptruck.DumpTruck(dbname="scraperwiki.sqlite")

def main():
    status("Scraping %s's history..." % user)
    getInfo()
    getRecentTracks()

def status(message, type='ok'):
    requests.post("https://x.scraperwiki.com/api/status", data={'type': type, 'message': message})
    print "%s: %s" % (type, message)

def getLatestScrobble():
    # Before we start scraping, we want to find out where
    # to start from. Are there already tracks in the database?
    try:
        r = dt.execute("SELECT date FROM recenttracks WHERE user='%s' ORDER BY date DESC LIMIT 1" % user)
        # Try selecting the most recently scraped track from the database
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            # Aha! First time the scraper's run. create the table.
            dt.execute("CREATE TABLE recenttracks (date INT, user TEXT, track TEXT, track_mbid TEXT, track_url TEXT, track_artwork TEXT, artist TEXT, artist_mbid TEXT, album TEXT, album_mbid TEXT)")
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
        else:
            # Aha! The table exists but it's empty. Ignore.
            latest_scrobble = 0

    return latest_scrobble

def getRecentTracks():
    while True:
        # We scrape *backwards*, from the past to the present - where are we up to?
	latest_scrobble = getLatestScrobble()
	t = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(latest_scrobble))
	status("Scraping %s's tracks since %s ..." %  (user, t))

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
	# print "... got %d scrobbles" % (len(recentTracks))
	dt.upsert(recentTracks, "recenttracks")

	if len(recentTracks) == 0:
	    status("Up to date")
	    break

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
