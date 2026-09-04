from flask import Flask, request, jsonify, session
from flask_cors import CORS
import cshogi
import random
from typing import Optional
import os
import threading
import uuid

app = Flask(__name__,
            static_folder='static',
            static_url_path='/static')
CORS(app)

FLAG = os.environ.get('FLAG', 'cIKaTA{ded_igraet_ne_po_pravilam}')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'local-game-session-key')

games = {}
games_lock = threading.RLock()

@app.route('/')
def serve_index():
    return app.send_static_file('index.html')

class Game:
    def __init__(self):
        # Black is the player. The browser offers only legal moves, while the
        # API deliberately accepts any syntactically valid USI move.
        self.board = cshogi.Board()
        self.game_over = False
        self.result = {}
        self.honest_moves = 0
        self.honest_move_limit = random.randint(4, 5)

    def get_state(self, terminal=None):
        if terminal is None:
            terminal = self.game_over
        try:
            legal_moves = [] if terminal else [cshogi.move_to_usi(move) for move in self.board.legal_moves]
        except Exception as e:
            print(f"Error getting legal moves: {e}")
            legal_moves = []
        current_player = cshogi.BLACK if self.board.turn == cshogi.BLACK else cshogi.WHITE
        try:
            black_hand = self.board.pieces_in_hand[cshogi.BLACK]
            white_hand = self.board.pieces_in_hand[cshogi.WHITE]
            captured_black = {i+1: count for i, count in enumerate(black_hand) if count > 0}
            captured_white = {i+1: count for i, count in enumerate(white_hand) if count > 0}
            captured_black = {i+1: count for i, count in enumerate(black_hand) if count > 0}
            captured_white = {i+1: count for i, count in enumerate(white_hand) if count > 0}
        except Exception as e:
            print(f"Error converting captured pieces: {e}")
            captured_black = {}
            captured_white = {}

        if terminal:
            is_game_over = True
            is_check = False
        else:
            is_game_over = self.board.is_game_over()
            is_check = self.board.is_check()

        state = {
            "sfen": self.board.sfen(),
            "legal_moves": legal_moves,
            "is_check": is_check,
            "is_checkmate": is_game_over and is_check,
            "is_stalemate": is_game_over and not is_check,
            "game_over": is_game_over,
            "turn": "black" if self.board.turn == cshogi.BLACK else "white",
            "captured_pieces": {
                "black": captured_black,
                "white": captured_white
            }
        }
        state.update(self.result)
        return state

    def finish(self, winner: str, victory: bool, message: str):
        self.game_over = True
        self.result = {
            "game_over": True,
            "is_checkmate": True,
            "is_stalemate": False,
            "winner": winner,
            "victory": victory,
            "message": message,
        }
        if victory:
            self.result["flag"] = FLAG

    def generate_drop_moves(self, color):
        drop_moves = []
        captured_list = self.board.pieces_in_hand[color]
        captured = {i+1: count for i, count in enumerate(captured_list) if count > 0}
        captured = {i+1: count for i, count in enumerate(captured_list) if count > 0}

        for piece_type, count in captured.items():
            if count > 0:
                piece_symbol = self.get_drop_piece_symbol(piece_type, color)
                test_squares = ['5e', '4d', '6f', '3c', '7g']
                for square in test_squares:
                    drop_moves.append(f"{piece_symbol}*{square}")

        return drop_moves

    def get_drop_piece_symbol(self, piece_type, color):
        symbols = {
            cshogi.PAWN: 'P',
            cshogi.LANCE: 'L',
            cshogi.KNIGHT: 'N',
            cshogi.SILVER: 'S',
            cshogi.GOLD: 'G',
            cshogi.BISHOP: 'B',
            cshogi.ROOK: 'R'
        }
        return symbols.get(piece_type, '?')

    def get_piece_type_from_symbol(self, symbol):
        symbol_to_type = {
            'P': cshogi.PAWN,
            'L': cshogi.LANCE,
            'N': cshogi.KNIGHT,
            'S': cshogi.SILVER,
            'G': cshogi.GOLD,
            'B': cshogi.BISHOP,
            'R': cshogi.ROOK
        }
        return symbol_to_type.get(symbol, 0)

    def is_square_empty(self, square):
        sfen = self.board.sfen()
        board_part = sfen.split(' ')[0]
        rows = board_part.split('/')
        file = square[0]
        rank = square[1]
        row_names = 'abcdefghi'
        col_names = '123456789'
        row_idx = row_names.index(rank)
        col_idx = col_names.index(file)
        if row_idx >= len(rows):
            return True
        row = rows[row_idx]
        col_pos = 0
        for char in row:
            if char.isdigit():
                col_pos += int(char)
            elif col_pos == col_idx:
                return False
            else:
                col_pos += 1
        return True

    def make_move(self, move_usi: str) -> bool:
        """Apply a move without checking its legality (the intended API bug)."""
        try:
            move = self.board.move_from_usi(move_usi)
            if move == 0:
                print(f"{move_usi=} {move=}")
                raise ValueError("Invalid move")
            self.board.push(move)

            return True
        except (ValueError, Exception) as e:
            print(f"Move error: {e}")
            return False

    def find_king_square(self, color) -> Optional[str]:
        """Find a king directly in SFEN without relying on move legality."""
        wanted = 'K' if color == cshogi.BLACK else 'k'
        files = '987654321'
        ranks = 'abcdefghi'

        for row_index, row in enumerate(self.board.sfen().split(' ')[0].split('/')):
            column = 0
            promoted = False
            for char in row:
                if char == '+':
                    promoted = True
                    continue
                if char.isdigit():
                    column += int(char)
                    continue
                if char == wanted and not promoted:
                    return f"{files[column]}{ranks[row_index]}"
                column += 1
                promoted = False
        return None

    def piece_at_square(self, square: str) -> Optional[str]:
        """Return the SFEN piece symbol located on a USI square."""
        if len(square) != 2 or square[0] not in '123456789' or square[1] not in 'abcdefghi':
            return None

        wanted_column = '987654321'.index(square[0])
        wanted_row = 'abcdefghi'.index(square[1])
        row = self.board.sfen().split(' ')[0].split('/')[wanted_row]
        column = 0
        promoted = False

        for char in row:
            if char == '+':
                promoted = True
                continue
            if char.isdigit():
                column += int(char)
                continue
            if column == wanted_column:
                return f"+{char}" if promoted else char
            column += 1
            promoted = False
        return None

    def captures_king(self, move_usi: str, king_color) -> bool:
        """Treat any ordinary move onto the enemy king as a king capture."""
        if not isinstance(move_usi, str) or len(move_usi) not in (4, 5) or '*' in move_usi:
            return False
        source_piece = self.piece_at_square(move_usi[:2])
        player_owns_piece = source_piece is not None and source_piece[-1].isupper()
        return player_owns_piece and move_usi[2:4] == self.find_king_square(king_color)

    def force_king_capture(self, attacker_color, victim_color) -> Optional[str]:
        """Describe the old man's illegal king capture without asking cshogi to validate it."""
        source = self.find_king_square(attacker_color)
        target = self.find_king_square(victim_color)
        if not source or not target:
            return None
        return f"{source}{target}"

    def find_immediate_mate(self) -> Optional[str]:
        """Prefer a legal mating reply before the old man resorts to cheating."""
        for move in list(self.board.legal_moves):
            self.board.push(move)
            is_mate = self.board.is_game_over() and self.board.is_check()
            self.board.pop()
            if is_mate:
                self.board.push(move)
                return cshogi.move_to_usi(move)
        return None

    def is_valid_drop(self, move, color):
        return True

    def ai_move(self) -> Optional[str]:
        legal_moves = list(self.board.legal_moves)
        if not legal_moves:
            return None
        best_move = None
        best_score = -float('inf')
        for move in legal_moves:
            self.board.push(move)
            score = self.evaluate_position()
            self.board.pop()

            if score > best_score:
                best_score = score
                best_move = move

        if best_move:
            self.board.push(best_move)
            return cshogi.move_to_usi(best_move)
        move = random.choice(legal_moves)
        self.board.push(move)
        return cshogi.move_to_usi(move)

    def evaluate_position(self) -> float:
        score = 0
        piece_values = {
            cshogi.PAWN: 1,
            cshogi.LANCE: 3,
            cshogi.KNIGHT: 4,
            cshogi.SILVER: 5,
            cshogi.GOLD: 6,
            cshogi.BISHOP: 8,
            cshogi.ROOK: 10,
            cshogi.KING: 100
        }
        white_hand = self.board.pieces_in_hand[cshogi.WHITE]
        black_hand = self.board.pieces_in_hand[cshogi.BLACK]
        white_captured_value = sum(count * piece_values.get(piece_type, 0)
                                  for piece_type, count in enumerate(white_hand) if count > 0)
        black_captured_value = sum(count * piece_values.get(piece_type, 0)
                                  for piece_type, count in enumerate(black_hand) if count > 0)
        score = white_captured_value - black_captured_value
        if self.board.is_check():
            score += 5
        if self.board.is_game_over() and self.board.is_check():
            score += 1000
        return score

