# Homework Bot  
### Описание
Tlegram-бот, который обращается к API сервиса Практикум.Домашка и узнаёт статус вашей домашней работы.
### Технологии
Python 3.9
### Запуск проекта 
* Создайте и активируйте виртуальное окружение
* Установите зависимости из файла requirements.txt
```
pip install -r requirements.txt
```
* В директории проекта создайте файл .env со следующим содержимым:
```
PRACTICUM_TOKEN=<Ваш токен Яндекс.Практикума>
TELEGRAM_TOKEN=<Токен телеграмм-бота>
TELEGRAM_CHAT_ID=<ваш id в Телеграмме>
```
* Запустите бота
```
python homework.py
```
