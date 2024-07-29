# import pytest
# import polars as pl
# from pymongo import MongoClient
# from analysis.run_lobster import pick_one

# def test_all_comparisons_true():
#     # Connect to DB
#     client = MongoClient("localhost", 27017)
#     db = client["trader"]
#     collection = db["message"]
#     trading_session_id = "3ff39a04-d244-44f1-b9a0-a33465394143"
#     documents = list(collection.find({"trading_session_id": trading_session_id}))
#     run_data = pl.DataFrame(documents)

#     lobster_data = pick_one(trading_session_id)
#     lobster_data = pl.from_pandas(lobster_data)
#     lobster_data = lobster_data.drop(['trading_session_id', 'Event Type', 'Order ID', 'Size', 'Price', 'Direction'])

#     comparison_results = []

#     for i in range(len(lobster_data)):
#         lobster_value = lobster_data['LOBSTER_BOOK_0'][i]
        
#         if lobster_value is not True:
#             # If NaN, append True
#             comparison_results.append(True)
#         else:
#             # If not NaN, compare with 'best_ask_prices'
#             best_ask_value = run_data['best_ask_prices'][i]
#             comparison_results.append(lobster_value == best_ask_value)

#     run_data = run_data.with_columns(pl.Series("comparison_with_lobster", comparison_results))

#     all_true = run_data['comparison_with_lobster'].all()

#     assert all_true, "Not all comparisons are True"