<p align="center">
  <img src="front/src/assets/trading_platform_logo.png" alt="Trading Platform Logo" width="200"/>
</p>

<h1 align="center">Trading Platform</h1>

<p align="center">
  A simple platform for conducting financial market experiments and simulations.
</p>

<p align="center">
  <a href="https://github.com/dthinkr/trading_platform/stargazers"><img src="https://img.shields.io/github/stars/dthinkr/trading_platform" alt="Stars Badge"/></a>
  <a href="https://github.com/dthinkr/trading_platform/network/members"><img src="https://img.shields.io/github/forks/dthinkr/trading_platform" alt="Forks Badge"/></a>
  <a href="https://github.com/dthinkr/trading_platform/pulls"><img src="https://img.shields.io/github/issues-pr/dthinkr/trading_platform" alt="Pull Requests Badge"/></a>
  <a href="https://github.com/dthinkr/trading_platform/issues"><img src="https://img.shields.io/github/issues/dthinkr/trading_platform" alt="Issues Badge"/></a>
  <a href="https://github.com/dthinkr/trading_platform/graphs/contributors"><img alt="GitHub contributors" src="https://img.shields.io/github/contributors/dthinkr/trading_platform?color=2b9348"></a>
  <a href="https://github.com/dthinkr/trading_platform/blob/master/LICENSE"><img src="https://img.shields.io/github/license/dthinkr/trading_platform?color=2b9348" alt="License Badge"/></a>
</p>

<p align="center">
  <a href="#key-features">Key Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#usage">Usage</a> •
  <a href="#project-structure">Project Structure</a> •
  <a href="#contributing">Contributing</a> •
  <a href="#license">License</a>
</p>

<p align="center">
    <img src="front/src/assets/demo.gif" alt="Trading Platform Demo" width="600">
  </p>
</div>

## Key Features

- 🚀 Real-time trading simulation
- 🌐 WebSocket-based communication
- 🖥️ Vue.js front with Vuetify
- ⚡ FastAPI back
- 🔧 Customizable trading scenarios
- 📊 Advanced data analysis tools

## Installation

### One-liner Self-Host

```bash
bash <(curl -sSL https://raw.githubusercontent.com/dthinkr/trading_platform/main/trading_platform_run.sh)
```

### Manual Setup

#### front

```bash
cd front
npm install
```

#### back

```bash
cd back
pip install -r requirements.txt
```

## Usage

### Development Server

#### front

```bash
cd front
npm run dev
```

Access at `http://localhost:3000`

#### back

```bash
cd back
uvicorn api.endpoints:app --reload
```

API available at `http://localhost:8000`

### Production Build

```bash
cd front
npm run build
```

## Project Structure

```
trading_platform/
├── front/                 # Vue.js front
│   ├── src/
│   │   ├── assets/
│   │   ├── components/
│   │   ├── layouts/
│   │   ├── pages/
│   │   ├── plugins/
│   │   ├── store/
│   │   └── styles/
│   ├── public/
│   └── package.json
├── back/                  # FastAPI back
│   ├── api/
│   ├── core/
│   ├── traders/
│   ├── data_models/
│   └── analysis/
└── README.md
```

## Recent Updates

For the most recent updates and changes, please refer to our [Changelog](CHANGELOG.md).

Key highlights from previous releases:

- 🔄 Background processing for multiple trading sessions
- 🖼️ Visual summary of time-series results
- 🎨 Redesigned platform front and back
- 🧭 Improved instruction flow with navigation buttons
- 🌐 Public access link and one-liner self-host command
- 📊 Expanded evaluation framework (20+ metrics)
- 🔄 Enhanced Noise and Informed Trader behaviors

## Contributing

We welcome contributions! Here's how you can help:

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgements

- [Vue.js](https://vuejs.org/)
- [Vuetify](https://vuetifyjs.com/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Highcharts](https://www.highcharts.com/)

---

<p align="center">
  Made with ❤️ by the Team
</p>
