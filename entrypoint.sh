#!/bin/sh
# Start Uvicorn with live reload
uvicorn client_connector.main:app --host 0.0.0.0 --port $PORT