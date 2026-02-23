#configs

import os 
from dotenv import load_dotenv


load_dotenv() 

# Получаем значения
TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))  # 0 если не найден


# Проверка что токен загружен
if not TOKEN:
    raise ValueError("Нет токена! Создай файл .env with:\n BOT_TOKEN=example_token\n ADMINE_ID=example_id")