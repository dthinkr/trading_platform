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

## Key Features (v2.0.0) 🚀

### 🏗️ **Elegant Session-Based Architecture**
- **Lightweight Session Pools**: Users join fast session pools, not heavy markets
- **Lazy Market Creation**: Markets created only when trading actually starts  
- **Zero Resource Waste**: No more zombie markets consuming resources
- **Simplified State Management**: 57% reduction in complexity (7→3 dictionaries)

### 🎭 **Advanced Role-Based Trading System**
- **Informed Traders**: Buy/Sell specialists with predefined goals
- **Speculators**: Free trading with flexible strategies
- **Persistent Roles**: Role assignment maintained across market sessions
- **Goal-Based Matching**: Automatic trader pairing based on complementary goals

### 👥 **Intelligent Multi-Trader Markets**
- **Coordinated Market Starts**: All traders must be ready before trading begins
- **Real-Time Status Updates**: Live trader count and readiness indicators
- **Enhanced Waiting Room**: Beautiful interface with session progress tracking
- **Automatic Market Launching**: Seamless transition from waiting to active trading

### 📊 **Real-Time Market Data & Analytics**
- **Live Order Book**: Dynamic depth visualization with real-time updates
- **Interactive Price Charts**: Historical price movement with trade markers
- **Instant Execution Feedback**: Immediate confirmation of trade executions
- **Market Summary Dashboard**: Real-time P&L, VWAP, and performance metrics

### 🔒 **Secure & Scalable Infrastructure**
- **Google-Based Authentication**: Secure login with Gmail integration
- **WebSocket Communication**: Real-time bidirectional data flow
- **Comprehensive Error Handling**: Robust message sanitization and validation
- **Event-Driven Architecture**: Modular design for maintainability and scaling

### 🎯 **Research-Grade Features**
- **Configurable Market Parameters**: Extensive customization for experimental design
- **Detailed Logging & Analytics**: Complete audit trail for research analysis
- **Export Capabilities**: Market data and metrics download for further analysis
- **Admin Management Panel**: Real-time monitoring and session control

## 🏗️ **How Multi-Trader Markets Work**

The platform uses an elegant **session pool mechanism** that handles multiple human traders in the same market:

### **Session Pool Phase (Lightweight & Fast)**
1. **Users join session pools** instead of heavy markets
2. **Goal assignment** based on predefined trader slots (e.g., [100, -200, 150])
3. **Real-time updates** show trader count (e.g., "2 out of 3 traders joined")
4. **Waiting room interface** provides smooth user experience

### **Market Creation Phase (On-Demand)**
1. **All traders ready** triggers automatic market creation
2. **Heavy infrastructure** (TraderManager, OrderBook) created only when needed
3. **Human + AI traders** added to complete market ecosystem
4. **Trading begins** with coordinated start across all participants

### **Key Benefits**
- ⚡ **Fast user onboarding** - no waiting for heavy market creation
- 🎯 **Zero resource waste** - markets created only when actually used
- 🔄 **Automatic role assignment** - balanced market composition
- 📊 **Seamless scaling** - handles 1 to N traders per market

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
