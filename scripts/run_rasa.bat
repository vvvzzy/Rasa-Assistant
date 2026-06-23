@echo off
call conda activate rasa-order-bot
rasa run --enable-api --cors "*" --debug
