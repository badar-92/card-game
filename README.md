# Bhabhi / Thulla Card Game

A digital implementation of the popular South Asian card game, featuring strict follow-suit rules, smooth animations, and professional gameplay experience.

[Game start](https://replit.com/@70154287/card-game)

## 🎯 Overview

Bhabhi (also known as Thulla) is a trick-taking card game popular in South Asia, particularly in Pakistan and India. This digital version faithfully recreates the authentic gameplay with modern visuals and intuitive controls.

## 🎮 Features

- **Authentic Gameplay**: Strict follow-suit enforcement and proper "tochoo/thula" rules
- **Smooth Animations**: Card movement with easing effects and visual feedback
- **Professional UI**: Clean, intuitive interface with visual cues for game state
- **Flexible Setup**: 3-6 players with Human/CPU mix options
- **Smart CPU**: Intelligent AI that follows game rules and strategies
- **Visual Feedback**: Dimmed unplayable cards, turn indicators, and warnings
- **Sound Effects**: Immersive audio for card plays and special events

## 📋 Game Rules

### Core Mechanics
- **Follow Suit**: Players must follow the led suit if they have cards of that suit
- **Tochoo/Thula**: If a player cannot follow suit, they may play any card, making it a "tochoo"
- **Trick Resolution**: 
  - Normal play: Highest card of led suit wins, cards discarded
  - Tochoo: Highest card of led suit picks up all trick cards
- **Winning**: Players aim to get rid of all cards; last player with cards loses

### Special Rules
- Game starts with Ace of Spades
- Players who pick up tricks should avoid leading the same suit
- Finished players are ranked as they empty their hands

## 🚀 Installation & Requirements

### Prerequisites
- Python 3.7 or higher
- Pygame library

### Installation Steps
1. **Clone or Download** the game files
2. **Install Dependencies**:
   ```bash
   pip install pygame
   ```
3. **Optional**: Place sound files in the same directory:
   - `mixkit-poker-card-flick-2002.wav` (card play sound)
   - `mixkit-classic-click-1117.wav` (tochoo sound)

### Running the Game
```bash
python bhabhi_game.py
```

## 🎯 How to Play

### Setup Phase
1. Select number of players (3-6)
2. Configure each player as Human or CPU
3. Click "Start Game" to begin

### During Gameplay
- **Human Players**: Click on playable cards from your hand
- **CPU Players**: Automatically play with strategic decisions
- **Card Display**: 
  - Bright cards = playable
  - Dimmed cards = unplayable (must follow suit)
  - Blue border = selectable cards
  - Yellow highlight = current trick winner

### Controls
- **Mouse**: Click cards to play, use buttons for game control
- **Mouse Wheel**: Scroll through hand when many cards
- **Arrow Keys**: Scroll through hand (Left/Right)
- **P Key**: Pause/Resume game
- **R Key**: Restart to setup

## 🎨 Interface Elements

### Main Game Screen
- **Center**: Current trick with played cards
- **Bottom**: Your hand with scrollable display
- **Around Table**: Player positions with status indicators
- **Top Left**: Game title and instructions
- **Top Right**: Pause/Restart buttons
- **Left Side**: Finish order tracking

### Visual Indicators
- 🟡 Yellow circle = Current player's turn
- 🔵 Blue name box = Current trick leader
- ⚪ Normal cards = Playable cards
- 🎭 Dimmed cards = Unplayable (follow suit required)
- 📊 Card counts = Number of cards remaining

## 🔧 Technical Details

### Game States
- `setup`: Player configuration
- `play`: Active gameplay
- `showing_trick`: Trick resolution display
- `finished`: Game completion with rankings
- `paused`: Game temporarily stopped

### Key Components
- **Card Animation System**: Smooth card movement with easing
- **Scrollable Hand**: Handles large numbers of cards
- **Rule Enforcement**: Strict follow-suit validation
- **AI Decision Making**: CPU player strategy implementation

## 🎵 Audio Features

- Card placement sounds
- Special "tochoo" event sounds
- Mutable audio system (easily extendable)

## 🛠️ Customization

### Easy Modifications
- **Card Appearance**: Modify `CARD_W`, `CARD_H` in configuration
- **Animation Speed**: Adjust `CARD_ANIM_DURATION_MS`
- **CPU Delay**: Change `auto_play_delay` for different difficulty
- **Colors**: Modify color constants for different themes

### Adding Features
The code is structured to easily add:
- New game variants
- Additional sound effects
- Different card themes
- Network multiplayer

## 🤝 Contributing

Contributions are welcome! Areas for improvement:
- Additional game variants
- Enhanced AI difficulty levels
- Network multiplayer support
- Mobile device compatibility
- Localization for different languages

## 📄 License

This project is open source and available under the MIT License.

## 🎊 Enjoy Playing!

Experience the authentic thrill of Bhabhi/Thulla with this digital adaptation. Perfect for learning the game, practicing strategies, or enjoying with friends and AI opponents.

---

*For rules clarification or to learn more about the traditional game, consult local card game enthusiasts or cultural resources.*
