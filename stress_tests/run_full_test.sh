#!/bin/bash

# Full Stress Test Suite
# Runs comprehensive tests and generates visualizations

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Trading Platform - Full Stress Test Suite                    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check if backend is running
if ! curl -s http://localhost:8000/traders/defaults > /dev/null 2>&1; then
    echo "❌ Error: Backend is not running on port 8000"
    echo "   Please start the backend first with:"
    echo "   cd ../back && python -m uvicorn api.endpoints:app --host 0.0.0.0 --port 8000"
    exit 1
fi

echo "✓ Backend is running"
echo ""

# Install dependencies if needed
echo "Checking dependencies..."
pip install -q aiohttp matplotlib numpy 2>/dev/null

echo "✓ Dependencies ready"
echo ""

# Configure platform for 4 users per market
echo "Configuring platform (4 users per market)..."
curl -s -X POST http://localhost:8000/admin/update_base_settings \
  -H "Content-Type: application/json" \
  -d '{"settings": {"predefined_goals": [100, -200, 150, 50]}}' > /dev/null

echo "✓ Configuration updated"
echo ""

# Run stress tests
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Running Stress Tests                                          ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

python stress_test.py --multi-test

# Generate visualizations
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Generating Visualizations                                     ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

python visualize_results.py

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Test Suite Complete!                                          ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Output files generated in current directory:"
ls -lh stress_test_* 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
echo ""

