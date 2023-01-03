from flask import Flask, redirect, request, render_template, make_response
from db import Game, Player, RateLimit, engine
from sqlalchemy.orm import Session
from rate_limit import rate_limit
from bitcoin import get_new_address, get_height, validate_address
from geoip import is_australia

app = Flask(__name__)

@app.route('/')
def index():
  rate_limit()
  if is_australia(): return redirect('/australia')
  with Session(engine) as session:
    games = session.query(Game).order_by(Game.id.desc()).all()
    games = [{
      'game_id': game.id,
      'pot': game.pot,
      'deadline': game.height + game.length if not game.finished else None
      } for game in games]
    return render_template('index.html', games=games)

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
  if not request.form.get('addresses'):
    return render_template('new_game.html')
  addresses = [address for address in request.form['addresses'].strip().split()]
  for address in addresses:
    if len([a for a in addresses if a == address]) > 1:
      return 'Player addresses must be unique'
    if not validate_address(address):
      return 'Invalid bitcoin address'
  try:
    length = int(request.form['length'])
    if length < 1 or length > 525600:
      raise Exception
  except:
    return 'Invalid length'
  try:
    winners = int(request.form['winners'])
    if winners < 1 or winners > len(addresses):
      raise Exception
  except:
    return 'Invalid n'
  with Session(engine) as session:
    game = Game(height=get_height(), winners=winners, length=length, finished=False)
    session.add(game)
    for address in addresses:
      session.add(Player(game=game, betting_address=get_new_address(), payout_address=address, bet=0))
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
    players = [{
        'betting_address': player.betting_address,
        'payout_address': player.payout_address,
        'bet': player.bet
      } for player in game.players]
    deadline = game.height + game.length if not game.finished else None
    return render_template('game.html', game_id=game.id, confirmed_height=get_height(), winners=game.winners, length=game.length, deadline=deadline, players=players)

@app.route('/australia')
def australia():
  return render_template('australia.html')
