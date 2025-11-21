import sys
import os
from PyQt5.QtWidgets import QApplication, QMessageBox, QFileDialog

from ui.main_window import RedShapeEditor


def main():
    app = QApplication(sys.argv)

    # Создаем главное окно
    editor = RedShapeEditor()
    editor.show()

    # Автоматически ищем документ или предлагаем выбрать
    docx_path = find_docx_file()

    if docx_path:
        if editor.load_word_document(docx_path):
            print(f"Загружен документ: {docx_path}")
        else:
            # Если автоматическая загрузка не удалась, предлагаем выбрать вручную
            editor.show_file_selection_dialog()
    else:
        # Если файл не найден, сразу предлагаем выбрать
        editor.show_file_selection_dialog()

    sys.exit(app.exec_())


def find_docx_file():
    """Поиск DOCX файла"""
    # Сначала ищем test.docx
    if os.path.exists("test.docx"):
        return "test.docx"

    # Ищем любые docx файлы в текущей папке
    import glob
    docx_files = glob.glob("*.docx")
    if docx_files:
        return docx_files[0]

    return None


if __name__ == "__main__":
    main()