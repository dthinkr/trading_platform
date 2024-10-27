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

## Key Features (v2.0.0)

- 🎭 Advanced Role-Based Trading System
  - Informed Traders (Buy/Sell specialists)
  - Speculators (Free trading)
  - Persistent roles across sessions
- 👥 Multi-Trader Sessions
  - Coordinated session starts
  - Real-time trader status updates
  - Enhanced waiting room interface
- 📊 Real-Time Market Data
  - Live order book visualization
  - Dynamic price charts
  - Instant trade execution feedback
- 🔒 Secure Authentication
  - Google-based login
  - Role persistence
  - Session management
- 📈 Advanced Analytics
  - Session metrics download
  - Performance tracking
  - Goal achievement monitoring

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
