# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Parameter change tracking system
  - New JSON-based parameter history with timestamped states
  - Added `/admin/download_parameter_history` endpoint
  - Added parameter history download button in market configuration UI

To propose changes:

1. Edit this section directly in CHANGELOG.md
2. Add your proposed change under the appropriate category below
3. Use the format: "- [ ] Your proposed change"

### Proposed Features

- [X] Add better error handling for partially filled markets
- [ ] Conversion rate implementation and payoff display (due to missing max profit, both upper and lower bounds, definition)
- [X] Informed side randomization option
- [X] End of market page (screenshot attached)
- ​[X] Adjusted price display so prices are more visible (implemented while the proposed questions re x axis were not clarified)
- ​[X] Informed option to enable passive orders

## [2.0.2][2.0.2] - 2024-11-02

### Fixed

- Added retry mechanism (2.5s) to prevent creation of partially filled markets
- Improved market validation before creation
- Enhanced cleanup of incomplete markets

## [2.0.1][2.0.1] - 2024-11-01

### Fixed

- Fixed double counting of passive orders in trade history display
- Improved goal assignment system to maintain consistent roles across markets
- Renamed "Order History" to "Trades History" for clarity
- Enhanced trade history display with better position tracking and VWAP calculations

### Changed

- Moved goal assignment parameters to human parameters section
- Simplified random goal assignment to maintain role consistency while allowing sign flips
- Added visual improvements to trade history display including better organization of buy/sell trades

## [2.0.0][2.0.0] - 2024-10-25

### Added

- New role assignment system with persistent user roles across markets
- Real-time market status updates showing ready traders count
- Enhanced waiting room interface with clear market status indicators
- Improved trader role display with distinct visual indicators for:
  - Informed (Buy) traders
  - Informed (Sell) traders
  - Speculator traders
- Market coordination system requiring all traders to be ready before start

### Changed

- Fundamentally changed market management:
  - Markets now require all traders to actively press "Start Trading"
  - Trading only begins when all expected traders are present and ready
  - Each market now maintains exactly one informed trader
- Improved role persistence: user roles now persist across market refreshes
- Enhanced user experience:
  - Clearer role indicators with color-coded chips and icons
  - Better visual feedback for market status
  - More intuitive waiting room interface

### Fixed

- Market state preservation when refreshing the page
- Role assignment consistency across multiple markets
- User authentication and market management
- Gmail address now correctly associated with one human trader at any time

### Removed

- Market timeout functionality for more stable market management
- Automatic market termination for incomplete trader groups

## [1.3.5][1.3.5] - 2024-10-16

### Added

- Google Form integration for participant information collection
- Automatic task randomization for multiple markets
- Log file generation for each market market

### Changed

- Implemented participant verification system for platform login
- Updated backend to support multiple market markets per participant

### Fixed

- Resolved issues with manual task setting in admin panel

## [1.3.4][1.3.4] - 2024-10-16

### Added

- Implemented automatic periodic update of registered users on server startup

### Changed

- Refactored startup event to use asyncio for better performance

### Fixed

- Resolved issue with registered users not being updated regularly

## [1.3.3] - 2024-10-10

### Changed

- Updated frontend components to improve consistency and user experience:
  - Adjusted font sizes and styles across all components
  - Improved layout and spacing in ActiveOrders, OrderHistory, and PlaceOrder components
  - Enhanced chart readability in PriceHistory and BidAskDistribution components
  - Standardized the use of 'Inter' font family throughout the interface
  - Refined color scheme for better visual hierarchy

### Fixed

- Resolved issues with price formatting in ActiveOrders and PlaceOrder components
- Improved responsiveness and scrolling behavior in various components

## [1.3.2] - 2024-10-02

### Fixed

- Resolved issue with trading market not starting properly
- Fixed issue where passive orders show on both buy and sell sides of order history
- Adjusted chart sizes, now they should be properly displayed
- The deployment now monitors changes in the "deploy" branch and automatically updates the production version

## [1.3.1][1.3.1] - 2024-09-17

### Added

- Implemented download of market metrics from log files
- Enhanced frontend to display CSV data preview after downloading metrics
- Enabled user authentication system
- Implemented multi-trader, multi-market trading, platforms starts only after participants are ready
- Added support for manual setting of goals for each human trader
- Add options to set trader as Informed or Speculator
- Improved display of bought/sold shares at top right of platform
- Add Market Earnings calculation and display
- Implement correct counting of shares needed to reach the goal

### Changed

- Refactored backend structure for increased modularity
- Improved frontend routes and trading platform UI
- Enhanced trading dashboard with better order display
- Updated websocket connection handling
- Simplified order sending process to use button clicks
- Improved My Orders Page with faster updates of outstanding orders
- Remove market updates messages from top left of trading platform

### Fixed

- Corrected login behavior for proper trading platform access
- Resolved issues with human trader messages after refactoring
- Improved transaction history display
- Fixed display of sell order goals at end of page
- Addressed various frontend and backend bugs

### Removed

- Eliminated database dependency, shifting to log-based data storage
- Removed potentially confusing metrics (initial cash, final cash, etc.)
- Removed dollar sign from initial and final shares display

### Known Issues

- Some human trader messages may be missing after recent refactoring
- Certain aspects of the trading platform require additional fixes

## [1.2.0][1.2.0] - 2024-08-29

### Added

- Enhanced metrics to show both sides of each matched order
- Improved Order ID system for better traceability
- New Informed Trader behavior with dynamic passive order management
- Refined Noise Trader with dynamically consistent activity frequency and internal clock

### Known Issue

- Informed Trader now achieves approximately 1.3 times its expected goal

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

- Background processing for multiple trading markets
- Visual summary of time-series results directly on the platform

### Changed

- Review and adjust initial midprice and tick size

## [1.0.2] - 2024-08-01

### Changed

- Redesigned both front and back of the trading platform
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
- Integrated front and back with a cleaner structure
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
- front timer now syncs with the back

## [0.1.0][0.1.0] - 2024-07-01

### Added

- Initial fork of the Trading Platform from [chapkovski/trader_london](https://github.com/chapkovski/trader_london)
- Real-time trading simulation
- WebSocket-based communication
- Vue.js front with Vuetify
- FastAPI back
- Customizable trading scenarios
- Basic data analysis tools

[2.0.2]: https://github.com/dthinkr/trading_platform/compare/v2.0.1...v2.0.2
[2.0.1]: https://github.com/dthinkr/trading_platform/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/dthinkr/trading_platform/compare/v1.3.5...v2.0.0
[1.3.5]: https://github.com/dthinkr/trading_platform/compare/v1.3.4...v1.3.5
[1.3.4]: https://github.com/dthinkr/trading_platform/compare/v1.3.3...v1.3.4
[1.3.1]: https://github.com/dthinkr/trading_platform/compare/v1.2.0...v1.3.1
[1.2.0]: https://github.com/dthinkr/trading_platform/compare/v1.1.1...v1.2.0
[1.1.1]: https://github.com/dthinkr/trading_platform/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/dthinkr/trading_platform/compare/v1.0.2...v1.1.0
[1.0.1]: https://github.com/dthinkr/trading_platform/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/dthinkr/trading_platform/compare/v0.2.0...v1.0.0
[0.2.0]: https://github.com/dthinkr/trading_platform/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/dthinkr/trading_platform/releases/tag/v0.1.0
