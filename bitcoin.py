from sqlalchemy.orm import Session
from db import Game, Player, Height
from sqlalchemy import create_engine
from time import sleep
from env import DB
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from math import floor
from decimal import Decimal
from env import BITCOIN, DB
from http.client import CannotSendRequest
from bitcoinrpc.authproxy import JSONRPCException
from hashlib import sha256

MINCONF = 4


def get_height():
  while True:
    try:
      rpc = AuthServiceProxy(BITCOIN)
      return rpc.getblockcount() - MINCONF
    except:
      sleep(1)

def get_incoming_txs(height):
  while True:
    try:
      rpc = AuthServiceProxy(BITCOIN)
      txs = rpc.listsinceblock(rpc.getblockhash(height-1))
      incoming_txs = []
      for tx in txs['transactions']:
        if tx.get('category') == 'receive' and tx.get('blockheight') == height:
          incoming_txs.append((tx['address'], tx['amount']))
      return incoming_txs
    except:
      sleep(1)

def get_unconfirmed_transactions():
  while True:
    try:
      rpc = AuthServiceProxy(BITCOIN)
      txs = rpc.listsinceblock(rpc.getblockhash(get_height()))
      incoming_txs = {}
      for tx in txs['transactions']:
        if tx.get('category') == 'receive':
          if not tx.get('address') in incoming_txs:
            incoming_txs[tx.get('address')] = []
          incoming_txs[tx.get('address')].append({'amount': Decimal(tx.get('amount')), 'confirmations': tx.get('confirmations') or 0})
      return incoming_txs
    except Exception as e:
      print(e)
      sleep(1)

def send(address, amount):
  while True:
    try:
      rpc = AuthServiceProxy(BITCOIN)
      return rpc.send({address: amount})
    except JSONRPCException:
      return
    except:
      sleep(1)

def get_new_address():
  while True:
    try:
      rpc = AuthServiceProxy(BITCOIN)
      return rpc.getnewaddress()
    except:
      sleep(1)

def round_down(amount):
  return floor(amount * 10**8) / Decimal(10**8)

def validate_address(address):
  while True:
    try:
      rpc = AuthServiceProxy(BITCOIN)
      return rpc.validateaddress(address)['isvalid']
    except:
      sleep(1)

if __name__ == '__main__':
  with Session(create_engine(DB)) as session:
    while True:
      heightstore = session.query(Height).one()
      height = heightstore.height
      while height <= get_height():
        print("Processing height", height)
        for address, amount in get_incoming_txs(height):
          try:
            [player] = session.query(Player).where(Player.betting_address == address)
          except:
            continue
          if not player.game.finished:
            player.bet += amount
            [game] = session.query(Game).where(Game.id == player.game_id)
            if player.bet >= max([p.bet for p in game.players]):
              game.height = height
            game.pot += amount
            session.commit()
          else:
            amount -= Decimal('0.0001')
            if amount >= Decimal('0.00005460'):
              send(player.payout_address, amount)
        games = session.query(Game).where(Game.height == height - Game.length)
        for game in games:
          winners = []
          for player in game.players:
            if player.bet >= list(reversed(sorted([p.bet for p in game.players])))[game.winners-1]:
              winners.append(player)
          payout = round_down(sum([p.bet for p in game.players]) * Decimal('0.98') / len(winners))
          for winner in winners:
            send(winner.payout_address, payout)
          game.finished = True
        heightstore.height += 1
        height = heightstore.height
        session.commit()
      sleep(1)
