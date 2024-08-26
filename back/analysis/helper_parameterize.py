import itertools
import json
from typing import Dict, List, Optional, Tuple, Union

import matplotlib.pyplot as plt
from SALib.sample import sobol
from sklearn.decomposition import PCA

from structures.structures import TradeDirection, TraderCreationData


def generate_sobol_parameters(
    bounds: Dict[str, Tuple[float, float]], resolution: int
) -> List[List[float]]:
    problem = {
        "num_vars": len(bounds),
        "names": list(bounds.keys()),
        "bounds": [bounds[name] for name in bounds.keys()],
    }
    param_values = sobol.sample(problem, 2**resolution)
    return param_values


def store_parameters(filename: str, parameters: List[Dict[str, float]]) -> None:
    with open(filename, "w") as f:
        json.dump(parameters, f)


def generate_and_store_parameters(
    bounds: Dict[str, Union[Tuple[float, float], List[float]]],
    resolution: int,
    filepath: Optional[str] = None,
) -> Union[Tuple[List[Dict[str, float]], List[Dict[str, float]], Dict], None]:
    sobol_problem = None
    if all(isinstance(b, list) for b in bounds.values()):
        keys = list(bounds.keys())
        values_product = list(itertools.product(*bounds.values()))
        parameter_dicts = [
            {key: value for key, value in zip(keys, values)}
            for values in values_product
        ]
        unscaled_params = parameter_dicts.copy()
    else:
        sobol_problem = {
            "num_vars": len(bounds),
            "names": list(bounds.keys()),
            "bounds": [bounds[name] for name in bounds.keys()],
        }
        sobol_params = generate_sobol_parameters(bounds, resolution)
        print(sobol_params)
        parameter_dicts = []
        unscaled_params = []
        for params in sobol_params:
            param_dict = {}
            unscaled_dict = {}
            for name, value in zip(bounds.keys(), params):
                unscaled_dict[name] = value
                if name == "informed_trade_direction":
                    param_dict[name] = "buy" if round(value) == 1 else "sell"
                elif isinstance(bounds[name][0], int) and isinstance(
                    bounds[name][1], int
                ):
                    param_dict[name] = int(round(value))
                else:
                    param_dict[name] = value
            parameter_dicts.append(param_dict)
            unscaled_params.append(unscaled_dict)

    validated_params = [
        TraderCreationData(**params).dict() for params in parameter_dicts
    ]

    if filepath:
        store_parameters(filepath, validated_params)
        return None
    else:
        return validated_params, unscaled_params, sobol_problem

def plot_parameters(parameters: List[Dict[str, float]]) -> None:
    data = []
    for param in parameters:
        row = []
        for value in param.values():
            if isinstance(value, (int, float)):
                row.append(value)
        if row:
            data.append(row)

    if not data:
        return

    pca = PCA(n_components=2)
    reduced_data = pca.fit_transform(data)
    plt.figure(figsize=(8, 6))
    plt.scatter(reduced_data[:, 0], reduced_data[:, 1], alpha=0.5)
    plt.title("Parameter Space Visualization")
    plt.xlabel("Principal Component 1")
    plt.ylabel("Principal Component 2")
    plt.grid(True)
    plt.savefig("analysis/results/parameter_space.pdf")
    plt.show()
