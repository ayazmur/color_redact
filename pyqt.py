import sys
import os
import tempfile
import shutil
import cv2
import numpy as np
from PIL import Image
from docx import Document
import glob
import shutil

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QGroupBox, QRadioButton, QButtonGroup,
                             QProgressBar, QMessageBox, QColorDialog, QFileDialog)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QColor

from ui.ui_shape_editor import ShapeEditorUI


class ShapeEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Редактор красных фигур")
        self.setGeometry(100, 100, 1400, 900)

        # Настройки
        self.target_color = (236, 19, 27)
        self.replacement_color = (0, 0, 255)
        self.mode = "rectangle"
        self.current_tool = "draw"  # draw, erase

        # Данные изображений
        self.image_parts = []
        self.current_index = 0
        self.filtered_indices = []
        self.original_paths = []
        self.processed_paths = []

        # Временные файлы
        self.temp_dir = tempfile.mkdtemp()
        self.comparison_dir = os.path.join(self.temp_dir, "comparison")
        os.makedirs(self.comparison_dir, exist_ok=True)

        # Для рисования
        self.current_image = None
        self.current_pixmap = None
        self.drawing = False
        self.last_point = None
        self.start_point = None
        self.regions = []
        self.mask_regions = []
        self.current_points = []

        self.auto_preview = True  # Автоматический предпросмотр

        self.preview_mode = False  # Режим предпросмотра
        self.preview_image = None
        self.docx_path = None

        # Для истории изменений
        self.history = []  # История всех действий
        self.history_index = -1  # Текущая позиция в истории
        self.max_history_size = 50  # Максимальный размер истории
        self.adding_to_history = False  # Флаг для предотвращения рекурсии

        # Инициализация UI
        self.ui = ShapeEditorUI()
        self.setCentralWidget(self.ui)
        self.setup_ui_connections()

    def setup_ui_connections(self):
        """Настройка соединений сигналов и слотов"""
        # Кнопки цветов
        self.ui.btn_choose_target.clicked.connect(self.choose_target_color)
        self.ui.btn_choose_replacement.clicked.connect(self.choose_replacement_color)

        # Режимы выделения
        self.ui.mode_group.buttonClicked.connect(self.change_mode)
        self.ui.mask_btn_group.buttonClicked.connect(self.change_mask_mode)

        # Автопредпросмотр
        self.ui.auto_preview_check.toggled.connect(self.toggle_auto_preview)

        # Кнопки управления
        self.ui.btn_undo.clicked.connect(self.undo_from_history)
        self.ui.btn_preview.clicked.connect(self.toggle_preview)
        self.ui.btn_next.clicked.connect(self.process_or_skip)
        self.ui.btn_finish.clicked.connect(self.finish_processing)

        # Обработка событий мыши на изображении
        self.ui.image_label.mousePressEvent = self.on_mouse_press
        self.ui.image_label.mouseMoveEvent = self.on_mouse_move
        self.ui.image_label.mouseReleaseEvent = self.on_mouse_release

        # Устанавливаем фокус политику для обработки горячих клавиш
        self.ui.setFocusPolicy(Qt.StrongFocus)
        self.ui.setFocus()

    def keyPressEvent(self, event):
        """Обработка нажатий клавиш"""
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_Z:
            # Ctrl+Z - отмена
            self.undo_from_history()
            event.accept()
        elif event.modifiers() == (Qt.ControlModifier | Qt.ShiftModifier) and event.key() == Qt.Key_Z:
            # Ctrl+Shift+Z - повтор
            self.redo_from_history()
            event.accept()
        elif event.key() == Qt.Key_Space:
            # Пробел - далее (вперед)
            self.process_or_skip()
            event.accept()
        elif event.key() == Qt.Key_Alt:
            # Alt - назад (предыдущее изображение)
            self.go_to_previous()
            event.accept()
        else:
            super().keyPressEvent(event)

    def go_to_previous(self):
        """Перейти к предыдущему изображению"""
        if self.current_index > 0:
            # Уменьшаем индекс и загружаем предыдущее изображение
            self.current_index -= 1

            # Удаляем последний элемент из processed_paths и original_paths
            if self.processed_paths:
                self.processed_paths.pop()
            if self.original_paths:
                self.original_paths.pop()

            # Загружаем предыдущее изображение
            self.load_current_image()
            print(f"← Вернулись к изображению {self.current_index + 1}")
        else:
            print("Это первое изображение, нельзя вернуться назад")

    def add_to_history(self):
        """Добавление текущего состояния в историю"""
        # Защита от рекурсии
        if self.adding_to_history:
            return

        self.adding_to_history = True

        try:
            # Сохраняем текущие регионы и маски
            state = {
                'regions': [],
                'mask_regions': []
            }

            # Глубокое копирование регионов
            for region in self.regions:
                if region['type'] == 'rectangle':
                    state['regions'].append({
                        'type': 'rectangle',
                        'x1': region['x1'],
                        'y1': region['y1'],
                        'x2': region['x2'],
                        'y2': region['y2']
                    })
                elif region['type'] == 'ellipse':
                    state['regions'].append({
                        'type': 'ellipse',
                        'x1': region['x1'],
                        'y1': region['y1'],
                        'x2': region['x2'],
                        'y2': region['y2']
                    })
                elif region['type'] == 'lasso':
                    state['regions'].append({
                        'type': 'lasso',
                        'points': region['points'].copy()
                    })

            # Глубокое копирование масок
            for mask in self.mask_regions:
                state['mask_regions'].append({
                    'type': 'mask',
                    'tool': mask['tool'],
                    'points': mask['points'].copy()
                })

            # Удаляем все состояния после текущего индекса (если мы откатились назад и делаем новое действие)
            if self.history_index < len(self.history) - 1:
                self.history = self.history[:self.history_index + 1]

            # Добавляем новое состояние
            self.history.append(state)
            self.history_index = len(self.history) - 1

            # Ограничиваем размер истории
            if len(self.history) > self.max_history_size:
                self.history.pop(0)
                self.history_index -= 1

            print(f"История: {len(self.history)} состояний, индекс: {self.history_index}")

        finally:
            self.adding_to_history = False

    def undo_from_history(self):
        """Отмена из истории"""
        if self.history_index > 0:
            self.history_index -= 1
            self.restore_from_history()
            print(f"Отмена - индекс истории: {self.history_index}")

            # Обновляем статистику после отмены
            if self.regions or self.mask_regions:
                self.create_auto_preview()
                preview_img, red_count = self.process_image_with_regions()
                self.show_auto_preview_stats(red_count)
            else:
                if hasattr(self, 'current_image') and self.current_image is not None:
                    self.ui.red_pixels_label.setText(f"Красных пикселей: {self.count_red_pixels(self.current_image)}")
                    self.ui.red_pixels_label.setStyleSheet("")
        else:
            print("Нет действий для отмены")

    def redo_from_history(self):
        """Повтор из истории"""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.restore_from_history()
            print(f"Повтор - индекс истории: {self.history_index}")

            # Обновляем статистику после повтора
            if self.regions or self.mask_regions:
                self.create_auto_preview()
                preview_img, red_count = self.process_image_with_regions()
                self.show_auto_preview_stats(red_count)
        else:
            print("Нет действий для повтора")

    def restore_from_history(self):
        """Восстановление состояния из истории"""
        if 0 <= self.history_index < len(self.history):
            state = self.history[self.history_index]

            # Восстанавливаем регионы
            self.regions = []
            for region in state['regions']:
                if region['type'] == 'rectangle':
                    self.regions.append({
                        'type': 'rectangle',
                        'x1': region['x1'],
                        'y1': region['y1'],
                        'x2': region['x2'],
                        'y2': region['y2']
                    })
                elif region['type'] == 'ellipse':
                    self.regions.append({
                        'type': 'ellipse',
                        'x1': region['x1'],
                        'y1': region['y1'],
                        'x2': region['x2'],
                        'y2': region['y2']
                    })
                elif region['type'] == 'lasso':
                    self.regions.append({
                        'type': 'lasso',
                        'points': region['points'].copy()
                    })

            # Восстанавливаем маски
            self.mask_regions = []
            for mask in state['mask_regions']:
                self.mask_regions.append({
                    'type': 'mask',
                    'tool': mask['tool'],
                    'points': mask['points'].copy()
                })

            # Обновляем отображение без добавления в историю
            self.adding_to_history = True
            try:
                # Всегда обновляем предпросмотр при восстановлении из истории
                if self.regions or self.mask_regions:
                    self.create_auto_preview()
                else:
                    # Если нет регионов, показываем оригинал
                    self.display_image()
                    if hasattr(self, 'current_image') and self.current_image is not None:
                        self.ui.red_pixels_label.setText(
                            f"Красных пикселей: {self.count_red_pixels(self.current_image)}")
                        self.ui.red_pixels_label.setStyleSheet("")
            finally:
                self.adding_to_history = False

    def toggle_auto_preview(self, enabled):
        """Включение/выключение автопредпросмотра"""
        self.auto_preview = enabled
        if enabled and (self.regions or self.mask_regions):
            self.create_auto_preview()

    def toggle_preview(self):
        """Переключение режима предпросмотра"""
        if not self.regions and not self.mask_regions:
            QMessageBox.warning(self, "Внимание", "Не выделено ни одной области для предпросмотра!")
            return

        if not self.preview_mode:
            # Включаем предпросмотр
            self.preview_mode = True
            self.ui.btn_preview.setText("✏ Редактировать")
            self.ui.btn_preview.setStyleSheet(
                "QPushButton { background-color: #ffa94d; color: black; font-weight: bold; }")

            # Создаем предпросмотр
            self.create_preview()
        else:
            # Выключаем предпросмотр
            self.preview_mode = False
            self.ui.btn_preview.setText("👁 Предпросмотр")
            self.ui.btn_preview.setStyleSheet(
                "QPushButton { background-color: #a9e34b; color: black; font-weight: bold; }")

            # Возвращаем оригинальное изображение
            self.redraw_all_shapes()

    def create_preview(self):
        """Создание предпросмотра с изменениями"""
        try:
            # Обрабатываем изображение для предпросмотра
            preview_img, red_count = self.process_image_with_regions()

            # Сохраняем для отображения
            self.preview_image = preview_img.copy()

            # Отображаем предпросмотр
            self.display_preview_image(preview_img)

            # Показываем статистику
            self.show_preview_stats(red_count)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка создания предпросмотра: {str(e)}")

    def display_preview_image(self, img):
        """Отображение изображения предпросмотра"""
        # Конвертируем BGR в RGB
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w, ch = img_rgb.shape
        bytes_per_line = ch * w

        # Создаем QImage
        q_img = QImage(img_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)

        # Масштабируем для отображения
        scaled_pixmap = pixmap.scaled(self.ui.image_label.width(), self.ui.image_label.height(),
                                      Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self.ui.image_label.setPixmap(scaled_pixmap)

    def show_preview_stats(self, red_count):
        """Показать статистику предпросмотра"""
        # Временно меняем текст прогресса для показа статистики
        original_text = self.ui.progress_label.text()
        self.ui.progress_label.setText(
            f"{original_text} | Предпросмотр: заменено {red_count} пикселей"
        )

        # Меняем цвет метки красных пикселей
        self.ui.red_pixels_label.setText(
            f"🔴 Заменено красных пикселей: {red_count}"
        )
        self.ui.red_pixels_label.setStyleSheet("color: #51cf66; font-weight: bold;")

    def choose_target_color(self):
        """Выбор целевого цвета"""
        color = QColorDialog.getColor(QColor(*self.target_color), self, "Выберите целевой красный цвет")
        if color.isValid():
            self.target_color = (color.red(), color.green(), color.blue())
            self.update_color_info()

    def choose_replacement_color(self):
        """Выбор цвета замены"""
        color = QColorDialog.getColor(QColor(*self.replacement_color), self, "Выберите цвет для замены")
        if color.isValid():
            self.replacement_color = (color.red(), color.green(), color.blue())
            self.update_color_info()

    def update_color_info(self):
        """Обновление информации о цветах"""
        self.ui.color_info.setText(f"Замена: RGB{self.target_color} → RGB{self.replacement_color}")

    def change_mode(self, button):
        """Смена режима выделения"""
        if button.text() == "Прямоугольник":
            self.mode = "rectangle"
            self.ui.mask_mode_group.setVisible(False)
        elif button.text() == "Эллипс":
            self.mode = "ellipse"
            self.ui.mask_mode_group.setVisible(False)
        elif button.text() == "Лассо":
            self.mode = "lasso"
            self.ui.mask_mode_group.setVisible(False)
        else:  # Маска
            self.mode = "mask"
            self.ui.mask_mode_group.setVisible(True)

    def change_mask_mode(self, button):
        """Смена режима маски"""
        self.current_tool = "draw" if button.text() == "Рисовать область" else "erase"

    def load_word_document(self, docx_path):
        """Загрузка Word документа"""
        try:
            self.docx_path = docx_path
            self.doc = Document(docx_path)
            self.image_parts = []

            # Получаем все изображения
            for rel_id, rel in self.doc.part.rels.items():
                if "image" in rel.reltype:
                    self.image_parts.append(rel.target_part)

            if not self.image_parts:
                QMessageBox.critical(self, "Ошибка", "В документе нет изображений!")
                return False

            print(f"Найдено изображений: {len(self.image_parts)}")

            # Фильтруем изображения с красным цветом
            self.filter_images_with_red()

            if not self.filtered_indices:
                QMessageBox.information(self, "Информация", "Не найдено изображений с красным цветом!")
                return False

            print(f"Изображений с красным: {len(self.filtered_indices)}")

            self.current_index = 0

            # Обновляем прогресс
            self.update_progress()

            # Загружаем первое изображение
            self.load_current_image()

            return True

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки документа: {str(e)}")
            return False

    def filter_images_with_red(self):
        """Фильтрация изображений с красным цветом в порядке документа"""
        self.filtered_indices = []
        self.red_pixels_info = []

        for i, image_part in enumerate(self.image_parts):
            image_bytes = image_part.blob
            image_array = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

            if img is not None:
                red_count = self.count_red_pixels(img)
                self.red_pixels_info.append((i, red_count))

                if red_count > 0:
                    self.filtered_indices.append(i)

        # УБИРАЕМ СОРТИРОВКУ - сохраняем порядок из документа
        print(f"Изображения с красным в порядке документа: {self.filtered_indices}")

    def count_red_pixels(self, img):
        """Подсчет красных пикселей"""
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        lower_red1 = np.array([0, 100, 100])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([160, 100, 100])
        upper_red2 = np.array([180, 255, 255])

        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = cv2.bitwise_or(mask1, mask2)

        return np.sum(red_mask > 0)

    def load_current_image(self):
        """Загрузка текущего изображения"""
        if self.current_index >= len(self.filtered_indices):
            self.finish_processing()
            return

        # Очищаем предыдущие регионы и сбрасываем предпросмотр
        self.regions = []
        self.mask_regions = []
        self.current_points = []
        self.preview_image = None
        self.preview_mode = False
        if hasattr(self, 'ui'):
            self.ui.btn_preview.setText("👁 Предпросмотр")
            self.ui.btn_preview.setStyleSheet(
                "QPushButton { background-color: #a9e34b; color: black; font-weight: bold; }")

        # Сбрасываем историю для нового изображения
        self.history = []
        self.history_index = -1
        self.add_to_history()  # Добавляем начальное пустое состояние

        # Загружаем изображение в порядке из документа
        image_idx = self.filtered_indices[self.current_index]
        image_part = self.image_parts[image_idx]
        image_bytes = image_part.blob

        # Сохраняем оригинал с номером по порядку в документе (только если это новое изображение)
        if len(self.original_paths) <= self.current_index:
            orig_path = os.path.join(self.comparison_dir,
                                     f"original_{self.current_index + 1:03d}_docpos_{image_idx + 1:03d}.png")
            with open(orig_path, 'wb') as f:
                f.write(image_bytes)
            self.original_paths.append(orig_path)

            # Для пропущенных изображений добавляем оригинал в processed_paths
            if len(self.processed_paths) <= self.current_index:
                self.processed_paths.append(orig_path)

        # Декодируем для отображения
        image_array = np.frombuffer(image_bytes, np.uint8)
        self.current_image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        # Конвертируем для отображения
        self.display_image()
        self.update_progress()

    def display_image(self):
        """Отображение изображения на метке с УВЕЛИЧЕННЫМ РАЗМЕРОМ"""
        if self.current_image is None:
            return

        # Конвертируем BGR в RGB
        img_rgb = cv2.cvtColor(self.current_image, cv2.COLOR_BGR2RGB)
        h, w, ch = img_rgb.shape
        bytes_per_line = ch * w

        # Создаем QImage
        q_img = QImage(img_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)

        # Масштабируем для отображения с УВЕЛИЧЕННЫМ РАЗМЕРОМ
        scaled_pixmap = pixmap.scaled(
            self.ui.image_label.width() - 20,  # Увеличиваем рабочую область
            self.ui.image_label.height() - 20,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.current_pixmap = scaled_pixmap
        self.ui.image_label.setPixmap(scaled_pixmap)

    def update_progress(self):
        """Обновление прогресса с информацией о порядке в документе"""
        if not self.filtered_indices:
            return

        total_red = len(self.filtered_indices)
        current_red_pixels = 0

        if self.current_image is not None:
            current_red_pixels = self.count_red_pixels(self.current_image)

        # Показываем порядковый номер в документе
        image_idx = self.filtered_indices[self.current_index]
        total_images = len(self.image_parts)

        self.ui.progress_label.setText(
            f"Изображение {self.current_index + 1}/{total_red} "
            f"(в документе: №{image_idx + 1} из {total_images})"
        )

        # Сбрасываем стиль метки красных пикселей
        self.ui.red_pixels_label.setText(f"Красных пикселей: {current_red_pixels}")
        self.ui.red_pixels_label.setStyleSheet("")

        self.ui.progress_bar.setMaximum(total_red)
        self.ui.progress_bar.setValue(self.current_index + 1)

    def on_mouse_press(self, event):
        """Нажатие мыши на изображении"""
        if self.current_pixmap is None:
            return

        # Получаем координаты относительно изображения
        pixmap_size = self.current_pixmap.size()
        label_size = self.ui.image_label.size()

        x_offset = (label_size.width() - pixmap_size.width()) // 2
        y_offset = (label_size.height() - pixmap_size.height()) // 2

        x = event.pos().x() - x_offset
        y = event.pos().y() - y_offset

        # РАЗРЕШАЕМ КЛИК ЗА ПРЕДЕЛАМИ ИЗОБРАЖЕНИЯ, НО В ПРЕДЕЛАХ LABEL
        # Расширяем область для выделения на 50 пикселей вокруг изображения
        extended_width = pixmap_size.width() + 100  # +50 с каждой стороны
        extended_height = pixmap_size.height() + 100  # +50 с каждой стороны

        if (-50 <= x < extended_width - 50 and
                -50 <= y < extended_height - 50):
            self.drawing = True
            self.last_point = (x, y)

            if self.mode == "rectangle" or self.mode == "ellipse":
                # Для прямоугольника и эллипса сохраняем начальную точку
                self.start_point = (x, y)
                self.current_points = [(x, y)]
            elif self.mode == "lasso" or self.mode == "mask":
                self.current_points = [(x, y)]

    def on_mouse_move(self, event):
        """Движение мыши с зажатой кнопкой"""
        if not self.drawing or self.current_pixmap is None:
            return

        pixmap_size = self.current_pixmap.size()
        label_size = self.ui.image_label.size()

        x_offset = (label_size.width() - pixmap_size.width()) // 2
        y_offset = (label_size.height() - pixmap_size.height()) // 2

        x = event.pos().x() - x_offset
        y = event.pos().y() - y_offset

        # РАЗРЕШАЕМ ДВИЖЕНИЕ ЗА ПРЕДЕЛАМИ ИЗОБРАЖЕНИЯ
        # Не проверяем границы при движении - позволяем рисовать где угодно
        if self.mode == "lasso" or self.mode == "mask":
            self.current_points.append((x, y))
            self.draw_temp_shape()
        elif self.mode == "rectangle":
            self.draw_temp_rectangle(x, y)
        elif self.mode == "ellipse":
            self.draw_temp_ellipse(x, y)

        self.last_point = (x, y)

    def on_mouse_release(self, event):
        """Отпускание кнопки мыши"""
        if not self.drawing or self.current_pixmap is None:
            return

        self.drawing = False

        pixmap_size = self.current_pixmap.size()
        label_size = self.ui.image_label.size()

        x_offset = (label_size.width() - pixmap_size.width()) // 2
        y_offset = (label_size.height() - pixmap_size.height()) // 2

        x = event.pos().x() - x_offset
        y = event.pos().y() - y_offset

        # РАЗРЕШАЕМ ОТПУСКАНИЕ ЗА ПРЕДЕЛАМИ ИЗОБРАЖЕНИЯ
        # Финализируем фигуру независимо от положения курсора
        if self.mode == "rectangle":
            self.finalize_rectangle(x, y)
        elif self.mode == "ellipse":
            self.finalize_ellipse(x, y)
        elif self.mode == "lasso":
            self.finalize_lasso()
        elif self.mode == "mask":
            self.finalize_mask()

        self.last_point = None
        self.start_point = None

        # АВТОМАТИЧЕСКИЙ ПРЕДПРОСМОТР после добавления области
        if self.auto_preview and (self.regions or self.mask_regions):
            self.create_auto_preview()

    def create_auto_preview(self):
        """Создание автоматического предпросмотра"""
        # Защита от рекурсии при обновлении предпросмотра
        if self.adding_to_history:
            return

        try:
            # Обрабатываем изображение для предпросмотра
            preview_img, red_count = self.process_image_with_regions()

            # Сохраняем для отображения
            self.preview_image = preview_img.copy()

            # Отображаем предпросмотр с подсветкой
            self.display_auto_preview(preview_img)

            # Показываем статистику
            self.show_auto_preview_stats(red_count)

        except Exception as e:
            print(f"Ошибка автопредпросмотра: {e}")
            # Показываем обычное изображение с контурами в случае ошибки
            self.redraw_all_shapes()

    def display_auto_preview(self, img):
        """Отображение автоматического предпросмотра с подсветкой изменений"""
        if self.current_image is None:
            return

        try:
            # Находим разницу между оригиналом и предпросмотром
            diff = cv2.absdiff(self.current_image, img)
            gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

            # Создаем маску измененных областей
            change_mask = gray_diff > 10

            # Создаем копию изображения для подсветки
            highlighted_img = img.copy()

            # ПРАВИЛЬНОЕ индексирование для подсветки измененных областей
            # Получаем координаты измененных пикселей
            changed_coords = np.where(change_mask)

            if len(changed_coords[0]) > 0:
                # Подсвечиваем измененные области зеленым (более мягко)
                for i in range(len(changed_coords[0])):
                    y, x = changed_coords[0][i], changed_coords[1][i]
                    # Смешиваем с зеленым цветом (30% зеленого)
                    highlighted_img[y, x, 0] = int(highlighted_img[y, x, 0] * 0.7)  # B
                    highlighted_img[y, x, 1] = int(highlighted_img[y, x, 1] * 0.7 + 255 * 0.3)  # G
                    highlighted_img[y, x, 2] = int(highlighted_img[y, x, 2] * 0.7)  # R

            # Конвертируем для отображения
            img_rgb = cv2.cvtColor(highlighted_img, cv2.COLOR_BGR2RGB)
            h, w, ch = img_rgb.shape
            bytes_per_line = ch * w

            # Создаем QImage
            q_img = QImage(img_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(q_img)

            # Масштабируем для отображения (С УВЕЛИЧЕННЫМ РАЗМЕРОМ)
            scaled_pixmap = pixmap.scaled(
                self.ui.image_label.width() - 20,
                self.ui.image_label.height() - 20,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            self.ui.image_label.setPixmap(scaled_pixmap)

        except Exception as e:
            print(f"Ошибка в display_auto_preview: {e}")
            # В случае ошибки показываем обычный предпросмотр
            self.display_preview_fallback(img)

    def display_preview_fallback(self, img):
        """Резервный метод отображения предпросмотра"""
        try:
            # Конвертируем BGR в RGB
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            h, w, ch = img_rgb.shape
            bytes_per_line = ch * w

            # Создаем QImage
            q_img = QImage(img_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(q_img)

            # Масштабируем для отображения
            scaled_pixmap = pixmap.scaled(
                self.ui.image_label.width() - 20,
                self.ui.image_label.height() - 20,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            self.ui.image_label.setPixmap(scaled_pixmap)
        except Exception as e:
            print(f"Ошибка в резервном отображении: {e}")

    def show_auto_preview_stats(self, red_count):
        """Показать статистику автопредпросмотра"""
        if hasattr(self, 'ui'):
            self.ui.red_pixels_label.setText(
                f"🟢 Будет заменено: {red_count} пикселей"
            )
            self.ui.red_pixels_label.setStyleSheet(
                "color: #51cf66; font-weight: bold; background-color: #f8f9fa; padding: 5px;")

    def draw_temp_shape(self):
        """Рисование временной фигуры"""
        if not self.current_points:
            return

        pixmap = self.current_pixmap.copy()
        painter = QPainter(pixmap)
        painter.setPen(QPen(QColor(255, 255, 0), 2))

        if len(self.current_points) > 1:
            for i in range(len(self.current_points) - 1):
                x1, y1 = self.current_points[i]
                x2, y2 = self.current_points[i + 1]
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        painter.end()
        self.ui.image_label.setPixmap(pixmap)

    def draw_temp_rectangle(self, x, y):
        """Рисование временного прямоугольника"""
        if self.start_point is None:
            return

        pixmap = self.current_pixmap.copy()
        painter = QPainter(pixmap)
        painter.setPen(QPen(QColor(255, 255, 0), 2))

        x1, y1 = self.start_point
        x2, y2 = x, y

        # Рисуем прямоугольник от начальной точки до текущей
        # Ограничиваем отрисовку размерами pixmap, но координаты могут быть за пределами
        draw_x1 = max(0, min(x1, x2))
        draw_y1 = max(0, min(y1, y2))
        draw_x2 = min(pixmap.width(), max(x1, x2))
        draw_y2 = min(pixmap.height(), max(y1, y2))

        painter.drawRect(int(draw_x1), int(draw_y1),
                         int(draw_x2 - draw_x1), int(draw_y2 - draw_y1))

        painter.end()
        self.ui.image_label.setPixmap(pixmap)

    def draw_temp_ellipse(self, x, y):
        """Рисование временного эллипса"""
        if self.start_point is None:
            return

        pixmap = self.current_pixmap.copy()
        painter = QPainter(pixmap)
        painter.setPen(QPen(QColor(255, 255, 0), 2))

        x1, y1 = self.start_point
        x2, y2 = x, y

        # Ограничиваем отрисовку размерами pixmap
        draw_x1 = max(0, min(x1, x2))
        draw_y1 = max(0, min(y1, y2))
        draw_x2 = min(pixmap.width(), max(x1, x2))
        draw_y2 = min(pixmap.height(), max(y1, y2))

        # Рисуем эллипс в ограничивающем прямоугольнике
        painter.drawEllipse(int(draw_x1), int(draw_y1),
                            int(draw_x2 - draw_x1), int(draw_y2 - draw_y1))

        painter.end()
        self.ui.image_label.setPixmap(pixmap)

    def finalize_rectangle(self, x, y):
        """Финализация прямоугольника"""
        if self.start_point is None:
            return

        x1, y1 = self.start_point
        x2, y2 = x, y

        self.regions.append({
            'type': 'rectangle',
            'x1': min(x1, x2), 'y1': min(y1, y2),
            'x2': max(x1, x2), 'y2': max(y1, y2)
        })

        # Добавляем в историю
        self.add_to_history()

        # Обновляем предпросмотр
        if self.auto_preview:
            self.create_auto_preview()

    def finalize_ellipse(self, x, y):
        """Финализация эллипса"""
        if self.start_point is None:
            return

        x1, y1 = self.start_point
        x2, y2 = x, y

        self.regions.append({
            'type': 'ellipse',
            'x1': min(x1, x2), 'y1': min(y1, y2),
            'x2': max(x1, x2), 'y2': max(y1, y2)
        })

        # Добавляем в историю
        self.add_to_history()

        # Обновляем предпросмотр
        if self.auto_preview:
            self.create_auto_preview()

    def finalize_lasso(self):
        """Финализация лассо"""
        if len(self.current_points) < 3:
            return

        self.regions.append({
            'type': 'lasso',
            'points': self.current_points.copy()
        })

        # Добавляем в историю
        self.add_to_history()

        # Обновляем предпросмотр
        if self.auto_preview:
            self.create_auto_preview()

    def finalize_mask(self):
        """Финализация маски"""
        if len(self.current_points) < 3:
            return

        self.mask_regions.append({
            'type': 'mask',
            'tool': self.current_tool,
            'points': self.current_points.copy()
        })

        # Добавляем в историю
        self.add_to_history()

        # Обновляем предпросмотр
        if self.auto_preview:
            self.create_auto_preview()

    def redraw_all_shapes(self):
        """Перерисовка всех фигур"""
        if self.current_pixmap is None:
            return

        # Если есть автопредпросмотр и регионы, показываем предпросмотр
        if self.auto_preview and self.preview_image is not None and (self.regions or self.mask_regions):
            self.display_auto_preview(self.preview_image)
            return

        # Иначе показываем оригинал с контурами
        pixmap = self.current_pixmap.copy()
        painter = QPainter(pixmap)

        # Рисуем регионы с БОЛЕЕ ЯРКИМИ И ТОЛСТЫМИ ЛИНИЯМИ
        painter.setPen(QPen(QColor(255, 255, 0), 3))
        for region in self.regions:
            if region['type'] == 'rectangle':
                x1, y1, x2, y2 = region['x1'], region['y1'], region['x2'], region['y2']
                # Ограничиваем отрисовку размерами pixmap
                draw_x1 = max(0, min(x1, x2))
                draw_y1 = max(0, min(y1, y2))
                draw_x2 = min(pixmap.width(), max(x1, x2))
                draw_y2 = min(pixmap.height(), max(y1, y2))
                painter.drawRect(int(draw_x1), int(draw_y1), int(draw_x2 - draw_x1), int(draw_y2 - draw_y1))

            elif region['type'] == 'ellipse':
                x1, y1, x2, y2 = region['x1'], region['y1'], region['x2'], region['y2']
                # Ограничиваем отрисовку размерами pixmap
                draw_x1 = max(0, min(x1, x2))
                draw_y1 = max(0, min(y1, y2))
                draw_x2 = min(pixmap.width(), max(x1, x2))
                draw_y2 = min(pixmap.height(), max(y1, y2))
                painter.drawEllipse(int(draw_x1), int(draw_y1), int(draw_x2 - draw_x1), int(draw_y2 - draw_y1))

            elif region['type'] == 'lasso':
                points = region['points']
                for i in range(len(points) - 1):
                    x1, y1 = points[i]
                    x2, y2 = points[i + 1]
                    # Ограничиваем линии размерами pixmap
                    if (0 <= x1 < pixmap.width() and 0 <= y1 < pixmap.height() and
                            0 <= x2 < pixmap.width() and 0 <= y2 < pixmap.height()):
                        painter.drawLine(int(x1), int(y1), int(x2), int(y2))

                # Замыкаем контур
                if len(points) > 1:
                    x1, y1 = points[-1]
                    x2, y2 = points[0]
                    if (0 <= x1 < pixmap.width() and 0 <= y1 < pixmap.height() and
                            0 <= x2 < pixmap.width() and 0 <= y2 < pixmap.height()):
                        painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        # Рисуем маски с БОЛЕЕ ЯРКИМИ ЦВЕТАМИ
        for mask in self.mask_regions:
            color = QColor(255, 100, 100) if mask['tool'] == 'draw' else QColor(200, 255, 200)
            painter.setPen(QPen(color, 4))

            points = mask['points']
            for i in range(len(points) - 1):
                x1, y1 = points[i]
                x2, y2 = points[i + 1]
                # Ограничиваем линии размерами pixmap
                if (0 <= x1 < pixmap.width() and 0 <= y1 < pixmap.height() and
                        0 <= x2 < pixmap.width() and 0 <= y2 < pixmap.height()):
                    painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        painter.end()

        # Масштабируем с УВЕЛИЧЕННЫМ РАЗМЕРОМ
        scaled_pixmap = pixmap.scaled(
            self.ui.image_label.width() - 20,
            self.ui.image_label.height() - 20,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.ui.image_label.setPixmap(scaled_pixmap)

    def process_current(self):
        """Обработка текущего изображения"""
        try:
            # Если в режиме предпросмотра, используем уже обработанное изображение
            if self.preview_mode and self.preview_image is not None:
                processed_img = self.preview_image
                red_count = self.count_changed_pixels()
            else:
                # Иначе обрабатываем заново
                processed_img, red_count = self.process_image_with_regions()

            # Сохраняем результат с номером по порядку в документе
            image_idx = self.filtered_indices[self.current_index]
            proc_path = os.path.join(self.comparison_dir,
                                     f"processed_{self.current_index + 1:03d}_docpos_{image_idx + 1:03d}.png")

            if red_count > 0:
                cv2.imwrite(proc_path, processed_img)
                print(f"✓ Обработано: {red_count} красных пикселей (изображение {image_idx + 1} в документе)")
            else:
                # Если красных пикселей не найдено, копируем оригинал
                orig_path = self.original_paths[-1]
                import shutil
                shutil.copy2(orig_path, proc_path)
                print(f"○ Красные пиксели не найдены (изображение {image_idx + 1} в документе)")

            self.processed_paths.append(proc_path)

            # Обновляем изображение в документе
            self.update_image_in_document(image_idx, proc_path)

            # Сбрасываем режим предпросмотра
            self.preview_mode = False
            self.ui.btn_preview.setText("👁 Предпросмотр")
            self.ui.btn_preview.setStyleSheet(
                "QPushButton { background-color: #a9e34b; color: black; font-weight: bold; }")

            # Переходим к следующему
            self.current_index += 1
            self.load_current_image()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка обработки: {str(e)}")
            print(f"Ошибка обработки: {e}")

    def count_changed_pixels(self):
        """Подсчет измененных пикселей в предпросмотре"""
        if self.preview_image is None or self.current_image is None:
            return 0

        # Сравниваем оригинал и предпросмотр
        diff = cv2.absdiff(self.current_image, self.preview_image)
        gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

        # Считаем пиксели, которые действительно изменились
        changed_pixels = np.sum(gray_diff > 10)  # Порог для учета изменений

        return changed_pixels

    def update_image_in_document(self, image_idx, proc_path):
        """Обновление изображения в документе"""
        try:
            # Находим соответствующую связь в документе
            for rel_id, rel in self.doc.part.rels.items():
                if hasattr(rel, 'target_part') and rel.target_part == self.image_parts[image_idx]:
                    # Заменяем данные изображения
                    with open(proc_path, 'rb') as f:
                        image_data = f.read()
                    rel.target_part._blob = image_data
                    print(f"✓ Обновлено изображение {image_idx + 1} в документе")
                    return True
            print(f"⚠ Не найдена связь для изображения {image_idx + 1}")
            return False
        except Exception as e:
            print(f"❌ Ошибка обновления изображения {image_idx + 1}: {e}")
            return False

    def process_image_with_regions(self):
        """Обработка изображения с регионами"""
        result_img = self.current_image.copy()

        # Создаем маску для замены
        replacement_mask = np.zeros(result_img.shape[:2], dtype=np.uint8)

        # Добавляем регионы
        for region in self.regions:
            if region['type'] == 'rectangle':
                # Конвертируем координаты
                x1, y1, x2, y2 = self.canvas_to_image_coords(
                    region['x1'], region['y1'], region['x2'], region['y2'])

                # Заполняем прямоугольник на маске
                replacement_mask[y1:y2, x1:x2] = 255

            elif region['type'] == 'ellipse':
                # Конвертируем координаты
                x1, y1, x2, y2 = self.canvas_to_image_coords(
                    region['x1'], region['y1'], region['x2'], region['y2'])

                # Создаем маску для эллипса
                ellipse_mask = np.zeros(result_img.shape[:2], dtype=np.uint8)

                # Вычисляем параметры эллипса
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                width = abs(x2 - x1)
                height = abs(y2 - y1)

                # Рисуем заполненный эллипс на маске
                if width > 0 and height > 0:
                    cv2.ellipse(ellipse_mask,
                                (center_x, center_y),
                                (width // 2, height // 2),
                                0, 0, 360, 255, -1)

                replacement_mask = cv2.bitwise_or(replacement_mask, ellipse_mask)

            elif region['type'] == 'lasso':
                mask = np.zeros(result_img.shape[:2], dtype=np.uint8)
                points = []
                for x, y in region['points']:
                    img_x, img_y = self.canvas_to_image_coords(x, y)
                    points.append([img_x, img_y])

                if len(points) >= 3:
                    cv2.fillPoly(mask, [np.array(points, dtype=np.int32)], 255)
                    replacement_mask = cv2.bitwise_or(replacement_mask, mask)

        # Применяем маски
        for mask_region in self.mask_regions:
            mask = np.zeros(result_img.shape[:2], dtype=np.uint8)
            points = []
            for x, y in mask_region['points']:
                img_x, img_y = self.canvas_to_image_coords(x, y)
                points.append([img_x, img_y])

            if len(points) >= 3:
                cv2.fillPoly(mask, [np.array(points, dtype=np.int32)], 255)
                if mask_region['tool'] == 'draw':
                    replacement_mask = cv2.bitwise_or(replacement_mask, mask)
                else:
                    replacement_mask = cv2.bitwise_and(replacement_mask, cv2.bitwise_not(mask))

        # Находим и заменяем красные пиксели
        red_pixels = self.find_red_pixels_in_mask(result_img, replacement_mask)
        result_img[red_pixels > 0] = list(self.replacement_color)[::-1]  # BGR

        return result_img, np.sum(red_pixels > 0)

    def canvas_to_image_coords(self, canvas_x, canvas_y, canvas_x2=None, canvas_y2=None):
        """Конвертация координат canvas в координаты изображения"""
        if self.current_pixmap is None or self.current_image is None:
            return int(canvas_x), int(canvas_y)

        pixmap_w = self.current_pixmap.width()
        pixmap_h = self.current_pixmap.height()
        img_w = self.current_image.shape[1]
        img_h = self.current_image.shape[0]

        # Масштабируем координаты, ОГРАНИЧИВАЯ диапазон размерами изображения
        img_x = max(0, min(img_w - 1, int(canvas_x * img_w / pixmap_w)))
        img_y = max(0, min(img_h - 1, int(canvas_y * img_h / pixmap_h)))

        if canvas_x2 is not None and canvas_y2 is not None:
            img_x2 = max(0, min(img_w, int(canvas_x2 * img_w / pixmap_w)))
            img_y2 = max(0, min(img_h, int(canvas_y2 * img_h / pixmap_h)))
            return img_x, img_y, img_x2, img_y2

        return img_x, img_y

    def find_red_pixels_in_mask(self, img, mask):
        """Находит красные пиксели в маске"""
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # Используем целевой цвет с допуском
        target_hsv = cv2.cvtColor(np.uint8([[list(self.target_color)]]), cv2.COLOR_RGB2HSV)[0][0]
        tolerance = 20

        lower_red = np.array([max(0, target_hsv[0] - tolerance), 100, 100])
        upper_red = np.array([min(179, target_hsv[0] + tolerance), 255, 255])

        red_mask = cv2.inRange(hsv, lower_red, upper_red)
        return cv2.bitwise_and(red_mask, red_mask, mask=mask)

    def finish_processing(self):
        """Завершение обработки"""
        try:
            # Всегда обрабатываем текущее изображение, если есть выделения (даже если это последнее)
            if self.regions or self.mask_regions:
                print("💾 Сохраняем текущее изображение перед завершением...")

                # Обрабатываем текущее изображение
                if self.preview_mode and self.preview_image is not None:
                    processed_img = self.preview_image
                    red_count = self.count_changed_pixels()
                else:
                    processed_img, red_count = self.process_image_with_regions()

                # Сохраняем результат текущего изображения
                image_idx = self.filtered_indices[self.current_index]
                proc_path = os.path.join(self.comparison_dir,
                                         f"processed_{self.current_index + 1:03d}_docpos_{image_idx + 1:03d}.png")

                if red_count > 0:
                    cv2.imwrite(proc_path, processed_img)
                    print(f"✓ Обработано текущее: {red_count} красных пикселей (изображение {image_idx + 1})")
                else:
                    # Если красных пикселей не найдено, копируем оригинал
                    orig_path = self.original_paths[self.current_index]
                    import shutil
                    shutil.copy2(orig_path, proc_path)
                    print(f"○ Красные пиксели не найдены (изображение {image_idx + 1})")

                # Добавляем или заменяем путь в processed_paths
                if len(self.processed_paths) > self.current_index:
                    self.processed_paths[self.current_index] = proc_path
                else:
                    self.processed_paths.append(proc_path)

                # Обновляем изображение в документе
                self.update_image_in_document(image_idx, proc_path)

            # Сохраняем документ с новым именем
            base_name = os.path.splitext(self.docx_path)[0]
            output_path = f"{base_name}_processed.docx"

            # Дополнительная проверка: обновляем все обработанные изображения
            updated_count = 0
            for i, proc_path in enumerate(self.processed_paths):
                if i < len(self.filtered_indices) and os.path.exists(proc_path):
                    image_idx = self.filtered_indices[i]
                    if self.update_image_in_document(image_idx, proc_path):
                        updated_count += 1

            # Сохраняем документ
            self.doc.save(output_path)
            print(f"📄 Документ сохранен как: {output_path}")
            print(f"🖼 Обновлено изображений: {updated_count}/{len(self.processed_paths)}")

            # Показываем результаты
            self.show_results(output_path, updated_count)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка сохранения: {str(e)}")
            print(f"❌ Ошибка сохранения: {e}")

    def process_or_skip(self):
        """Обработка или пропуск текущего изображения"""
        if self.regions or self.mask_regions:
            # Если есть выделения - обрабатываем
            self.process_current()
        else:
            # Если нет выделений - пропускаем
            self.skip_current()

    def skip_current(self):
        """Пропустить текущее изображение"""
        # Добавляем оригинальный путь в processed_paths для пропущенного изображения
        if len(self.processed_paths) <= self.current_index:
            self.processed_paths.append(self.original_paths[-1])

        self.current_index += 1
        self.load_current_image()

    def show_results(self, output_path, updated_count):
        """Показать результаты"""
        # Создаем папку сравнения
        output_folder = "comparison_results"
        os.makedirs(output_folder, exist_ok=True)

        comparison_count = 0
        changed_images = []

        for i, (orig_path, proc_path) in enumerate(zip(self.original_paths, self.processed_paths)):
            if os.path.exists(orig_path) and os.path.exists(proc_path):
                orig_img = cv2.imread(orig_path)
                proc_img = cv2.imread(proc_path)

                if orig_img is not None and proc_img is not None:
                    # Проверяем, что изображения действительно разные
                    if not np.array_equal(orig_img, proc_img):
                        # Приводим изображения к одинаковому размеру перед объединением
                        height = max(orig_img.shape[0], proc_img.shape[0])
                        width = max(orig_img.shape[1], proc_img.shape[1])

                        # Создаем изображения одинакового размера
                        orig_resized = cv2.resize(orig_img, (width, height))
                        proc_resized = cv2.resize(proc_img, (width, height))

                        # Объединяем горизонтально
                        try:
                            comparison = np.hstack([orig_resized, proc_resized])
                            image_idx = self.filtered_indices[i]
                            comp_path = os.path.join(output_folder, f"comparison_{image_idx + 1:03d}.png")
                            cv2.imwrite(comp_path, comparison)
                            comparison_count += 1
                            changed_images.append(image_idx + 1)
                        except Exception as e:
                            print(f"Ошибка при создании сравнения для изображения {i}: {e}")

        # Показываем изображения без красного
        self.show_images_without_red()

        # Формируем информационное сообщение
        changed_text = ""
        if changed_images:
            changed_text = f"\nИзмененные изображения (номера в документе): {sorted(changed_images)}"

        QMessageBox.information(
            self,
            "Готово!",
            f"📊 Статистика обработки:\n\n"
            f"• Всего изображений в документе: {len(self.image_parts)}\n"
            f"• Изображений с красным цветом: {len(self.filtered_indices)}\n"
            f"• Обработано изображений: {len(self.processed_paths)}\n"
            f"• Фактически изменено: {comparison_count}\n"
            f"• Обновлено в документе: {updated_count}\n\n"
            f"💾 Сохраненный документ:\n{output_path}\n"
            f"📁 Папка сравнения: {output_folder}"
            f"{changed_text}"
        )

    def show_images_without_red(self):
        """Показать изображения без красного"""
        no_red_indices = [i for i in range(len(self.image_parts)) if i not in self.filtered_indices]

        if no_red_indices:
            check_folder = "check_no_red_images"
            os.makedirs(check_folder, exist_ok=True)

            for i, idx in enumerate(no_red_indices):
                image_part = self.image_parts[idx]
                image_bytes = image_part.blob
                image_array = np.frombuffer(image_bytes, np.uint8)
                img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

                if img is not None:
                    cv2.imwrite(os.path.join(check_folder, f"no_red_{i + 1:03d}.png"), img)

            print(f"Сохранено {len(no_red_indices)} изображений без красного в '{check_folder}'")

    def closeEvent(self, event):
        """Обработка закрытия окна"""
        # Очистка временных файлов
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        event.accept()


def main():
    app = QApplication(sys.argv)

    # Автоматически ищем test.docx
    docx_path = "test.docx"
    if not os.path.exists(docx_path):
        docx_files = glob.glob("*.docx")
        if docx_files:
            docx_path = docx_files[0]
            print(f"Используется файл: {docx_path}")
        else:
            QMessageBox.critical(None, "Ошибка", "Не найден файл test.docx!")
            return

    editor = ShapeEditor()
    if editor.load_word_document(docx_path):
        editor.show()
    else:
        sys.exit(1)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()