def get_game_id():
    if 'game_id' not in session:
        session['game_id'] = str(uuid.uuid4())
    return session['game_id']


def get_game():
    game_id = get_game_id()
    with games_lock:
        if game_id not in games:
            games[game_id] = Game()
        return games[game_id]


@app.route("/game/state", methods=["GET"])
def get_game_state():
    return jsonify(get_game().get_state())

@app.route("/game/move", methods=["POST"])
def make_move():
    game = get_game()

    if game.game_over:
        return jsonify({"error": "Game is over"}), 400

    data = request.get_json()
    if not data or 'move' not in data:
        return jsonify({"error": "Move required"}), 400

    player_move = data['move']
    captures_white_king = game.captures_king(player_move, cshogi.WHITE)

    # Capturing a king is illegal in real shogi and is therefore never offered
    # by the frontend. The API intentionally recognizes it as the winning move.
    if captures_white_king:
        game.finish("black", True, "You captured the old man's king.")
        state = game.get_state()
        state["moves_made"] = [player_move]
        return jsonify(state)

    success = game.make_move(player_move)
    if not success:
        return jsonify({"error": "Invalid move"}), 400

    moves_made = [player_move]

    state = game.get_state()

    # A normal checkmate is a second valid victory condition.
    if state['is_checkmate']:
        game.finish("black", True, "Checkmate.")
        state = game.get_state()
        state["moves_made"] = moves_made
        return jsonify(state)

    # While he is not in check, the old man answers legally four or five times.
    if not state['is_check'] and game.honest_moves < game.honest_move_limit:
        old_man_move = game.ai_move()
        if old_man_move:
            game.honest_moves += 1
            moves_made.append(old_man_move)
            state = game.get_state()
            if state['is_checkmate']:
                game.finish("white", False, "The old man checkmated you.")
                state = game.get_state()
            state["moves_made"] = moves_made
            return jsonify(state)

    # A check, or an exhausted supply of honest replies, makes him cheat.
    old_man_move = game.force_king_capture(cshogi.WHITE, cshogi.BLACK)
    if old_man_move:
        moves_made.append(old_man_move)
    game.finish("white", False, "The old man cheated and captured your king.")
    state = game.get_state()
    state["moves_made"] = moves_made
    return jsonify(state)

@app.route("/game/new", methods=["POST"])
def new_game():
    game_id = get_game_id()
    with games_lock:
        games[game_id] = Game()
    return jsonify({"message": "New game started"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001, debug=True)
