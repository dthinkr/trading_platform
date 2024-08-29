import os
import json
import numpy as np
import matplotlib.pyplot as plt
from SALib.analyze import sobol
from .record_pm import get_time_series_metrics_for_sessions
from .utilities import load_config

CONFIG = load_config()


def load_problem_and_sessions():
    latest_file = max(
        [
            f
            for f in os.listdir(CONFIG.DATA_DIR)
            if f.startswith("trader_data_mapping") and f.endswith(".json")
        ],
        key=lambda f: os.path.getmtime(os.path.join(CONFIG.DATA_DIR, f)),
    )
    with open(os.path.join(CONFIG.DATA_DIR, latest_file), "r") as f:
        data = json.load(f)

    problem = data["sobol_problem"]
    sorted_sessions = sorted(data["sessions"].items(), key=lambda x: x[1]["order"])
    sorted_session_ids = [session[0] for session in sorted_sessions]

    # Extract date and time from the filename
    parts = latest_file.split("_")
    date_str = f"{parts[2]}_{parts[3].split('.')[0]}"

    return problem, sorted_session_ids, date_str


def process_results(sorted_session_ids):
    time_series_metrics = get_time_series_metrics_for_sessions(sorted_session_ids)
    return process_session_data(time_series_metrics, sorted_session_ids)


def process_session_data(time_series_metrics, sorted_session_ids):
    processed_data = {}
    min_time = float("inf")
    max_time = 0

    for session_id in sorted_session_ids:
        key = (session_id,)
        if key not in time_series_metrics:
            print(f"Warning: No time series data for session {session_id}")
            continue
        df = time_series_metrics[key]
        seconds = df["seconds_into_session"].to_numpy()
        min_time = min(min_time, np.floor(seconds.min()))
        max_time = max(max_time, np.ceil(seconds.max()))

    if min_time == float("inf") or max_time == 0:
        print("Error: No valid time series data found")
        return None, None

    time_range = np.arange(int(min_time), int(max_time) + 1)

    for session_id in sorted_session_ids:
        key = (session_id,)
        if key not in time_series_metrics:
            continue
        df = time_series_metrics[key]
        seconds = df["seconds_into_session"].to_numpy()
        imbalances = df["order_book_imbalance"].to_numpy()

        processed_imbalances = np.zeros_like(time_range, dtype=float)
        for i, t in enumerate(time_range):
            mask = (seconds >= t - 0.5) & (seconds < t + 0.5)
            if np.any(mask):
                processed_imbalances[i] = np.mean(imbalances[mask])
            elif i > 0:
                processed_imbalances[i] = processed_imbalances[i - 1]

        processed_data[session_id] = processed_imbalances

    return time_range, processed_data


def run_sobol_analysis(problem, Y):
    Si_first = np.zeros((Y.shape[1], len(problem["names"])))
    Si_total = np.zeros((Y.shape[1], len(problem["names"])))

    for i in range(Y.shape[1]):
        Si = sobol.analyze(problem, Y[:, i], print_to_console=False)
        Si_first[i, :] = Si["S1"]
        Si_total[i, :] = Si["ST"]

    return {"S1": Si_first, "ST": Si_total}


def plot_sobol_indices(time_range, Si, problem, date_str):
    plt.figure(figsize=(12, 6))
    for i, param in enumerate(problem["names"]):
        plt.plot(time_range, Si["S1"][:, i], label=f"{param} (First Order)")
        plt.plot(
            time_range, Si["ST"][:, i], label=f"{param} (Total Order)", linestyle="--"
        )

    plt.xlabel("Time")
    plt.ylabel("Sensitivity Index")
    plt.title(f"Sobol Sensitivity Indices Over Time - {date_str}")
    plt.legend()
    plt.grid(True)
    plt.savefig(
        os.path.join(CONFIG.DATA_DIR, f"figs/sobol_sensitivity_indices_{date_str}.png")
    )
    plt.close()


def export_sobol_indices(Si, problem, date_str):
    export_data = {
        "parameters": problem["names"],
        "S1": Si["S1"].tolist(),
        "ST": Si["ST"].tolist(),
    }
    with open(
        os.path.join(CONFIG.DATA_DIR, f"sobol_indices_{date_str}.json"), "w"
    ) as f:
        json.dump(export_data, f, indent=2)


if __name__ == "__main__":
    problem, sorted_session_ids, date_str = load_problem_and_sessions()
    time_range, processed_data = process_results(sorted_session_ids)

    if processed_data is None:
        print("Error: Could not process results")
    else:
        Y = np.array([processed_data[sid] for sid in sorted_session_ids])
        Si = run_sobol_analysis(problem, Y)
        plot_sobol_indices(time_range, Si, problem, date_str)
        export_sobol_indices(Si, problem, date_str)
