## To generate data, use two commands:

python -m analysis.run_server

python -m analysis.run_simulation

## To anlayze data, use one command:

1. genereate time series sobol sensitivities, with order book imbalance used as the metric 

   1. python -m analysis.run_evaluation
2. generate a set of performance metrics

   1. python -m analysis.record_pm.py
