from openai import OpenAI
from .models import LLMRequest


class AIModelAPI:
    """
    Класс для взаимодействия с моделью ИИ через API.

    :param api: API ключ для доступа к сервису.
    :param url: URL сервера API.
    :param model_name: Имя модели, к которой осуществляется обращение.
    """
    def __init__(self, api: str, url: str, model_name: str):
        self.api = api
        self.url = url
        self.model_name = model_name
        self.client = OpenAI(api_key=self.api, base_url=self.url)


    async def get_response(self, request: LLMRequest, temperature: float = 0.1) -> str | None:
        """
        Генерирует ответ на запрос через API ИИ.

        :param request: Запрос пользователя.
        :param temperature: Параметр случайности генерации.

        :return: Строка с ответом, сгенерированным моделью.
        """
        prompt = request.to_prompt()
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=prompt,
            temperature=temperature,
            stream=False
        )
        return response.choices[0].message.content
