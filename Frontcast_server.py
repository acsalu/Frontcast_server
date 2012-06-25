 #coding=utf-8 
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

import pywapi

from xml.dom import minidom

from django.utils import simplejson
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template

def GeoCode(address, sensor = "true", **geo_args):
    geo_args.update({
        'address': address,
        'sensor': sensor,
        'region': 'Taiwan'
    })
    GEOCODE_BASE_URL = 'http://maps.googleapis.com/maps/api/geocode/json' 
    url = GEOCODE_BASE_URL + '?' + urllib.urlencode(geo_args)
    results = simplejson.load(urllib.urlopen(url))
    if results['status'] != 'OK':
        return ''
    #print (results['results'][0]['geometry']['location']['lat'])
    #print (results['results'][0]['geometry']['location']['lng'])
    geoCoordinate = results['results'][0]['geometry']['location']
    #return db.GeoPt(lat = geoCoordinate['lat'], lon = geoCoordinate['lng'])
    return {'lat' : geoCoordinate['lat'], 'lon' : geoCoordinate['lng']}

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
    latitude = db.FloatProperty()
    longitude = db.FloatProperty()
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
        frontcast.latitude = float(args[1])
        frontcast.longitude = float(args[2])
        frontcast.type = db.Category(args[3])
        frontcast.level = int(args[4])
        frontcast.time = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
        frontcast.put()
        return
    
    def GetFrontcasts(self, locationName, *args):
        if isinstance(locationName, unicode):
    	      locationName = locationName.encode('utf-8')
        center = GeoCode(locationName)
        if center == '':
            return ''
        
        bound = (center['lat'] + 0.1, center['lat'] - 0.1, center['lon'] - 0.1, center['lon'] + 0.1)
        query = db.GqlQuery("SELECT * FROM Frontcast WHERE 
              latitude <= :top AND latitude >= :bottom  ORDER BY latitude DESC LIMIT 200",
                             top = bound[0], bottom = bound[1])
        castList = []
        for cast in query:
            if cast.longitude >= bound[2] and cast.longitude <= bound[3]:
                castList.append(cast)
        return {'results': sorted(castList, key=lambda x: x.time, reverse=True)}
    
    def GetLocationName(self, lat, lon, sensor='true', **loc_args):
        loc_args.update({
            'latlng': lat+','+lon,
            'sensor': sensor
        })
        GEOCODE_BASE_URL = 'http://maps.googleapis.com/maps/api/geocode/json' 
        url = GEOCODE_BASE_URL + '?' + urllib.urlencode(loc_args)
        results = simplejson.load(urllib.urlopen(url))
        if results['status'] != 'OK':
           return ''
        locationInfo = results['results'][0]['address_components']
        for n in locationInfo:
            if n['types'][0] == 'colloquial_area':
                return n['short_name']
        for n in locationInfo:
            if n['types'][0] == 'natural_feature':
                return n['short_name']
        for n in locationInfo:
            if n['types'][0] == 'sublocality':
                return n['short_name']
        for n in locationInfo:
            if n['types'][0] == 'locality':
                return n['short_name']
        for n in locationInfo:
            if n['types'][0] == 'administrative_area_level_1':
                return n['short_name']
        for n in locationInfo:
            if n['types'][0] == 'administrative_area_level_2':
                return n['short_name']
        for n in locationInfo:
            if n['types'][0] == 'administrative_area_level_3':
                return n['short_name']
        return locationInfo[len(locationInfo)-1]['short_name']
        #results
        #locationName = results['results'][0]
        #return results

    def GetGoogleWeather(self, locationName, **googleweather_args):
        if isinstance(locationName, unicode):
    	      locationName = locationName.encode('utf-8')
        weatherInfo = pywapi.get_weather_from_google(locationName, hl='zh-TW')
        currentInfo = weatherInfo['current_conditions']
        return currentInfo


def main():
    util.run_wsgi_app(webapp.WSGIApplication(
        [(r"/", HomeHandler),
         (r"/rpc", RPCHandler)],
        debug = True))
    #GeoCode(address = "taipei", sensor = "true")

if __name__ == "__main__":
    main()
