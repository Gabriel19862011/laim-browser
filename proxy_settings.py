from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QComboBox, 
    QPushButton, QMessageBox, QLabel, QHBoxLayout
)
from PyQt6.QtGui import QIcon
from styles import main_styles as styles

class ProxySettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки прокси")
        self.setFixedSize(400, 300)
        
        current_proxy = parent.get_current_proxy() if hasattr(parent, 'get_current_proxy') else ("", 0, "HTTP", "", "")
        proxy_host, proxy_port, proxy_type, username, password = current_proxy
        proxy_edit_text = f"{proxy_host}:{proxy_port}" if proxy_host else ""
        
        layout = QVBoxLayout()
        
        self.proxy_edit = QLineEdit(proxy_edit_text)
        self.proxy_edit.setPlaceholderText("host:port (например: 198.12.249.249:64999)")
        layout.addWidget(QLabel("Прокси:"))
        layout.addWidget(self.proxy_edit)
        
        self.proxy_type = QComboBox()
        self.proxy_type.addItems(["HTTP", "SOCKS5"])
        self.proxy_type.setCurrentText(proxy_type)
        layout.addWidget(QLabel("Тип:"))
        layout.addWidget(self.proxy_type)
        
        self.username = QLineEdit(username)
        layout.addWidget(QLabel("Логин (опционально):"))
        layout.addWidget(self.username)
        
        self.password = QLineEdit(password)
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(QLabel("Пароль (опционально):"))
        layout.addWidget(self.password)
        
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.setStyleSheet(styles.OK_BUTTON_STYLE.format(color=styles.OK_BUTTON_COLOR))
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setStyleSheet(styles.CLOSE_BUTTON_STYLE.format(color=styles.CLOSE_BUTTON_COLOR))
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def get_proxy(self):
        text = self.proxy_edit.text().strip()
        if not text:
            return ("", 0, "HTTP", "", "")  # Прокси отключен
        
        if ":" not in text:
            QMessageBox.warning(self, "Ошибка", "Неверный формат (пример: host:port)")
            return None
        
        host, port_str = text.split(":", 1)
        try:
            port = int(port_str)
            if not (1 <= port <= 65535):
                raise ValueError("Порт должен быть в диапазоне 1-65535")
        except:
            QMessageBox.warning(self, "Ошибка", "Порт должен быть числом")
            return None
        
        return (
            host.strip(),
            port,
            self.proxy_type.currentText(),
            self.username.text(),
            self.password.text()
        )