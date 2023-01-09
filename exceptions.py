class NegativeValueException(Exception):
    """Исключение возникает при отсутствии переменных окружения."""
    ...


class EndpointHTTPException(Exception):
    """Исключение возникает при недоступности эндпоинта."""
    ...


class InvalidTaskStatusException(Exception):
    """Исключение возникает при получении неожиданного статус домашней работы
    в ответе API.
    """
    ...
