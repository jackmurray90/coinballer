from maxminddb import open_database
from flask import request
from env import IP_WHITELIST

reader = open_database('geoip.mmdb')

def is_australia():
  if request.remote_addr in IP_WHITELIST: return False
  return reader.get(request.remote_addr)['country']['iso_code'] == 'AU'
