import cv2
import numpy as np
from typing import List, Tuple, Dict, Any


class ImageProcessor:
    def __init__(self, document_processor):
        self.document_processor = document_processor

        # Текущее изображение
        self.current_image = None
        self.current_image_idx = None

        # Регионы и маски
        self.regions = []
        self.mask_regions = []

    def load_image(self, image_idx: int) -> np.ndarray:
        """Загрузка изображения по индексу"""
        image_part = self.document_processor.image_parts[image_idx]
        image_bytes = image_part.blob
        image_array = np.frombuffer(image_bytes, np.uint8)
        self.current_image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        self.current_image_idx = image_idx
        return self.current_image

    def count_color_pixels(self, img: np.ndarray, target_color: Tuple[int, int, int]) -> int:
        """Подсчет пикселей указанного цвета"""
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # Конвертируем целевой цвет в HSV
        target_bgr = np.uint8([[list(target_color)]])
        target_hsv = cv2.cvtColor(target_bgr, cv2.COLOR_RGB2HSV)[0][0]

        tolerance = self.document_processor.color_tolerance
        sat_thresh = self.document_processor.saturation_threshold
        val_thresh = self.document_processor.value_threshold

        # Создаем маску для цвета
        lower_color = np.array([
            max(0, target_hsv[0] - tolerance),
            sat_thresh,
            val_thresh
        ])
        upper_color = np.array([
            min(179, target_hsv[0] + tolerance),
            255,
            255
        ])

        color_mask = cv2.inRange(hsv, lower_color, upper_color)
        return np.sum(color_mask > 0)

    def process_image_with_regions(self) -> Tuple[np.ndarray, int]:
        """Обработка изображения с регионами"""
        if self.current_image is None:
            return None, 0

        result_img = self.current_image.copy()
        replacement_mask = np.zeros(result_img.shape[:2], dtype=np.uint8)

        # Добавляем регионы в маску
        for region in self.regions:
            mask = self._create_region_mask(region)
            replacement_mask = cv2.bitwise_or(replacement_mask, mask)

        # Применяем маски
        for mask_region in self.mask_regions:
            mask = self._create_region_mask(mask_region)
            if mask_region['tool'] == 'draw':
                replacement_mask = cv2.bitwise_or(replacement_mask, mask)
            else:
                replacement_mask = cv2.bitwise_and(replacement_mask, cv2.bitwise_not(mask))

        # Находим и заменяем пиксели всех целевых цветов
        total_replaced = 0
        for target_color in self.document_processor.target_colors:
            color_pixels = self._find_color_pixels_in_mask(result_img, replacement_mask, target_color)
            result_img[color_pixels > 0] = list(self.document_processor.replacement_color)[::-1]  # BGR
            total_replaced += np.sum(color_pixels > 0)

        return result_img, total_replaced

    def _create_region_mask(self, region: Dict[str, Any]) -> np.ndarray:
        """Создание маски для региона"""
        mask = np.zeros(self.current_image.shape[:2], dtype=np.uint8)

        if region['type'] == 'rectangle':
            x1, y1, x2, y2 = region['x1'], region['y1'], region['x2'], region['y2']
            cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1)

        elif region['type'] == 'ellipse':
            x1, y1, x2, y2 = region['x1'], region['y1'], region['x2'], region['y2']
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            width = abs(x2 - x1)
            height = abs(y2 - y1)

            if width > 0 and height > 0:
                cv2.ellipse(mask, (center_x, center_y), (width // 2, height // 2),
                            0, 0, 360, 255, -1)

        elif region['type'] == 'lasso' or region['type'] == 'mask':
            points = np.array(region['points'], dtype=np.int32)
            if len(points) >= 3:
                cv2.fillPoly(mask, [points], 255)

        return mask

    def _find_color_pixels_in_mask(self, img: np.ndarray, mask: np.ndarray,
                                   target_color: Tuple[int, int, int]) -> np.ndarray:
        """Находит пиксели указанного цвета в маске"""
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # Конвертируем целевой цвет в HSV
        target_bgr = np.uint8([[list(target_color)]])
        target_hsv = cv2.cvtColor(target_bgr, cv2.COLOR_RGB2HSV)[0][0]

        tolerance = self.document_processor.color_tolerance
        sat_thresh = self.document_processor.saturation_threshold
        val_thresh = self.document_processor.value_threshold

        lower_color = np.array([
            max(0, target_hsv[0] - tolerance),
            sat_thresh,
            val_thresh
        ])
        upper_color = np.array([
            min(179, target_hsv[0] + tolerance),
            255,
            255
        ])

        color_mask = cv2.inRange(hsv, lower_color, upper_color)
        return cv2.bitwise_and(color_mask, color_mask, mask=mask)

    def add_region(self, region: Dict[str, Any]):
        """Добавление региона"""
        self.regions.append(region)

    def add_mask_region(self, mask_region: Dict[str, Any]):
        """Добавление маски"""
        self.mask_regions.append(mask_region)

    def clear_regions(self):
        """Очистка всех регионов и масок"""
        self.regions.clear()
        self.mask_regions.clear()

    def get_region_count(self) -> int:
        """Получение количества регионов"""
        return len(self.regions) + len(self.mask_regions)