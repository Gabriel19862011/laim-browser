import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import sys
import os
import json
import urllib.parse
from datetime import datetime

# Настройки для уменьшения количества ошибок в консоли
os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = '--disable-logging --no-sandbox --ignore-certificate-errors'

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget,
    QLineEdit, QPushButton, QHBoxLayout, QTabWidget,
    QToolBar, QDialog, QMessageBox, QLabel, QMenu,
    QListWidget, QListWidgetItem, QTextEdit, QFileDialog
)
from PyQt6.QtGui import QAction, QIcon, QImage, QClipboard
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineDownloadRequest
from PyQt6.QtCore import (
    QUrl, Qt, QSettings, QSize, QObject, 
    pyqtSlot, QTranslator, QLibraryInfo, QEvent
)
from PyQt6.QtNetwork import (
    QNetworkProxy, 
    QNetworkAccessManager,
    QNetworkRequest,
    QNetworkReply
)
from PyQt6.QtWebChannel import QWebChannel

# Для Windows-специфичной функциональности
if sys.platform == 'win32':
    try:
        from PyQt6.QtWinExtras import QtWin
        import win32clipboard
        WIN32_CLIPBOARD_SUPPORT = True
    except ImportError:
        WIN32_CLIPBOARD_SUPPORT = False
        print("Warning: pywin32 not installed, Windows clipboard support limited")

from settings_dialog import SettingsDialog
from proxy_settings import ProxySettingsDialog
from history_dialog import HistoryDialog

