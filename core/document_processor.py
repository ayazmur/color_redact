import os
import tempfile
import shutil
import cv2
import numpy as np
from docx import Document
from typing import List, Tuple, Dict, Any


class DocumentProcessor:
    def __init__(self):
        self.docx_path = None
        self.doc = None
        self.image_parts = []
        self.filtered_indices = []
        self.original_paths = []
        self.processed_paths = []

        # Временные файлы
        self.temp_dir = tempfile.mkdtemp()
        self.comparison_dir = os.path.join(self.temp_dir, "comparison")
        os.makedirs(self.comparison_dir, exist_ok=True)

        # Цвета для замены
        self.target_colors = [(236, 19, 27)]  # Список целевых цветов
        self.replacement_color = (0, 0, 255)  # Цвет замены

        # Настройки цвета
        self.color_tolerance = 20
        self.saturation_threshold = 100
        self.value_threshold = 100

    def load_document(self, docx_path: str) -> bool:
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
                return False

            return True
        except Exception as e:
            print(f"Ошибка загрузки документа: {e}")
            return False

    def filter_images_with_red(self, color_detector) -> None:
        """Фильтрация изображений с целевыми цветами"""
        self.filtered_indices = []

        for i, image_part in enumerate(self.image_parts):
            image_bytes = image_part.blob
            image_array = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

            if img is not None:
                # Проверяем все целевые цвета
                has_target_color = False
                for target_color in self.target_colors:
                    red_count = color_detector.count_color_pixels(img, target_color)
                    if red_count > 0:
                        has_target_color = True
                        break

                if has_target_color:
                    self.filtered_indices.append(i)

        print(f"Изображения с целевыми цветами в порядке документа: {self.filtered_indices}")

    def save_original_image(self, index: int, image_idx: int) -> str:
        """Сохранение оригинального изображения"""
        image_part = self.image_parts[image_idx]
        orig_path = os.path.join(self.comparison_dir,
                                 f"original_{index + 1:03d}_docpos_{image_idx + 1:03d}.png")

        with open(orig_path, 'wb') as f:
            f.write(image_part.blob)

        return orig_path

    def update_image_in_document(self, image_idx: int, proc_path: str) -> bool:
        """Обновление изображения в документе"""
        try:
            for rel_id, rel in self.doc.part.rels.items():
                if hasattr(rel, 'target_part') and rel.target_part == self.image_parts[image_idx]:
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

    def save_processed_document(self) -> str:
        """Сохранение обработанного документа"""
        base_name = os.path.splitext(self.docx_path)[0]
        output_path = f"{base_name}_processed.docx"
        self.doc.save(output_path)
        return output_path

    def cleanup(self):
        """Очистка временных файлов"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def add_target_color(self, color: Tuple[int, int, int]):
        """Добавление целевого цвета"""
        if color not in self.target_colors:
            self.target_colors.append(color)

    def remove_target_color(self, color: Tuple[int, int, int]):
        """Удаление целевого цвета"""
        if color in self.target_colors:
            self.target_colors.remove(color)

    def set_replacement_color(self, color: Tuple[int, int, int]):
        """Установка цвета замены"""
        self.replacement_color = color

    def set_color_tolerance(self, tolerance: int):
        """Установка допуска цвета"""
        self.color_tolerance = tolerance

    def set_saturation_threshold(self, threshold: int):
        """Установка порога насыщенности"""
        self.saturation_threshold = threshold

    def set_value_threshold(self, threshold: int):
        """Установка порога значения"""
        self.value_threshold = threshold