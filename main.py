import cgi
import datetime
import urllib
import webapp2
import md5
import base64

from datetime import date
from datetime import datetime
from google.appengine.ext import db
from google.appengine.api import users

class AppUser(db.Model):
  name = db.StringProperty()
  password = db.StringProperty()
  
class Expence(db.Model):
  amount = db.FloatProperty()
  type = db.StringProperty()
  datetime = db.DateTimeProperty(auto_now_add=True)

  def to_tuple(self):
    return (amount, type, datetime)
  
class Kind(db.Model):
  type = db.StringProperty()
  freq = db.IntegerProperty()

## Fetch Expences from particular mont - current month as default
def fetchExpencesFromParticularMonth(now = datetime.now()):
  ## Calculate given month begin and end
  beginOfMonth = datetime(now.year, now.month, 1)
  beginOfNextMonth = 0
  if(beginOfMonth.month == 12):
    beginOfNextMonth = datetime(now.year + 1, 1, 1,0,0,0)
  else:
    beginOfNextMonth = datetime(now.year, now.month+1,1,0,0,0)

  ## Fetch all from given month month
  q = Expence.all()
  q.filter('datetime >=', beginOfMonth)
  q.filter('datetime <', beginOfNextMonth)
  expences = q.fetch(99999)
  return expences;

def sumExpences(now = datetime.now()):
  expences = fetchExpencesFromParticularMonth(now);
  
  ## Sum all expences from current month
  summary = 0
  for expence in expences:
    summary += expence.amount
  return summary

def estimate(currentSum):
  day = date.today().day
  dailyExpence = currentSum/day
  estimatedMonthlyExpence = dailyExpence * 30
  return estimatedMonthlyExpence
  
def basicAuth(request, response):
  try:
    key = request.headers['Authorization']
    key = key[6:]
    secret = base64.b64decode(key)
    userpassPair = secret.split(":")
    secretPass = md5.new(userpassPair[1]).hexdigest()
    q = AppUser.all()
    q.filter("name =", userpassPair[0])
    users = q.fetch(1)
    for user in users:
      if(user.password == secretPass):
        return user
      else:
        raise Error
    raise Error
  except:
    response.set_status(401, message = "Authorization Required")
    headers = response.headers
    headers.add_header("WWW-Authenticate", "Basic realm=\"Secure Area\"")
    raise Error

class MainPage(webapp2.RequestHandler):
  def get(self):
    try:
      basicAuth(self.request, self.response)
      
      q = Kind.all()
      q.order("-freq")
      kinds = q.fetch(9999)
      
      self.response.headers['Content-Type'] = 'text/html'
      self.response.out.write('<html><body>')
      self.response.out.write("""
      <form action="/add" method="post">
          <p>Add expence</p>
          <p>Amount: <input type="text" name="amount" /></p>
          <p>Type: <select name="type">""")
      
      for kind in kinds:
        self.response.out.write("<option>" + kind.type + "</option>")
          
      self.response.out.write("""</select></p>
          <p><input type="submit" value="Add" /></p>
      </form>
      """)

      currentExpences = sumExpences()
      self.response.out.write("<p>Current expences: " + str(currentExpences) + "</p>")
      self.response.out.write("<p>Estimated monthly: " + str(estimate(currentExpences)) + "</p>")
      self.response.out.write("""<p>
      <a href="/status">Summary</a>
      <a href="/status?csv=true">CSV</a>
      <a href="/kind">New expence kind</a>
      </p>
      """)
    except:
      self.response.out.write("Unauthorized!")
      


class AddHandler(webapp2.RequestHandler):
  def post(self):
    try:
      basicAuth(self.request, self.response)
      expenceType = self.request.get('type')
      expenceAmount = float(self.request.get('amount'))
      
      expence = Expence(amount = expenceAmount, type = expenceType)
      self.response.write("ok")
      self.response.write(expence.amount)
      expence.put()
      
      q = Kind.all()
      q.filter("type =", expenceType)
      list = q.fetch(1)
      for kind in list:
        kind.freq = kind.freq + 1
        kind.put()
    except:
      self.response.out.write("Unauthorized!")

    

class KindHandler(webapp2.RequestHandler):
  def post(self):
    try: 
      basicAuth(self.request, self.response)
      new_kind = Kind(type = self.request.get('kindType'), freq = 0)
      new_kind.put()
    except:
      self.response.out.write("Unauthorized!")
   
  def get(self):
    try:
      basicAuth(self.request, self.response)
      self.response.write("""
      <p>Add new kind of expence</p>
      <form action = "/kind" method = "POST">
        <p><input type="text" name="kindType" /></p>
        <p><input type="submit" value="Add new kind" /></p>
      </form>
      """)
    except:
      self.response.out.write("Unauthorized!")

class Status(webapp2.RequestHandler):
  def get(self):
    try:
      basicAuth(self.request, self.response)
      q = Kind.all()
      kinds = q.fetch(999)

      ## try to get CSV parameter to decide which format should be printed
      isCSV = self.request.get("csv")

      for kind in kinds:
        q = Expence.all()
        q.filter("type =", kind.type)
        expencesOfOneKind = q.fetch(9999)
        summary = 0
      
        for exp in expencesOfOneKind:
          summary += exp.amount


        if(isCSV == "true"):
          self.response.out.write(kind.type + ";" + str(summary) + "\n")
        else:
          self.response.out.write("<p>" + kind.type + ": " + str(summary) + "</p>")
    except:
      self.response.out.write("Unauthorized!")

## Request mapping
app = webapp2.WSGIApplication([('/', MainPage), 
                               ('/add', AddHandler),
                               ('/kind', KindHandler),
                               ('/status', Status)
                               ],
                              debug=True)

