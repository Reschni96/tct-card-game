# card_app.py
from flask import Blueprint, render_template, url_for, redirect
import uuid

card_app = Blueprint('cardgame', __name__, template_folder='templates')

# In-memory storage for game states
game_states = {}

@card_app.route('/cardgame')
def cardgame():
    return render_template('cardgame.html')

@card_app.route('/create_game', methods=['POST'])
def create_game():
    game_id = str(uuid.uuid4())
    game_states[game_id] = {'players': [], 'square_color': 'red', 'current_turn': None}
    return redirect(url_for('.play_game', game_id=game_id))

@card_app.route('/play_game/<game_id>')
def play_game(game_id):
    if game_id not in game_states:
        return "Game not found", 404
    game_state = game_states[game_id]
    return render_template('play_game.html', game_id=game_id, square_color=game_state['square_color'])


@card_app.route('/game_board')
def game_board():
    return render_template('game_board.html')

