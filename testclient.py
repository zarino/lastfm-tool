#!/usr/bin/env python
import sys
import json
import requests
import time

PER_REQUEST = 200

class LastFMClient(object):

    def __init__(self, key, username, callback):
        self.key = key
        self.callback = callback
        self.username = username
        self.retrieved = 0

    def recent_tracks(self):
        first_page = self._get_page(self.username)
        info = first_page['@attr']

        total = int(info['total'])
        print "There are a total of %d entries" % total
        pages = float(total) / float(PER_REQUEST)
        if total % PER_REQUEST != 0:
            pages += 1

        print "We will fetch %d pages" % pages

        items = first_page['track']
        self.retrieved += len(items)                
        self.callback(items)

        for page in xrange(2, int(pages)+1):
            print "Fetching page %d" % page
            items = self._get_page(page)['track']
            self.retrieved += len(items)
            self.callback(items)
            time.sleep(1)

        print "We retrieved %d of %d" % (self.retrieved, total)

    def _build_url(self, page):
        return "http://ws.audioscrobbler.com/2.0/?page={p}&limit={l}&method=user.getrecenttracks&user={u}&api_key={k}&format=json".format(k=self.key,
            u=self.username,l=PER_REQUEST,p=page)

    def _get_page(self, page=1):
        url = self._build_url(page)
        r = requests.get(url)
        try:
            data = json.loads(r.content)
        except:
            print r.status_code, r.content
        return data['recenttracks']

def print_info(items):
    print "    Received %d items" % len(items)
    #print "++++++++ %s by %s" % (item['album']['#text'], item['artist']['#text'])


if __name__ == "__main__":
    l = LastFMClient("YOUR_API_KEY", sys.argv[1], print_info)
    l.recent_tracks()

