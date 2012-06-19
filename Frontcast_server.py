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

from django.utils import simplejson
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template

class HomeHandler(webapp.RequestHandler):
    def get(self):
        path = os.path.join(os.path.dirname(__file__), "index.html")
        frontcast_query = Frontcast.all().order('-time')
        theFrontcasts = frontcast_query.fetch(1000)
        args = dict(frontcasts = theFrontcasts)
        self.response.out.write(template.render(path, args))


class Frontcast(db.Model):
    user_id = db.StringProperty()
    time = db.DateTimeProperty(auto_now_add=True)
    location = db.GeoPtProperty()
    type = db.CategoryProperty()
    level = db.FloatProperty()

class RPCHandler(webapp.RequestHandler):
    """ Allows the functions defined in the RPCMethods class to be RPCed."""
    def __init__(self):
        BaseHandler.__init__(self)
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

if __name__ == "__main__":
    main()
