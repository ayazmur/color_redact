import os
import glob


def find_docx_file():
    """Поиск DOCX файла"""
    # Сначала ищем test.docx
    if os.path.exists("test.docx"):
        return "test.docx"

    # Ищем любые docx файлы
    docx_files = glob.glob("*.docx")
    if docx_files:
        return docx_files[0]

    return None


def ensure_directory(directory):
    """Создание директории если не существует"""
    if not os.path.exists(directory):
        os.makedirs(directory)


def get_unique_filename(directory, base_name, extension):
    """Получение уникального имени файла"""
    counter = 1
    while True:
        if counter == 1:
            filename = f"{base_name}.{extension}"
        else:
            filename = f"{base_name}_{counter}.{extension}"

        full_path = os.path.join(directory, filename)
        if not os.path.exists(full_path):
            return full_path
        counter += 1