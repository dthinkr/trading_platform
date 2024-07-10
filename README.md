
# Trading Platform

![Trading Platform Logo](front/src/assets/trading_platform_logo.svg)

A trading platform for conducting financial market experiments and simulations.

## 🚀 Features

- Real-time trading simulation
- WebSocket-based communication
- Vue.js frontend with Vuetify
- FastAPI backend
- Customizable trading scenarios
- Data analysis tools

## 📋 Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

## 🛠 Installation

### Frontend

```bash
cd front
npm install
```


### Backend

```bash
cd back
pip install -r requirements.txt
```

## 🖥 Usage

### Starting the Development Server

#### Frontend

```bash
cd front
npm run dev
```

The frontend will be accessible at `http://localhost:3000`.

#### Backend

```bash
cd back
uvicorn client_connector.main:app --reload
```

The backend API will be available at `http://localhost:8000`.

### Building for Production

```bash
cd front
npm run build
```

## 🗂 Project Structure

```
trading_platform/
├── front/                 # Vue.js frontend
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
├── back/                  # FastAPI backend
│   ├── client_connector/
│   ├── main_platform/
│   ├── traders/
│   ├── structures/
│   └── analysis/
└── README.md
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

- [Vue.js](https://vuejs.org/)
- [Vuetify](https://vuetifyjs.com/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Highcharts](https://www.highcharts.com/)
