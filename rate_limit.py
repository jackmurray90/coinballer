from flask import request, abort
from sqlalchemy.orm import Session
from db import engine, RateLimit
from time import time

def rate_limit():
  with Session(engine) as session:
    try:
      [rate_limit] = session.query(RateLimit).where(RateLimit.address == request.remote_addr)
    except:
      rate_limit = RateLimit(address=request.remote_addr, timestamp=0)
      session.add(rate_limit)
      session.commit()
    if rate_limit.timestamp + 0.5 > time():
      abort(429)
    rate_limit.timestamp = time()
    session.commit()

