# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

- Make all Control Questions mandatory and show correct answers with explanations
- Fix order cancellation not removing orders from the table
- Correct share count updates when buying/selling
- Review and adjust initial midprice and tick size
- Adjust profits to range from 5 to 15 GBP

## [1.0.1] - 2024-07-26

### Added

- Implemented 'Next' and 'Back' buttons for navigation between instruction pages
- Automatically generate instruction page information from parameter settings
- Moved 'Start Trading' button to the end of all instructions
- Added a table showing the goal, initial shares, and initial cash before market start
- Implemented market wrapping under a single link with 'Next' button navigation

### Changed

- Calibrated exchange rate from liras to GBP

### Improved

- Enhanced user interface for better navigation and clarity
- Updated documentation to reflect new features and changes

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

[1.0.1]: https://github.com/dthinkr/trading_platform/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/dthinkr/trading_platform/compare/v0.2.0...v1.0.0
[0.2.0]: https://github.com/dthinkr/trading_platform/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/dthinkr/trading_platform/releases/tag/v0.1.0
