import random

import numpy as np
import pandas as pd

from analysis import load_config
from analysis.helper_prepare_data import prepare_data

CONFIG = load_config()


def run_lobster(max_depth: int = 10) -> pd.DataFrame:
    df_ref, df_res = prepare_data()
    df_copy = df_res.to_pandas()

    num_values = max_depth * 4

    if "LOBSTER_BOOK" in df_copy.columns:

        def convert_and_flatten(entry):
            if isinstance(entry, pd.DataFrame):
                return entry.iloc[0].tolist()
            elif isinstance(entry, np.ndarray):
                return entry.tolist()
            elif hasattr(entry, "to_pandas"):
                if len(entry) == 0:
                    return [np.nan] * num_values
                return entry.to_pandas().iloc[0].tolist()
            return [np.nan] * num_values

        df_copy["LOBSTER_BOOK"] = df_copy["LOBSTER_BOOK"].apply(convert_and_flatten)

        # expand the LOBSTER_BOOK column
        try:
            lobster_book_df = pd.DataFrame(
                df_copy["LOBSTER_BOOK"].tolist(), index=df_copy.index
            )
            lobster_book_df.columns = [f"LOBSTER_BOOK_{i}" for i in range(num_values)]
        except Exception as e:
            print("Error expanding LOBSTER_BOOK:", e)
            lobster_book_df = pd.DataFrame(
                columns=[f"LOBSTER_BOOK_{i}" for i in range(num_values)]
            )

        result_df = pd.concat(
            [df_copy[CONFIG.MESSAGE_COLUMNS], lobster_book_df], axis=1
        )
    else:
        # if LOBSTER does not exist, create the desired structure
        lobster_book_df = pd.DataFrame(
            columns=[f"LOBSTER_BOOK_{i}" for i in range(num_values)]
        )
        result_df = pd.concat(
            [df_copy[CONFIG.MESSAGE_COLUMNS], lobster_book_df], axis=1
        )

    # save
    result_df.to_csv(f"{CONFIG.DATA_DIR}/LOBSTER.csv", index=False)
    return result_df


def pick_one(trading_session_id: str = None, max_depth: int = 10) -> pd.DataFrame:
    df = run_lobster(max_depth)
    if trading_session_id:
        filtered_df = df[df["trading_session_id"] == trading_session_id]
    else:
        unique_ids = df["trading_session_id"].drop_duplicates().tolist()
        if unique_ids:
            # selected_id = random.choice(unique_ids)
            selected_id = unique_ids[-1]
            filtered_df = df[df["trading_session_id"] == selected_id]
        else:
            return pd.DataFrame()  # Return empty if no IDs found

    if not filtered_df.empty:
        filtered_df.to_csv(
            f"{CONFIG.DATA_DIR}/LOBSTER_{filtered_df['trading_session_id'].iloc[0]}.csv",
            index=False,
        )
    return filtered_df


if __name__ == "__main__":
    # run_lobster()
    pick_one()
