from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QGroupBox, QRadioButton, QButtonGroup,
                             QProgressBar)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage


class ShapeEditorUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        """Настройка интерфейса"""
        # Главный layout
        main_layout = QHBoxLayout(self)

        # Левая панель - инструменты
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 1)

        # Правая панель - изображение
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 3)

        # Нижняя панель - кнопки управления
        bottom_panel = self.create_bottom_panel()
        main_layout.addLayout(bottom_panel)

    def create_left_panel(self):
        """Создание левой панели с инструментами"""
        panel = QGroupBox("Инструменты")
        panel.setMaximumWidth(300)
        layout = QVBoxLayout(panel)

        # Информация о цветах
        color_group = QGroupBox("Цвета")
        color_layout = QVBoxLayout(color_group)

        self.color_info = QLabel(f"Замена: RGB(236, 19, 27) → RGB(0, 0, 255)")
        self.color_info.setWordWrap(True)
        color_layout.addWidget(self.color_info)

        self.btn_choose_target = QPushButton("Выбрать целевой цвет")
        color_layout.addWidget(self.btn_choose_target)

        self.btn_choose_replacement = QPushButton("Выбрать цвет замены")
        color_layout.addWidget(self.btn_choose_replacement)

        layout.addWidget(color_group)

        # Режимы выделения
        mode_group = QGroupBox("Режим выделения")
        mode_layout = QVBoxLayout(mode_group)

        self.mode_group = QButtonGroup()

        btn_rect = QRadioButton("Прямоугольник")
        btn_rect.setChecked(True)
        self.mode_group.addButton(btn_rect, 1)
        mode_layout.addWidget(btn_rect)

        btn_ellipse = QRadioButton("Эллипс")
        self.mode_group.addButton(btn_ellipse, 2)
        mode_layout.addWidget(btn_ellipse)

        btn_lasso = QRadioButton("Лассо")
        self.mode_group.addButton(btn_lasso, 3)
        mode_layout.addWidget(btn_lasso)

        btn_mask = QRadioButton("Маска")
        self.mode_group.addButton(btn_mask, 4)
        mode_layout.addWidget(btn_mask)

        layout.addWidget(mode_group)

        # Режим маски
        self.mask_mode_group = QGroupBox("Режим маски")
        self.mask_mode_layout = QVBoxLayout(self.mask_mode_group)

        self.mask_btn_group = QButtonGroup()

        btn_draw = QRadioButton("Рисовать область")
        btn_draw.setChecked(True)
        self.mask_btn_group.addButton(btn_draw, 1)
        self.mask_mode_layout.addWidget(btn_draw)

        btn_erase = QRadioButton("Создать дырку")
        self.mask_btn_group.addButton(btn_erase, 2)
        self.mask_mode_layout.addWidget(btn_erase)

        layout.addWidget(self.mask_mode_group)
        self.mask_mode_group.setVisible(False)

        # Информация о прогрессе
        progress_group = QGroupBox("Прогресс")
        progress_layout = QVBoxLayout(progress_group)

        self.progress_label = QLabel("Ожидание загрузки...")
        progress_layout.addWidget(self.progress_label)

        self.red_pixels_label = QLabel("")
        progress_layout.addWidget(self.red_pixels_label)

        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)

        layout.addWidget(progress_group)

        preview_group = QGroupBox("Автопредпросмотр")
        preview_layout = QVBoxLayout(preview_group)

        self.auto_preview_check = QRadioButton("Включить автопредпросмотр")
        self.auto_preview_check.setChecked(True)
        preview_layout.addWidget(self.auto_preview_check)

        preview_info = QLabel(
            "• Цвет меняется сразу при выделении\n• Зеленый - будет заменен\n• Желтый - контур выделения")
        preview_info.setStyleSheet("color: #666; font-size: 11px;")
        preview_info.setWordWrap(True)
        preview_layout.addWidget(preview_info)

        layout.addWidget(preview_group)

        # Инструкция
        instruction_group = QGroupBox("Инструкция")
        instruction_layout = QVBoxLayout(instruction_group)

        instructions = [
            "• Выделите области с красными фигурами",
            "• Можно выделять ЗА ПРЕДЕЛАМИ изображения",
            "• Полезно для красных элементов у границ",
            "• Цвет автоматически меняется при выделении",
            "• ЗЕЛЕНАЯ подсветка - пиксели, которые будут заменены",
            "• ЖЕЛТЫЙ контур - ваше выделение",
            "• 'Отменить' - удаляет последнее выделение",
            "• Ctrl+Z - отмена, Ctrl+Shift+Z - повтор",
            "• ПРОБЕЛ - перейти к следующему изображению",
            "• ALT - вернуться к предыдущему изображению",
            "• Если есть выделения - обрабатывает, если нет - пропускает",
            "• 'Завершить' - закончить обработку и сохранить документ"
        ]

        for instruction in instructions:
            label = QLabel(instruction)
            label.setWordWrap(True)
            instruction_layout.addWidget(label)

        layout.addWidget(instruction_group)
        layout.addStretch()

        return panel

    def create_right_panel(self):
        """Создание правой панели с изображением"""
        panel = QGroupBox("Изображение")
        layout = QVBoxLayout(panel)

        # Метка для изображения
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(800, 600)
        self.image_label.setStyleSheet("border: 1px solid gray; background-color: white;")

        layout.addWidget(self.image_label)

        return panel

    def create_bottom_panel(self):
        """Создание нижней панели с кнопками"""
        layout = QHBoxLayout()

        self.btn_undo = QPushButton("↶ Отменить")
        self.btn_undo.setStyleSheet("QPushButton { background-color: #ff6b6b; color: white; font-weight: bold; }")
        layout.addWidget(self.btn_undo)

        self.btn_preview = QPushButton("👁 Предпросмотр")
        self.btn_preview.setStyleSheet("QPushButton { background-color: #a9e34b; color: black; font-weight: bold; }")
        layout.addWidget(self.btn_preview)

        # Объединенная кнопка "Далее" вместо "Готово" и "Пропустить"
        self.btn_next = QPushButton("⏭ Далее (Пробел)")
        self.btn_next.setStyleSheet(
            "QPushButton { background-color: #51cf66; color: white; font-weight: bold; font-size: 14px; }")
        layout.addWidget(self.btn_next)

        self.btn_finish = QPushButton("🏁 Завершить")
        self.btn_finish.setStyleSheet("QPushButton { background-color: #339af0; color: white; font-weight: bold; }")
        layout.addWidget(self.btn_finish)

        return layout