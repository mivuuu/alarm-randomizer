# Alarm Randomizer

Termux Telegram bot for randomized alert posts.

## Run in Termux

```sh
cd alarm-app
pip install -r requirements.txt
python termux_bot.py
```

On first start, enter the Telegram bot token and channel ID. The bot stores them in `bot_config.json`.

Optional test run:

```sh
python termux_bot.py --test
```
