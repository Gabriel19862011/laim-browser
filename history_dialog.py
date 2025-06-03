from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QListWidget, QPushButton,
    QHBoxLayout, QLabel, QMessageBox
)
from PyQt6.QtCore import Qt
from styles import main_styles as styles

class HistoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle(self.parent_window.tr("История просмотров"))
        self.setFixedSize(600, 400)
        
        layout = QVBoxLayout()
        
        self.history_list = QListWidget()
        for item in self.parent_window.history:
            self.history_list.addItem(f"{item['title']} - {item['date']}")
        
        self.history_list.itemDoubleClicked.connect(self.open_history_item)
        
        clear_btn = QPushButton("Очистить историю")
        clear_btn.setStyleSheet(styles.CLOSE_BUTTON_STYLE.format(color=styles.CLOSE_BUTTON_COLOR))
        clear_btn.clicked.connect(self.clear_history)
        
        layout.addWidget(self.history_list)
        layout.addWidget(clear_btn)
        self.setLayout(layout)

    def open_history_item(self, item):
        index = self.history_list.row(item)
        if 0 <= index < len(self.parent_window.history):
            url = self.parent_window.history[index]['url']
            self.parent_window.add_new_tab(url)
            self.accept()

    def clear_history(self):  # Добавлено недостающее двоеточие
        self.parent_window.history = []
        self.parent_window._save_history_data()
        self.history_list.clear()
        QMessageBox.information(self, "Готово", "История очищена")