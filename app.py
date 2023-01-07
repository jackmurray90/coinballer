from flask import Flask, redirect, request, render_template, make_response
from db import Game, Player, RateLimit, engine
from sqlalchemy.orm import Session
from rate_limit import rate_limit
from bitcoin import get_new_address, get_height, validate_address, round_down, get_unconfirmed_transactions, get_real_height
from geoip import is_australia
from decimal import Decimal
from math import floor

app = Flask(__name__)

@app.template_filter()
def js_string(s):
  return str(s).replace('"', '\\"').replace("'", "\\'").replace('\\', '\\\\')

@app.template_filter()
def format_decimal(d, decimal_places):
  digit = Decimal('10')
  while digit <= d:
    digit *= 10
  result = ''
  while decimal_places:
    result += str(floor(d % digit * 10 / digit))
    digit /= 10
    if digit == 1:
      result += '.'
    if digit < 1:
      decimal_places -= 1
  return result

@app.route('/')
def index():
  rate_limit()
  if is_australia(): return redirect('/australia')
  with Session(engine) as session:
    games = session.query(Game).where(Game.finished == False).order_by(Game.id.desc()).all()
    games = [{
      'game_id': game.id,
      'pot': game.pot,
      'deadline': game.height + game.length if not game.finished else None
      } for game in games]
    return render_template('index.html', games=games)

@app.route('/games')
def games():
  rate_limit()
  if is_australia(): return redirect('/australia')
  with Session(engine) as session:
    games = session.query(Game).where((Game.finished == True) & (Game.pot != 0)).order_by(Game.id.desc()).all()
    games = [{
      'game_id': game.id,
      'pot': game.pot
      } for game in games]
    return render_template('games.html', games=games)

@app.route('/rules')
def rules():
  rate_limit()
  if is_australia(): return redirect('/australia')
  return render_template('rules.html')

@app.route('/about')
def about():
  rate_limit()
  if is_australia(): return redirect('/australia')
  return render_template('about.html')

@app.route('/new_game', methods=['GET', 'POST'])
def new_game():
  rate_limit()
  if is_australia(): return redirect('/australia')
  if not request.form.getlist('username'):
    return render_template('new_game.html', length=144, winners=1, players=[('', ''), ('', '')])
  usernames = [u.strip() for u in request.form.getlist('username')]
  addresses = [a.strip() for a in request.form.getlist('address')]
  if len(usernames) != len(addresses):
    return redirect('/new_game')
  errors = []
  for address in addresses:
    if len([a for a in addresses if a == address]) > 1:
      errors.append('Player addresses must be unique.')
      break
  for address in addresses:
    if not validate_address(address):
      errors.append('Invalid Bitcoin address: ' + address)
  for username in usernames:
    if len(username) > 35:
      errors.append(username + ' is an invalid username. Maximum length is 35 characters.')
  try:
    length = int(request.form['length'])
    if length < 12 or length > 432:
      raise Exception
  except:
    errors.append('An invalid length was provided. Length must be between 12 and 432 blocks.')
  try:
    winners = int(request.form['winners'])
    if winners < 1 or winners >= len(addresses):
      raise Exception
  except:
    errors.append('An invalid number of winners was provided. It must be between 1 and one less than the number of players.')
  if errors:
    return render_template('new_game.html',
                           length=request.form['length'],
                           winners=request.form['winners'],
                           players=zip(usernames, addresses),
                           errors=errors)
  with Session(engine) as session:
    game = Game(height=get_height(), winners=winners, length=length, finished=False)
    session.add(game)
    for username, address in zip(usernames, addresses):
      session.add(Player(game=game, username=username, betting_address=get_new_address(), payout_address=address, bet=0))
    session.commit()
    return redirect('/game/%d' % game.id)

@app.route('/game/<game_id>')
def game(game_id):
  if is_australia(): return redirect('/australia')
  with Session(engine) as session:
    try:
      [game] = session.query(Game).where(Game.id == game_id)
    except:
      return 'Game not found.'
    unconfirmed_transactions = get_unconfirmed_transactions()
    def get_unconfirmed_bet(address):
      if address in unconfirmed_transactions:
        return max([tx['amount'] for tx in unconfirmed_transactions[address]])
      return Decimal(0)
    players = [{
      'username': player.username,
      'betting_address': player.betting_address,
      'payout_address': player.payout_address,
      'bet': player.bet,
      'unconfirmed_bet': get_unconfirmed_bet(player.betting_address)
      } for player in game.players]
    pot = sum([p.bet for p in game.players])
    countdown = game.height + game.length - get_real_height()
    winners = []
    for player in game.players:
      if player.bet >= list(reversed(sorted([p.bet for p in game.players])))[game.winners-1]:
        winners.append(player)
    payout = round_down(sum([p.bet for p in game.players]) * Decimal('0.98') / len(winners))
    if countdown < 0:
      countdown = 'Game is finished'
    return render_template('game.html', game_id=game.id, winners=game.winners, length=game.length, countdown=countdown, players=players, payout=payout)

@app.route('/australia')
def australia():
  return render_template('australia.html')
