import inspect
import re
import json
import asyncio
from pydantic import BaseModel

from bot_api.AI.models.class_ai_api import AIModelAPI
from bot_api.AI.models.class_ai_local import AIModelLocal
from bot_api.AI.models.models import InstructionBlock, LLMRequest
from bot_api.AI.models.instructions_loader import load_instruction

from bot_api.AI.functions import get_schedule, get_homework, get_news, get_events

# ─── внешний, «чистый» реестр ─────────────────────────────────────────
_FUNCTION_REGISTRY = {}

def register(func=None, *, defaults=None):
    """
    Декоратор для регистрации функции
    """
    if func is None:
        def wrapper(f):
            _FUNCTION_REGISTRY[f.__name__] = (f, defaults or {})
            return f
        return wrapper

    _FUNCTION_REGISTRY[func.__name__] = (func, defaults or {})
    return func


class FunctionCall(BaseModel):
    name: str
    arguments: dict

    @classmethod
    def _strip_fences(cls, raw: str) -> str:
        pattern = r"^```(?:json)?\s*([\s\S]*?)\s*```$"
        m = re.match(pattern, raw.strip(), flags=re.IGNORECASE)
        return m.group(1) if m else raw

    @classmethod
    def parse_response(cls, raw: str) -> "FunctionCall":
        # 1) Удаляем Markdown-ограждения, если они есть
        stripped = raw.strip()
        if stripped.startswith('```') and stripped.endswith('```'):
            raw = cls._strip_fences(raw)

        # 2) Извлекаем первый JSON-блок
        match = re.search(r"\{[\s\S]*\}", raw)
        if not match:
            raise ValueError("Не найден JSON-блок в ответе")
        json_str = match.group(0)

        # 3) Парсим JSON
        try:
            payload = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Невалидный JSON: {e}\n>>> {json_str}")

        # 4) Достаём поле function_call
        fc = payload.get("function_call")
        if not isinstance(fc, dict):
            raise ValueError("В JSON нет 'function_call'")

        # 5) Обработка списка аргументов vs словарь
        args = fc.get("arguments")
        if isinstance(args, list):
            # Преобразуем простой список в объект параметров 'ds'
            fc["arguments"] = {"ds": args}
        elif not isinstance(args, dict):
            raise ValueError("Аргументы должны быть объектом или списком строк")

        # 6) Конструируем Pydantic-модель
        return cls(**fc)

    async def run(self):
        # 1) Получаем функцию и её дефолты из реестра
        entry = _FUNCTION_REGISTRY.get(self.name)
        if entry is None:
            raise ValueError(f"Функция {self.name!r} не зарегистрирована")
        func, defaults = entry

        # 2) Подмешиваем дефолтные аргументы
        for key, val in defaults.items():
            self.arguments.setdefault(key, val)

        # 3) Валидация аргументов по сигнатуре
        sig = inspect.signature(func)
        try:
            sig.bind(**self.arguments)
        except TypeError as e:
            raise ValueError(f"Неподходящие аргументы для {self.name!r}: {e}")

        # 4) Вызов функции (await если корутина)
        result = func(**self.arguments)
        if inspect.iscoroutine(result):
            return await result
        return result


from config import deepseek_api
MODEL = deepseek_api
PATH = 'C:\\Users\\Admin\\PycharmProjects\\TG_bot\\bot_api\\AI\\models\\instructions\\instructions_news.json'

register(get_schedule, defaults={'ds': []})
register(get_homework, defaults={'group_id': 0})
register(get_events,   defaults={'group_id': 0})
register(get_news,     defaults={'model': MODEL, 'path_to_instructions': PATH})


def for_silly_answer(s: str) -> str:
    pattern = r"^```(?:json)?\s*([\s\S]*?)\s*```$"
    m = re.match(pattern, s.strip(), flags=re.IGNORECASE)
    return m.group(1) if m else s


class Agent:
    def __init__(self, model: AIModelAPI | AIModelLocal, instructions: InstructionBlock):
        self.model = model
        self.instructions = instructions

    async def run(self, user_input: str, group_id: int) -> str:
        pre = self.instructions.to_pre_prompt()
        task = f"Запрос от пользователя:\n{user_input}"
        request = LLMRequest(role_instructions=pre, task=task)

        raw = await self.model.get_response(request)

        if "function_call" in raw:
            cleaned = for_silly_answer(raw)
            print(cleaned)
            call = FunctionCall.parse_response(cleaned)

            func, defaults = _FUNCTION_REGISTRY[call.name]
            for k, v in defaults.items():
                call.arguments.setdefault(k, v)

            if "group_id" in inspect.signature(func).parameters:
                call.arguments["group_id"] = group_id

            return await call.run()

        return raw


async def main():
    from config import deepseek_api
    path = "C:\\Users\\Admin\\PycharmProjects\\TG_bot\\bot_api\\AI\\models\\instructions\\instructions.json"
    instructs = load_instruction(path, InstructionBlock)
    agent = Agent(deepseek_api, instructs)

    out = await agent.run("скинь новости", group_id=12345)
    print(out)

if __name__ == "__main__":
    asyncio.run(main())
