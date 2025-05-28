from pydantic import BaseModel
from openai.types.chat import (
    ChatCompletionUserMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionMessageParam
)


class PrePrompt(BaseModel):
    role: str
    instructions: str


class LLMRequest(BaseModel):
    role_instructions: PrePrompt
    task: str


    def to_prompt(self) -> list[ChatCompletionMessageParam]:
        instruction_task = self.role_instructions.instructions + self.task
        prompt: list[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(role="system", content=self.role_instructions.role),
            ChatCompletionUserMessageParam(role="user", content=instruction_task)
        ]

        return prompt


class ParameterInfo(BaseModel):
    argument_name: str
    typeof: str
    description: str


    def unit_it(self) -> str:
        s = (
            f"  Аргумент функции: {self.argument_name}\n"
            f"  Тип аргумента: {self.typeof}\n"
            f"  Описание аргумента: {self.description}\n"
        )

        return s


class FunctionData(BaseModel):
    name: str
    description: str
    parameters: list[ParameterInfo] | None = None
    returns: str | None = None
    example: str = ""
    bad_example: str = ""


    def unit_it(self) -> str:
        params = "\n".join(param.unit_it() for param in self.parameters)
        s = (
            f" Название функции: {self.name}\n"
            f" Описание функции: {self.description}\n"
            f" Параметры функции:\n{params}"
        )
        if self.returns:
            s += f"\n Функция возвращает: {self.returns}\n"
        s += (
             f" Пример вызова функции:\n{self.example}\n"
             f" Пример некорректного вызова:\n{self.bad_example}\n"
        )
        return s


class InstructionBlock(BaseModel):
    role: str
    instructions: str
    context: list[str]
    functions: list[FunctionData]
    output_format: str
    example: str
    bad_example: str


    def to_pre_prompt(self) -> PrePrompt:
        functions = "\n".join(func.unit_it() for func in self.functions)
        context = "\n".join( (part + ';') for part in self.context)
        s = (
            f"{self.instructions}\n\n"
            f"Контекст для обработки данных:\n{context}\n\n"
            f"Функции и справка по ним:\n{functions}\n\n"
            f"Информация о выводе:\n{self.output_format}\n\n"
            f"Примеры вывода:\nПравильный формат вывода:\n{self.example}\n\nНеправильный формат вывода:\n{self.bad_example}"
        )

        pre_prompt = PrePrompt(role=self.role, instructions=s)
        return pre_prompt


class InstructionBlockNews(BaseModel):
    role: str
    instructions: list[str]
    context: list[str]
    output_format: str
    example: str

    def to_pre_prompt(self) -> PrePrompt:
        instr_block = "\n".join(self.instructions)
        context_block = "\n".join(f"{item};" for item in self.context)


        full_instructions = (
            f"{instr_block}\n\n"
            f"Контекст для обработки данных:\n{context_block}\n\n"
            f"Формат вывода:\n{self.output_format}\n\n"
            f"Пример:\n{self.example}\n"
        )

        return PrePrompt(role=self.role, instructions=full_instructions)
