# Цвета
PROXY_ON_COLOR = "#7CFC00"  # Зеленый при включенном прокси
PROXY_OFF_COLOR = "#414141"  # Серый при выключенном
SETTINGS_BUTTON_COLOR = "#14B814"
CLOSE_BUTTON_COLOR = "#F44336"
OK_BUTTON_COLOR = "#4CAF50"
SECTION_BORDER_COLOR = "#D0D0D0"  # Цвет разделителей

# Стиль кнопок навигации (назад, вперед, обновить)
NAV_BUTTON_STYLE = """
QPushButton {
    background: transparent;
    border: none;
    padding: 5px;
}
QPushButton:hover {
    background: rgba(0, 255, 0, 0.1);
    border-radius: 5px;
}
"""

# Стиль кнопки прокси
PROXY_BUTTON_STYLE = """
QPushButton {{
    border-radius: 20px;
    padding: 10px;
    font-weight: bold;
    color: black;
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1, 
        stop:0 {on_color}, 
        stop:1 {off_color}
    );
    border: 2px solid #008000;
}}
QPushButton:checked {{
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1, 
        stop:0 {on_color}, 
        stop:1 {off_color}
    );
}}
"""

# Стиль кнопки OK
OK_BUTTON_STYLE = """
QPushButton {{
    background-color: {color};
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
}}
QPushButton:hover {{
    background-color: #45a049;
}}
"""

# Стиль кнопки закрытия
CLOSE_BUTTON_STYLE = """
QPushButton {{
    background-color: {color};
    color: white;
    border: none;
    border-radius: 12px;
    font-weight: bold;
    padding: 8px 16px;
}}
QPushButton:hover {{
    background-color: #d32f2f;
}}
"""

# Стиль разделителя (линии)
LINE_STYLE = f"""
QFrame {{
    background-color: {SECTION_BORDER_COLOR};
    height: 1px;
    margin: 8px 0;
}}
"""

# Стиль заголовков разделов
SECTION_HEADER_STYLE = """
QLabel {
    color: #222222;
    padding: 8px 0;
    font-size: 14px;
    font-weight: bold;
}
"""