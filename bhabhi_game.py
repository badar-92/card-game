"""
bhabhi_game_fixed.py
Full game with strict follow-suit enforcement and dimmed unplayable cards.

Rules implemented:
- When a trick is led, players who HAVE the led suit can only play that suit.
  Other suits are dimmed and clicking them does nothing (with a short warning).
- If a player does NOT have the led suit, they may play any suit (this is a legit tochoo/thula).
  When that happens the trick is resolved as tochoo: the highest card of the led suit among played cards
  picks up the whole trick into their hand.
- If everyone follows the suit, the highest of the led suit wins and the trick cards are discarded.
- Cards overlap with at least half visible and clicks target visible portions correctly.
- CPU uses the same legality rules (will follow if it can; otherwise will play any card).
"""

import pygame
import sys
import random
import math
import time

# ---------------- Configuration ----------------
SCREEN_WIDTH = 1100
SCREEN_HEIGHT = 700
FPS = 30

CARD_W = 80
CARD_H = 120
# half visible overlap: step = CARD_W // 2 => CARD_GAP = step - CARD_W = -CARD_W//2
CARD_GAP = -40  # overlap so at least half of each card visible

# Animation & sound config (place your sound file name here)
CARD_PLAY_SOUND_FILE = "mixkit-poker-card-flick-2002.wav"  # <- put your sound file name here
TOCHOO_SOUND_FILE = "mixkit-classic-click-1117.wav"  # <- put your tochoo sound file name here
CARD_ANIM_DURATION_MS = 350              # how long card fly takes (milliseconds)

# Colors
WHITE = (255, 255, 255)
BLACK = (10, 10, 10)
GREEN = (18, 120, 20)
GRAY = (200, 200, 200)
DARK_GRAY = (50, 50, 50)
RED = (200, 30, 30)
BLUE = (30, 80, 200)
YELLOW = (230, 200, 50)
LIGHT_BLUE = (100, 180, 255)
LIGHT_RED = (255, 100, 100)
WARNING_COLOR = (255, 220, 110)

# Ranks and suits
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
RANK_VALUE = {r: i+2 for i, r in enumerate(RANKS)}  # 2 -> 2 ... A -> 14
SUITS = ['♠', '♥', '♦', '♣']  # use text suits
SUIT_NAMES = {'♠': 'spades', '♥': 'hearts', '♦': 'diamonds', '♣': 'clubs'}

# ---------------- Helper classes ----------------

