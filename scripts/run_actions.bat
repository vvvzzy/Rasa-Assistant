@echo off
call conda activate rasa-order-bot
rasa run actions --debug
