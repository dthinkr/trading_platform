# Trading Platform Tests

## Overview
After removing RabbitMQ from the architecture, we've created new endpoint health tests to ensure the refactored system works correctly.

## Running Tests with Pytest

### All Tests
```bash
cd back
pytest tests/ -v
```

### Specific Endpoint Health Tests
```bash
cd back
pytest tests/test_endpoints_health.py -v
```

### Integration Tests Only
```bash
cd back
pytest tests/test_endpoints_health.py::TestEndpointIntegration -v
```

## Continuous Testing
For continuous monitoring during development:
```bash
cd back/tests
python test_endpoint_health.py --interval 10 --max 5
```

Options:
- `--interval X`: Test every X seconds (default: 30)
- `--max N`: Run N iterations then stop
- `--once`: Run once and exit
- `--url URL`: Test different URL (default: http://localhost:8000)

## What We're Testing
1. **Root endpoint** (`/`) - Basic server health
2. **Trader defaults** (`/traders/defaults`) - Configuration endpoint  
3. **Trader info** (`/trader_info/HUMAN_*`) - The problematic endpoint after RabbitMQ removal

## Expected Results
- Root endpoint: ✅ 200 OK
- Trader defaults: ✅ 200 OK  
- Trader info: ✅ 401 Unauthorized (expected, requires auth)

## Debugging 500 Errors
If you see 500 Internal Server Errors:
1. Check the FastAPI server logs for detailed debug output
2. The `trader_info` endpoint now has enhanced logging
3. Look for database/RabbitMQ connection errors

## Server Setup
Make sure your FastAPI server is running:
```bash
cd back
python -m uvicorn api.endpoints:app --reload
``` 