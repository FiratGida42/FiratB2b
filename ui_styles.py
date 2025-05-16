'''
Kullanıcı Arayüzü Stil Tanımlamaları Modülü
'''

FONT_NAME = "Lucida Console"
FONT_SIZE = 10

MODERN_STYLESHEET = """
QMainWindow {
    background-color: #f0f0f0; /* Açık gri arka plan */
}
QLabel {
    font-size: 10pt; /* Bu, genel font boyutundan bağımsız olabilir veya FONT_SIZE ile ayarlanabilir */
    color: #333333; /* Koyu gri metin */
}
QLineEdit, QComboBox {
    border: 1px solid #cccccc;
    padding: 5px;
    border-radius: 3px;
    font-size: 10pt; /* Bu, genel font boyutundan bağımsız olabilir veya FONT_SIZE ile ayarlanabilir */
    background-color: #ffffff; /* Beyaz giriş alanları */
}
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #0078d7; /* Odaklandığında mavi çerçeve (Windows mavisi gibi) */
}
QPushButton {
    background-color: #0078d7; /* Ana eylem mavisi */
    color: white;
    border: none;
    padding: 8px 16px;
    font-size: 10pt; /* Bu, genel font boyutundan bağımsız olabilir veya FONT_SIZE ile ayarlanabilir */
    border-radius: 3px;
}
QPushButton:hover {
    background-color: #005a9e; /* Hover durumunda biraz daha koyu mavi */
}
QPushButton:pressed {
    background-color: #004578; /* Basıldığında daha da koyu mavi */
}
QComboBox::drop-down {
    border: 0px; /* ComboBox okunun etrafındaki çerçeveyi kaldır */
}
QComboBox::down-arrow {
    image: url(noexist.png); /* Varsayılan oku kullanmak için (alternatif ikon eklenebilir) */
    width: 12px;
    height: 12px;
    padding-right: 5px;
}
""" 