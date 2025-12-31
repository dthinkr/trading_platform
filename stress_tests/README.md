# Trading Platform Stress Testing Suite

Comprehensive stress testing tools to measure platform performance under various load conditions.

## Files

### Core Test Scripts
- **`stress_test.py`** - Main stress testing script (login/session capacity)
- **`test_session_manager.py`** - Session manager tests (slot assignment, goal changes)

### Visualization Tools
- **`visualize_results.py`** - Generate charts from stress test results

### Utilities
- **`run_full_test.sh`** - Run complete test suite with visualization
- **`README.md`** - This file

### Generated Files (ignored by git)
- `*_results_*.json` - Test result data
- `*_charts_*.png` - Generated visualizations
- `*_report_*.txt` - Test reports
- `__pycache__/` - Python cache

## Quick Start

### 1. Make sure backend is running

```bash
cd ../back
python -m uvicorn api.endpoints:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Run the full test suite

```bash
cd stress_tests
chmod +x run_full_test.sh
./run_full_test.sh
```

This will:
- Run 5 stress tests with increasing user loads (5, 10, 20, 50, 100 users)
- Generate performance charts
- Create a summary report

## Manual Testing

### Single Test

Test with specific number of users:

```bash
python stress_test.py --users 50 --batch-size 10
```

Options:
- `--users N` - Number of users to simulate
- `--batch-size N` - Concurrent requests per batch
- `--backend URL` - Backend URL (default: http://localhost:8000)

### Multiple Tests

Run predefined test suite:

```bash
python stress_test.py --multi-test
```

### Generate Charts from Existing Results

```bash
python visualize_results.py
```

Or specify a specific results file:

```bash
python visualize_results.py --results stress_test_results_20250108_123456.json
```

## Metrics Collected

### Performance Metrics
- **Login Response Time** - Avg, median, min, max login times
- **Throughput** - Users processed per second
- **Total Duration** - Time to complete full test
- **Success Rate** - Percentage of successful logins
- **Error Count** - Number of failed operations

### Charts Generated

1. **Login Success Rate** - Success rate vs number of users
2. **Login Response Time** - Average and median response times
3. **Platform Throughput** - Users processed per second
4. **Total Test Duration** - Time to complete each test
5. **Error Count** - Errors encountered per test
6. **Login Time Range** - Min/median/max distribution
7. **Scalability Analysis** - Actual vs ideal linear scaling
8. **Success/Failure Breakdown** - Stacked bar chart
9. **Summary Statistics** - Key metrics table

## Output Files

After running tests, you'll get:

- `stress_test_results_TIMESTAMP.json` - Raw test data
- `stress_test_charts_TIMESTAMP.png` - Performance charts (high-res)
- `stress_test_report_TIMESTAMP.txt` - Text summary report

## Example Use Cases

### Test Maximum Capacity

```bash
# Test with 200 users
python stress_test.py --users 200 --batch-size 50
```

### Test Concurrent Sessions

```bash
# 100 users = 25 markets of 4 users each (with default config)
python stress_test.py --users 100 --batch-size 25
```

### Benchmark Different Configurations

1. Set 4 users per market:
```bash
curl -X POST http://localhost:8000/admin/update_base_settings \
  -H "Content-Type: application/json" \
  -d '{"settings": {"predefined_goals": [100, -200, 150, 50]}}'
```

2. Run test:
```bash
python stress_test.py --users 40 --batch-size 20
```

3. Set 10 users per market and compare:
```bash
curl -X POST http://localhost:8000/admin/update_base_settings \
  -H "Content-Type: application/json" \
  -d '{"settings": {"predefined_goals": [100, -200, 150, 50, -100, 75, -50, 125, -75, 25]}}'

python stress_test.py --users 40 --batch-size 20
```

## Interpreting Results

### Good Performance Indicators
- ✅ Success rate > 95%
- ✅ Average login time < 1s
- ✅ Throughput scales linearly with users
- ✅ Low error count

### Performance Issues
- ⚠️ Success rate < 90%
- ⚠️ Login time > 2s
- ⚠️ Throughput plateaus or decreases
- ⚠️ High error count

### Scalability
- **Linear scaling**: Duration increases proportionally with users (ideal)
- **Sub-linear**: Platform handles more users efficiently (excellent)
- **Super-linear**: Performance degrades with more users (needs optimization)

## Troubleshooting

### "Backend not running"
Start the backend:
```bash
cd ../back
python -m uvicorn api.endpoints:app --host 0.0.0.0 --port 8000
```

### "Connection refused" errors
- Check backend is accessible at http://localhost:8000
- Try reducing batch size: `--batch-size 5`

### High error rates
- Backend may be overloaded
- Try smaller user counts
- Check backend logs for errors

### Module not found
Install dependencies:
```bash
pip install aiohttp matplotlib numpy
```

## Advanced Usage

### Custom Test Configuration

Edit `stress_test.py` and modify `test_configs`:

```python
test_configs = [
    {'num_users': 10, 'batch_size': 5},
    {'num_users': 25, 'batch_size': 10},
    {'num_users': 50, 'batch_size': 15},
    # Add your own configurations
]
```

### Continuous Monitoring

Run tests periodically to monitor platform performance over time:

```bash
# Run every hour
watch -n 3600 "./run_full_test.sh"
```

### Integration with CI/CD

Add to your CI pipeline:

```yaml
- name: Stress Test
  run: |
    cd stress_tests
    python stress_test.py --users 50 --batch-size 10
    # Fail if success rate < 95%
    python -c "import json; d=json.load(open('stress_test_results_*.json')); assert d[0]['summary']['success_rate'] > 95"
```

## Platform Capacity Guidelines

Based on testing:

| Users per Market | Recommended Max Concurrent Users | Expected Throughput |
|-----------------|----------------------------------|---------------------|
| 4               | 100-200                          | ~20-30 users/sec    |
| 5               | 100-250                          | ~20-35 users/sec    |
| 10              | 200-500                          | ~25-40 users/sec    |

*Actual numbers depend on server resources*

