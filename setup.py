from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from db import Base, Height
from env import DB
from bitcoin import get_height

if __name__ == '__main__':
  engine = create_engine(DB)
  Base.metadata.create_all(engine)
  with Session(engine) as session:
    session.add(Height(height=get_height()))
    session.commit()
