import os, re, json

from langchain.schema import Document
from langchain.text_splitter import TokenTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, "embeddings_data")
os.makedirs(CACHE_DIR, exist_ok=True)

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
JSON_PATH = os.path.join(BASE_DIR, "embeddings_data", "json_data", "sfedu_mmcs_data.json")
FAISS_PATH = os.path.join(CACHE_DIR, "faiss_index")

EMBEDDINGS = HuggingFaceEmbeddings(
    model_name=MODEL_NAME,
    model_kwargs={"device": "cuda"},
    encode_kwargs={"normalize_embeddings": True},
    cache_folder=CACHE_DIR
)


def build_embedding_db(
    json_path: str,
    faiss_path: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50
) -> FAISS:
    """
    Гибридная нарезка:
    1. Разбиваем разделы по параграфам \n\n.
    2. Если параграф короче chunk_size токенов — берём целиком.
    3. Иначе пробуем группировать по предложениям (~chunk_size токенов).
    4. Если после группировки параграф всё ещё больше — дробим на чанки еще меньше.
    Сохраняем все чанки в FAISS.

    :param json_path: Путь к данным для перевода в эмбеддинги
    :param faiss_path: Путь для сохранения векторной базы
    :param chunk_size: Размер чанка для нарезания
    :param chunk_overlap: Погрешность для нарезки

    :return: Векторная база
    """
    with open(json_path, "r", encoding="utf-8") as f:
        entries = json.load(f)

    splitter = TokenTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    docs: list[Document] = []

    for entry in entries:
        for section, text in entry.items():
            header = f"[{section.strip()}]\n"

            # Разбиваем на параграфы
            paragraphs = text.strip().split("\n\n")
            for para in paragraphs:
                para = para.strip()
                words = para.split()

                # Менее порога — без изменений
                if len(words) <= chunk_size:
                    docs.append(Document(page_content=header + para))
                else:
                    # Группируем по предложениям
                    sentences = re.split(r'(?<=[.!?])\s+', para)
                    sent_chunks = []
                    current, curr_len = [], 0
                    for sent in sentences:
                        wcount = len(sent.split())
                        if current and curr_len + wcount > chunk_size:
                            sent_chunks.append(" ".join(current))
                            current, curr_len = [sent], wcount
                        else:
                            current.append(sent)
                            curr_len += wcount
                    if current:
                        sent_chunks.append(" ".join(current))

                    # Для каждого sentence-chunk - либо взять, либо токен-чанк
                    for sch in sent_chunks:
                        if len(sch.split()) <= chunk_size:
                            docs.append(Document(page_content=header + sch))
                        else:
                            for chunk in splitter.split_text(sch):
                                docs.append(Document(page_content=header + chunk))

    db = FAISS.from_documents(docs, EMBEDDINGS)
    db.save_local(faiss_path)
    return db


async def load_embedding_db(faiss_path: str) -> FAISS:
    """
    Загружает FAISS-индекс

    :param faiss_path: Путь к faiss_index
    :return: faiss_index
    """
    return FAISS.load_local(faiss_path, EMBEDDINGS, allow_dangerous_deserialization=True)


async def get_best_match(db: FAISS, query: str) -> str:
    """
    Возвращает текст самого релевантного чанка по запросу.

    :param db: Векторная база для поиска
    :param query: Строка для поиска совпадений
    :return: Наилучшее совпадение в векторной базе по строке
    """
    results = db.similarity_search(query, k=1)
    return results[0].page_content if results else "Ничего не найдено"


'''
# Создание векторной базы и тест
async def main():
    if os.path.exists(FAISS_PATH):
        print("Векторная база найдена\nЗагрузка ...")
        db = await load_embedding_db(FAISS_PATH)
    else:
        print("Векторная база не найдена\nСоздание новой базы ...")
        db = build_embedding_db(JSON_PATH, FAISS_PATH)

    user_query = "Расскажи про магистратуру на мехмате"
    
    best = await get_best_match(db, user_query)
    print(f"По запросу:, '{user_query}', \nЛучший фрагмент:\n\n{best}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
'''
