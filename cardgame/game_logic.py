import random
from enum import Enum, auto
from abc import ABC, abstractmethod
import uuid

class Faction(Enum):
    DEMOCRATS = auto()
    REPUBLICANS = auto()
    THIRD_PARTIES = auto()
    INTERNATIONAL = auto()

class Rarity(Enum):
    COMMON = auto()
    RARE = auto()
    EPIC = auto()

class Player:
    def __init__(self, name, owned_row):
        self.id = str(uuid.uuid4())
        self.name = name
        self.owned_row = owned_row  # This is either 1 or 2, representing the row they control on the board
        self.deck = Deck()  # The player's deck of cards
        self.hand = Hand()  # The cards currently in the player's hand
        self.retirement_area = RetirementArea()  # Area for cards that have been used
        self.board = None  # This will be a reference to the shared board
        self.hasPassed = False

    def draw_card(self):
        """Draw a card from the player's deck and add it to their hand."""
        card = self.deck.draw_card()
        if card:
            self.hand.add_card(card)

    def play_card(self, card, row=None, column=None):
        """Play a card from the player's hand."""
        if card in self.hand.cards:
            if isinstance(card, ActionCard):
                # Apply the effect of the Action card and retire the card
                card.play(self)
            elif isinstance(card, PoliticianCard):  # Assuming you have a PoliticianCard class
                # Politician cards must specify where they are being played on the board
                if row is not None and column is not None:
                    # Special cases can be handled here if needed
                    if self.board.add_card(row, column, card):
                        self.hand.remove_card(card)
                    else:
                        raise ValueError("Could not play card on the board.")
                else:
                    raise ValueError("Row and column must be specified for Politician cards.")
            else:
                raise ValueError("Unsupported card type.")
        else:
            raise ValueError("Card not in hand.")

    def retire_card(self, card):
        """Move a card from the player's hand to the retirement area."""
        if card in self.hand.cards:
            self.retirement_area.add_card(self.hand.remove_card(card))
        else:
            raise ValueError("Card not in hand.")

    def set_board(self, board):
        """Set the shared board for the player."""
        self.board = board

    def __repr__(self):
        return f"Player({self.name}, Row {self.owned_row})"


class CardZone:
    def __init__(self):
        self.cards = []

    def add_card(self, card):
        self.cards.append(card)

    def remove_card(self, card):
        if card in self.cards:
            self.cards.remove(card)
            return card
        return None

    def shuffle(self):

        random.shuffle(self.cards)

    def is_empty(self):
        return len(self.cards) == 0

    def count(self):
        return len(self.cards)

class Deck(CardZone):
    def __init__(self):
        super().__init__()

    def draw_card(self):
        """Remove the top card from the deck and return it."""
        return self.cards.pop() if not self.is_empty() else None

class Hand(CardZone):
    def __init__(self):
        super().__init__()

    def play_card(self, card_to_play):
        """Play a specified card from the hand."""
        for i, card in enumerate(self.cards):
            if card == card_to_play:
                return self.cards.pop(i)
        raise ValueError("Card not in hand.")


class RetirementArea(CardZone):
    def __init__(self):
        super().__init__()

    def add_card(self, card):
        """Add a card to the retirement area. Overrides to ensure no shuffling of discard pile."""
        super().add_card(card)

    def shuffle_back_into_deck(self, deck):
        """Shuffle all cards from the retirement area back into the deck."""
        deck.cards.extend(self.cards)
        self.cards.clear()
        deck.shuffle()

class Slot:
    def __init__(self, row, column):
        self.row = row
        self.column = column
        self.card = None
        # Set initial slot value based on the position
        if (row == 1 and 1 <= column <= 3) or (row == 2 and 7 <= column <= 9):
            self.value = 'Left'
        elif (row == 1 and 4 <= column <= 6) or (row == 2 and 4 <= column <= 6):
            self.value = 'Center'
        else:
            self.value = 'Right'

    def set_card(self, card):
        self.card = card

    def remove_card(self):
        self.card = None

    def is_empty(self):
        return self.card is None

    def change_slot_value(self, new_value):
        # The new_value should be one of 'Left', 'Center', 'Right'
        if new_value in ['Left', 'Center', 'Right']:
            self.value = new_value
        else:
            raise ValueError("Invalid slot value. Must be 'Left', 'Center', or 'Right'.")


class Board:
    def __init__(self):
        # Define slots in a dictionary where keys are tuples of (row, column)
        self.slots = {(row, col): Slot(row, col) for row in (1, 2) for col in range(1, 10)}

    def get_neighbors(self, row, column):
        # This will return all three neighbors of a slot: left, right, and opposite
        neighbors = self.get_friendly_neighbors(row, column)
        neighbors.extend(self.get_opponent_neighbors(row, column))
        return neighbors


    def get_friendly_neighbors(self, row, column):
        # This will return the friendly neighbors (same row)
        return [self.slots[(row, col)] for col in range(max(1, column - 1), min(10, column + 2)) if col != column]

    def get_opponent_neighbors(self, row, column):
        # This will return the opponent neighbors (opposite row)
        opposite_row = 3 - row
        return [self.slots[(opposite_row, column)]]

    def add_card(self, row, column, card):
        slot = self.slots.get((row, column))
        if slot and slot.is_empty():
            slot.set_card(card)
            return True
        return False

    def remove_card(self, row, column):
        slot = self.slots.get((row, column))
        if slot and not slot.is_empty():
            slot.remove_card()
            return True
        return False

    def change_slot_value(self, row, column, new_value):
        slot = self.slots.get((row, column))
        if slot:
            slot.change_slot_value(new_value)
            return True
        return False


