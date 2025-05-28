from os import path
from json import load
from bot_api.AI.models.models import InstructionBlock
from bot_api.AI.models.models import InstructionBlockNews


def is_file_is_correct(path_to_file: str, file_format: str, is_file: bool = True, is_correct: bool = True) -> None:
    if is_file and not path.exists(path_to_file):
        raise FileNotFoundError(f"Файл не найден: {path_to_file}")

    if is_correct and not file_format.startswith("."):
        raise ValueError(f"Аргумент 'file_format' должен начинаться с точки. Получено: \"{file_format}\"")

    shaped_path = path.splitext(path.basename(path_to_file))
    format_of_file = shaped_path[1]

    if is_correct and format_of_file != file_format:
        raise ValueError(f"Ожидаемый формат файла - \"{file_format}\", получен - {format_of_file}")


def load_instruction(json_instruction_path: str, data_type) -> InstructionBlock | InstructionBlockNews:
    """
    Загружает JSON-файл инструкций и возвращает объект указанного класса блока инструкций.

    :param json_instruction_path: Путь к JSON-файлу инструкций.
    :param data_type: Класс блока инструкций (InstructionBlock или InstructionBlockNews).

    :return: Экземпляр блока инструкций типа data_type.
    """

    is_file_is_correct(json_instruction_path, ".json")
    with open(json_instruction_path, "r", encoding="utf-8") as f:
        data = load(f)

    return data_type.model_validate(data)


'''
def main():
  
    path = "C:\\Users\\Admin\\PycharmProjects\\TG_bot\\bot_api\\AI\\models\\instructions\\instructions.json"
    instructions = load_instruction(path, InstructionBlockNews)
    instructions = instructions.to_pre_prompt()
    print(f"role:\n{instructions.role}\n\n"
          f"instructions:\n{instructions.instructions}")

    print('\n\n\n\n\n\n\n')
    
    path = "C:\\Users\\Admin\\PycharmProjects\\TG_bot\\bot_api\\AI\\models\\instructions\\instructions_news.json"
    instructions = load_instruction(path, InstructionBlockNews)
    instructions = instructions.to_pre_prompt()
    print(f"role:\n{instructions.role}\n\n"
          f"instructions:\n{instructions.instructions}")


if __name__ == "__main__":
    main()
'''
