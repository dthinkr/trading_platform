import requests
import json

def create_trading_session(trader_data):
    url = 'http://localhost:8000/trading/initiate'
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, data=json.dumps(trader_data), headers=headers)
    return response.json()

def main():
    # Adjusted trader data to match the TraderCreationData model
    trader_data = {
        "num_human_traders": 1,
        "num_noise_traders": 1,
        "num_informed_traders": 1,
        "trading_day_duration": 10,  # Duration in minutes
        "step": 1,
        "activity_frequency": 1.0,  # Frequency in seconds
        "order_amount": 1,
        "trade_intensity_informed": 0.1,
        "trade_direction_informed": "sell",  # Use string value of the enum
        "noise_warm_ups": 10,
        "initial_cash": 100000,
        "initial_stocks": 100,
        "depth_book_shown": 5
    }
    
    # Create a trading session
    result = create_trading_session(trader_data)
    print("Trading Session Initiated:", result)

if __name__ == "__main__":
    main()