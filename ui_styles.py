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

/* Sol Menü Listesi Stilleri */
QListWidget {
    background-color: #e8ecf0; /* Menü için biraz daha farklı bir gri tonu */
    border: none; /* Kenarlık yok */
    font-size: 11pt; /* Menü fontu biraz daha büyük */
    outline: 0; /* Fokus çerçevesini kaldır (isteğe bağlı) */
}
QListWidget::item {
    padding: 10px 15px; /* Her öğe için iç boşluk */
    border-bottom: 1px solid #d5dbe0; /* Öğeler arası ayırıcı çizgi */
    color: #2c3e50; /* Koyu mavi-gri yazı rengi */
}
QListWidget::item:hover {
    background-color: #d1d8de; /* Fare üzerine gelince hafif arkaplan */
    color: #1a242f; /* Fare üzerine gelince biraz daha koyu yazı */
}
QListWidget::item:selected {
    background-color: #0078d7; /* Seçili öğe için ana eylem mavisi */
    color: white; /* Seçili öğe için beyaz yazı */
    border-left: 3px solid #005a9e; /* Seçili olduğunu belirtmek için sol kenarlık */
    padding-left: 12px; /* Sol kenarlık için padding ayarı */
}

/* Ürünler Sayfası - Grup Kodu Filtre Listesi Stilleri */
QListWidget#productGroupFilterList {
    background-color: #e8ecf0; /* Ana menü ile aynı arkaplan */
    border: 1px solid #d5dbe0; /* Dış kenarlık eklendi */
    font-size: 10pt; /* İstenen font boyutu */
    outline: 0;
}

QListWidget#productGroupFilterList::item {
    padding: 6px 10px; /* Daha sıkı padding */
    border-bottom: 1px solid #d5dbe0; /* Öğeler arası ayırıcı çizgi */
    color: #333333; /* QLabel ile aynı renk */
}

QListWidget#productGroupFilterList::item:hover {
    background-color: #d1d8de;
    color: #1a242f;
}

QListWidget#productGroupFilterList::item:selected {
    background-color: #cce5ff; /* Daha açık bir seçili rengi */
    color: #004578; /* Koyu mavi yazı */
    /* border-left: 3px solid #005a9e;  Bu liste için sol kenarlık kaldırıldı */
}

/* Tablo Stilleri (İsteğe bağlı, zaten genel ayarlar var) */
/*
QTableWidget {
    border: 1px solid #cccccc;
    gridline-color: #d0d0d0; 
}
QHeaderView::section {
    background-color: #e8e8e8;
    padding: 4px;
    border: 1px solid #d0d0d0;
    font-size: 10pt;
}
*/

""" 