class Bridge(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
    
    @pyqtSlot(str, str)
    def addBookmark(self, url, title):
        self.parent().add_bookmark(url, title)
    
    @pyqtSlot(str)
    def removeBookmark(self, url):
        self.parent().remove_bookmark(url)
    
    @pyqtSlot(result=str)
    def getLanguage(self):
        return self.parent().current_language
    
    @pyqtSlot(result=str)
    def load_bookmarks(self):
        return json.dumps(self.parent().load_bookmarks())
    
    @pyqtSlot(result=str)
    def getSearchEngine(self):
        return self.parent().search_engine

class WebEngineView(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.browser_window = parent
        self.network_manager = QNetworkAccessManager(self)
        profile = self.page().profile()
        profile.setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.context_menu_pos = None
        self.current_download = None

        # Настраиваем обработчик загрузок для страниц
        profile.downloadRequested.connect(self.handle_download_requested)

    def handle_download_requested(self, download):
        """Обработчик запроса на загрузку (для сохранения страниц)"""
        if download.url().scheme() == 'http' or download.url().scheme() == 'https':
            # Это загрузка страницы
            self._save_page(download)
        else:
            # Другие типы загрузок
            self._download_url(download.url().toString(), download.path())

    def createWindow(self, type):
        return self.browser_window.add_new_tab()

    def contextMenuEvent(self, event):
        self.context_menu_pos = event.globalPos()
        
        self.page().runJavaScript(
            f"""
            var element = document.elementFromPoint({event.pos().x()}, {event.pos().y()});
            var result = {{
                isImage: element.tagName === 'IMG',
                isLink: element.tagName === 'A' && element.href,
                href: element.tagName === 'A' ? element.href : '',
                imgSrc: element.tagName === 'IMG' ? element.src : ''
            }};
            result;
            """,
            lambda result: self._show_context_menu(result)
        )
        event.accept()

    def _show_context_menu(self, element_info):
        try:
            if not self.context_menu_pos:
                return
                
            menu = QMenu(self)
            
            # Если элемент - ссылка
            if element_info.get('isLink'):
                url = element_info.get('href', '')
                
                action = QAction(self.browser_window.tr("Open link in new tab"), self)
                action.triggered.connect(lambda: self.browser_window.add_new_tab(url))
                menu.addAction(action)
                
                action = QAction(self.browser_window.tr("Save link as..."), self)
                action.triggered.connect(lambda: self._download_link(url))
                menu.addAction(action)
                menu.addSeparator()
            
            # Если элемент - изображение
            if element_info.get('isImage'):
                img_url = element_info.get('imgSrc', '')
                
                action = QAction(self.browser_window.tr("Save image as..."), self)
                action.triggered.connect(lambda: self._download_image(img_url))
                menu.addAction(action)
                
                action = QAction(self.browser_window.tr("Copy image"), self)
                action.triggered.connect(lambda: self._copy_image(img_url))
                menu.addAction(action)
                menu.addSeparator()
            
            # Стандартные действия браузера
            back_action = QAction(self.browser_window.tr("Back"), self)
            back_action.triggered.connect(self.back)
            back_action.setEnabled(self.history().canGoBack())
            menu.addAction(back_action)
            
            forward_action = QAction(self.browser_window.tr("Forward"), self)
            forward_action.triggered.connect(self.forward)
            forward_action.setEnabled(self.history().canGoForward())
            menu.addAction(forward_action)
            
            reload_action = QAction(self.browser_window.tr("Reload"), self)
            reload_action.triggered.connect(self.reload)
            menu.addAction(reload_action)
            
            # Добавляем действие сохранения страницы
            save_page_action = QAction(self.browser_window.tr("Save page as..."), self)
            save_page_action.triggered.connect(self._init_page_save)
            menu.addAction(save_page_action)
            
            menu.exec(self.context_menu_pos)
            
        except Exception as e:
            print(f"Error showing context menu: {e}")

    def _init_page_save(self):
        """Инициирует сохранение страницы"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self.browser_window.tr("Save Page"),
            "webpage",
            self.browser_window.tr("Web Page, Complete (*.html *.htm);;Web Page, Single File (*.mhtml)")
        )
        
        if file_path:
            # Определяем формат сохранения
            if file_path.endswith('.mhtml'):
                # Для MHTML используем стандартный механизм загрузки
                self.page().download(file_path)
            else:
                # Для HTML сохраняем вручную
                if not file_path.endswith(('.html', '.htm')):
                    file_path += '.html'
                
                # Получаем HTML содержимое страницы
                self.page().toHtml(lambda html: self._save_html_to_file(html, file_path))

    def _save_html_to_file(self, html, file_path):
        """Сохраняет HTML содержимое в файл"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html)
            QMessageBox.information(
                self,
                self.browser_window.tr("Success"),
                self.browser_window.tr("Page saved successfully!")
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                self.browser_window.tr("Error"),
                self.browser_window.tr("Failed to save page: {}").format(str(e))
            )

    def _save_page(self, download):
        """Обрабатывает сохранение страницы через downloadRequested"""
        try:
            # Показываем диалог для выбора места сохранения
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                self.browser_window.tr("Save Page"),
                os.path.basename(download.url().toString())[:50] or "page",
                self.browser_window.tr("Web Page (*.html *.htm);;MHTML File (*.mhtml)")
            )
        
            if file_path:
                download.setPath(file_path)
                download.accept()
        except Exception as e:
            QMessageBox.warning(
                self, 
                self.browser_window.tr("Error"), 
                self.browser_window.tr("Failed to save page: {}").format(str(e))
            )

    def _download_link(self, url):
        """Сохранение ссылки как файла"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                self.browser_window.tr("Save link"),
                os.path.basename(url)[:50],
                self.browser_window.tr("All Files (*)")
            )
            if file_path:
                self._download_url(url, file_path)
        except Exception as e:
            QMessageBox.warning(
                self,
                self.browser_window.tr("Error"),
                self.browser_window.tr("Failed to save link: {}").format(str(e))
            )

    def _download_image(self, img_url):
        """Сохранение изображения"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                self.browser_window.tr("Save image"),
                f"image_{os.path.basename(img_url)[:50]}",
                self.browser_window.tr("Images (*.png *.jpg *.jpeg *.webp *.gif)")
            )
            if file_path:
                self._download_url(img_url, file_path)
        except Exception as e:
            QMessageBox.warning(
                self,
                self.browser_window.tr("Error"),
                self.browser_window.tr("Failed to save image: {}").format(str(e))
            )

    def _download_url(self, url, file_path):
        """Общая функция загрузки URL"""
        request = QNetworkRequest(QUrl(url))
        reply = self.network_manager.get(request)
        
        def on_finished():
            try:
                if reply.error() == QNetworkReply.NetworkError.NoError:
                    with open(file_path, 'wb') as f:
                        f.write(reply.readAll().data())
                    QMessageBox.information(
                        self,
                        self.browser_window.tr("Success"),
                        self.browser_window.tr("File saved successfully!")
                    )
                else:
                    QMessageBox.warning(
                        self,
                        self.browser_window.tr("Error"),
                        self.browser_window.tr("Download failed: {}").format(reply.errorString())
                    )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    self.browser_window.tr("Error"),
                    self.browser_window.tr("File save error: {}").format(str(e))
                )
            finally:
                reply.deleteLater()
        
        reply.finished.connect(on_finished)

    def _copy_image(self, img_url):
        """Копирование изображения в буфер обмена"""
        try:
            request = QNetworkRequest(QUrl(img_url))
            reply = self.network_manager.get(request)
            
            def on_finished():
                try:
                    if reply.error() == QNetworkReply.NetworkError.NoError:
                        image = QImage()
                        if image.loadFromData(reply.readAll()):
                            clipboard = QApplication.clipboard()
                            clipboard.setImage(image)
                            
                            # Дополнительная обработка для Windows
                            if sys.platform == 'win32' and WIN32_CLIPBOARD_SUPPORT:
                                try:
                                    win32clipboard.OpenClipboard()
                                    win32clipboard.EmptyClipboard()
                                    win32clipboard.SetClipboardData(win32clipboard.CF_DIB, QtWin.toHBITMAP(image).toDIB())
                                    win32clipboard.CloseClipboard()
                                except Exception as e:
                                    print(f"Windows clipboard error: {e}")
                    else:
                        print(f"Failed to download image: {reply.errorString()}")
                except Exception as e:
                    print(f"Error copying image: {e}")
                finally:
                    reply.deleteLater()
            
            reply.finished.connect(on_finished)
        except Exception as e:
            print(f"Error initializing image copy: {e}")

class BrowserWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Laim Browser")
        self.setWindowIcon(QIcon("icons/logo.ico"))
        self.settings = QSettings("Laim", "Browser")
        self.history = []
        self.translations = self.load_translations()
        self.current_language = "ru"
        self.init_settings()
        self.init_ui()
        self.load_settings()
        self.update_proxy()

    def load_translations(self):
        translations_path = os.path.join(os.path.dirname(__file__), "translations.json")
        if not os.path.exists(translations_path):
            return {
                "ru": {
                    "Laim Browser": "Браузер Laim",
                    "New tab": "Новая вкладка",
                    "Back": "Назад",
                    "Forward": "Вперёд",
                    "Reload": "Обновить",
                    "Home": "Домой",
                    "Settings": "Настройки",
                    "Enter URL or search query...": "Введите URL или поисковый запрос...",
                    "PROXY ON": "ПРОКСИ ВКЛ",
                    "PROXY OFF": "ПРОКСИ ВЫКЛ",
                    "Save image": "Сохранить изображение",
                    "Home Page": "Домашняя страница",
                    "Add bookmark": "Добавить закладку",
                    "Bookmarks": "Закладки",
                    "History": "История",
                    "Save page": "Сохранить страницу",
                    "View page source": "Просмотр кода страницы",
                    "url_label": "URL сайта",
                    "title_label": "Название",
                    "default_title": "Мой сайт",
                    "cancel": "Отмена",
                    "save": "Сохранить"
                },
                "en": {
                    "Laim Browser": "Laim Browser",
                    "New tab": "New tab",
                    "Back": "Back",
                    "Forward": "Forward",
                    "Reload": "Reload",
                    "Home": "Home",
                    "Settings": "Settings",
                    "Enter URL or search query...": "Enter URL or search query...",
                    "PROXY ON": "PROXY ON",
                    "PROXY OFF": "PROXY OFF",
                    "Save image": "Save image",
                    "Home Page": "Home Page",
                    "Add bookmark": "Add bookmark",
                    "Bookmarks": "Bookmarks",
                    "History": "History",
                    "Save page": "Save page",
                    "View page source": "View page source",
                    "url_label": "Site URL",
                    "title_label": "Title",
                    "default_title": "My site",
                    "cancel": "Cancel",
                    "save": "Save"
                }
            }
        
        try:
            with open(translations_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading translations: {e}")
            return {
                "ru": {
                    "Laim Browser": "Браузер Laim",
                    "New tab": "Новая вкладка",
                    "Back": "Назад",
                    "Forward": "Вперёд",
                    "Reload": "Обновить",
                    "Home": "Домой",
                    "Settings": "Настройки",
                    "Enter URL or search query...": "Введите URL или поисковый запрос...",
                    "PROXY ON": "ПРОКСИ ВКЛ",
                    "PROXY OFF": "ПРОКСИ ВЫКЛ",
                    "Save image": "Сохранить изображение"
                },
                "en": {
                    "Laim Browser": "Laim Browser",
                    "New tab": "New tab",
                    "Back": "Back",
                    "Forward": "Forward",
                    "Reload": "Reload",
                    "Home": "Home",
                    "Settings": "Settings",
                    "Enter URL or search query...": "Enter URL or search query...",
                    "PROXY ON": "PROXY ON",
                    "PROXY OFF": "PROXY OFF",
                    "Save image": "Save image"
                }
            }

    def tr(self, text):
        return self.translations.get(self.current_language, {}).get(text, text)

    def change_language(self, lang_code):
        if lang_code in self.translations:
            self.current_language = lang_code
            self.retranslate_ui()
            self.update_home_page_translation()
            
            direction = "rtl" if lang_code == "ar" else "ltr"
            text_align = "right" if lang_code == "ar" else "left"
            
            js = """
            document.body.style.direction = '{direction}';
            document.querySelectorAll('input').forEach(el => {{
                el.style.textAlign = '{text_align}';
            }});
            """.format(direction=direction, text_align=text_align)
            
            for i in range(self.tabs.count()):
                self.tabs.widget(i).page().runJavaScript(js)
            
            self.save_settings()
            self.update_search_engine_by_language()

    def init_settings(self):
        self.home_page = os.path.join(os.path.dirname(__file__), "resources", "start_page.html")
        self.search_engine = "https://yandex.ru/search/?text="
        self.language = "ru"
        self.is_proxy_enabled = False
        self.proxy_host = ""
        self.proxy_port = 0
        self.proxy_type = "HTTP"
        self.proxy_username = ""
        self.proxy_password = ""
        self.download_dir = os.path.expanduser("~\\Downloads")
        self.save_history = False
        self.save_passwords = True
        self.safe_downloads = True

    def init_ui(self):
        self.setup_toolbar()
        self.setup_tabs()
        self.setup_web_channel()
        self.setup_downloads()
        self.add_new_tab()

    def setup_downloads(self):
        profile = QWebEngineProfile.defaultProfile()
        
        # Устанавливаем папку загрузок по умолчанию
        download_dir = os.path.expanduser("~/Downloads")
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        profile.setDownloadPath(download_dir)
        
        # Подключаем обработчик загрузок
        profile.downloadRequested.connect(self.on_download_requested)

    def on_download_requested(self, download):
        try:
            # Получаем имя файла из URL
            suggested_name = download.url().fileName()
            if not suggested_name:
                suggested_name = "download"
            
            # Диалог сохранения файла
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                self.tr("Save File"),
                suggested_name,
                self.tr("All Files (*)")
            )
            
            if file_path:
                download.setPath(file_path)
                download.accept()
                
                if self.safe_downloads and sys.platform == 'win32':
                    import ctypes
                    folder = os.path.dirname(file_path)
                    ctypes.windll.shell32.ShellExecuteW(
                        None, "open", folder, None, None, 1
                    )
                    
        except Exception as e:
            QMessageBox.warning(
                self,
                self.tr("Error"),
                self.tr("Download failed: {}").format(str(e))
            )

    def setup_toolbar(self):
        toolbar = QToolBar(self.tr("Main Toolbar"))
        self.addToolBar(toolbar)

        self.back_btn = QAction(QIcon("icons/back.png"), "", self)
        self.forward_btn = QAction(QIcon("icons/forward.png"), "", self)
        self.reload_btn = QAction(QIcon("icons/update.png"), "", self)
        self.home_btn = QAction(QIcon("icons/home.png"), "", self)
        
        self.back_btn.triggered.connect(self.navigate_back)
        self.forward_btn.triggered.connect(self.navigate_forward)
        self.reload_btn.triggered.connect(self.reload_page)
        self.home_btn.triggered.connect(self.go_home)
        
        toolbar.addAction(self.back_btn)
        toolbar.addAction(self.forward_btn)
        toolbar.addAction(self.reload_btn)
        toolbar.addAction(self.home_btn)

        self.address_bar = QLineEdit()
        self.address_bar.returnPressed.connect(self.navigate_to_url)
        toolbar.addWidget(self.address_bar)

        self.proxy_btn = QPushButton()
        self.proxy_btn.setFixedSize(100, 30)
        self.proxy_btn.setCheckable(True)
        self.proxy_btn.clicked.connect(self.toggle_proxy)
        toolbar.addWidget(self.proxy_btn)

        self.settings_btn = QAction(QIcon("icons/settings.png"), "", self)
        self.settings_btn.triggered.connect(self.show_settings)
        toolbar.addAction(self.settings_btn)

    def setup_tabs(self):
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.tab_changed)
        self.tabs.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabs.customContextMenuRequested.connect(self.show_tab_context_menu)
        self.setCentralWidget(self.tabs)

    def setup_web_channel(self):
        self.web_channel = QWebChannel()
        self.web_bridge = Bridge(self)
        self.web_channel.registerObject("pyObject", self.web_bridge)

    def load_settings(self):
        self.search_engine = self.settings.value("search_engine", "https://yandex.ru/search/?text=")
        self.current_language = self.settings.value("language", "ru")
        self.is_proxy_enabled = self.settings.value("proxy_enabled", False, type=bool)
        self.proxy_host = self.settings.value("proxy_host", "")
        self.proxy_port = self.settings.value("proxy_port", 0, type=int)
        self.proxy_type = self.settings.value("proxy_type", "HTTP")
        self.proxy_username = self.settings.value("proxy_username", "")
        self.proxy_password = self.settings.value("proxy_password", "")
        self.download_dir = self.settings.value("download_dir", os.path.expanduser("~\\Downloads"))
        self.save_history = self.settings.value("save_history", False, type=bool)
        self.save_passwords = self.settings.value("save_passwords", True, type=bool)
        self.safe_downloads = self.settings.value("safe_downloads", True, type=bool)
        self.load_history()
        self.retranslate_ui()

    def save_settings(self):
        self.settings.setValue("search_engine", self.search_engine)
        self.settings.setValue("language", self.current_language)
        self.settings.setValue("proxy_enabled", self.is_proxy_enabled)
        self.settings.setValue("proxy_host", self.proxy_host)
        self.settings.setValue("proxy_port", self.proxy_port)
        self.settings.setValue("proxy_type", self.proxy_type)
        self.settings.setValue("proxy_username", self.proxy_username)
        self.settings.setValue("proxy_password", self.proxy_password)
        self.settings.setValue("download_dir", self.download_dir)
        self.settings.setValue("save_history", self.save_history)
        self.settings.setValue("save_passwords", self.save_passwords)
        self.settings.setValue("safe_downloads", self.safe_downloads)
        if self.save_history:
            self._save_history_data()

    def retranslate_ui(self):
        self.setWindowTitle(self.tr("Laim Browser"))
        self.address_bar.setPlaceholderText(self.tr("Enter URL or search query..."))
        self.proxy_btn.setText(self.tr("PROXY ON") if self.is_proxy_enabled else self.tr("PROXY OFF"))
        
        self.back_btn.setToolTip(self.tr("Back"))
        self.forward_btn.setToolTip(self.tr("Forward"))
        self.reload_btn.setToolTip(self.tr("Reload"))
        self.home_btn.setToolTip(self.tr("Home"))
        self.settings_btn.setToolTip(self.tr("Settings"))
        
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) in ["New tab", "Новая вкладка", "Яңа бит", "علامة تبويب جديدة"]:
                self.tabs.setTabText(i, self.tr("New tab"))
        
        self.update_home_page_translation()

    def update_home_page_translation(self):
        if os.path.exists(self.home_page):
            with open(self.home_page, 'r', encoding='utf-8') as f:
                html = f.read()
            
            translations = {
                "browser_title": self.tr("Laim Browser"),
                "search_placeholder": self.tr("Enter URL or search query..."),
                "add_bookmark": self.tr("Add bookmark"),
                "url_label": self.tr("url_label"),
                "title_label": self.tr("title_label"),
                "default_title": self.tr("default_title"),
                "cancel": self.tr("cancel"),
                "save": self.tr("save")
            }
            
            for key, value in translations.items():
                html = html.replace(f'{{{{{key}}}}}', value)
            
            for i in range(self.tabs.count()):
                if self.tabs.widget(i).url().toString().endswith("start_page.html"):
                    self.tabs.widget(i).setHtml(html, QUrl.fromLocalFile(self.home_page))

    def load_history(self):
        history = self.settings.value("history", [])
        self.history = json.loads(history) if isinstance(history, str) else history

    def _save_history_data(self):
        if self.save_history:
            self.settings.setValue("history", json.dumps(self.history))

    def add_to_history(self, url, title):
        if self.save_history:
            entry = {
                "url": url,
                "title": title,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.history.insert(0, entry)
            if len(self.history) > 100:
                self.history = self.history[:100]
            self._save_history_data()

    def show_history_dialog(self):
        if self.save_history and self.history:
            dialog = HistoryDialog(self)
            dialog.exec()

    def update_search_engine_by_language(self):
        search_engines = {
            "ru": "https://yandex.ru/search/?text=",
            "en": "https://google.com/search?q=",
            "tt": "https://yandex.ru/search/?text=",
            "ar": "https://www.google.com/search?q="
        }
        self.search_engine = search_engines.get(self.current_language, "https://google.com/search?q=")
        self.save_settings()

    def add_new_tab(self, url=None, title=None):
        tab = WebEngineView(self)
        if url:
            tab.setUrl(QUrl(url))
        else:
            if os.path.exists(self.home_page):
                tab.setUrl(QUrl.fromLocalFile(self.home_page))
            else:
                tab.setUrl(QUrl(self.search_engine))
        
        tab.urlChanged.connect(lambda url: self.update_address_bar(url, tab))
        tab.loadFinished.connect(lambda: self.update_title(tab))
        tab.page().setWebChannel(self.web_channel)
        
        index = self.tabs.addTab(tab, self.tr("New tab"))
        self.tabs.setCurrentIndex(index)
        return tab

    def navigate_to_url(self):
        text = self.address_bar.text().strip()
        if self.is_valid_url(text):
            url = QUrl(text) if text.startswith(('http://', 'https://')) else QUrl(f"https://{text}")
            self.current_tab().setUrl(url)
            self.add_to_history(url.toString(), self.current_tab().title())
        else:
            search_url = QUrl(f"{self.search_engine}{urllib.parse.quote(text)}")
            self.current_tab().setUrl(search_url)
            self.add_to_history(search_url.toString(), f"{self.tr('Search')}: {text}")

    def is_valid_url(self, text):
        try:
            result = urllib.parse.urlparse(text)
            return all([result.scheme, result.netloc]) or '.' in result.path
        except:
            return False

    def current_tab(self):
        return self.tabs.currentWidget()

    def update_address_bar(self, url, tab=None):
        if not tab:
            tab = self.current_tab()
        if tab == self.current_tab():
            self.address_bar.setText(url.toString())

    def update_title(self, tab):
        title = tab.title()
        index = self.tabs.indexOf(tab)
        if title:
            self.tabs.setTabText(index, title[:20] + "..." if len(title) > 20 else title)
            if self.save_history:
                url = tab.url().toString()
                if url.startswith(('http://', 'https://')):
                    self.add_to_history(url, title)

    def navigate_back(self):
        if self.current_tab().history().canGoBack():
            self.current_tab().back()

    def navigate_forward(self):
        if self.current_tab().history().canGoForward():
            self.current_tab().forward()

    def reload_page(self):
        self.current_tab().reload()

    def go_home(self):
        if os.path.exists(self.home_page):
            self.current_tab().setUrl(QUrl.fromLocalFile(self.home_page))
        else:
            self.current_tab().setUrl(QUrl(self.search_engine))

    def show_tab_context_menu(self, pos):
        menu = QMenu(self)
        index = self.tabs.tabBar().tabAt(pos)
        
        edit_action = menu.addAction(self.tr("Edit"))
        edit_action.triggered.connect(lambda: self.edit_tab(index))
        
        reload_action = menu.addAction(self.tr("Reload"))
        reload_action.triggered.connect(lambda: self.tabs.widget(index).reload())
        
        duplicate_action = menu.addAction(self.tr("Duplicate"))
        duplicate_action.triggered.connect(
            lambda: self.add_new_tab(
                self.tabs.widget(index).url().toString(),
                f"{self.tabs.tabText(index)} ({self.tr('Copy')})"
            )
        )
        
        menu.addSeparator()
        
        if self.tabs.count() > 1:
            close_others_action = menu.addAction(self.tr("Close others"))
            close_others_action.triggered.connect(lambda: self.close_other_tabs(index))
            
            close_right_action = menu.addAction(self.tr("Close to the right"))
            close_right_action.triggered.connect(lambda: self.close_tabs_to_right(index))
        
        close_action = menu.addAction(self.tr("Close"))
        close_action.triggered.connect(lambda: self.close_tab(index))
        
        menu.exec(self.tabs.mapToGlobal(pos))

    def edit_tab(self, index):
        tab = self.tabs.widget(index)
        dialog = QDialog(self)
        layout = QVBoxLayout()
        
        url_edit = QLineEdit(tab.url().toString())
        title_edit = QLineEdit(self.tabs.tabText(index))
        
        save_btn = QPushButton(self.tr("Save"))
        cancel_btn = QPushButton(self.tr("Cancel"))
        
        layout.addWidget(QLabel("URL:"))
        layout.addWidget(url_edit)
        layout.addWidget(QLabel(self.tr("Title:")))
        layout.addWidget(title_edit)
        layout.addWidget(save_btn)
        layout.addWidget(cancel_btn)
        
        dialog.setLayout(layout)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_url = url_edit.text().strip()
            new_title = title_edit.text().strip()
            
            if new_url:
                tab.setUrl(QUrl(new_url))
            if new_title:
                self.tabs.setTabText(index, new_title)

    def close_other_tabs(self, index):
        for i in reversed(range(self.tabs.count())):
            if i != index:
                self.tabs.removeTab(i)

    def close_tabs_to_right(self, index):
        for i in reversed(range(index + 1, self.tabs.count())):
            self.tabs.removeTab(i)

    def close_tab(self, index):
        if self.tabs.count() > 1:
            self.tabs.removeTab(index)
        else:
            self.close()

    def toggle_proxy(self):
        self.is_proxy_enabled = not self.is_proxy_enabled
        self.update_proxy()

    def update_proxy(self):
        if self.is_proxy_enabled:
            proxy = QNetworkProxy()
            if self.proxy_type == "HTTP":
                proxy.setType(QNetworkProxy.ProxyType.HttpProxy)
            else:
                proxy.setType(QNetworkProxy.ProxyType.Socks5Proxy)
            proxy.setHostName(self.proxy_host)
            proxy.setPort(self.proxy_port)
            proxy.setUser(self.proxy_username)
            proxy.setPassword(self.proxy_password)
            QNetworkProxy.setApplicationProxy(proxy)
        else:
            QNetworkProxy.setApplicationProxy(QNetworkProxy())
        self.save_settings()
        self.current_tab().reload()
        self.retranslate_ui()

    def show_settings(self):
        dialog = SettingsDialog(self)
        dialog.download_dir.setText(self.download_dir)
        dialog.language_combo.setCurrentText(self.current_language)
        dialog.save_history.setChecked(self.save_history)
        dialog.save_passwords.setChecked(self.save_passwords)
        dialog.safe_downloads.setChecked(self.safe_downloads)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.download_dir = dialog.download_dir.text()
            self.change_language(dialog.language_combo.currentText())
            self.save_history = dialog.save_history.isChecked()
            self.save_passwords = dialog.save_passwords.isChecked()
            self.safe_downloads = dialog.safe_downloads.isChecked()
            self.save_settings()

    def load_bookmarks(self):
        bookmarks = self.settings.value("bookmarks", [])
        return json.loads(bookmarks) if isinstance(bookmarks, str) else bookmarks

    def save_bookmarks(self, bookmarks):
        self.settings.setValue("bookmarks", json.dumps(bookmarks))

    def add_bookmark(self, url, title):
        bookmarks = self.load_bookmarks()
        bookmarks.append({"url": url, "title": title})
        self.save_bookmarks(bookmarks)
        self.current_tab().page().runJavaScript(f"updateBookmarks({json.dumps(bookmarks)})")

    def remove_bookmark(self, url):
        bookmarks = self.load_bookmarks()
        bookmarks = [b for b in bookmarks if b["url"] != url]
        self.save_bookmarks(bookmarks)
        self.current_tab().page().runJavaScript(f"updateBookmarks({json.dumps(bookmarks)})")

    def tab_changed(self, index):
        if index >= 0:
            tab = self.tabs.widget(index)
            self.update_address_bar(tab.url(), tab)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Установка переводов Qt
    translator = QTranslator()
    if translator.load("qtbase_ru", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
        app.installTranslator(translator)
    
    window = BrowserWindow()
    window.showMaximized()
    
    sys.exit(app.exec())