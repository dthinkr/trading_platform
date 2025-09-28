<p align="center">
  <img src="front/src/assets/trading_platform_logo.png" alt="Trading Platform Logo" width="200"/>
</p>

<h1 align="center">Trading Platform</h1>

<p align="center">
  A platform for conducting financial market experiments with multiple traders and role-based interactions.
</p>

<p align="center">
  <a href="https://github.com/dthinkr/trading_platform/stargazers"><img src="https://img.shields.io/github/stars/dthinkr/trading_platform" alt="Stars Badge"/></a>
  <a href="https://github.com/dthinkr/trading_platform/network/members"><img src="https://img.shields.io/github/forks/dthinkr/trading_platform" alt="Forks Badge"/></a>
  <a href="https://github.com/dthinkr/trading_platform/pulls"><img src="https://img.shields.io/github/issues-pr/dthinkr/trading_platform" alt="Pull Requests Badge"/></a>
  <a href="https://github.com/dthinkr/trading_platform/issues"><img src="https://img.shields.io/github/issues/dthinkr/trading_platform" alt="Issues Badge"/></a>
  <a href="https://github.com/dthinkr/trading_platform/graphs/contributors"><img alt="GitHub contributors" src="https://img.shields.io/github/contributors/dthinkr/trading_platform?color=2b9348"></a>
  <a href="https://github.com/dthinkr/trading_platform/blob/master/LICENSE"><img src="https://img.shields.io/github/license/dthinkr/trading_platform?color=2b9348" alt="License Badge"/></a>
</p>

## Key Features (v2.2.0) 🚀

### 🏗️ **Session-Based Architecture**
- Lightweight session pools with lazy market creation
- Zero resource waste from zombie markets

### 🎭 **Role-Based Trading**
- Informed traders (buy/sell specialists) 
- Speculators (flexible strategies)
- Automatic goal-based trader matching

### 👥 **Multi-Trader Markets**
- Coordinated market starts when all traders ready
- Real-time status updates and waiting room
- Seamless session-to-market conversion

### 📊 **Real-Time Data**
- Live order book and price charts
- Instant execution feedback
- Market summary with P&L and VWAP

### 🔒 **Infrastructure**
- Google authentication
- WebSocket communication
- Comprehensive error handling
- Modular event-driven architecture

## 🏗️ **How Multi-Trader Markets Work**

Session pool mechanism handles multiple human traders elegantly:

### Session Pool Phase
1. Users join lightweight session pools (not heavy markets)
2. Goal assignment based on predefined slots (e.g., [100, -200, 150])
3. Real-time trader count updates ("2 out of 3 traders joined")

### Market Creation Phase  
1. All traders ready → automatic market creation
2. Heavy infrastructure created only when needed
3. Human + AI traders added, trading begins

### Benefits
- Fast user onboarding
- Zero resource waste  
- Automatic role assignment
- Seamless scaling

## Quick Start

### One-Line Installation

```bash
bash <(curl -sSL https://raw.githubusercontent.com/dthinkr/trading_platform/main/trading_platform_run.sh)
```

### Development Setup

```bash
# Frontend
cd front
npm install
npm run dev

# Backend
cd back
pip install -r requirements.txt
uvicorn api.endpoints:app --reload
```

## Documentation

For detailed documentation, feature explanations, and API references, please visit our [Wiki](https://github.com/dthinkr/trading_platform/wiki).

## Recent Updates

See our [Changelog](CHANGELOG.md) for detailed version history and updates.

## License

MIT License - see [LICENSE](LICENSE) for details.

---
