from typing import List, Dict, Any


class HistoryManager:
    def __init__(self, max_history_size: int = 50):
        self.history = []
        self.history_index = -1
        self.max_history_size = max_history_size
        self.adding_to_history = False

    def add_state(self, regions: List[Dict], mask_regions: List[Dict]) -> None:
        """Добавление состояния в историю"""
        if self.adding_to_history:
            return

        self.adding_to_history = True

        try:
            state = {
                'regions': self._deep_copy_regions(regions),
                'mask_regions': self._deep_copy_regions(mask_regions)
            }

            # Удаляем состояния после текущего индекса
            if self.history_index < len(self.history) - 1:
                self.history = self.history[:self.history_index + 1]

            # Добавляем новое состояние
            self.history.append(state)
            self.history_index = len(self.history) - 1

            # Ограничиваем размер истории
            if len(self.history) > self.max_history_size:
                self.history.pop(0)
                self.history_index -= 1

        finally:
            self.adding_to_history = False

    def undo(self) -> Dict[str, List]:
        """Отмена последнего действия"""
        if self.history_index > 0:
            self.history_index -= 1
            return self._get_current_state()
        return None

    def redo(self) -> Dict[str, List]:
        """Повтор отмененного действия"""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            return self._get_current_state()
        return None

    def _get_current_state(self) -> Dict[str, List]:
        """Получение текущего состояния"""
        if 0 <= self.history_index < len(self.history):
            return self.history[self.history_index]
        return {'regions': [], 'mask_regions': []}

    def _deep_copy_regions(self, regions: List[Dict]) -> List[Dict]:
        """Глубокое копирование регионов"""
        copied_regions = []
        for region in regions:
            if region['type'] in ['rectangle', 'ellipse']:
                copied_regions.append({
                    'type': region['type'],
                    'x1': region['x1'],
                    'y1': region['y1'],
                    'x2': region['x2'],
                    'y2': region['y2']
                })
            elif region['type'] in ['lasso', 'mask']:
                copied_regions.append({
                    'type': region['type'],
                    'tool': region.get('tool', 'draw'),
                    'points': region['points'].copy()
                })
        return copied_regions

    def can_undo(self) -> bool:
        """Можно ли отменить"""
        return self.history_index > 0

    def can_redo(self) -> bool:
        """Можно ли повторить"""
        return self.history_index < len(self.history) - 1

    def clear(self):
        """Очистка истории"""
        self.history.clear()
        self.history_index = -1