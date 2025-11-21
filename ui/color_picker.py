from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QListWidget, QListWidgetItem, QColorDialog,
                             QMessageBox, QDialogButtonBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor


class ColorPickerDialog(QDialog):
    def __init__(self, initial_colors, parent=None):
        super().__init__(parent)
        self.colors = initial_colors.copy()
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Управление целевыми цветами")
        self.setModal(True)
        self.resize(400, 500)

        layout = QVBoxLayout(self)

        # Список цветов
        layout.addWidget(QLabel("Целевые цвета:"))

        self.color_list = QListWidget()
        self.color_list.itemDoubleClicked.connect(self.edit_color)
        layout.addWidget(self.color_list)

        # Кнопки управления
        button_layout = QHBoxLayout()

        btn_add = QPushButton("Добавить цвет")
        btn_add.clicked.connect(self.add_color)
        button_layout.addWidget(btn_add)

        btn_edit = QPushButton("Изменить")
        btn_edit.clicked.connect(self.edit_selected_color)
        button_layout.addWidget(btn_edit)

        btn_remove = QPushButton("Удалить")
        btn_remove.clicked.connect(self.remove_selected_color)
        button_layout.addWidget(btn_remove)

        layout.addLayout(button_layout)

        # Кнопки диалога
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.update_color_list()

    def update_color_list(self):
        """Обновление списка цветов"""
        self.color_list.clear()
        for color in self.colors:
            item = QListWidgetItem(f"RGB{color}")
            item.setBackground(QColor(*color))

            # Определяем цвет текста в зависимости от яркости фона
            brightness = color[0] * 0.299 + color[1] * 0.587 + color[2] * 0.114
            text_color = QColor("white") if brightness < 128 else QColor("black")
            item.setForeground(text_color)

            self.color_list.addItem(item)

    def add_color(self):
        """Добавление нового цвета"""
        color = QColorDialog.getColor()
        if color.isValid():
            rgb_color = (color.red(), color.green(), color.blue())
            if rgb_color not in self.colors:
                self.colors.append(rgb_color)
                self.update_color_list()

    def edit_selected_color(self):
        """Редактирование выбранного цвета"""
        current_item = self.color_list.currentItem()
        if current_item:
            self.edit_color(current_item)

    def edit_color(self, item):
        """Редактирование цвета"""
        index = self.color_list.row(item)
        old_color = self.colors[index]

        color = QColorDialog.getColor(QColor(*old_color))
        if color.isValid():
            new_color = (color.red(), color.green(), color.blue())
            self.colors[index] = new_color
            self.update_color_list()

    def remove_selected_color(self):
        """Удаление выбранного цвета"""
        current_item = self.color_list.currentItem()
        if current_item:
            index = self.color_list.row(current_item)
            self.colors.pop(index)
            self.update_color_list()

    def get_colors(self):
        """Получение списка цветов"""
        return self.colors