# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

- Make all Control Questions mandatory and show correct answers with explanations
- Adjust profits to range from 5 to 15 GBP

## [1.1.1][1.1.1] - 2024-08-26

### Fixed

- Corrected noise trader behavior to match expected order execution rate
- Fixed informed trader's trading volume calculation
- Improved trade execution recording in time series data
- Added columns for bid, ask, and actual trade price in time series output
- Refined num_trades column to accurately reflect executed trades

### Known Issue

- Order book log does not update correctly when there is matched trade

## [1.1.0][1.1.0] - 2024-08-16

### Added

- Background processing for multiple trading sessions
- Visual summary of time-series results directly on the platform

### Changed

- Review and adjust initial midprice and tick size

## [1.0.2] - 2024-08-01

### Changed

- Redesigned both frontend and backend of the trading platform
- Updated order matching logic for improved efficiency and accuracy
- Fix order cancellation not removing orders from the table
- Correct share count updates when buying/selling

## [1.0.1][1.0.1] - 2024-07-26

### Changed

- Implemented 'Next' and 'Back' buttons for navigation between instruction pages
- Automatically generate instruction page information from parameter settings
- Moved 'Start Trading' button to the end of all instructions
- Added a table showing the goal, initial shares, and initial cash before market start
- Implemented market wrapping under a single link with 'Next' button navigation
- Calibrated exchange rate from liras to GBP

## [1.0.0][1.0.0] - 2024-07-10

### Added

- Public access link to the trading platform (https://dthinkr.ngrok.app/)
- One-liner command for self-hosting the platform
- Expanded evaluation framework with 20+ time-series performance metrics
- Time-series sensitivity analysis capability
  - New feature to evaluate individual contributions of parameters to performance metrics variability
- New analysis tools in `/back/analysis` directory

### Changed

- Major overhaul of the trading platform for improved evaluation and understanding
- Integrated front and backend with a cleaner structure
- Refactored codebase for better maintainability and scalability

### Improved

- Enhanced documentation and README for easier onboarding and usage

### Known Issues

- Single access limitation to the trading platform
- Matching engine efficiency needs improvement
- Human traders' orders are not behaving correctly
- Inventory tracking requires further development

## [0.2.0][0.2.0] - 2024-07-04

### Changed

- Enhanced Noise Trader behavior to override existing orders when sending a new one
- Implemented controlled function for Order Book State
- Made default price configurable throughout the system

### Added

- Book initializer to set the initial order book state

### Improved

- Informed Trader behavior:
  - Orders now based on best bid plus an edge parameter
  - Updated order execution logic

### Fixed

- Timer and agents now do not act until the order book is initialized
- Frontend timer now syncs with the backend

## [0.1.0][0.1.0] - 2024-07-01

### Added

- Initial fork of the Trading Platform from [chapkovski/trader_london](https://github.com/chapkovski/trader_london)
- Real-time trading simulation
- WebSocket-based communication
- Vue.js frontend with Vuetify
- FastAPI backend
- Customizable trading scenarios
- Basic data analysis tools

[1.1.1]: https://github.com/dthinkr/trading_platform/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/dthinkr/trading_platform/compare/v1.0.2...v1.1.0
[1.0.1]: https://github.com/dthinkr/trading_platform/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/dthinkr/trading_platform/compare/v0.2.0...v1.0.0
[0.2.0]: https://github.com/dthinkr/trading_platform/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/dthinkr/trading_platform/releases/tag/v0.1.0
