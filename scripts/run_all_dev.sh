#!/usr/bin/env bash
set -e
rasa run actions --debug &
sleep 3
rasa run --enable-api --cors "*" --debug &
sleep 3
python app.py
