import datetime
import base64
import cgi
import Cookie
import email.utils
import hashlib
import hmac
import logging
import os.path
import time
import urllib
import wsgiref.handlers
import json

import sys
import urlparse

from django.utils import simplejson
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template

def GeoCode(address, sensor = "true", **geo_args):
    geo_args.update({
        'address': address,
        'sensor': sensor  
    })
    GEOCODE_BASE_URL = 'http://maps.googleapis.com/maps/api/geocode/json' 
    url = GEOCODE_BASE_URL + '?' + urllib.urlencode(geo_args)
    results = simplejson.load(urllib.urlopen(url))
    #print simplejson.dumps([s['formatted_address'] for s in results['results']], indent=2)
    #print (results['results'][0]['geometry']['location']['lat'])
    #print (results['results'][0]['geometry']['location']['lng'])
    geoCoordinate = results['results'][0]['geometry']['location']
    print (geoCoordinate['lat'])
    print (geoCoordinate['lng'])
    return db.GeoPt(lat = geoCoordinate['lat'], lon = geoCoordinate['lng'])

class HomeHandler(webapp.RequestHandler):
    def get(self):
        path = os.path.join(os.path.dirname(__file__), "index.html")
        frontcast_query = Frontcast.all().order('-time')
        theFrontcasts = frontcast_query.fetch(1000)
        args = dict(frontcasts = theFrontcasts)
        self.response.out.write(template.render(path, args))

class Frontcast(db.Model):
    user_id = db.StringProperty()
    time = db.DateTimeProperty(auto_now_add=False)
    location = db.GeoPtProperty()
    type = db.CategoryProperty()
    level = db.IntegerProperty()


class RPCHandler(webapp.RequestHandler):
    """ Allows the functions defined in the RPCMethods class to be RPCed."""
    def __init__(self):
        webapp.RequestHandler.__init__(self)
        self.methods = RPCMethods()

    def post(self):
        args = simplejson.loads(self.request.body)
        func, args = args[0], args[1:]

        if func[0] == '_':
            self.error(403) # access denied
            return

        func = getattr(self.methods, func, None)
        if not func:
            self.error(404) # file not found
            return

        result = func(*args)
        self.response.out.write(cgi.escape(json.encode(result)))
        

class RPCMethods():
    """ Defines the methods that can be RPCed.
    NOTE: Do not allow remote callers access to private/protected "_*" methods.
    """

    def ReportFrontcast(self, *args):
        frontcast = Frontcast()
        frontcast.user_id = args[0]
        frontcast.location = db.GeoPt(lat = float(args[1]), lon = float(args[2]))
        frontcast.type = db.Category(args[3])
        frontcast.level = int(args[4])
        frontcast.time = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
        frontcast.put()
        print (frontcast.location.lat)
        return
    
    def GetFrontcasts(self, locationName, *args):
        center = GeoCode(locationName)
        bound = (center.lat + 0.1, center.lat - 0.1, center.lon - 0.1, center.lon + 0.1)

        query = db.GqlQuery("SELECT * FROM Frontcast WHERE location.lat <= :top AND location.lat >= :bottom AND location.lon >= :left AND location.lon <= :right ORDER BY time DESC LIMIT 100",
                             top = center[0], bottom = center[1], left = center[2], right = center[3])
        return query
    
    """
    def GetGreetings(self, current_user, *args):
        greetings_query = Greeting.all().order('-date')
        greetings = greetings_query.fetch(1000)
        return greetings

    def PostGreeting(self, current_user, *args):
        
        greeting = Greeting()
        if current_user:
            greeting.user_id = current_user.id
            greeting.user_name = current_user.name
        greeting.content = args[0]
        greeting.date = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
        greeting.put()
        return
    """
def main():
    util.run_wsgi_app(webapp.WSGIApplication(
        [(r"/", HomeHandler),
         (r"/rpc", RPCHandler)],
        debug = True))
    #GeoCode(address = "taipei", sensor = "true")

if __name__ == "__main__":
    main()
