import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (
    NegativeValueException,
    EndpointHTTPException,
    InvalidTaskStatusException,
)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s, [%(levelname)s], %(message)s, %(name)s',
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}


def check_tokens():
    """Функция проверяет доступность переменных окружения."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }
    for token, value in tokens.items():
        if value is None:
            logger.critical(
                f'Отсутствует обязательная переменная окружения: {token}. '
                f'Программа принудительно остановлена.'
            )
            return False
    return True


def send_message(bot, message):
    """Функция отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Бот отправил сообщение в Telegram: {message}')
    except Exception as error:
        logging.error(
            f'Сбой при отправке сообщения в Telegram: {error}',
            exc_info=True,
        )


def get_api_answer(timestamp):
    """Функция запроса к эндпоинту API-сервиса Практикум.Домашка."""
    payload = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            url=ENDPOINT, headers=HEADERS, params=payload
        )
        if homework_statuses.status_code != HTTPStatus.OK:
            logging.error(
                f'Эндпоинт {ENDPOINT} недоступен. '
                f'Код ответа API: {homework_statuses.status_code}'
            )
            raise EndpointHTTPException(
                f'Эндпоинт {ENDPOINT} недоступен. '
                f'Код ответа API: {homework_statuses.status_code}'
            )
        return homework_statuses.json()
    except requests.exceptions.RequestException:
        logging.error('Сбой при запросе к эндпоинту!')


def check_response(response):
    """Функция проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('Вернулся не словарь!')
    if 'homeworks' not in response:
        logging.error('Ответ от API не содержит ключ homeworks')
        raise KeyError('Ответ от API не содержит ключ homeworks')
    if 'current_date' not in response:
        logging.error('Ответ от API не содержит ключ current_date')
        raise KeyError('Ответ от API не содержит ключ current_date')
    homework = response.get('homeworks')
    if not isinstance(homework, list) or not homework:
        raise TypeError('Вернулся не список!')
    return homework


def parse_status(homework):
    """Функция извлекает статус домашней работы."""
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise KeyError('Ответ от API не содержит ключ homework_name!')
    status = homework.get('status')
    if status is None:
        raise KeyError('Ответ от API не содержит ключ status!')
    verdict = HOMEWORK_VERDICTS.get(status)
    if verdict is None:
        logging.error('Получен неожиданный статус работы!')
        raise InvalidTaskStatusException('Получен неожиданный статус работы!')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise NegativeValueException(
            'Отсутствует обязательная переменная окружения!'
        )
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    previous_update = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if homework[0].get('date_updated') != previous_update:
                message = parse_status(homework[0])
                send_message(bot, message)
                previous_update = homework[0].get('date_updated')
            else:
                logging.debug('Статус работы не изменился.')
        except Exception as error:
            logging.error(error, exc_info=True)
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
