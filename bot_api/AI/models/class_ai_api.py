from openai import OpenAI


class AIModelAPI:
    def __init__(self, api: str, url: str, model_name: str):
        """
        Класс для взаимодействия с моделью ИИ через API.

        :param api: API ключ для доступа к сервису.
        :param url: URL сервера API.
        :param model_name: Имя модели, к которой осуществляется обращение.
        """
        self.api = api
        self.url = url
        self.model_name = model_name
        self.client = OpenAI(api_key=self.api, base_url=self.url)

    def get_response(self, message: str, _chat: list[dict[str, str]] = None, role: str = None, instruction: str = None,
                     max_tokens: int = 50, temperature: float = 1.0):
        """
        Генерирует ответ на запрос через API ИИ.

        :param message: Сообщение пользователя.
        :param _chat: Список сообщений для диалога. Если не задан, формируется на основе role и instruction.
        :param role: Роль для системы (например, "assistant" или описание поведения).
        :param instruction: Инструкция для модели.
        :param max_tokens: Максимальное число токенов в ответе.
        :param temperature: Параметр случайности генерации.

        :return: Строка с ответом, сгенерированным моделью.
        """
        if _chat is None:
            _chat = [
                {"role": "system", "content": role if role is not None else ""},
                {"role": "user", "content": f"{instruction} {message}" if instruction is not None else message}
            ]

        # Данное предупреждение - ошибка linter
        response = self.client.chat.completions.create(
            messages=_chat,
            model=self.model_name,
            stream=False,
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.choices[0].message.content

