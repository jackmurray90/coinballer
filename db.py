from sqlalchemy import Integer, Boolean, Numeric, Column, String, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, relationship
from env import DB

Base = declarative_base()

class Game(Base):
  __tablename__ = 'games'

  id = Column(Integer, primary_key=True)
  height = Column(Integer)
  players = relationship('Player')
  length = Column(Integer)
  finished = Column(Boolean)
  pot = Column(Numeric(16, 8), default=0)

class Player(Base):
  __tablename__ = 'players'

  id = Column(Integer, primary_key=True)
  game_id = Column(Integer, ForeignKey('games.id'))
  betting_address = Column(String)
  payout_address = Column(String)
  bet = Column(Numeric(16, 8))
  game = relationship('Game', back_populates='players')

class Height(Base):
  __tablename__ = 'height'

  height = Column(Integer, primary_key=True)

class RateLimit(Base):
  __tablename__ = 'ratelimit'

  address = Column(String, primary_key=True)
  timestamp = Column(Numeric(17, 5))

engine = create_engine(DB)
