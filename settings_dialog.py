from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QPushButton, QComboBox, QCheckBox,
    QWidget, QFrame, QLabel, QHBoxLayout, QFileDialog,
    QMessageBox, QGroupBox, QLineEdit, QScrollArea, QApplication
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt
import os
from styles import main_styles as styles
from proxy_settings import ProxySettingsDialog

import requests
import os
import sys
from packaging import version
from version import VERSION

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setup_ui()
        self.setup_window_flags()

    def setup_window_flags(self):
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowSystemMenuHint
        )
        self.setFixedSize(500, 600)

    def setup_ui(self):
        self.setWindowTitle(self.parent_window.tr("Settings"))
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self.main_layout = QVBoxLayout(container)
        self.main_layout.setSpacing(10)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Секции настроек
        self.add_section(self.parent_window.tr("Downloads"), self.create_downloads_section())
        self.add_section(self.parent_window.tr("Language"), self.create_language_section())
        self.add_section(self.parent_window.tr("Proxy"), self.create_proxy_section())
        self.add_section(self.parent_window.tr("History"), self.create_history_section())
        self.add_section(self.parent_window.tr("Security"), self.create_security_section())
        self.add_section(self.parent_window.tr("About"), self.create_about_section())
        
        self.main_layout.addStretch()
        scroll.setWidget(container)
        
        layout = QVBoxLayout(self)
        layout.addWidget(scroll)
        
        # Кнопки OK/Cancel
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton(self.parent_window.tr("OK"))
        ok_btn.setStyleSheet(styles.OK_BUTTON_STYLE.format(color=styles.OK_BUTTON_COLOR))
        ok_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton(self.parent_window.tr("Cancel"))
        cancel_btn.setStyleSheet(styles.CLOSE_BUTTON_STYLE.format(color=styles.CLOSE_BUTTON_COLOR))
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def add_section(self, title, widget):
        container = QWidget()
        container_layout = QVBoxLayout()
        container_layout.setSpacing(0)
        
        header = QLabel(title)
        header.setStyleSheet(styles.SECTION_HEADER_STYLE)
        container_layout.addWidget(header)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(styles.LINE_STYLE)
        container_layout.addWidget(line)
        
        container_layout.addWidget(widget)
        container.setLayout(container_layout)
        self.main_layout.addWidget(container)

    def create_downloads_section(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Выбор папки загрузок
        dir_layout = QHBoxLayout()
        self.download_dir = QLineEdit()
        self.download_dir.setText(self.parent_window.download_dir)
        dir_layout.addWidget(self.download_dir)
        
        browse_btn = QPushButton(self.parent_window.tr("Browse..."))
        browse_btn.setStyleSheet(styles.OK_BUTTON_STYLE.format(color=styles.OK_BUTTON_COLOR))
        browse_btn.clicked.connect(self.select_download_dir)
        dir_layout.addWidget(browse_btn)
        layout.addLayout(dir_layout)
        
        # Безопасные загрузки
        self.safe_downloads = QCheckBox(self.parent_window.tr("Safe downloads (scan files)"))
        self.safe_downloads.setChecked(self.parent_window.safe_downloads)
        layout.addWidget(self.safe_downloads)
        
        return widget

    def select_download_dir(self):
        dir_path = QFileDialog.getExistingDirectory(
            self,
            self.parent_window.tr("Select download directory"),
            self.parent_window.download_dir
        )
        if dir_path:
            self.download_dir.setText(dir_path)

    def create_language_section(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        self.language_combo = QComboBox()
        languages = [
            ("English", "en", QIcon("icons/en_flag.png")),
            ("Русский", "ru", QIcon("icons/ru_flag.png")),
            ("Татарча", "tt", QIcon("icons/tt_flag.png")),
            ("العربية", "ar", QIcon("icons/ar_flag.png"))
        ]
        
        for name, code, icon in languages:
            self.language_combo.addItem(icon, name, code)
        
        # Установка текущего языка
        current_index = self.language_combo.findData(self.parent_window.current_language)
        if current_index >= 0:
            self.language_combo.setCurrentIndex(current_index)
        
        layout.addWidget(self.language_combo)
        layout.addStretch()
        
        return widget

    def create_proxy_section(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        proxy_btn = QPushButton(self.parent_window.tr("Proxy settings..."))
        proxy_btn.setStyleSheet(styles.OK_BUTTON_STYLE.format(color=styles.OK_BUTTON_COLOR))
        proxy_btn.clicked.connect(self.open_proxy_settings)
        layout.addWidget(proxy_btn)
        
        return widget

    def open_proxy_settings(self):
        dialog = ProxySettingsDialog(self.parent_window)
        dialog.exec()

    def create_history_section(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.save_history = QCheckBox(self.parent_window.tr("Save browsing history"))
        self.save_history.setChecked(self.parent_window.save_history)
        layout.addWidget(self.save_history)
        
        if self.parent_window.save_history and self.parent_window.history:
            history_btn = QPushButton(self.parent_window.tr("View history"))
            history_btn.setStyleSheet(styles.OK_BUTTON_STYLE.format(color=styles.OK_BUTTON_COLOR))
            history_btn.clicked.connect(self.parent_window.show_history_dialog)
            layout.addWidget(history_btn)
        
        return widget

    def create_security_section(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.save_passwords = QCheckBox(self.parent_window.tr("Save passwords"))
        self.save_passwords.setChecked(self.parent_window.save_passwords)
        layout.addWidget(self.save_passwords)
        
        return widget

    def create_about_section(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Проверка обновлений
        update_btn = QPushButton(self.parent_window.tr("Check for updates"))
        update_btn.setStyleSheet(styles.OK_BUTTON_STYLE.format(color=styles.OK_BUTTON_COLOR))
        update_btn.clicked.connect(self.check_updates)
        layout.addWidget(update_btn)
        
        # Информация о разработчике
        info_label = QLabel(self.parent_window.tr("Laim Browser\nVersion 1.0\nDeveloped by Airat Valitov"))
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        return widget

def check_updates(self):
    try:
        repo = "Gabriel19862011/laim-browser"
        current_version = VERSION  # Добавляем эту строку
        headers = {"User-Agent": "LaimBrowser"}
        url = f"https://api.github.com/repos/{repo}/releases"  # Пока используем все релизы
        
        response = requests.get(url, headers=headers)
        if response.status_code == 404:
            QMessageBox.information(
                self,
                self.parent_window.tr("Updates"),
                self.parent_window.tr("No releases found on GitHub")
            )
            return
            
        response.raise_for_status()
        data = response.json()
        
        # Теперь data - это список всех релизов
        if not data:
            QMessageBox.information(
                self,
                self.parent_window.tr("Updates"),
                self.parent_window.tr("No releases available")
            )
            return
            
        # Берем первый (последний) релиз из списка
        latest_release = data[0]
        latest_version = latest_release["tag_name"].replace("v", "").strip()
        
        # Проверяем assets (должна быть небольшая корректировка)
        if not latest_release.get("assets"):
            QMessageBox.warning(
                self,
                self.parent_window.tr("Warning"),
                self.parent_window.tr("Release found but no executable file attached")
            )
            return
            
        download_url = latest_release["assets"][0]["browser_download_url"]
        
        # Сравнение версий
        if version.parse(latest_version) > version.parse(current_version):
            msg = QMessageBox(self)
            msg.setWindowTitle(self.parent_window.tr("Updates"))
            msg.setText(self.parent_window.tr("New version available: {}").format(latest_version))
            msg.setInformativeText(self.parent_window.tr("Do you want to download it?"))
            
            download_btn = msg.addButton(self.parent_window.tr("Download"), QMessageBox.ButtonRole.AcceptRole)
            cancel_btn = msg.addButton(self.parent_window.tr("Later"), QMessageBox.ButtonRole.RejectRole)
            
            msg.exec()
            
            if msg.clickedButton() == download_btn:
                self.download_and_install_update(download_url)
        else:
            QMessageBox.information(
                self,
                self.parent_window.tr("Updates"),
                self.parent_window.tr("You have the latest version: {}").format(current_version)
            )
            
    except Exception as e:
        QMessageBox.warning(
            self,
            self.parent_window.tr("Error"),
            self.parent_window.tr("Update check failed: {}").format(str(e))
        )

    def download_and_install_update(self, url):
        try:
            temp_dir = os.path.join(os.environ["TEMP"], "LaimBrowserUpdate")
            os.makedirs(temp_dir, exist_ok=True)
            
            file_name = url.split("/")[-1]
            file_path = os.path.join(temp_dir, file_name)
            
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            if sys.platform == "win32":
                os.startfile(file_path)
            else:
                os.system(f'open "{file_path}"' if sys.platform == "darwin" else f'xdg-open "{file_path}"')
            
            QApplication.quit()
            
        except Exception as e:
            QMessageBox.warning(
                self,
                self.parent_window.tr("Error"),
                self.parent_window.tr("Failed to download update: {}").format(str(e))
            )

    def accept(self):
        # Валидация пути загрузки
        new_download_dir = self.download_dir.text().strip()
        if not os.path.exists(new_download_dir):
            QMessageBox.warning(
                self,
                self.parent_window.tr("Invalid Directory"),
                self.parent_window.tr("The specified directory does not exist. Please choose a valid directory.")
            )
            return

        # Получаем новые значения настроек
        new_settings = {
            'download_dir': new_download_dir,
            'safe_downloads': self.safe_downloads.isChecked(),
            'save_history': self.save_history.isChecked(),
            'save_passwords': self.save_passwords.isChecked(),
            'language': self.language_combo.currentData()
        }

        # Применяем изменения языка
        lang_changed = new_settings['language'] != self.parent_window.current_language
        if lang_changed:
            try:
                self.parent_window.change_language(new_settings['language'])
            except Exception as e:
                QMessageBox.critical(
                    self,
                    self.parent_window.tr("Language Change Error"),
                    self.parent_window.tr("Failed to change language: {}").format(str(e))
                )
                return

        # Обновляем остальные настройки
        self.parent_window.download_dir = new_settings['download_dir']
        self.parent_window.safe_downloads = new_settings['safe_downloads']
        self.parent_window.save_history = new_settings['save_history']
        self.parent_window.save_passwords = new_settings['save_passwords']

        # Сохраняем и закрываем
        self.parent_window.save_settings()
        super().accept()

        # Обновляем связанные компоненты
        self.parent_window.update_search_engine_by_language()
        if hasattr(self.parent_window, 'update_home_page_translation'):
            self.parent_window.update_home_page_translation()