class Card:
    def __init__(self, name, print_name, factions, rarity, image, description):
        self.name = name  # internal name for reference
        self.print_name = print_name  # name displayed on the card
        self.factions = factions  # list of factions the card belongs to
        self.rarity = rarity
        self.image = image  # URL to the card's image
        self.description = description  # description text for the card
        self.tags = []

    def add_tag(self, tag):
        if tag not in self.tags:
            self.tags.append(tag)

    def belongs_to_faction(self, faction):
        # Check if the card belongs to the given faction
        return faction in self.factions

    def __eq__(self, other):
        # Check if 'other' is the same instance as 'self'
        return id(self) == id(other)

    def __hash__(self):
        # This is necessary if you want to use the card as a key in a dictionary
        return hash(id(self))

    def __repr__(self):
        faction_names = ', '.join([faction.name for faction in self.factions])  # Assuming faction has a 'name' attribute
        return (f"<Card: {self.print_name}, Factions: {faction_names}, "
                f"Rarity: {self.rarity.name}, Image: {self.image}, "
                f"Description: {self.description}>")

class Effect(ABC):
    @abstractmethod
    def apply(self, *args, **kwargs):
        pass

class ActionCard(Card):
    def __init__(self, name, print_name, factions, rarity, image, description, effect):
        super().__init__(name, print_name, factions, rarity, image, description)
        self.effect = effect

    def play(self, player):
        if self in player.hand:
            self.effect.apply()
            player.hand.remove(self)
            player.retirement_area.append(self)
        else:
            print("Card is not in hand and cannot be played.")

class PoliticianCard(Card):
    def __init__(self, name, print_name, factions, rarity, image, description,
                 power, momentum, run_again, allowed_positions, operative,
                 on_play_effect=None, end_of_turn_effect=None, permanent_effect=None,
                 on_friendly_play_effect=None, on_opponent_play_effect=None):
        super().__init__(name, print_name, factions, rarity, image, description)
        self.power = power
        self.momentum = momentum
        self.run_again = run_again
        self.allowed_positions = allowed_positions
        self.operative = operative
        # Assigning strategies for effects
        self.on_play_effect = on_play_effect
        self.end_of_turn_effect = end_of_turn_effect
        self.permanent_effect = permanent_effect
        self.on_friendly_play_effect = on_friendly_play_effect
        self.on_opponent_play_effect = on_opponent_play_effect

    def play(self, game, position):
        if position in self.allowed_positions:
            game.board.place_card(position, self)
            if self.on_play_effect:
                self.on_play_effect.apply(game, self)
        else:
            print(f"This card cannot be played in {position} position.")

    def end_of_turn(self, game):
        if self.end_of_turn_effect:
            self.end_of_turn_effect.apply(game, self)

    def apply_permanent_effect(self, game):
        if self.permanent_effect:
            self.permanent_effect.apply(game, self)

    def on_friendly_play(self, game):
        if self.on_friendly_play_effect:
            self.on_friendly_play_effect.apply(game, self)

    def on_opponent_play(self, game):
        if self.on_opponent_play_effect:
            self.on_opponent_play_effect.apply(game, self)

    def retire(self, game):
        if self.power < 0:
            game.retire_card(self)

    def __repr__(self):
        return (super().__repr__() +
                f", Power: {self.power}, Momentum: {self.momentum}, "
                f"Run Again: {self.run_again}, Allowed Positions: {self.allowed_positions}, "
                f"Operative: {self.operative}")
class CardFactory:
    def create_card(self, card_type, *args, **kwargs):
        if card_type == "action":
            return ActionCard(*args, **kwargs)
        elif card_type == "politician":
            return PoliticianCard(*args, **kwargs)
        else:
            raise ValueError(f"Unknown card type: {card_type}")

class Game:
    def __init__(self, player1_name, player2_name):
        self.board = Board()
        self.players = {
            1: Player(player1_name, owned_row=1),
            2: Player(player2_name, owned_row=2)
        }
        self.active_player = random.choice([1, 2])
        self.round = 1
        self.turn = 1
        self.players[1].set_board(self.board)
        self.players[2].set_board(self.board)

    def start(self):
        # Game initialization logic such as shuffling decks, drawing starting hands, etc.
        pass

    def play_turn(self, player_id):
        pass

    def check_victory(self):
        pass

    def end_game(self):
        pass

