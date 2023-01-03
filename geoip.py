from maxminddb import open_database
from flask import request

reader = open_database('geoip.mmdb')

def is_australia():
  return reader.get(request.remote_addr)['country']['iso_code'] == 'AU'
