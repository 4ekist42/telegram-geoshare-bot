import os
import logging
from typing import Dict, Set, Tuple

from aiogram import Bot, Dispatcher

from .models import Config, UserState
from .config_loader import load_json_config, parse_config


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

CONFIG_PATH = os.getenv("CONFIG_PATH", "config.json")
CONFIG: Config = parse_config(load_json_config(CONFIG_PATH))
logging.info("Конфиг загружен: %d зон, %d админов", len(CONFIG.zones), len(CONFIG.telegram.admins))

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Переменная окружения BOT_TOKEN не задана")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

active_live_locations: Set[int] = set()
user_states: Dict[int, UserState] = {}
absent_notified: Set[Tuple[int, int]] = set()