class Card:
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit
        self.value = RANK_VALUE[rank]

    def __repr__(self):
        return f"{self.rank}{self.suit}"

    def draw(self, surf, x, y, face=True, selectable=False, highlight=False, disabled=False):
        rect = pygame.Rect(x, y, CARD_W, CARD_H)
        # background
        # ALWAYS draw normal background; we'll overlay a dim surface if disabled so the card remains visible.
        pygame.draw.rect(surf, WHITE if face else DARK_GRAY, rect, border_radius=6)
        pygame.draw.rect(surf, BLACK, rect, 2, border_radius=6)

        if face:
            color = RED if self.suit in ['♥', '♦'] else BLACK
            # (removed forcing color to DARK_GRAY when disabled so ranks/suits remain readable under overlay)
            font = pygame.font.SysFont('arial', 20, bold=True)
            rsurf = font.render(self.rank, True, color)
            ssurf = font.render(self.suit, True, color)
            surf.blit(rsurf, (x+6, y+6))
            surf.blit(ssurf, (x+CARD_W-22, y+6))
            bigfont = pygame.font.SysFont('arial', 36, bold=True)
            big = bigfont.render(self.suit, True, color)
            surf.blit(big, (x + CARD_W//2 - big.get_width()//2, y + CARD_H//2 - big.get_height()//2))
            if selectable and not disabled:
                pygame.draw.rect(surf, BLUE, rect, 3, border_radius=6)
            if highlight:
                pygame.draw.rect(surf, YELLOW, rect, 3, border_radius=6)
        else:
            pygame.draw.rect(surf, BLACK, rect, 2, border_radius=6)
            inner = rect.inflate(-10, -18)
            pygame.draw.rect(surf, (50, 50, 120), inner, border_radius=5)
            for i in range(3):
                pygame.draw.line(surf, (100, 100, 200), (x+12, y+18 + i*30), (x+CARD_W-12, y+18 + i*30), 2)

        # --- DIM overlay if disabled (semi-transparent gray so details remain visible) ---
        if disabled:
            overlay = pygame.Surface((CARD_W, CARD_H), pygame.SRCALPHA)
            # RGBA: gray with alpha (0 transparent ... 255 opaque). Tune alpha to taste (120-160 looks good).
            overlay.fill((80, 80, 80, 140))
            surf.blit(overlay, (x, y))

# ---------------- Deck and players ----------------

def full_deck():
    deck = [Card(rank, suit) for suit in SUITS for rank in RANKS]
    return deck

class Player:
    def __init__(self, name, is_human=True):
        self.name = name
        self.is_human = is_human
        self.hand = []
        self.is_active = True  # in-game (not finished)
        self.finished_rank = None
        # NEW: flags to control behavior after picking up a trick
        self.just_picked_up = False
        self.avoid_suit = None

    def card_count(self):
        return len(self.hand)

    def sort_hand(self):
        # Sort by suit then value for nicer display
        self.hand.sort(key=lambda c: (SUITS.index(c.suit), c.value))

    def has_suit(self, suit):
        return any(c.suit == suit for c in self.hand)

    def play_card(self, card_index):
        return self.hand.pop(card_index)

    def pick_up(self, cards):
        # cards: list of Card
        self.hand.extend(cards)
        self.sort_hand()

# ---------------- UI components ----------------

class Button:
    def __init__(self, rect, text, onclick=None, font_size=20):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.onclick = onclick
        self.font = pygame.font.SysFont('arial', font_size, bold=True)

    def draw(self, surf, hover=False):
        color = YELLOW if hover else GRAY
        pygame.draw.rect(surf, color, self.rect, border_radius=6)
        pygame.draw.rect(surf, BLACK, self.rect, 2, border_radius=6)
        tsurf = self.font.render(self.text, True, BLACK)
        surf.blit(tsurf, (self.rect.centerx - tsurf.get_width()/2, self.rect.centery - tsurf.get_height()/2))

    def check_click(self, pos):
        if self.rect.collidepoint(pos) and self.onclick:
            self.onclick()

class ScrollableHand:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.scroll_x = 0
        self.max_scroll = 0
        self.scroll_speed = 20
        
    def update_scroll_limit(self, card_count):
        total_width = card_count * (CARD_W + CARD_GAP) - CARD_GAP
        self.max_scroll = max(0, total_width - self.width)
        
    def scroll(self, direction):
        self.scroll_x = max(0, min(self.max_scroll, self.scroll_x + direction * self.scroll_speed))
        
    def get_card_position(self, index):
        x = self.x + index * (CARD_W + CARD_GAP) - self.scroll_x
        y = self.y
        return x, y
        
    def get_card_index_at_pos(self, pos, card_count):
        x, y = pos
        # check visible portion (from topmost to bottommost)
        for i in range(card_count-1, -1, -1):
            card_x, card_y = self.get_card_position(i)
            if i == card_count - 1:
                vis_w = CARD_W
            else:
                vis_w = max(1, CARD_W + CARD_GAP)
            rect = pygame.Rect(card_x, card_y, vis_w, CARD_H)
            if rect.collidepoint(x, y):
                return i
        return None

# ---------------- Animation helper ----------------

class MovingCard:
    """
    Animate a Card object from start_pos -> end_pos (both top-left coordinates).
    Use easing and report when finished.
    """
    def __init__(self, card, start_pos, end_pos, duration_ms=CARD_ANIM_DURATION_MS):
        self.card = card
        self.start_x, self.start_y = start_pos
        self.end_x, self.end_y = end_pos
        self.duration = max(1, int(duration_ms))
        self.start_time = pygame.time.get_ticks()
        self.finished = False

    def update(self):
        t = pygame.time.get_ticks() - self.start_time
        progress = min(1.0, float(t) / float(self.duration))
        # ease-out cubic
        ease = 1 - (1 - progress) ** 3
        x = self.start_x + (self.end_x - self.start_x) * ease
        y = self.start_y + (self.end_y - self.start_y) * ease
        if progress >= 1.0:
            self.finished = True
        return int(x), int(y), self.finished

# ---------------- Game Engine ----------------

class Game:
    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.font_small = pygame.font.SysFont('arial', 16)
        self.font_med = pygame.font.SysFont('arial', 20, bold=True)
        self.font_big = pygame.font.SysFont('arial', 28, bold=True)

        # Game states
        self.state = 'setup'  # setup, dealing, play, finished, paused, showing_trick
        self.players = []
        self.player_count = 4
        self.buttons = []
        self.setup_ui_objects()

        # Runtime variables
        self.deck = []
        self.discard_pile = []
        self.trick_cards = []  # list of tuples (player_index, Card)
        self.leader_index = 0
        self.active_index = 0  # whose turn it is within current trick
        self.required_suit = None
        self.ranks_assigned = 0
        self.finish_order = []  # list of (player_name, rank)
        self.pause_reason = ''
        self.last_action_time = 0
        self.trick_display_time = 0
        self.showing_trick = False
        self.last_played_cards = []  # For displaying played cards
        self.pending_tochoo = False  # whether the pending resolution is a tochoo

        # NEW: remember last trick suit while showing/resolving
        self.last_trick_suit = None

        # Warning message (for illegal click feedback)
        self.warning_text = ""
        self.warning_time = 0.0

        # UI toggles
        self.paused = False
        self.auto_play_delay = 1.0  # cpu wait seconds before playing
        
        # Scrollable hand
        hand_area_width = SCREEN_WIDTH - 100
        self.hand_area = ScrollableHand(50, SCREEN_HEIGHT - CARD_H - 30, hand_area_width, CARD_H)

        # New flag: first move must be Ace of Spades
        self.first_move = False

        # ---------------- Animation state ----------------
        self.animating = False
        self.moving_card = None  # MovingCard instance
        self.animating_card = None  # the Card object being animated (identity)
        self.resolve_after_animation = None  # None or boolean (tochoo_occurred)
        # Try load sound (safe)
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
            self.card_place_sound = pygame.mixer.Sound(CARD_PLAY_SOUND_FILE)
            self.tochoo_sound = pygame.mixer.Sound(TOCHOO_SOUND_FILE)
        except Exception:
            self.card_place_sound = None
            self.tochoo_sound = None
        self.animation_duration = CARD_ANIM_DURATION_MS

    # ---------- Setup UI ----------
    def setup_ui_objects(self):
        self.buttons = []
        self.pause_button = Button((SCREEN_WIDTH-220, 10, 100, 36), "Pause", onclick=self.toggle_pause)
        self.restart_button = Button((SCREEN_WIDTH-110, 10, 100, 36), "Restart", onclick=self.restart_to_setup)
        self.setup_buttons = []

    def restart_to_setup(self):
        self.state = 'setup'
        self.players = []
        self.player_count = 4
        self.trick_cards = []
        self.discard_pile = []
        self.deck = []
        self.ranks_assigned = 0
        self.finish_order = []
        self.required_suit = None
        self.pause_reason = ''
        self.paused = False
        self.showing_trick = False
        self.pending_tochoo = False
        self.warning_text = ""
        self.warning_time = 0.0
        self.first_move = False
        self.last_trick_suit = None
        # reset animation state too
        self.animating = False
        self.moving_card = None
        self.animating_card = None
        self.resolve_after_animation = None
        self.setup_ui_objects()

    def toggle_pause(self):
        if self.state in ('play', 'showing_trick'):
            self.paused = not self.paused
            self.pause_button.text = "Resume" if self.paused else "Pause"
            if self.paused:
                self.state = 'paused'
            else:
                self.state = 'play' if not self.showing_trick else 'showing_trick'

    # ---------- Setup flow ----------
    def draw_setup(self):
        self.screen.fill(GREEN)
        title = self.font_big.render("Bhabhi / Thulla - Setup", True, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 30))

        label = self.font_med.render("Select number of players (3 - 6):", True, WHITE)
        self.screen.blit(label, (50, 110))
        xstart = 50
        for i in range(3, 7):
            rect = (xstart + (i-3)*70, 150, 60, 40)
            btn = Button(rect, str(i), onclick=lambda n=i: self.set_player_count(n))
            btn.draw(self.screen)
        current = self.font_med.render(f"Current: {self.player_count}", True, WHITE)
        self.screen.blit(current, (50, 210))

        label2 = self.font_med.render("Set each player as Human or CPU:", True, WHITE)
        self.screen.blit(label2, (50, 260))
        if not self.players:
            self.players = [Player(f"P{i+1}", is_human=True) for i in range(self.player_count)]
        for i in range(self.player_count):
            p = self.players[i] if i < len(self.players) else Player(f"P{i+1}", True)
            rect = (50 + i*170, 300, 150, 42)
            txt = f"{p.name}: {'Human' if p.is_human else 'CPU'}"
            def make_toggle(idx):
                return lambda: self.toggle_player_type(idx)
            btn = Button(rect, txt, onclick=make_toggle(i))
            btn.draw(self.screen)

        start_btn = Button((SCREEN_WIDTH//2 - 80, SCREEN_HEIGHT - 110, 160, 48), "Start Game", onclick=self.start_game, font_size=24)
        start_btn.draw(self.screen)
        self.setup_buttons = [start_btn]

        inst = self.font_small.render("Click player buttons to toggle Human/CPU. Then click Start Game.", True, WHITE)
        self.screen.blit(inst, (50, SCREEN_HEIGHT - 60))

    def set_player_count(self, n):
        self.player_count = n
        new_players = []
        for i in range(n):
            if i < len(self.players):
                new_players.append(self.players[i])
            else:
                new_players.append(Player(f"P{i+1}", is_human=True))
        self.players = new_players

    def toggle_player_type(self, idx):
        if idx >= len(self.players):
            return
        self.players[idx].is_human = not self.players[idx].is_human

    # ---------- Start / Deal ----------
    def start_game(self):
        self.state = 'dealing'
        self.deck = full_deck()
        random.shuffle(self.deck)
        counts = [len(self.deck)//self.player_count] * self.player_count
        extra = len(self.deck) - sum(counts)
        for i in range(extra):
            counts[i] += 1
        pos = 0
        for i, p in enumerate(self.players):
            p.hand = []
            for _ in range(counts[i]):
                p.hand.append(self.deck[pos])
                pos += 1
            p.sort_hand()
            p.is_active = True
            p.finished_rank = None
            # reset pickup flags
            p.just_picked_up = False
            p.avoid_suit = None
        self.discard_pile = []
        self.trick_cards = []
        self.finish_order = []
        self.ranks_assigned = 0
        self.last_trick_suit = None

        # Find Ace of Spades starter
        starter = None
        for i, p in enumerate(self.players):
            for c in p.hand:
                if c.rank == 'A' and c.suit == '♠':
                    starter = i
                    break
            if starter is not None:
                break
        if starter is None:
            starter = random.randrange(len(self.players))
        self.leader_index = starter
        self.active_index = starter
        self.required_suit = None
        self.state = 'play'
        self.paused = False
        self.pause_button.text = "Pause"
        self.showing_trick = False
        self.pending_tochoo = False
        self.warning_text = ""
        self.warning_time = 0.0

        # Enforce first-move Ace of Spades
        self.first_move = True

        # Reset animation flags at new deal
        self.animating = False
        self.moving_card = None
        self.animating_card = None
        self.resolve_after_animation = None

    # ---------- Play helpers ----------
    def get_active_players_indices(self):
        return [i for i, p in enumerate(self.players) if p.is_active]

    def next_active_index(self, current):
        n = len(self.players)
        if n == 0:
            return None
        i = (current + 1) % n
        loop_protect = 0
        while not self.players[i].is_active and loop_protect < n:
            i = (i + 1) % n
            loop_protect += 1
        return i

    def count_active_players(self):
        return sum(1 for p in self.players if p.is_active)

    def check_game_end(self):
     active_players = [p for p in self.players if p.is_active]
     if len(active_players) <= 1:
        # Only one player left - they are the loser
        for p in self.players:
            if p.is_active and p.finished_rank is None:
                self.ranks_assigned += 1
                p.finished_rank = self.ranks_assigned
                p.is_active = False
                self.finish_order.append((p.name, p.finished_rank))
        self.state = 'finished'

    def resolve_trick(self, tochoo_occurred=False):
        if not self.trick_cards:
            return
        # remember the suit of the trick while showing/resolving
        self.last_trick_suit = self.required_suit
        self.showing_trick = True
        self.trick_display_time = time.time()
        self.last_played_cards = self.trick_cards.copy()
        self.pending_tochoo = tochoo_occurred
        self.state = 'showing_trick'

    def actually_resolve_trick(self, tochoo_occurred=None):
        if tochoo_occurred is None:
            tochoo_occurred = self.pending_tochoo
            
        # Play tochoo sound if applicable
        if tochoo_occurred and self.tochoo_sound:
            try:
                self.tochoo_sound.play()
            except Exception:
                pass
                
        suited = [(pi,card) for (pi,card) in self.trick_cards if card.suit == self.required_suit]
        if tochoo_occurred:
            if suited:
                pickup_player = max(suited, key=lambda t: t[1].value)[0]
            else:
                pickup_player = self.leader_index
            pickup_cards = [card for (_,card) in self.trick_cards]
            random.shuffle(pickup_cards)
            self.players[pickup_player].pick_up(pickup_cards)
            # Mark that this player just picked up and should avoid leading the same suit next
            self.players[pickup_player].just_picked_up = True
            self.players[pickup_player].avoid_suit = self.last_trick_suit
            self.leader_index = pickup_player
            self.active_index = pickup_player
        else:
            if not suited:
                winner = self.leader_index
            else:
                winner = max(suited, key=lambda t: t[1].value)[0]
            self.discard_pile.extend([card for (_,card) in self.trick_cards])
            self.leader_index = winner
            self.active_index = winner

        self.trick_cards = []
        self.required_suit = None

        for i, p in enumerate(self.players):
            if p.is_active and len(p.hand) == 0:
                self.ranks_assigned += 1
                p.finished_rank = self.ranks_assigned
                p.is_active = False
                self.finish_order.append((p.name, p.finished_rank))

        self.check_game_end()

        self.showing_trick = False
        self.last_played_cards = []
        self.pending_tochoo = False
        # reset last_trick_suit after resolution (avoid confusion later)
        self.last_trick_suit = None
        if self.state != 'finished':
            self.state = 'play'

    # ---------- Playability helpers ----------
    def is_card_playable(self, player_idx, card_index):
        """
        Return True if the specific card (by index) is playable by player_idx under strict follow-suit enforcement.
        Also enforce: if it's the very first move (self.first_move) and the leader is to play, only Ace of Spades is allowed.
        """
        p = self.players[player_idx]
        if not p.is_active:
            return False
        # If first move and no trick started, only Ace of Spades is allowed for the leader
        if self.required_suit is None and self.first_move and player_idx == self.active_index:
            card = p.hand[card_index]
            return (card.rank == 'A' and card.suit == '♠')
        if self.required_suit is None:
            return True  # leader can normally play any card
        # If player has the required suit, only cards of that suit are playable
        has_req = p.has_suit(self.required_suit)
        card = p.hand[card_index]
        if has_req:
            return card.suit == self.required_suit
        else:
            # player doesn't have required suit -> any card playable (legitimate tochoo)
            return True

    def playable_indices_for_player(self, player_idx):
        p = self.players[player_idx]
        playable = []
        for i in range(len(p.hand)):
            if self.is_card_playable(player_idx, i):
                playable.append(i)
        return playable

    # ---------- Helper: player screen position for CPU card start ----------
    def get_player_card_start_pos(self, player_idx):
        cx, cy = SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 20
        radius = 280
        n = len(self.players)
        angle = math.radians(270 + (360 / n) * player_idx)
        px = int(cx + math.cos(angle) * (radius - 140))
        py = int(cy + math.sin(angle) * (radius - 140))
        # return top-left so card.draw can use directly
        return px - CARD_W//2, py - CARD_H//2

    # ---------- Player moves ----------
    def cpu_choose_card_index(self, player_idx):
        p = self.players[player_idx]
        if not p.hand:
            return None

        # If this CPU just picked up a trick previously, try to avoid leading the same suit now
        # This is only relevant when it's the leader (required_suit is None) or when CPU is to play and
        # doesn't need to follow a suit (it has no required suit in hand).
        avoid_suit = p.avoid_suit if getattr(p, 'just_picked_up', False) else None

        # must follow suit if possible
        if self.required_suit is None:
            # If it's the very first move, and CPU is leader, force Ace of Spades if present
            if self.first_move and player_idx == self.active_index:
                for i, c in enumerate(p.hand):
                    if c.rank == 'A' and c.suit == '♠':
                        return i
                # (If somehow not present, fall back to lowest)
            # leader: choose lowest overall, but if just picked up try to choose a card with suit != avoid_suit
            if avoid_suit:
                non_avoid = [i for i, c in enumerate(p.hand) if c.suit != avoid_suit]
                if non_avoid:
                    # choose lowest among non-avoid
                    return min(non_avoid, key=lambda i: p.hand[i].value)
                # if can't (all cards are avoid_suit), fall through to normal selection
            return min(range(len(p.hand)), key=lambda i: p.hand[i].value)
        else:
            same_suit_indices = [i for i, c in enumerate(p.hand) if c.suit == self.required_suit]
            if same_suit_indices:
                # follow with lowest of suit
                return min(same_suit_indices, key=lambda i: p.hand[i].value)
            else:
                # cannot follow -> legitimate tochoo: dump highest
                # If CPU had just picked up and is avoiding a suit, prefer dump not of avoid_suit? But since we are forced tochoo (no required suit in hand),
                # to reduce repeated patterns, prefer to dump highest of any suit != avoid_suit if possible.
                if avoid_suit:
                    non_avoid = [i for i in range(len(p.hand)) if p.hand[i].suit != avoid_suit]
                    if non_avoid:
                        return max(non_avoid, key=lambda i: p.hand[i].value)
                return max(range(len(p.hand)), key=lambda i: p.hand[i].value)

    def attempt_play_card(self, player_idx, card_index):
        # Prevent new plays while an animation is running
        if self.animating:
            return

        p = self.players[player_idx]
        if player_idx != self.active_index:
            return
        if not p.is_active:
            return

        # Enforce follow-suit strictly:
        had_required = (self.required_suit is not None and p.has_suit(self.required_suit))
        card = p.hand[card_index]

        # If a trick is not started (leader)
        if self.required_suit is None:
            # Enforce first-move Ace of Spades: if this is the first move of game, leader must play A♠
            if self.first_move and player_idx == self.active_index:
                if not (card.rank == 'A' and card.suit == '♠'):
                    self.warning_text = "Game must start with Ace of Spades!"
                    self.warning_time = time.time()
                    return
                # otherwise allow and clear the first-move flag after playing

            # compute start pos BEFORE removing the card (so hand coordinates still valid)
            if p.is_human:
                start_x, start_y = self.hand_area.get_card_position(card_index)
            else:
                start_x, start_y = self.get_player_card_start_pos(player_idx)

            # remove card & append to trick
            played_card = p.play_card(card_index)
            self.trick_cards.append((player_idx, played_card))

            # compute where the played card should land in trick area (use same logic as draw_play)
            center_x, center_y = SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 60
            num_cards = len(self.trick_cards)
            idx = num_cards - 1
            angle = 2 * math.pi * idx / max(1, num_cards)
            offset_x = int(math.cos(angle) * 80)
            offset_y = int(math.sin(angle) * 60)
            end_x = center_x + offset_x - CARD_W//2
            end_y = center_y + offset_y - CARD_H//2

            # spawn animation
            self.moving_card = MovingCard(played_card, (start_x, start_y), (end_x, end_y), self.animation_duration)
            self.animating = True
            self.animating_card = played_card

            # if the move was the special first move, clear the flag
            if self.first_move:
                self.first_move = False
            self.required_suit = played_card.suit
            self.active_index = self.next_active_index(player_idx)
            self.last_action_time = time.time()
            if p.card_count() == 0:
             self.ranks_assigned += 1
             p.finished_rank = self.ranks_assigned
             p.is_active = False
             self.finish_order.append((p.name, p.finished_rank))
             self.check_game_end()
            # If player had just picked up we'll clear the flag now that they have led/played a card
            if getattr(p, 'just_picked_up', False):
                p.just_picked_up = False
                p.avoid_suit = None
            # No immediate resolve for leader; return and let animation finish
            return

        # If trick already led:
        if had_required and card.suit != self.required_suit:
            # Strict enforcement: player has required suit but clicked different suit -> block
            self.warning_text = "You must follow suit!"
            self.warning_time = time.time()
            return

        # compute start pos BEFORE removing card
        if p.is_human:
            start_x, start_y = self.hand_area.get_card_position(card_index)
        else:
            start_x, start_y = self.get_player_card_start_pos(player_idx)

        # Now either the player followed suit, or legitimately cannot follow (no required suit in hand)
        played_card = p.play_card(card_index)
        self.trick_cards.append((player_idx, played_card))
        self.last_action_time = time.time()

        # compute end pos for the just-played card
        center_x, center_y = SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 60
        num_cards = len(self.trick_cards)
        idx = num_cards - 1
        angle = 2 * math.pi * idx / max(1, num_cards)
        offset_x = int(math.cos(angle) * 80)
        offset_y = int(math.sin(angle) * 60)
        end_x = center_x + offset_x - CARD_W//2
        end_y = center_y + offset_y - CARD_H//2

        # spawn animation
        self.moving_card = MovingCard(played_card, (start_x, start_y), (end_x, end_y), self.animation_duration)
        self.animating = True
        self.animating_card = played_card

        # If the player legitimately could not follow (i.e., they don't have the required suit) and thus played different suit,
        # that's a legitimate tochoo -> schedule immediate tochoo resolution (after display)
        if played_card.suit != self.required_suit and not had_required:
            # legitimate tochoo (player did not have required suit)
            # If the player had just picked up (they dumped a card immediately after pickup), clear their flag now
            if getattr(p, 'just_picked_up', False):
                p.just_picked_up = False
                p.avoid_suit = None
            # Delay the resolution until animation ends
            self.resolve_after_animation = True
            return
        else:
            # normal follow
            self.active_index = self.next_active_index(player_idx)
            # if we've come full circle, trick complete
            if self.active_index == self.leader_index:
                active_count = self.count_active_players()
                if len(self.trick_cards) >= active_count:
                    # Delay the resolution until animation ends
                    self.resolve_after_animation = False
                    return
            # If player had just picked up and simply followed (unlikely right after pickup), clear the flag now
            if getattr(p, 'just_picked_up', False):
                p.just_picked_up = False
                p.avoid_suit = None
            return

    def cpu_auto_play_if_needed(self):
        if self.active_index is None:
            return
        if self.animating:
            return
        active_idx = self.active_index
        p = self.players[active_idx]
        if not p.is_active or p.is_human:
            return
        if time.time() - self.last_action_time < self.auto_play_delay:
            return
        idx = self.cpu_choose_card_index(active_idx)
        if idx is None:
            return
        # CPU should only play cards that are playable under the strict rule.
        # cpu_choose_card_index already follows the rule, but double-check:
        if not self.is_card_playable(active_idx, idx):
            # find first playable
            playable = self.playable_indices_for_player(active_idx)
            if not playable:
                return
            idx = playable[0]
        self.attempt_play_card(active_idx, idx)

    def update_play(self, dt):
        if self.state != 'play' or self.paused:
            return
        if self.active_index is None:
            return
        if self.animating:
            return
        if not self.players[self.active_index].is_human:
            self.cpu_auto_play_if_needed()

    # ---------- Main loop -------
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 4:
                        self.hand_area.scroll(-1)
                    elif event.button == 5:
                        self.hand_area.scroll(1)
                    elif self.state == 'setup':
                        pos = pygame.mouse.get_pos()
                        self.handle_setup_click(pos)
                    elif self.state in ('play', 'showing_trick') and not self.paused:
                        pos = pygame.mouse.get_pos()
                        if self.state == 'play':
                            self.handle_play_click(pos)
                    elif self.state == 'finished':
                        pos = pygame.mouse.get_pos()
                        if self.restart_button.rect.collidepoint(pos):
                            self.restart_to_setup()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self.restart_to_setup()
                    if event.key == pygame.K_p:
                        self.toggle_pause()
                    if event.key == pygame.K_LEFT:
                        self.hand_area.scroll(-1)
                    if event.key == pygame.K_RIGHT:
                        self.hand_area.scroll(1)

            # draw current state
            if self.state == 'setup':
                self.draw_setup()
            elif self.state == 'play':
                self.draw_play()
                if not self.paused:
                    self.update_play(dt)
            elif self.state == 'finished':
                self.draw_finished()
            elif self.state == 'paused':
                self.draw_play()
                self.draw_pause_overlay()
            elif self.state == 'showing_trick':
                self.draw_play()
                if not self.paused and (time.time() - self.trick_display_time > 3):
                    self.actually_resolve_trick(self.pending_tochoo)

            if self.state in ['play', 'finished', 'paused', 'showing_trick']:
                self.pause_button.draw(self.screen, hover=False)
                self.restart_button.draw(self.screen, hover=False)

            pygame.display.flip()
        pygame.quit()
        sys.exit()

    # ---------- Drawing ----------
    def draw_pause_overlay(self):
        s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        s.fill((0, 0, 0, 128))
        self.screen.blit(s, (0, 0))
        text = self.font_big.render("GAME PAUSED", True, WHITE)
        self.screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, SCREEN_HEIGHT//2 - text.get_height()//2))
        instruction = self.font_med.render("Press P to resume", True, WHITE)
        self.screen.blit(instruction, (SCREEN_WIDTH//2 - instruction.get_width()//2, SCREEN_HEIGHT//2 + 50))

    def handle_setup_click(self, pos):
        x, y = pos
        if 150 <= y <= 190 and 50 <= x <= 50 + 4*70 + 60:
            relx = x - 50
            idx = int(relx // 70)
            sel = 3 + idx
            if 3 <= sel <= 6:
                self.set_player_count(sel)
                return
        for i in range(self.player_count):
            rx = 50 + i*170
            if rx <= x <= rx+150 and 300 <= y <= 342:
                self.toggle_player_type(i)
                return
        sx, sy, sw, sh = (SCREEN_WIDTH//2 - 80, SCREEN_HEIGHT - 110, 160, 48)
        if sx <= x <= sx+sw and sy <= y <= sy+sh:
            self.start_game()
            return

    def handle_play_click(self, pos):
        # block clicks while a card animation is running
        if self.animating:
            return

        x, y = pos
        active_idx = self.active_index
        if active_idx is None:
            return
        if not self.players[active_idx].is_active:
            return
        player = self.players[active_idx]
        if player.is_human:
            hand = player.hand
            if not hand:
                return
            hand_rect = pygame.Rect(self.hand_area.x, self.hand_area.y, self.hand_area.width, self.hand_area.height)
            if hand_rect.collidepoint(pos):
                card_index = self.hand_area.get_card_index_at_pos(pos, len(hand))
                if card_index is not None:
                    # Block clicks on unplayable cards
                    if not self.is_card_playable(active_idx, card_index):
                        # Provide special message if first move restriction violated
                        if self.first_move and self.required_suit is None and active_idx == self.active_index:
                            self.warning_text = "Game must start with Ace of Spades!"
                        else:
                            self.warning_text = "You must follow suit!"
                        self.warning_time = time.time()
                        return
                    self.attempt_play_card(active_idx, card_index)
                    return

        if self.pause_button.rect.collidepoint(pos):
            self.toggle_pause()
        if self.restart_button.rect.collidepoint(pos):
            self.restart_to_setup()

    def draw_play(self):
        # update/draw; also drive animation update here so we can draw the moving card on top
        self.screen.fill(GREEN)
        pygame.draw.circle(self.screen, (20, 90, 30), (SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 20), 240)
        title = self.font_big.render("Bhabhi / Thulla", True, WHITE)
        self.screen.blit(title, (24, 10))
        inst = self.font_small.render("Click your cards (bottom) when it's your turn. Pause = P or button. Restart = button. Scroll = mouse wheel or arrows.", True, WHITE)
        self.screen.blit(inst, (24, 46))

        active_players = self.get_active_players_indices()
        cx, cy = SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 20
        radius = 280
        n = len(self.players)
        for i, p in enumerate(self.players):
         angle = math.radians(270 + (360 / n) * i)
         px = int(cx + math.cos(angle) * radius)
         py = int(cy + math.sin(angle) * radius)
         boxw, boxh = 160, 48
         box_rect = pygame.Rect(px - boxw//2, py - boxh//2, boxw, boxh)
         color = BLUE if i == self.leader_index else DARK_GRAY
         pygame.draw.rect(self.screen, color, box_rect, border_radius=8)
         pygame.draw.rect(self.screen, BLACK, box_rect, 2, border_radius=8)

    # --- UPDATED: show card count next to name ---
         if p.is_active:
          name_text = f"{p.name} ({'Human' if p.is_human else 'CPU'})  [{p.card_count()}]"
         else:
          name_text = f"{p.name} - Rank: {p.finished_rank}"

         t = self.font_small.render(name_text, True, WHITE)
         self.screen.blit(t, (box_rect.x + 6, box_rect.y + 8))

         if i == self.active_index and p.is_active:
          pygame.draw.circle(self.screen, YELLOW, (box_rect.right+14, box_rect.centery), 8)


        center_x, center_y = SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 60
        cards_to_show = self.last_played_cards if self.showing_trick else self.trick_cards
        num_cards = len(cards_to_show)
        # Draw played/trick cards, but skip the one currently animating (we'll draw it separately)
        for idx, (pi, card) in enumerate(cards_to_show):
            if self.animating and card is self.animating_card:
                # skip drawing the static placed version while it's animating
                continue
            angle = 2 * math.pi * idx / max(1, num_cards)
            offset_x = int(math.cos(angle) * 80)
            offset_y = int(math.sin(angle) * 60)
            card.draw(self.screen, center_x + offset_x - CARD_W//2, center_y + offset_y - CARD_H//2, face=True)

        # If an animated card is running, update its position and draw it on top
        if self.animating and self.moving_card is not None:
            ax, ay, finished = self.moving_card.update()
            # draw the moving card (face up)
            try:
                self.animating_card.draw(self.screen, ax, ay, face=True)
            except Exception:
                # fallback: in rare case animating_card is None or wrong, just draw moving_card.card
                self.moving_card.card.draw(self.screen, ax, ay, face=True)
            if finished:
                # play sound (if available)
                if self.card_place_sound:
                    try:
                        self.card_place_sound.play()
                    except Exception:
                        pass
                # stop animating
                self.animating = False
                # clear moving object and animating card ref
                self.moving_card = None
                self.animating_card = None
                # if resolution was queued (tochoo or full trick), call resolve_trick now
                if self.resolve_after_animation is not None:
                    tochoo_bool = self.resolve_after_animation
                    self.resolve_after_animation = None
                    # Call resolve_trick which will set showing_trick and last_played_cards
                    self.resolve_trick(tochoo_occurred=tochoo_bool)

        rs = f"Required suit: {self.required_suit}" if self.required_suit else "Leader to play"
        rsurf = self.font_med.render(rs, True, WHITE)
        self.screen.blit(rsurf, (SCREEN_WIDTH//2 - rsurf.get_width()//2, SCREEN_HEIGHT//2 + 130))

        active = self.players[self.active_index] if self.active_index is not None else None
        bottom_y = SCREEN_HEIGHT - CARD_H - 30
        if active is None:
            return

        turn_text = f"Turn: {active.name} ({'Human' if active.is_human else 'CPU'})"
        t2 = self.font_med.render(turn_text, True, WHITE)
        self.screen.blit(t2, (SCREEN_WIDTH//2 - t2.get_width()//2, SCREEN_HEIGHT - CARD_H - 80))

        # Show warning if any
        if self.warning_text and (time.time() - self.warning_time) < 1.8:
            warn_surf = self.font_med.render(self.warning_text, True, WARNING_COLOR)
            self.screen.blit(warn_surf, (SCREEN_WIDTH//2 - warn_surf.get_width()//2, SCREEN_HEIGHT - CARD_H - 110))
        elif self.warning_text:
            self.warning_text = ""

        if active.is_human:
            hand = active.hand
            if not hand:
                hmm = self.font_med.render("You have no cards.", True, WHITE)
                self.screen.blit(hmm, (SCREEN_WIDTH//2 - hmm.get_width()//2, bottom_y - 60))
            else:
                self.hand_area.update_scroll_limit(len(hand))

                if self.hand_area.scroll_x > 0:
                    pygame.draw.polygon(self.screen, WHITE, [
                        (self.hand_area.x + 10, bottom_y + CARD_H//2 - 10),
                        (self.hand_area.x + 10, bottom_y + CARD_H//2 + 10),
                        (self.hand_area.x, bottom_y + CARD_H//2)
                    ])

                if self.hand_area.scroll_x < self.hand_area.max_scroll:
                    pygame.draw.polygon(self.screen, WHITE, [
                        (self.hand_area.x + self.hand_area.width - 10, bottom_y + CARD_H//2 - 10),
                        (self.hand_area.x + self.hand_area.width - 10, bottom_y + CARD_H//2 + 10),
                        (self.hand_area.x + self.hand_area.width, bottom_y + CARD_H//2)
                    ])

                playable_idxs = set(self.playable_indices_for_player(self.active_index))

                for i, card in enumerate(hand):
                    cx, cy = self.hand_area.get_card_position(i)
                    if cx + CARD_W > self.hand_area.x and cx < self.hand_area.x + self.hand_area.width:
                        disabled = False
                        if self.required_suit is not None and active.has_suit(self.required_suit) and card.suit != self.required_suit:
                            disabled = True
                        # Also dim any non-A♠ on first move for the leader
                        if self.required_suit is None and self.first_move and self.active_index == self.players.index(active):
                            if not (card.rank == 'A' and card.suit == '♠'):
                                disabled = True
                        selectable = (i in playable_idxs)
                        card.draw(self.screen, cx, cy, face=True, selectable=selectable, disabled=disabled)
        else:
            cpu_msg = self.font_med.render(f"{active.name} (CPU) is thinking...", True, WHITE)
            self.screen.blit(cpu_msg, (SCREEN_WIDTH//2 - cpu_msg.get_width()//2, bottom_y))

        # Draw other players' backs & counts - REMOVED the visual "card back + count" so it doesn't overlay player's hand.
        # Previously the code drew a dark card-shaped rect with the opponent card count overlaying the screen.
        # That draw was removed per user's request to avoid obstruction.
        for i, p in enumerate(self.players):
            if i == self.active_index:
                continue
            angle = math.radians(270 + (360 / n) * i)
            px = int(cx + math.cos(angle) * (radius - 140))
            py = int(cy + math.sin(angle) * (radius - 140))
            # Do not draw the extra backrect or count to avoid clutter.
            # If player finished, still show rank text at their position.
            if not p.is_active:
                done_text = self.font_small.render(f"Rank {p.finished_rank}", True, WHITE)
                self.screen.blit(done_text, (px - 20, py - 10))

        left = 30
        top = 120
        if self.finish_order:
            h = self.font_med.render("Finish order:", True, WHITE)
            self.screen.blit(h, (left, top))
            for i, (name, rank) in enumerate(self.finish_order):
                t = self.font_small.render(f"{rank}. {name}", True, WHITE)
                self.screen.blit(t, (left, top + 26 + i*20))

    # ---------- Finished screen ----------
    def draw_finished(self):
        self.screen.fill(GREEN)
        title = self.font_big.render("Game Over - Rankings", True, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 40))
        ordered = sorted([(p.finished_rank, p.name) for p in self.players if p.finished_rank is not None], key=lambda t: t[0])
        y = 140
        for rank, name in ordered:
            line = self.font_med.render(f"{rank}. {name}", True, WHITE)
            self.screen.blit(line, (SCREEN_WIDTH//2 - line.get_width()//2, y))
            y += 48

        sub = self.font_small.render("Click Restart to play again.", True, WHITE)
        self.screen.blit(sub, (SCREEN_WIDTH//2 - sub.get_width()//2, y+20))
        self.restart_button.draw(self.screen)

# ---------------- Main entrypoint ----------------

def main():
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Bhabhi / Thulla - Fixed")
    game = Game(screen)
    game.run()

if __name__ == "__main__":
    main()