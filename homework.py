import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from telegram.error import TelegramError
from requests.exceptions import RequestException
from dotenv import load_dotenv

from exceptions import (
    NegativeValueException,
    EndpointRequestException,
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
                f'Отсутствует обязательная переменная окружения: {token}.'
            )
            return False
    return True


def send_message(bot, message):
    """Функция отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Бот отправил сообщение в Telegram: {message}')
    except TelegramError as error:
        logging.error(
            f'Сбой при отправке сообщения в Telegram: {error}',
            exc_info=True,
        )


def get_api_answer(timestamp):
    """Функция запроса к эндпоинту API сервиса Практикум.Домашка."""
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
            raise ConnectionError(
                f'Эндпоинт {ENDPOINT} недоступен. '
                f'Код ответа API: {homework_statuses.status_code}'
            )
        return homework_statuses.json()
    except RequestException as error:
        logging.error(
            f'Сбой при запросе к API сервису Практикум.Домашка {error}.'
        )
        raise EndpointRequestException(
            'Сбой при запросе к API сервису Практикум.Домашка.'
        ) from error


def check_response(response):
    """Функция проверяет ответ API на соответствие документации."""
    if isinstance(response, dict):
        if 'homeworks' not in response or 'current_date' not in response:
            logging.error('Ответ от API не содержит обязательный ключ.')
            raise KeyError('Ответ от API не содержит обязательный ключ.')
        if not isinstance(response['homeworks'], list):
            logging.error(
                'В ответе API под ключом homeworks вернулся не список.'
            )
            raise TypeError(
                'В ответе API под ключом homeworks вернулся не список.'
            )
        if not response['homeworks']:
            logging.error('Список работ пуст.')
            raise TypeError('Список работ пуст.')
        return response['homeworks']
    else:
        logging.error('В ответе API вернулся не словарь.')
        raise TypeError('В ответе API вернулся не словарь.')


def parse_status(homework):
    """Функция извлекает статус домашней работы."""
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if homework_name is None:
        logging.error('Ответ от API не содержит ключ homework_name.')
        raise KeyError('Ответ от API не содержит ключ homework_name.')
    if status is None:
        logging.error('Ответ от API не содержит ключ status.')
        raise KeyError('Ответ от API не содержит ключ status.')
    if status in HOMEWORK_VERDICTS:
        verdict = HOMEWORK_VERDICTS.get(status)
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        logging.error('Получен неожиданный статус работы.')
        raise InvalidTaskStatusException('Получен неожиданный статус работы.')


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise NegativeValueException(
            'Отсутствует обязательная переменная окружения!'
        )
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    previous_update = ''
    previous_message = ''

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
            if message != previous_message:
                send_message(bot, message)
                previous_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
