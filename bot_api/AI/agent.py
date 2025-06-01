import inspect
import re
import json
import asyncio
from pydantic import BaseModel
from os import path

from bot_api.AI.embedding_manager import get_best_match, load_embedding_db

from bot_api.AI.models.class_ai_api import AIModelAPI
from bot_api.AI.models.class_ai_local import AIModelLocal
from bot_api.AI.models.models import InstructionBlock, LLMRequest
from bot_api.AI.models.instructions_loader import load_instruction

from bot_api.AI.functions import get_schedule, get_homework, get_news, get_events


BASE_DIR = path.dirname(path.abspath(__file__))
CACHE_DIR = path.join(BASE_DIR, "embeddings_data")
FAISS_PATH = path.join(CACHE_DIR, "faiss_index")
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
        stripped = raw.strip()
        if stripped.startswith('```') and stripped.endswith('```'):
            raw = cls._strip_fences(raw)

        match = re.search(r"\{[\s\S]*\}", raw)
        if not match:
            raise ValueError("Не найден JSON-блок в ответе")
        json_str = match.group(0)

        try:
            payload = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Невалидный JSON: {e}\n>>> {json_str}")


        fc = payload.get("function_call")
        if not isinstance(fc, dict):
            raise ValueError("В JSON нет 'function_call'")

        args = fc.get("arguments")
        if isinstance(args, list):
            fc["arguments"] = {"ds": args}
        elif not isinstance(args, dict):
            raise ValueError("Аргументы должны быть объектом или списком строк")

        return cls(**fc)

    async def run(self):
        entry = _FUNCTION_REGISTRY.get(self.name)
        if entry is None:
            raise ValueError(f"Функция {self.name!r} не зарегистрирована")
        func, defaults = entry

        for key, val in defaults.items():
            self.arguments.setdefault(key, val)

        sig = inspect.signature(func)
        try:
            sig.bind(**self.arguments)
        except TypeError as e:
            raise ValueError(f"Неподходящие аргументы для {self.name!r}: {e}")

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

        db = await load_embedding_db(FAISS_PATH)
        best_match = await get_best_match(db, user_input)
        matches = (f"Инструкция для дополнительная информация:\n"
                   f"Если запрос не подходит по инструкциям но хоть как то связан со следующей "
                   f"информацией - вот дополнительные данные по нему для генерации ответа:\n{best_match}"
                   f"\n**ВАЖНО** вывод для ДАННОГО варианта твоего ответа НЕ НУЖНО форматировать.\n\n"
                   f"Основная задача:\n")

        request = LLMRequest(role_instructions=pre, task=matches + task)

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

'''
async def main():
    from config import deepseek_api
    path = "C:\\Users\\Admin\\PycharmProjects\\TG_bot\\bot_api\\AI\\models\\instructions\\instructions.json"
    instructs = load_instruction(path, InstructionBlock)
    agent = Agent(deepseek_api, instructs)

    out = await agent.run("скинь пожалуйста новости", group_id=12345)
    print(out)

if __name__ == "__main__":
    asyncio.run(main())
'''