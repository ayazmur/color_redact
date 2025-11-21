import os
import cv2
import numpy as np
from PyQt5.QtWidgets import (QMainWindow, QMessageBox, QFileDialog, QToolBar, QAction)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QColor

from core.document_processor import DocumentProcessor
from core.image_processor import ImageProcessor
from core.history_manager import HistoryManager
from ui.widgets import RedShapeEditorUI
from ui.color_picker import ColorPickerDialog


class RedShapeEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Редактор цветовых фигур")
        self.setGeometry(100, 100, 1400, 900)

        # Инициализация компонентов
        self.document_processor = DocumentProcessor()
        self.image_processor = ImageProcessor(self.document_processor)
        self.history_manager = HistoryManager()

        # Настройки интерфейса
        self.mode = "rectangle"
        self.current_tool = "draw"
        self.auto_preview = True
        self.preview_mode = False
        self.preview_image = None

        # Для рисования
        self.current_pixmap = None
        self.drawing = False
        self.last_point = None
        self.start_point = None
        self.current_points = []

        # Инициализация UI
        self.ui = RedShapeEditorUI()
        self.setCentralWidget(self.ui)
        self.setup_ui_connections()
        self.setup_toolbar()  # Добавляем панель инструментов

        # Текущий индекс
        self.current_index = 0

    def setup_toolbar(self):
        """Настройка панели инструментов"""
        toolbar = QToolBar("Основные инструменты")
        self.addToolBar(toolbar)

        # Действие открытия файла
        open_action = QAction("📁 Открыть Word документ", self)
        open_action.triggered.connect(self.show_file_selection_dialog)
        toolbar.addAction(open_action)

        toolbar.addSeparator()

        # Действие выхода
        exit_action = QAction("🚪 Выход", self)
        exit_action.triggered.connect(self.close)
        toolbar.addAction(exit_action)

    def setup_ui_connections(self):
        """Настройка соединений сигналов и слотов"""
        # Кнопки цветов
        self.ui.btn_choose_target.clicked.connect(self.choose_target_color)
        self.ui.btn_choose_replacement.clicked.connect(self.choose_replacement_color)
        self.ui.btn_manage_colors.clicked.connect(self.manage_colors)

        # Режимы выделения
        self.ui.mode_group.buttonClicked.connect(self.change_mode)
        self.ui.mask_btn_group.buttonClicked.connect(self.change_mask_mode)

        # Автопредпросмотр
        self.ui.auto_preview_check.toggled.connect(self.toggle_auto_preview)

        # Кнопки управления
        self.ui.btn_undo.clicked.connect(self.undo)
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

    def show_file_selection_dialog(self):
        """Показать диалог выбора файла"""
        docx_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите Word документ",
            "",
            "Word Documents (*.docx);;All Files (*)"
        )

        if docx_path:
            if self.load_word_document(docx_path):
                QMessageBox.information(self, "Успех", f"Документ загружен: {os.path.basename(docx_path)}")
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось загрузить документ!")
    def keyPressEvent(self, event):
        """Обработка нажатий клавиш"""
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_Z:
            # Ctrl+Z - отмена
            self.undo()
            event.accept()
        elif event.modifiers() == (Qt.ControlModifier | Qt.ShiftModifier) and event.key() == Qt.Key_Z:
            # Ctrl+Shift+Z - повтор
            self.redo()
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

    def load_word_document(self, docx_path: str) -> bool:
        """Загрузка Word документа"""
        if not self.document_processor.load_document(docx_path):
            return False

        # Фильтруем изображения с целевыми цветами
        self.document_processor.filter_images_with_red(self.image_processor)

        if not self.document_processor.filtered_indices:
            QMessageBox.information(self, "Информация",
                                    "Не найдено изображений с целевыми цветами!\n"
                                    "Вы можете продолжить работу и добавить цвета вручную.")
            # Создаем пустой список для работы
            self.document_processor.filtered_indices = list(range(len(self.document_processor.image_parts)))

        self.current_index = 0
        self.load_current_image()
        self.update_color_info()
        return True

    def load_current_image(self):
        """Загрузка текущего изображения"""
        if self.current_index >= len(self.document_processor.filtered_indices):
            self.finish_processing()
            return

        # Очищаем регионы и сбрасываем предпросмотр
        self.image_processor.clear_regions()
        self.history_manager.clear()
        self.preview_image = None
        self.preview_mode = False

        self.ui.btn_preview.setText("👁 Предпросмотр")
        self.ui.btn_preview.setStyleSheet(
            "QPushButton { background-color: #a9e34b; color: black; font-weight: bold; }")

        # Загружаем изображение
        image_idx = self.document_processor.filtered_indices[self.current_index]
        self.image_processor.load_image(image_idx)

        # Сохраняем оригинал
        if len(self.document_processor.original_paths) <= self.current_index:
            orig_path = self.document_processor.save_original_image(self.current_index, image_idx)
            self.document_processor.original_paths.append(orig_path)

            if len(self.document_processor.processed_paths) <= self.current_index:
                self.document_processor.processed_paths.append(orig_path)

        # Отображаем изображение
        self.display_image()
        self.update_progress()

        # Добавляем начальное состояние в историю
        self.history_manager.add_state([], [])

    def display_image(self):
        """Отображение изображения на метке с УВЕЛИЧЕННЫМ РАЗМЕРОМ"""
        if self.image_processor.current_image is None:
            return

        # Конвертируем BGR в RGB
        img_rgb = cv2.cvtColor(self.image_processor.current_image, cv2.COLOR_BGR2RGB)
        h, w, ch = img_rgb.shape
        bytes_per_line = ch * w

        # Создаем QImage
        q_img = QImage(img_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)

        # Масштабируем для отображения с УВЕЛИЧЕННЫМ РАЗМЕРОМ
        scaled_pixmap = pixmap.scaled(
            self.ui.image_label.width() - 20,
            self.ui.image_label.height() - 20,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.current_pixmap = scaled_pixmap
        self.ui.image_label.setPixmap(scaled_pixmap)

    def update_progress(self):
        """Обновление прогресса с информацией о порядке в документе"""
        if not self.document_processor.filtered_indices:
            return

        total_red = len(self.document_processor.filtered_indices)
        current_color_pixels = 0

        if self.image_processor.current_image is not None:
            # Считаем пиксели всех целевых цветов
            for target_color in self.document_processor.target_colors:
                current_color_pixels += self.image_processor.count_color_pixels(
                    self.image_processor.current_image, target_color)

        # Показываем порядковый номер в документе
        image_idx = self.document_processor.filtered_indices[self.current_index]
        total_images = len(self.document_processor.image_parts)

        self.ui.progress_label.setText(
            f"Изображение {self.current_index + 1}/{total_red} "
            f"(в документе: №{image_idx + 1} из {total_images})"
        )

        # Сбрасываем стиль метки цветных пикселей
        self.ui.red_pixels_label.setText(f"Цветных пикселей: {current_color_pixels}")
        self.ui.red_pixels_label.setStyleSheet("")

        self.ui.progress_bar.setMaximum(total_red)
        self.ui.progress_bar.setValue(self.current_index + 1)

    def update_color_info(self):
        """Обновление информации о цветах"""
        colors_text = " → ".join([f"RGB{color}" for color in self.document_processor.target_colors])
        self.ui.color_info.setText(f"Замена: {colors_text} → RGB{self.document_processor.replacement_color}")
        self.ui.update_color_list(self.document_processor.target_colors)

    def choose_target_color(self):
        """Выбор целевого цвета"""
        dialog = ColorPickerDialog(self.document_processor.target_colors, self)
        if dialog.exec_():
            new_colors = dialog.get_colors()
            self.document_processor.target_colors = new_colors
            self.update_color_info()

    def choose_replacement_color(self):
        """Выбор цвета замены"""
        from PyQt5.QtWidgets import QColorDialog
        color = QColorDialog.getColor(QColor(*self.document_processor.replacement_color),
                                      self, "Выберите цвет для замены")
        if color.isValid():
            self.document_processor.set_replacement_color((color.red(), color.green(), color.blue()))
            self.update_color_info()

    def manage_colors(self):
        """Управление цветами"""
        dialog = ColorPickerDialog(self.document_processor.target_colors, self)
        if dialog.exec_():
            new_colors = dialog.get_colors()
            self.document_processor.target_colors = new_colors
            self.update_color_info()

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

    def toggle_auto_preview(self, enabled):
        """Включение/выключение автопредпросмотра"""
        self.auto_preview = enabled
        if enabled and self.image_processor.get_region_count() > 0:
            self.create_auto_preview()

    def toggle_preview(self):
        """Переключение режима предпросмотра"""
        if self.image_processor.get_region_count() == 0:
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
            preview_img, replaced_count = self.image_processor.process_image_with_regions()

            # Сохраняем для отображения
            self.preview_image = preview_img.copy()

            # Отображаем предпросмотр
            self.display_preview_image(preview_img)

            # Показываем статистику
            self.show_preview_stats(replaced_count)

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

    def show_preview_stats(self, replaced_count):
        """Показать статистику предпросмотра"""
        # Временно меняем текст прогресса для показа статистики
        original_text = self.ui.progress_label.text()
        self.ui.progress_label.setText(
            f"{original_text} | Предпросмотр: заменено {replaced_count} пикселей"
        )

        # Меняем цвет метки цветных пикселей
        self.ui.red_pixels_label.setText(
            f"🔴 Заменено цветных пикселей: {replaced_count}"
        )
        self.ui.red_pixels_label.setStyleSheet("color: #51cf66; font-weight: bold;")

    def create_auto_preview(self):
        """Создание автоматического предпросмотра"""
        # Защита от рекурсии при обновлении предпросмотра
        if self.history_manager.adding_to_history:
            return

        try:
            # Обрабатываем изображение для предпросмотра
            preview_img, replaced_count = self.image_processor.process_image_with_regions()

            # Сохраняем для отображения
            self.preview_image = preview_img.copy()

            # Отображаем предпросмотр с подсветкой
            self.display_auto_preview(preview_img)

            # Показываем статистику
            self.show_auto_preview_stats(replaced_count)

        except Exception as e:
            print(f"Ошибка автопредпросмотра: {e}")
            # Показываем обычное изображение с контурами в случае ошибки
            self.redraw_all_shapes()

    def display_auto_preview(self, img):
        """Отображение автоматического предпросмотра с подсветкой изменений"""
        if self.image_processor.current_image is None:
            return

        try:
            # Находим разницу между оригиналом и предпросмотром
            diff = cv2.absdiff(self.image_processor.current_image, img)
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

    def show_auto_preview_stats(self, replaced_count):
        """Показать статистику автопредпросмотра"""
        self.ui.red_pixels_label.setText(
            f"🟢 Будет заменено: {replaced_count} пикселей"
        )
        self.ui.red_pixels_label.setStyleSheet(
            "color: #51cf66; font-weight: bold; background-color: #f8f9fa; padding: 5px;")

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
        if self.auto_preview and self.image_processor.get_region_count() > 0:
            self.create_auto_preview()

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

        # Конвертируем координаты canvas в координаты изображения
        img_x1, img_y1 = self.canvas_to_image_coords(min(x1, x2), min(y1, y2))
        img_x2, img_y2 = self.canvas_to_image_coords(max(x1, x2), max(y1, y2))

        region = {
            'type': 'rectangle',
            'x1': img_x1, 'y1': img_y1,
            'x2': img_x2, 'y2': img_y2
        }

        self.image_processor.add_region(region)

        # Добавляем в историю
        self.history_manager.add_state(self.image_processor.regions, self.image_processor.mask_regions)

        # Обновляем предпросмотр
        if self.auto_preview:
            self.create_auto_preview()

    def finalize_ellipse(self, x, y):
        """Финализация эллипса"""
        if self.start_point is None:
            return

        x1, y1 = self.start_point
        x2, y2 = x, y

        # Конвертируем координаты canvas в координаты изображения
        img_x1, img_y1 = self.canvas_to_image_coords(min(x1, x2), min(y1, y2))
        img_x2, img_y2 = self.canvas_to_image_coords(max(x1, x2), max(y1, y2))

        region = {
            'type': 'ellipse',
            'x1': img_x1, 'y1': img_y1,
            'x2': img_x2, 'y2': img_y2
        }

        self.image_processor.add_region(region)

        # Добавляем в историю
        self.history_manager.add_state(self.image_processor.regions, self.image_processor.mask_regions)

        # Обновляем предпросмотр
        if self.auto_preview:
            self.create_auto_preview()

    def finalize_lasso(self):
        """Финализация лассо"""
        if len(self.current_points) < 3:
            return

        # Конвертируем координаты canvas в координаты изображения
        img_points = []
        for x, y in self.current_points:
            img_x, img_y = self.canvas_to_image_coords(x, y)
            img_points.append([img_x, img_y])

        region = {
            'type': 'lasso',
            'points': img_points
        }

        self.image_processor.add_region(region)

        # Добавляем в историю
        self.history_manager.add_state(self.image_processor.regions, self.image_processor.mask_regions)

        # Обновляем предпросмотр
        if self.auto_preview:
            self.create_auto_preview()

    def finalize_mask(self):
        """Финализация маски"""
        if len(self.current_points) < 3:
            return

        # Конвертируем координаты canvas в координаты изображения
        img_points = []
        for x, y in self.current_points:
            img_x, img_y = self.canvas_to_image_coords(x, y)
            img_points.append([img_x, img_y])

        mask_region = {
            'type': 'mask',
            'tool': self.current_tool,
            'points': img_points
        }

        self.image_processor.add_mask_region(mask_region)

        # Добавляем в историю
        self.history_manager.add_state(self.image_processor.regions, self.image_processor.mask_regions)

        # Обновляем предпросмотр
        if self.auto_preview:
            self.create_auto_preview()

    def canvas_to_image_coords(self, canvas_x, canvas_y):
        """Конвертация координат canvas в координаты изображения"""
        if self.current_pixmap is None or self.image_processor.current_image is None:
            return int(canvas_x), int(canvas_y)

        pixmap_w = self.current_pixmap.width()
        pixmap_h = self.current_pixmap.height()
        img_w = self.image_processor.current_image.shape[1]
        img_h = self.image_processor.current_image.shape[0]

        # Масштабируем координаты, ОГРАНИЧИВАЯ диапазон размерами изображения
        img_x = max(0, min(img_w - 1, int(canvas_x * img_w / pixmap_w)))
        img_y = max(0, min(img_h - 1, int(canvas_y * img_h / pixmap_h)))

        return img_x, img_y

    def redraw_all_shapes(self):
        """Перерисовка всех фигур"""
        if self.current_pixmap is None:
            return

        # Если есть автопредпросмотр и регионы, показываем предпросмотр
        if self.auto_preview and self.preview_image is not None and self.image_processor.get_region_count() > 0:
            self.display_auto_preview(self.preview_image)
            return

        # Иначе показываем оригинал с контурами
        pixmap = self.current_pixmap.copy()
        painter = QPainter(pixmap)

        # Рисуем регионы с БОЛЕЕ ЯРКИМИ И ТОЛСТЫМИ ЛИНИЯМИ
        painter.setPen(QPen(QColor(255, 255, 0), 3))

        # Временная функция для обратного преобразования координат
        def image_to_canvas_coords(img_x, img_y):
            if self.current_pixmap is None or self.image_processor.current_image is None:
                return img_x, img_y

            pixmap_w = self.current_pixmap.width()
            pixmap_h = self.current_pixmap.height()
            img_w = self.image_processor.current_image.shape[1]
            img_h = self.image_processor.current_image.shape[0]

            canvas_x = int(img_x * pixmap_w / img_w)
            canvas_y = int(img_y * pixmap_h / img_h)
            return canvas_x, canvas_y

        for region in self.image_processor.regions:
            if region['type'] == 'rectangle':
                # Конвертируем координаты обратно для отображения
                x1, y1 = image_to_canvas_coords(region['x1'], region['y1'])
                x2, y2 = image_to_canvas_coords(region['x2'], region['y2'])

                # Ограничиваем отрисовку размерами pixmap
                draw_x1 = max(0, min(x1, x2))
                draw_y1 = max(0, min(y1, y2))
                draw_x2 = min(pixmap.width(), max(x1, x2))
                draw_y2 = min(pixmap.height(), max(y1, y2))
                painter.drawRect(int(draw_x1), int(draw_y1), int(draw_x2 - draw_x1), int(draw_y2 - draw_y1))

            elif region['type'] == 'ellipse':
                # Конвертируем координаты обратно для отображения
                x1, y1 = image_to_canvas_coords(region['x1'], region['y1'])
                x2, y2 = image_to_canvas_coords(region['x2'], region['y2'])

                # Ограничиваем отрисовку размерами pixmap
                draw_x1 = max(0, min(x1, x2))
                draw_y1 = max(0, min(y1, y2))
                draw_x2 = min(pixmap.width(), max(x1, x2))
                draw_y2 = min(pixmap.height(), max(y1, y2))
                painter.drawEllipse(int(draw_x1), int(draw_y1), int(draw_x2 - draw_x1), int(draw_y2 - draw_y1))

            elif region['type'] == 'lasso':
                points = []
                for point in region['points']:
                    canvas_x, canvas_y = image_to_canvas_coords(point[0], point[1])
                    points.append((canvas_x, canvas_y))

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
        for mask in self.image_processor.mask_regions:
            color = QColor(255, 100, 100) if mask['tool'] == 'draw' else QColor(200, 255, 200)
            painter.setPen(QPen(color, 4))

            points = []
            for point in mask['points']:
                canvas_x, canvas_y = image_to_canvas_coords(point[0], point[1])
                points.append((canvas_x, canvas_y))

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

    def undo(self):
        """Отмена последнего действия"""
        state = self.history_manager.undo()
        if state:
            self.image_processor.regions = state['regions']
            self.image_processor.mask_regions = state['mask_regions']

            # Обновляем отображение
            if self.image_processor.get_region_count() > 0:
                self.create_auto_preview()
            else:
                self.display_image()
                self.update_progress()

    def redo(self):
        """Повтор отмененного действия"""
        state = self.history_manager.redo()
        if state:
            self.image_processor.regions = state['regions']
            self.image_processor.mask_regions = state['mask_regions']

            # Обновляем отображение
            if self.image_processor.get_region_count() > 0:
                self.create_auto_preview()

    def process_current(self):
        """Обработка текущего изображения"""
        try:
            # Если в режиме предпросмотра, используем уже обработанное изображение
            if self.preview_mode and self.preview_image is not None:
                processed_img = self.preview_image
                replaced_count = self.count_changed_pixels()
            else:
                # Иначе обрабатываем заново
                processed_img, replaced_count = self.image_processor.process_image_with_regions()

            # Сохраняем результат с номером по порядку в документе
            image_idx = self.document_processor.filtered_indices[self.current_index]
            proc_path = os.path.join(self.document_processor.comparison_dir,
                                     f"processed_{self.current_index + 1:03d}_docpos_{image_idx + 1:03d}.png")

            if replaced_count > 0:
                cv2.imwrite(proc_path, processed_img)
                print(f"✓ Обработано: {replaced_count} цветных пикселей (изображение {image_idx + 1} в документе)")
            else:
                # Если цветных пикселей не найдено, копируем оригинал
                orig_path = self.document_processor.original_paths[-1]
                import shutil
                shutil.copy2(orig_path, proc_path)
                print(f"○ Цветные пиксели не найдены (изображение {image_idx + 1} в документе)")

            self.document_processor.processed_paths.append(proc_path)

            # Обновляем изображение в документе
            self.document_processor.update_image_in_document(image_idx, proc_path)

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
        if self.preview_image is None or self.image_processor.current_image is None:
            return 0

        # Сравниваем оригинал и предпросмотр
        diff = cv2.absdiff(self.image_processor.current_image, self.preview_image)
        gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

        # Считаем пиксели, которые действительно изменились
        changed_pixels = np.sum(gray_diff > 10)  # Порог для учета изменений

        return changed_pixels

    def process_or_skip(self):
        """Обработка или пропуск текущего изображения"""
        if self.image_processor.get_region_count() > 0:
            # Если есть выделения - обрабатываем
            self.process_current()
        else:
            # Если нет выделений - пропускаем
            self.skip_current()

    def skip_current(self):
        """Пропустить текущее изображение"""
        # Добавляем оригинальный путь в processed_paths для пропущенного изображения
        if len(self.document_processor.processed_paths) <= self.current_index:
            self.document_processor.processed_paths.append(self.document_processor.original_paths[-1])

        self.current_index += 1
        self.load_current_image()

    def go_to_previous(self):
        """Перейти к предыдущему изображению"""
        if self.current_index > 0:
            # Уменьшаем индекс и загружаем предыдущее изображение
            self.current_index -= 1

            # Удаляем последний элемент из processed_paths и original_paths
            if self.document_processor.processed_paths:
                self.document_processor.processed_paths.pop()
            if self.document_processor.original_paths:
                self.document_processor.original_paths.pop()

            # Загружаем предыдущее изображение
            self.load_current_image()
            print(f"← Вернулись к изображению {self.current_index + 1}")
        else:
            print("Это первое изображение, нельзя вернуться назад")

    def finish_processing(self):
        """Завершение обработки"""
        try:
            # Всегда обрабатываем текущее изображение, если есть выделения (даже если это последнее)
            if self.image_processor.get_region_count() > 0:
                print("💾 Сохраняем текущее изображение перед завершением...")

                # Обрабатываем текущее изображение
                if self.preview_mode and self.preview_image is not None:
                    processed_img = self.preview_image
                    replaced_count = self.count_changed_pixels()
                else:
                    processed_img, replaced_count = self.image_processor.process_image_with_regions()

                # Сохраняем результат текущего изображения
                image_idx = self.document_processor.filtered_indices[self.current_index]
                proc_path = os.path.join(self.document_processor.comparison_dir,
                                         f"processed_{self.current_index + 1:03d}_docpos_{image_idx + 1:03d}.png")

                if replaced_count > 0:
                    cv2.imwrite(proc_path, processed_img)
                    print(f"✓ Обработано текущее: {replaced_count} цветных пикселей (изображение {image_idx + 1})")
                else:
                    # Если цветных пикселей не найдено, копируем оригинал
                    orig_path = self.document_processor.original_paths[self.current_index]
                    import shutil
                    shutil.copy2(orig_path, proc_path)
                    print(f"○ Цветные пиксели не найдены (изображение {image_idx + 1})")

                # Добавляем или заменяем путь в processed_paths
                if len(self.document_processor.processed_paths) > self.current_index:
                    self.document_processor.processed_paths[self.current_index] = proc_path
                else:
                    self.document_processor.processed_paths.append(proc_path)

                # Обновляем изображение в документе
                self.document_processor.update_image_in_document(image_idx, proc_path)

            # Сохраняем документ с новым именем
            output_path = self.document_processor.save_processed_document()

            # Дополнительная проверка: обновляем все обработанные изображения
            updated_count = 0
            for i, proc_path in enumerate(self.document_processor.processed_paths):
                if i < len(self.document_processor.filtered_indices) and os.path.exists(proc_path):
                    image_idx = self.document_processor.filtered_indices[i]
                    if self.document_processor.update_image_in_document(image_idx, proc_path):
                        updated_count += 1

            print(f"📄 Документ сохранен как: {output_path}")
            print(f"🖼 Обновлено изображений: {updated_count}/{len(self.document_processor.processed_paths)}")

            # Показываем результаты
            self.show_results(output_path, updated_count)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка сохранения: {str(e)}")
            print(f"❌ Ошибка сохранения: {e}")

    def show_results(self, output_path, updated_count):
        """Показать результаты"""
        # Создаем папку сравнения
        output_folder = "comparison_results"
        os.makedirs(output_folder, exist_ok=True)

        comparison_count = 0
        changed_images = []

        for i, (orig_path, proc_path) in enumerate(zip(self.document_processor.original_paths,
                                                       self.document_processor.processed_paths)):
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
                            image_idx = self.document_processor.filtered_indices[i]
                            comp_path = os.path.join(output_folder, f"comparison_{image_idx + 1:03d}.png")
                            cv2.imwrite(comp_path, comparison)
                            comparison_count += 1
                            changed_images.append(image_idx + 1)
                        except Exception as e:
                            print(f"Ошибка при создании сравнения для изображения {i}: {e}")

        # Показываем изображения без целевых цветов
        self.show_images_without_target_colors()

        # Формируем информационное сообщение
        changed_text = ""
        if changed_images:
            changed_text = f"\nИзмененные изображения (номера в документе): {sorted(changed_images)}"

        QMessageBox.information(
            self,
            "Готово!",
            f"📊 Статистика обработки:\n\n"
            f"• Всего изображений в документе: {len(self.document_processor.image_parts)}\n"
            f"• Изображений с целевыми цветами: {len(self.document_processor.filtered_indices)}\n"
            f"• Обработано изображений: {len(self.document_processor.processed_paths)}\n"
            f"• Фактически изменено: {comparison_count}\n"
            f"• Обновлено в документе: {updated_count}\n\n"
            f"💾 Сохраненный документ:\n{output_path}\n"
            f"📁 Папка сравнения: {output_folder}"
            f"{changed_text}"
        )

    def show_images_without_target_colors(self):
        """Показать изображения без целевых цветов"""
        no_color_indices = [i for i in range(len(self.document_processor.image_parts))
                            if i not in self.document_processor.filtered_indices]

        if no_color_indices:
            check_folder = "check_no_color_images"
            os.makedirs(check_folder, exist_ok=True)

            for i, idx in enumerate(no_color_indices):
                image_part = self.document_processor.image_parts[idx]
                image_bytes = image_part.blob
                image_array = np.frombuffer(image_bytes, np.uint8)
                img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

                if img is not None:
                    cv2.imwrite(os.path.join(check_folder, f"no_color_{i + 1:03d}.png"), img)

            print(f"Сохранено {len(no_color_indices)} изображений без целевых цветов в '{check_folder}'")

    def closeEvent(self, event):
        """Обработка закрытия окна"""
        # Очистка временных файлов
        self.document_processor.cleanup()
        event.accept()