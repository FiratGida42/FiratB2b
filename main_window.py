'''
Ana Arayüz Modülü
'''
import sys
import json
import keyring
import pyodbc
import os
import re # re modülü eklendi
import webbrowser # webbrowser modülü eklendi
from urllib.parse import quote_plus # URL encode için eklendi
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QComboBox,
    QLabel,
    QMessageBox,
    QTableWidget, 
    QTableWidgetItem,
    QHeaderView,
    QStatusBar,
    QListWidget,
    QListWidgetItem,
    QProgressDialog,
    QCheckBox,
    QSpinBox,
    QStackedWidget,
    QStyle,
    QDialog, # QDialog eklendi (büyütme için sonra kullanılacak)
    QTreeWidget,
    QTreeWidgetItem,
    QMenu,
    QDialogButtonBox
)
from PySide6.QtGui import QIcon, QFont, QScreen, QAction, QColor, QPixmap # QPixmap eklendi
from PySide6.QtCore import Qt, QSize, Signal, QThread, QObject # QThread, QObject tekrar eklendi
import requests

# Stil ve yardımcı fonksiyonları import et
from ui_styles import MODERN_STYLESHEET, FONT_NAME, FONT_SIZE 
from helpers import format_currency_tr, to_decimal
from data_extractor import (
    get_db_connection as get_data_db_connection, 
    fetch_product_data,
    save_data_to_json,
    send_data_to_web_api,
    DEFAULT_API_URL,
    LOG_FILE
)
# batch_image_downloader ve image_processor'dan gerekli importlar
# from image_processor import download_and_save_image as save_image_from_url, clean_product_name # YORUMA ALINDI
from customers_module import CustomersPage # <<< YENİ: Cari modülünü import et
try:
    from duckduckgo_search import DDGS
    DUCKDUCKGO_SEARCH_AVAILABLE = True
except ImportError:
    DUCKDUCKGO_SEARCH_AVAILABLE = False
    # Bu uyarıyı MainWindow içinde, ilk gerektiği yerde yapmak daha iyi olabilir.
    print("Uyarı: 'duckduckgo_search' kütüphanesi bulunamadı. Otomatik resim bulma özelliği kısıtlı çalışabilir.")
    print("Kurmak için: pip install duckduckgo-search")

SERVICE_NAME = "B2B_App_DB_Credentials"
SETTINGS_FILE = "settings.json"

PRODUCT_DATA_HEADERS = ["Resim", "Otomatik Resim", "Stok Kodu", "Stok Adı", "Bakiye", "Satış Fiyatı 1", "Grup Kodu", "Barkod 1"]

# Renk Tanımlamaları
CHECKED_ITEM_COLOR = QColor("black")      # İşaretli öğeler için varsayılan renk
UNCHECKED_ITEM_COLOR = QColor("gray")     # İşaretsiz öğeler için gri renk

# JSON dosyasının adı (data_extractor.py'deki ile aynı olmalı)
LAST_PREVIEWED_JSON_FILE = "onizlenen_filtrelenmis_urunler.json"

# Dosyanın başına ekle
KATEGORI_AGACI = [
    {
        "ad": "GIDA ÜRÜNLERİ",
        "id": "gida",
        "grupKodlari": ["BAKLIYAT", "MAKARNA", "UN", "CORBA", "BASAK", "KAHVALTI", "COKOKREM", "ETI", "GOFRET", "JELIBON", "LOKUM", "HELVA", "BAYRAM", "KENT", "KONSERVE", "BALIK", "KENTON", "DRO"]
    },
    {
        "ad": "İÇECEKLER",
        "id": "icecekler",
        "grupKodlari": ["CAY", "KAHVE", "ICECEK"]
    },
    {
        "ad": "TEMİZLİK & K. BAKIM",
        "id": "temizlik",
        "grupKodlari": ["DETERJAN", "KOZMETIK", "PED", "BEZ", "MENDIL", "ISLAK"]
    },
    {
        "ad": "EV YAŞAM & GEREÇLERİ",
        "id": "evyasam",
        "grupKodlari": ["BARDAK", "KAGIT"]
    },
    {
        "ad": "DİĞER ÜRÜNLER",
        "id": "diger",
        "grupKodlari": ["01", "DIGER"]
    }
]

# Kategoriler sayfasında bu sabit yapıdan sadece gösterim/filtreleme yap.
# Kategori ekle/sil/düzenle fonksiyonlarını ve butonlarını kaldır.

# --- Yardımcı Sınıflar (Dialoglar) ---

class ProductLoaderWorker(QObject):
    """Arka planda veritabanından ürün verilerini çeken worker."""
    products_fetched = Signal(list)
    error = Signal(str)
    finished = Signal()

    def __init__(self):
        super().__init__()
        self._is_running = True

    def run_loading(self):
        """Veritabanı bağlantısını kurar ve ürünleri çeker."""
        if not self._is_running: return

        db_conn = None # db_conn'u try bloğunun dışında tanımla
        try:
            # data_extractor.py'deki get_db_connection ayarları settings.json'dan okur,
            # bu yüzden worker'a ayrıca parametre geçmeye gerek yok.
            db_conn = get_data_db_connection() # is_worker=True argümanı kaldırıldı.
            if not db_conn:
                if self._is_running:
                    self.error.emit("Veritabanı bağlantısı kurulamadı. Lütfen ayarları kontrol edin.")
                return
            
            if not self._is_running: return

            product_list = fetch_product_data(db_conn)
            if not self._is_running: return

            self.products_fetched.emit(product_list or []) # product_list None ise boş liste gönder

        except pyodbc.Error as db_err:
            print(f"[ProductLoaderWorker] Veritabanı hatası: {db_err}")
            if self._is_running:
                self.error.emit(f"Veritabanı hatası: {db_err}")
        except Exception as e:
            print(f"[ProductLoaderWorker] Beklenmedik hata: {e}")
            if self._is_running:
                self.error.emit(f"Ürünler yüklenirken beklenmedik bir hata oluştu: {e}")
        finally:
            if db_conn:
                try:
                    db_conn.close()
                except Exception as e:
                    print(f"[ProductLoaderWorker] Veritabanı bağlantısı kapatılırken hata: {e}")
            if self._is_running:
                self.finished.emit()
    
    def stop(self):
        self._is_running = False


class ClickableImageLabel(QLabel):
    """Tıklandığında sinyal yayan özel QLabel sınıfı."""
    clicked = Signal(str)  # Tıklandığında resim yolunu (string) içeren sinyal

    def __init__(self, image_path: str, original_stok_kodu: str, original_stok_adi: str, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.original_stok_kodu = original_stok_kodu
        self.original_stok_adi = original_stok_adi
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"{self.original_stok_kodu} - {self.original_stok_adi}\n(Büyütmek için tıkla)")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.image_path)
        super().mousePressEvent(event)

class ImagePreviewDialog(QDialog):
    """Resmi büyütülmüş olarak gösteren diyalog."""
    def __init__(self, image_path: str, window_title: str = "Resim Önizleme", parent=None):
        super().__init__(parent)
        self.setWindowTitle(window_title)
        self.setMinimumSize(400, 300) # Minimum diyalog boyutu
        self.image_path = image_path # Resim yolunu sakla

        layout = QVBoxLayout(self)
        self.image_label = QLabel("Resim yükleniyor...")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.image_label)

        # Kapat butonu (isteğe bağlı, pencere kapatma butonu da var)
        # close_button = QPushButton("Kapat")
        # close_button.clicked.connect(self.accept)
        # layout.addWidget(close_button, 0, Qt.AlignmentFlag.AlignRight)
    
    def showEvent(self, event):
        """Diyalog gösterilmeden hemen önce çağrılır."""
        super().showEvent(event)
        # Resim yükleme ve ölçeklendirmeyi burada yap
        if not self.image_label.pixmap(): # Eğer resim zaten yüklenmemişse (örn. tekrar show çağrılırsa diye)
            pixmap = QPixmap(self.image_path)
            if pixmap.isNull():
                self.image_label.setText(f"Resim yüklenemedi:\n{os.path.basename(self.image_path)}")
            else:
                # Diyalogun mevcut boyutuna göre ölçeklendir (showEvent içinde olduğumuz için daha güvenilir)
                # veya daha büyük bir alana göre ölçeklendirip sonra diyaloğu ayarla.
                # Parent'ın boyutuna göre maksimum bir ölçek belirleyelim.
                max_width = self.parent().width() * 0.8 if self.parent() else 800
                max_height = self.parent().height() * 0.8 if self.parent() else 600
                
                # Orijinal resim boyutlarını al
                original_width = pixmap.width()
                original_height = pixmap.height()

                # Görüntülenecek maksimum boyutları aşmamak için hedef boyutları belirle
                target_width = min(original_width, int(max_width))
                target_height = min(original_height, int(max_height))

                scaled_pixmap = pixmap.scaled(target_width, target_height,
                                                Qt.AspectRatioMode.KeepAspectRatio, 
                                                Qt.TransformationMode.SmoothTransformation)
                self.image_label.setPixmap(scaled_pixmap)
                
                # Diyalog boyutunu, ölçeklenmiş resme ve başlıklara uyacak şekilde ayarla
                # Pencere çerçevesi ve layout boşlukları için biraz pay ekle
                new_width = max(self.minimumWidth(), scaled_pixmap.width() + 40) 
                new_height = max(self.minimumHeight(), scaled_pixmap.height() + 60) # Başlık ve olası butonlar için pay
                self.resize(new_width, new_height)
                # Diyaloğu parent'a göre ortala (eğer parent varsa)
                if self.parent():
                    parent_rect = self.parent().geometry()
                    self.move(parent_rect.center() - self.rect().center())

class MainWindow(QMainWindow):
    '''
    Ana uygulama penceresi.
    '''
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Veritabanı Yönetim Paneli")
        self.all_fetched_product_data = None
        self.current_product_data = None
        self.excluded_group_codes_pref = []
        self.image_preview_dialog = None
        self.product_load_thread = None
        self.product_loader_worker = None
        self.setup_ui_appearance()
        self._create_menu_bar()
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_app_layout = QHBoxLayout(central_widget)
        main_app_layout.setContentsMargins(10, 10, 10, 10)
        main_app_layout.setSpacing(10)
        self.menu_list_widget = QListWidget()
        self.menu_list_widget.setMinimumWidth(180)
        self.menu_list_widget.setMaximumWidth(200)
        settings_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
        products_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        categories_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DirLinkIcon)
        customers_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DriveNetIcon) # Cari için ikon

        ayarlar_item = QListWidgetItem("Ayarlar")
        ayarlar_item.setIcon(settings_icon)
        self.menu_list_widget.addItem(ayarlar_item)

        urunler_item = QListWidgetItem("Ürünler")
        urunler_item.setIcon(products_icon)
        self.menu_list_widget.addItem(urunler_item)

        kategoriler_item = QListWidgetItem("Kategoriler")
        kategoriler_item.setIcon(categories_icon)
        self.menu_list_widget.addItem(kategoriler_item)

        cariler_item = QListWidgetItem("Cariler") # <<< YENİ
        cariler_item.setIcon(customers_icon)      # <<< YENİ
        self.menu_list_widget.addItem(cariler_item) # <<< YENİ

        self.menu_list_widget.currentItemChanged.connect(self.change_view)
        main_app_layout.addWidget(self.menu_list_widget, 0)

        self.stacked_widget = QStackedWidget()
        main_app_layout.addWidget(self.stacked_widget, 1)

        self._create_settings_page()
        self._create_products_page()
        self._create_categories_page()
        self._create_customers_page_from_module() # <<< YENİ: Modülden cari sayfası oluştur

        self.menu_list_widget.setCurrentRow(0)
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Hazır.")
        self.load_settings()
        self.showFullScreen()  # Uygulama başlarken tam ekran aç

    def setup_ui_appearance(self):
        self.setMinimumSize(1000, 700) # Yeni layout için genişletildi
        font = QFont(FONT_NAME, FONT_SIZE)
        self.setFont(font)
        self.setStyleSheet(MODERN_STYLESHEET) 

    def _create_menu_bar(self):
        menu_bar = self.menuBar()
        # Dosya Menüsü
        file_menu = menu_bar.addMenu("&Dosya")

        # Tam Ekran Aç/Kapat Aksiyonu
        toggle_fullscreen_action = QAction("Tam Ekran Aç/Kapat", self)
        toggle_fullscreen_action.setShortcut("F11") # Kısayol
        toggle_fullscreen_action.triggered.connect(self.toggle_fullscreen)
        file_menu.addAction(toggle_fullscreen_action)

        file_menu.addSeparator()

        # Çıkış Aksiyonu
        exit_action = QAction("&Çıkış", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close) # self.close() QMainWindow'un kapanma olayını tetikler
        file_menu.addAction(exit_action)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal() # Önce normal moda geç
            # Şimdi pencereyi görev çubuğunu örtmeyecek şekilde ayarla
            screen = QApplication.primaryScreen()
            if screen:
                available_geometry = screen.availableGeometry()
                # Mevcut pencere boyutlarını koruyarak veya varsayılan bir boyuta ayarlayarak ortala
                # Örnek: Kullanılabilir alanın %80'i kadar bir boyut belirleyelim
                new_width = int(available_geometry.width() * 0.8)
                new_height = int(available_geometry.height() * 0.8)
                self.resize(new_width, new_height)
                
                # Ortala
                frame_geometry = self.frameGeometry()
                frame_geometry.moveCenter(available_geometry.center())
                self.move(frame_geometry.topLeft())

            self.status_bar.showMessage("Tam ekrandan çıkıldı.", 2000)
        else:
            self.showFullScreen()
            self.status_bar.showMessage("Tam ekrana geçildi.", 2000)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            if self.isFullScreen():
                self.showNormal() # Önce normal moda geç
                screen = QApplication.primaryScreen()
                if screen:
                    available_geometry = screen.availableGeometry()
                    new_width = int(available_geometry.width() * 0.8)
                    new_height = int(available_geometry.height() * 0.8)
                    self.resize(new_width, new_height)
                    
                    frame_geometry = self.frameGeometry()
                    frame_geometry.moveCenter(available_geometry.center())
                    self.move(frame_geometry.topLeft())
                self.status_bar.showMessage("Tam ekrandan çıkıldı (Esc).", 2000)
        super().keyPressEvent(event)

    def _create_settings_page(self):
        self.settings_page_widget = QWidget()
        settings_layout = QVBoxLayout(self.settings_page_widget)
        settings_layout.setContentsMargins(5, 5, 5, 5)
        settings_layout.setSpacing(10)

        # --- Sağ Üst Köşeye Çıkış Butonu --- (YENİ)
        exit_button_bar_layout = QHBoxLayout()
        exit_button_bar_layout.addStretch(1) # Butonu sağa itmek için stretch
        self.top_right_exit_button = QPushButton("Çıkış")
        self.top_right_exit_button.setToolTip("Uygulamayı Kapat (Ctrl+Q)")
        self.top_right_exit_button.setFixedSize(80, 28) # Butona sabit bir boyut verelim
        self.top_right_exit_button.clicked.connect(self.close)
        exit_button_bar_layout.addWidget(self.top_right_exit_button)
        settings_layout.addLayout(exit_button_bar_layout)

        form_layout = QFormLayout()
        form_layout.setHorizontalSpacing(10) 
        form_layout.setVerticalSpacing(10)   
        self.server_address_input = QLineEdit()
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        db_layout = QHBoxLayout()
        self.db_name_combo = QComboBox()
        self.db_name_combo.setMinimumWidth(180)
        db_layout.addWidget(self.db_name_combo)
        self.list_dbs_button = QPushButton("Veritabanlarını Listele")
        self.list_dbs_button.clicked.connect(self.list_databases)
        db_layout.addWidget(self.list_dbs_button)
        db_layout.setSpacing(10)
        form_layout.addRow(QLabel("Sunucu Adresi:"), self.server_address_input)
        form_layout.addRow(QLabel("Kullanıcı Adı:"), self.username_input)
        form_layout.addRow(QLabel("Şifre:"), self.password_input)
        form_layout.addRow(QLabel("Veritabanı Adı:"), db_layout)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Web API için ürünler API anahtarınızı girin")
        form_layout.addRow(QLabel("Ürünler API Anahtarı:"), self.api_key_input)
        settings_layout.addLayout(form_layout)

        scheduler_group_label = QLabel("Otomatik Ürün Güncelleme Ayarları:")
        scheduler_group_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        settings_layout.addWidget(scheduler_group_label)

        scheduler_form_layout = QFormLayout()
        scheduler_form_layout.setHorizontalSpacing(10)
        scheduler_form_layout.setVerticalSpacing(10)
        self.scheduler_enabled_checkbox = QCheckBox("Otomatik Güncellemeyi Etkinleştir")
        scheduler_form_layout.addRow(self.scheduler_enabled_checkbox)
        self.scheduler_interval_spinbox = QSpinBox()
        self.scheduler_interval_spinbox.setMinimum(15)
        self.scheduler_interval_spinbox.setMaximum(1440)
        self.scheduler_interval_spinbox.setValue(30)
        self.scheduler_interval_spinbox.setSuffix(" dakika")
        scheduler_form_layout.addRow(QLabel("Güncelleme Sıklığı:"), self.scheduler_interval_spinbox)

        # Otomatik Resim İndirme CheckBox'ı kaldırıldı.
        # self.auto_download_images_checkbox = QCheckBox("Eksik ürün resimlerini arka planda otomatik bul ve indir")
        # self.auto_download_images_checkbox.setToolTip("Veriler çekildikten sonra, resmi olmayan ürünler için otomatik olarak resim arar ve kaydeder.")
        # scheduler_form_layout.addRow(self.auto_download_images_checkbox)

        settings_layout.addLayout(scheduler_form_layout)
        # --- Zamanlayıcı Ayarları Sonu ---

        control_buttons_layout = QHBoxLayout()
        self.save_settings_button = QPushButton("Tüm Ayarları Kaydet")
        self.save_settings_button.clicked.connect(self.save_settings)
        control_buttons_layout.addWidget(self.save_settings_button)
        control_buttons_layout.addStretch()
        settings_layout.addLayout(control_buttons_layout)
        
        settings_layout.addStretch() # Ayar formunun üste yaslanması için
        self.stacked_widget.addWidget(self.settings_page_widget)

    def _create_products_page(self):
        self.products_page_widget = QWidget()
        # Ana ürünler sayfası düzeni: Yatay (Sol: Filtre, Sağ: İçerik)
        products_main_layout = QHBoxLayout(self.products_page_widget)
        products_main_layout.setContentsMargins(5,5,5,5)
        products_main_layout.setSpacing(10)

        # --- Sol Dikey Panel: Grup Kodu Filtresi ---
        group_filter_panel_widget = QWidget()
        group_filter_panel_layout = QVBoxLayout(group_filter_panel_widget)
        group_filter_panel_layout.setContentsMargins(0,0,0,0) # Panel içi boşlukları sıfırla
        group_filter_panel_layout.setSpacing(8)

        filter_label = QLabel("Grup Kodu Filtresi:")
        group_filter_panel_layout.addWidget(filter_label)

        # Tümünü Seç/Bırak butonları için yatay düzen
        select_all_layout = QHBoxLayout()
        self.select_all_button = QPushButton("Tümünü Seç")
        self.select_all_button.clicked.connect(self._select_all_groups)
        self.deselect_all_button = QPushButton("Tümünü Bırak")
        self.deselect_all_button.clicked.connect(self._deselect_all_groups)
        select_all_layout.addWidget(self.select_all_button)
        select_all_layout.addWidget(self.deselect_all_button)
        group_filter_panel_layout.addLayout(select_all_layout)

        self.group_code_list_widget = QListWidget() # Ürünler sayfasına özel
        self.group_code_list_widget.setObjectName("productGroupFilterList") # Object name eklendi
        self.group_code_list_widget.itemChanged.connect(self._on_group_code_item_changed)
        group_filter_panel_layout.addWidget(self.group_code_list_widget, 1) # Dikeyde genişlesin

        self.apply_filter_button = QPushButton("Filtreyi Uygula")
        self.apply_filter_button.clicked.connect(self.apply_group_code_filter)
        group_filter_panel_layout.addWidget(self.apply_filter_button) # Listenin altına buton
        
        group_filter_panel_widget.setMinimumWidth(180)
        group_filter_panel_widget.setMaximumWidth(220) # Filtre paneline bir genişlik sınırı
        products_main_layout.addWidget(group_filter_panel_widget, 0) # Filtre paneli genişlemesin

        # --- Sağ Dikey Panel: Ana İçerik (Butonlar ve Tablo) ---
        main_content_panel_widget = QWidget()
        main_content_layout = QVBoxLayout(main_content_panel_widget)
        main_content_layout.setContentsMargins(0,0,0,0)
        main_content_layout.setSpacing(10)

        # --- Veri Çekme Butonları ---
        data_action_layout = QHBoxLayout()
        self.preview_data_button = QPushButton("Ürün Verilerini Çek ve Önizle")
        self.preview_data_button.clicked.connect(self.preview_product_data)
        data_action_layout.addWidget(self.preview_data_button)

        self.save_json_button = QPushButton("Önizlenen Veriyi JSON'a Kaydet")
        self.save_json_button.clicked.connect(self.save_previewed_data_to_json)
        self.save_json_button.setEnabled(False) 
        data_action_layout.addWidget(self.save_json_button)

        self.send_to_api_button = QPushButton("Verileri Web API'sine Gönder")
        self.send_to_api_button.clicked.connect(self.send_data_to_api_action)
        self.send_to_api_button.setEnabled(False)
        data_action_layout.addWidget(self.send_to_api_button)
        data_action_layout.addStretch()
        main_content_layout.addLayout(data_action_layout)

        # --- Ürün Veri Tablosu ---
        self.product_table = QTableWidget()
        self.product_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers) 
        self.product_table.setAlternatingRowColors(True)
        self.product_table.setSortingEnabled(True)
        main_content_layout.addWidget(self.product_table, 1) # Tablo dikeyde genişlesin

        products_main_layout.addWidget(main_content_panel_widget, 1) # Ana içerik alanı genişlesin

        self.stacked_widget.addWidget(self.products_page_widget)

    def _create_categories_page(self):
        self.categories_page_widget = QWidget()
        layout = QVBoxLayout(self.categories_page_widget)
        label = QLabel("Kategori Ağacı (Sadece Okunabilir)")
        label.setStyleSheet("font-weight: bold; font-size: 16px; margin-bottom: 10px;")
        layout.addWidget(label)
        self.categories_tree = QTreeWidget()
        self.categories_tree.setHeaderLabels(["Ana Kategori", "Grup Kodu"])
        self.categories_tree.setColumnWidth(0, 250)
        self.categories_tree.setAlternatingRowColors(True)
        layout.addWidget(self.categories_tree)
        self.stacked_widget.addWidget(self.categories_page_widget)
        self._populate_static_category_tree()

    def _populate_static_category_tree(self):
        self.categories_tree.clear()
        for ana_kat in KATEGORI_AGACI:
            ana_item = QTreeWidgetItem([ana_kat["ad"], ""])
            for grup_kod in ana_kat["grupKodlari"]:
                alt_item = QTreeWidgetItem(["", grup_kod])
                ana_item.addChild(alt_item)
            self.categories_tree.addTopLevelItem(ana_item)
        self.categories_tree.expandAll()

    def _load_categories(self):
        """Web API'den kategori ağacını yükler."""
        try:
            # API URL'sini settings.json'dan al
            api_url = DEFAULT_API_URL.replace("/products", "/categories")
            self.categories_status_label.setText("Kategoriler yükleniyor...")
            QApplication.processEvents()

            # API anahtarını ayarlardan al
            api_key = self.api_key_input.text().strip()
            headers = {"X-API-Key": api_key} if api_key else {}

            # API URL'sini kontrol et
            if not api_url:
                raise ValueError("API URL'si bulunamadı. Lütfen ayarları kontrol edin.")
            print(f"API URL: {api_url}")  # Debug için URL'yi yazdır

            response = requests.get(api_url, headers=headers, timeout=10)  # 10 saniye timeout ekle
            if response.status_code == 200:
                categories = response.json()
                print("API'den dönen veri:", categories)  # Debug için
                self._populate_category_tree(categories)
                self.categories_status_label.setText(f"Toplam {self.categories_tree.topLevelItemCount()} kategori yüklendi.")
                self.save_categories_button.setEnabled(True)
            else:
                error_msg = f"Hata: {response.status_code} - {response.text}"
                self.categories_status_label.setText(error_msg)
                print(f"API Hatası: {error_msg}")  # Debug için hatayı yazdır
                QMessageBox.warning(self, "Hata", f"Kategoriler yüklenirken bir hata oluştu:\n{error_msg}")
        except requests.exceptions.ConnectionError:
            error_msg = "API sunucusuna bağlanılamadı. Lütfen internet bağlantınızı ve API URL'sini kontrol edin."
            self.categories_status_label.setText(error_msg)
            print(f"Bağlantı Hatası: {error_msg}")  # Debug için hatayı yazdır
            QMessageBox.critical(self, "Bağlantı Hatası", error_msg)
        except requests.exceptions.Timeout:
            error_msg = "API sunucusu yanıt vermedi. Lütfen daha sonra tekrar deneyin."
            self.categories_status_label.setText(error_msg)
            print(f"Zaman Aşımı: {error_msg}")  # Debug için hatayı yazdır
            QMessageBox.critical(self, "Zaman Aşımı", error_msg)
        except Exception as e:
            error_msg = f"Beklenmeyen bir hata oluştu: {str(e)}"
            self.categories_status_label.setText(error_msg)
            print(f"Genel Hata: {error_msg}")  # Debug için hatayı yazdır
            QMessageBox.critical(self, "Hata", error_msg)

    def _populate_category_tree(self, categories, parent_item=None):
        """Kategori ağacını doldurur."""
        if parent_item is None:
            self.categories_tree.clear()
        for category in categories:
            # Anahtarları esnek yap
            name = category.get('name') or category.get('ad', '')
            code = category.get('code') or category.get('id', '')
            item = QTreeWidgetItem(parent_item if parent_item else self.categories_tree)
            item.setText(0, name)
            item.setText(1, code)
            item.setData(0, Qt.ItemDataRole.UserRole, category)  # Tüm kategori verisini sakla
            # Alt kategorileri varsa onları da ekle
            children = category.get('children') or category.get('altKategoriler') or []
            if children:
                self._populate_category_tree(children, item)
            # Alt kategorileri genişlet
            item.setExpanded(True)

    def _show_category_context_menu(self, position):
        """Kategori ağacı için bağlam menüsünü gösterir."""
        menu = QMenu()
        
        add_action = menu.addAction("Yeni Kategori Ekle")
        edit_action = menu.addAction("Düzenle")
        delete_action = menu.addAction("Sil")
        
        # Seçili öğe yoksa bazı aksiyonları devre dışı bırak
        current_item = self.categories_tree.currentItem()
        if not current_item:
            edit_action.setEnabled(False)
            delete_action.setEnabled(False)
        
        action = menu.exec(self.categories_tree.mapToGlobal(position))
        
        if action == add_action:
            self._add_new_category(current_item)
        elif action == edit_action and current_item:
            self._edit_category(current_item)
        elif action == delete_action and current_item:
            self._delete_category(current_item)

    def _add_new_category(self, parent_item=None):
        """Yeni kategori ekler."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Yeni Kategori")
        layout = QFormLayout(dialog)
        
        name_edit = QLineEdit()
        code_edit = QLineEdit()
        
        layout.addRow("Kategori Adı:", name_edit)
        layout.addRow("Kategori Kodu:", code_edit)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_item = QTreeWidgetItem(parent_item if parent_item else self.categories_tree)
            new_item.setText(0, name_edit.text())
            new_item.setText(1, code_edit.text())
            self.save_categories_button.setEnabled(True)

    def _edit_category(self, item):
        """Kategoriyi düzenler."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Kategori Düzenle")
        layout = QFormLayout(dialog)
        
        name_edit = QLineEdit(item.text(0))
        code_edit = QLineEdit(item.text(1))
        
        layout.addRow("Kategori Adı:", name_edit)
        layout.addRow("Kategori Kodu:", code_edit)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            item.setText(0, name_edit.text())
            item.setText(1, code_edit.text())
            self.save_categories_button.setEnabled(True)

    def _delete_category(self, item):
        """Kategoriyi siler."""
        reply = QMessageBox.question(
            self, 
            "Kategori Sil",
            f"'{item.text(0)}' kategorisini silmek istediğinizden emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            parent = item.parent()
            if parent:
                parent.removeChild(item)
            else:
                self.categories_tree.takeTopLevelItem(self.categories_tree.indexOfTopLevelItem(item))
            self.save_categories_button.setEnabled(True)

    def _save_categories(self):
        """Kategori ağacını web API'ye kaydeder."""
        try:
            # Kategori ağacını JSON formatına dönüştür
            categories = self._tree_to_json()
            
            # API URL'sini settings.json'dan al
            api_url = DEFAULT_API_URL.replace("/products", "/categories")
            
            self.categories_status_label.setText("Kategoriler kaydediliyor...")
            QApplication.processEvents()
            
            response = requests.post(api_url, json=categories)
            if response.status_code == 200:
                self.categories_status_label.setText("Kategoriler başarıyla kaydedildi.")
                self.save_categories_button.setEnabled(False)
                QMessageBox.information(self, "Başarılı", "Kategoriler başarıyla kaydedildi.")
            else:
                self.categories_status_label.setText(f"Hata: {response.status_code} - {response.text}")
                QMessageBox.warning(self, "Hata", f"Kategoriler kaydedilirken bir hata oluştu: {response.text}")
        except Exception as e:
            self.categories_status_label.setText(f"Hata: {str(e)}")
            QMessageBox.critical(self, "Hata", f"Kategoriler kaydedilirken bir hata oluştu: {str(e)}")

    def _tree_to_json(self, parent_item=None):
        """Kategori ağacını JSON formatına dönüştürür."""
        result = []
        
        if parent_item is None:
            # Kök seviyesindeki öğeler
            for i in range(self.categories_tree.topLevelItemCount()):
                item = self.categories_tree.topLevelItem(i)
                result.append(self._item_to_json(item))
        else:
            # Alt öğeler
            for i in range(parent_item.childCount()):
                item = parent_item.child(i)
                result.append(self._item_to_json(item))
                
        return result

    def _item_to_json(self, item):
        """Tek bir ağaç öğesini JSON formatına dönüştürür."""
        category = {
            'name': item.text(0),
            'code': item.text(1),
            'children': []
        }
        
        # Alt kategorileri ekle
        for i in range(item.childCount()):
            child = item.child(i)
            category['children'].append(self._item_to_json(child))
            
        return category

    def change_view(self, current, previous):
        if not current: # Eğer bir şekilde current None ise (örn. liste boşsa)
            return
            
        if current.text() == "Ayarlar":
            self.stacked_widget.setCurrentWidget(self.settings_page_widget)
        elif current.text() == "Ürünler":
            self.stacked_widget.setCurrentWidget(self.products_page_widget)
            # Ürünler sayfasına geçildiğinde, eğer ham veri varsa filtreleri ve tabloyu güncelleyebiliriz
            if self.all_fetched_product_data:
                 self._update_group_filter_list(self.all_fetched_product_data)
                 self.apply_group_code_filter() # Otomatik uygula
            else: # Ham veri yoksa, filtre listesini temizle ve tabloyu boşalt
                 self._update_group_filter_list(None)
                 self.product_table.setRowCount(0)
                 self.save_json_button.setEnabled(False)
                 self.send_to_api_button.setEnabled(False)

        elif current.text() == "Kategoriler":
            self.stacked_widget.setCurrentWidget(self.categories_page_widget)
        elif current.text() == "Cariler": # <<< YENİ
            if hasattr(self, 'customers_page_widget'): # Widget'ın varlığını kontrol et
                self.stacked_widget.setCurrentWidget(self.customers_page_widget)
                self.status_bar.showMessage("Cariler sayfası açıldı.", 2000)
                 # İsteğe bağlı olarak, sayfaya her geçildiğinde verileri otomatik yükleyebilirsiniz:
                # if hasattr(self.customers_page_widget, 'load_customer_data'):
                #    self.customers_page_widget.load_customer_data()
            else:
                self.status_bar.showMessage("Cari sayfası widget'ı bulunamadı!", 3000)
        # Diğer menü öğeleri için benzer elif blokları eklenebilir

    def load_settings(self):
        '''
        Kaydedilmiş ayarları settings.json ve keyring'den yükler.
        Kullanıcı tercihleri (hariç tutulan grup kodları), zamanlayıcı ve API anahtarını da yükler.
        Ayrıca, mümkünse son önizlenen JSON'dan grup filtresini doldurur.
        '''
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings_data = json.load(f)
                self.server_address_input.setText(settings_data.get("server_address", ""))
                self.username_input.setText(settings_data.get("username", ""))
                saved_db_name = settings_data.get("db_name")
                if saved_db_name:
                    if self.db_name_combo.findText(saved_db_name) == -1:
                        self.db_name_combo.addItem(saved_db_name)
                    self.db_name_combo.setCurrentText(saved_db_name)
                
                # API Anahtarını yükle
                self.api_key_input.setText(settings_data.get("products_api_key", ""))

                username_for_keyring = settings_data.get("username")
                if username_for_keyring:
                    password = keyring.get_password(SERVICE_NAME, username_for_keyring)
                    if password:
                        self.password_input.setText(password)
                    else:
                        # Eğer keyring'de şifre yoksa ve kullanıcı adı "sa" ise varsayılan şifreyi ayarla
                        if username_for_keyring == "sa":
                            self.password_input.setText("sapass")
                            # Şifreyi keyring'e kaydet
                            try:
                                keyring.set_password(SERVICE_NAME, "sa", "sapass")
                                self.status_bar.showMessage("FIRATSRV şifresi keyring'e kaydedildi.", 3000)
                            except Exception as e:
                                self.status_bar.showMessage(f"Şifre keyring'e kaydedilemedi: {e}", 3000)
                
                user_prefs = settings_data.get("user_preferences", {})
                self.excluded_group_codes_pref = user_prefs.get("excluded_group_codes", [])

                scheduler_settings = settings_data.get("scheduler_settings", {})
                self.scheduler_enabled_checkbox.setChecked(scheduler_settings.get("enabled", False))
                self.scheduler_interval_spinbox.setValue(scheduler_settings.get("interval_minutes", 30))
                # Otomatik resim indirme ayarını yükleme kısmı kaldırıldı.
                # self.auto_download_images_checkbox.setChecked(scheduler_settings.get("auto_download_missing_images", False))

                self.status_bar.showMessage("Ayarlar, kullanıcı tercihleri ve zamanlayıcı ayarları yüklendi.", 3000)
        
        except FileNotFoundError:
            self.status_bar.showMessage(f"{SETTINGS_FILE} bulunamadı. FIRATSRV sunucusu için varsayılan ayarlar yükleniyor.", 3000)
            # FIRATSRV sunucusu için varsayılan değerler
            self.server_address_input.setText("FIRATSRV")
            self.username_input.setText("sa")
            self.password_input.setText("sapass")
            self.excluded_group_codes_pref = []
            self.scheduler_enabled_checkbox.setChecked(False)
            self.scheduler_interval_spinbox.setValue(30)
            # self.auto_download_images_checkbox.setChecked(False) # Hata durumunda varsayılan - KALDIRILDI
        except Exception as e:
            QMessageBox.warning(self, "Ayarlar Yüklenemedi", f"Ayarlar yüklenirken bir hata oluştu: {e}")
            self.status_bar.showMessage("Ayarlar yüklenemedi!", 3000)
            self.excluded_group_codes_pref = []
            self.scheduler_enabled_checkbox.setChecked(False)
            self.scheduler_interval_spinbox.setValue(30)
            # self.auto_download_images_checkbox.setChecked(False) # Hata durumunda varsayılan - KALDIRILDI
        finally:
            # Eğer settings.json dosyası yoksa, varsayılan ayarları kaydet
            if not os.path.exists(SETTINGS_FILE):
                self._save_default_settings()
            
            # Ayarlar yüklendikten sonra (veya hata durumunda bile) grup filtresini dosyadan doldurmayı dene
            # ve tabloyu başlangıçta boşalt/güncelle.
            # Bu işlem artık change_view veya preview_product_data içinde yönetilecek.
            # self._try_populate_filters_and_table_at_startup() # Bu satır kaldırıldı/yorumlandı.
            # Başlangıçta eğer son kaydedilen JSON varsa Ürünler sayfasını onunla doldurabiliriz
            if os.path.exists(LAST_PREVIEWED_JSON_FILE) and self.stacked_widget.currentWidget() == self.products_page_widget:
                 self._try_populate_filters_and_table_at_startup()

    def _try_populate_filters_and_table_at_startup(self):
        """
        Uygulama başlangıcında, eğer varsa, son kaydedilen JSON dosyasından
        grup filtresini doldurur ve tabloyu bu verilerle günceller.
        """
        initial_data_loaded = False
        if os.path.exists(LAST_PREVIEWED_JSON_FILE):
            try:
                with open(LAST_PREVIEWED_JSON_FILE, "r", encoding="utf-8") as f:
                    # JSON'dan Decimal'e dönüştürme gerekebilir, ancak grup kodları için string yeterli.
                    # Şimdilik doğrudan JSON verisini kullanıyoruz, ondalıklar string olarak kalacak.
                    # Eğer tabloyu da dolduracaksak, ondalık dönüşümü önemli olur.
                    data_from_file = json.load(f) 
                
                if data_from_file and isinstance(data_from_file, list):
                    self.status_bar.showMessage(f"'{LAST_PREVIEWED_JSON_FILE}' dosyasından grup kodları yükleniyor...", 2000)
                    # Grup filtresini bu dosyadaki verilere göre doldur
                    # Bu, self.all_fetched_product_data'yı geçici olarak bu veriyle ayarlar
                    # ve _update_group_filter_list çağrıldığında bunu kullanır.
                    # Ya da doğrudan _update_group_filter_list'e data_from_file'ı parametre olarak verelim.
                    self._update_group_filter_list(data_from_file) # Yeni yardımcı fonksiyonu kullan
                    
                    # Eğer başlangıçta tabloyu da doldurmak istiyorsak:
                    # self.all_fetched_product_data = data_from_file # Bu, filtrelerin uygulanacağı veri olur
                    # self.apply_group_code_filter() # Bu, tabloyu da doldurur
                    # self.status_bar.showMessage(f"'{LAST_PREVIEWED_JSON_FILE}' dosyasından {len(data_from_file)} ürün yüklendi ve filtreler uygulandı.", 3000)
                    # self.save_json_button.setEnabled(bool(self.current_product_data)) # current_product_data'ya göre
                    # self.send_to_api_button.setEnabled(bool(self.current_product_data))
                    initial_data_loaded = True
                else:
                    self.status_bar.showMessage(f"'{LAST_PREVIEWED_JSON_FILE}' dosyası boş veya formatı hatalı.", 3000)
            except json.JSONDecodeError:
                self.status_bar.showMessage(f"'{LAST_PREVIEWED_JSON_FILE}' dosyası okunamadı (JSON format hatası).", 3000)
            except Exception as e:
                self.status_bar.showMessage(f"'{LAST_PREVIEWED_JSON_FILE}' işlenirken hata: {e}", 3000)

        if not initial_data_loaded:
            # Eğer dosyadan veri yüklenemediyse, grup filtresi boş kalır (mevcut davranış).
            # Ya da, sadece self.excluded_group_codes_pref'teki kodları listeye ekleyebiliriz,
            # ama bu, olmayan grupları göstermek olur. Şimdilik boş bırakmak daha iyi.
            self.group_code_list_widget.clear() # Emin olmak için temizleyelim
            self.status_bar.showMessage("Grup filtresi için başlangıç verisi bulunamadı.", 3000)
        
        # Şimdilik tabloyu boşaltalım, veri çekilince dolsun.
        if not initial_data_loaded: # Eğer dosyadan veri yüklenmediyse tabloyu kesin boşalt
             # self.current_product_data = None # current_product_data'nın burada değiştirilmesi yerine,
             # self.all_fetched_product_data = None # change_view veya preview_data karar versin.
             if hasattr(self, 'product_table'): # Eğer product_table oluşturulduysa
                 self.product_table.setRowCount(0)
             if hasattr(self, 'save_json_button'):
                 self.save_json_button.setEnabled(False)
             if hasattr(self, 'send_to_api_button'):
                 self.send_to_api_button.setEnabled(False)
             if hasattr(self, 'group_code_list_widget'): # grup kodu listesi de temizlenebilir
                 self._update_group_filter_list(None)

    def _update_group_filter_list(self, source_product_data):
        """
        Verilen ürün listesinden (source_product_data) benzersiz grup kodlarını alır,
        sol paneldeki QListWidget'ı doldurur ve kullanıcı tercihlerine göre işaretler.
        """
        self.group_code_list_widget.blockSignals(True) # Sinyalleri geçici olarak engelle
        self.group_code_list_widget.clear()
        
        if source_product_data:
            unique_group_codes = sorted(list(set(p.get('GRUP_KODU', '') for p in source_product_data if p.get('GRUP_KODU'))))
            if not unique_group_codes:
                 self.status_bar.showMessage("Filtrelenecek grup kodu bulunamadı.", 3000)

            for code in unique_group_codes:
                item = QListWidgetItem(code)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                if code in self.excluded_group_codes_pref:
                    item.setCheckState(Qt.CheckState.Unchecked)
                    item.setForeground(UNCHECKED_ITEM_COLOR)
                else:
                    item.setCheckState(Qt.CheckState.Checked)
                    item.setForeground(CHECKED_ITEM_COLOR)
                self.group_code_list_widget.addItem(item)
        else:
            self.status_bar.showMessage("Grup filtresi için kaynak veri bulunmuyor.", 3000)
            
        self.group_code_list_widget.blockSignals(False) # Sinyalleri tekrar etkinleştir

    def list_databases(self):
        '''
        SQL Server'a bağlanır ve veritabanlarını QComboBox'a yükler.
        '''
        # Bu fonksiyon artık Ayarlar sayfasındaki self.db_name_combo ile çalışıyor olmalı.
        # Zaten bu şekilde yazılmış, bir değişiklik gerekmeyebilir.
        server = self.server_address_input.text()
        user = self.username_input.text()
        password = self.password_input.text() 

        if not server or not user:
            QMessageBox.warning(self, "Eksik Bilgi", "Sunucu Adresi ve Kullanıcı Adı girilmelidir.")
            return

        self.status_bar.showMessage(f"{server} sunucusundaki veritabanları listeleniyor...", 3000)

        # Sistemde kurulu SQL Server ODBC sürücüsünü tespit et (18 > 17 > generic)
        try:
            drivers = [d.strip() for d in pyodbc.drivers()]
        except Exception:
            drivers = []
        if any(d == 'ODBC Driver 18 for SQL Server' for d in drivers):
            driver_name = 'ODBC Driver 18 for SQL Server'
        elif any(d == 'ODBC Driver 17 for SQL Server' for d in drivers):
            driver_name = 'ODBC Driver 17 for SQL Server'
        else:
            driver_name = 'SQL Server'

        conn_str = (
            f"DRIVER={{{driver_name}}};" +
            f"SERVER={server};" +
            f"UID={user};" +
            f"PWD={password};" +
            f"TrustServerCertificate=yes;"
        )
        
        try:
            with pyodbc.connect(conn_str, timeout=5) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT name FROM sys.databases WHERE name NOT IN ('master', 'tempdb', 'model', 'msdb') ORDER BY name")
                    databases = [row.name for row in cursor.fetchall()]
                    
                    current_db_selection = self.db_name_combo.currentText()
                    self.db_name_combo.clear()
                    self.db_name_combo.addItems(databases)

                    if current_db_selection in databases:
                        self.db_name_combo.setCurrentText(current_db_selection)
                    elif databases:
                        self.db_name_combo.setCurrentIndex(0) 

                    if not databases:
                        QMessageBox.information(self, "Bilgi", "Listelenecek kullanıcı veritabanı bulunamadı.")
                        self.status_bar.showMessage("Listelenecek kullanıcı veritabanı bulunamadı.", 3000)
                    else:
                        QMessageBox.information(self, "Başarılı", "Veritabanları başarıyla listelendi.")
                        self.status_bar.showMessage("Veritabanları listelendi.", 3000)

        except pyodbc.Error as ex:
            sqlstate = ex.args[0]
            QMessageBox.critical(self, "Veritabanı Listeleme Hatası", f"Bağlantı veya sorgu hatası: {sqlstate} - {ex}")
            self.status_bar.showMessage("Veritabanı listeleme hatası!", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Veritabanı Listeleme Hatası", f"Beklenmedik bir hata oluştu: {e}")
            self.status_bar.showMessage("Veritabanı listeleme hatası!", 3000)

    def _save_default_settings(self):
        '''
        FIRATSRV sunucusu için varsayılan ayarları settings.json dosyasına kaydeder.
        Bu fonksiyon sadece ilk çalıştırmada kullanılır.
        '''
        settings_data = {
            "server_address": "FIRATSRV",
            "username": "sa",
            "db_name": "",  # Veritabanı adı boş bırakılır, kullanıcı seçecek
            "products_api_key": "",
            "scheduler_settings": {
                "enabled": False,
                "interval_minutes": 30
            },
            "user_preferences": {
                "excluded_group_codes": []
            }
        }

        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(settings_data, f, ensure_ascii=False, indent=4)
            
            # Şifreyi keyring'e kaydet
            keyring.set_password(SERVICE_NAME, "sa", "sapass")
            
            self.status_bar.showMessage("FIRATSRV sunucusu için varsayılan ayarlar kaydedildi.", 3000)

        except Exception as e:
            self.status_bar.showMessage(f"Varsayılan ayarlar kaydedilemedi: {e}", 3000)

    def save_settings(self):
        '''
        Bağlantı ayarlarını, zamanlayıcı ayarlarını, kullanıcı filtre tercihlerini ve API anahtarını 
        settings.json dosyasına ve şifreyi keyring'e kaydeder.
        Bu fonksiyon artık Ayarlar sayfasındaki self.save_settings_button tarafından çağrılıyor.
        '''
        server_address = self.server_address_input.text()
        username = self.username_input.text()
        password = self.password_input.text()
        db_name = self.db_name_combo.currentText()
        api_key = self.api_key_input.text().strip() # API anahtarını al ve boşlukları temizle

        if not server_address or not username:
            QMessageBox.warning(self, "Eksik Bilgi", "Sunucu Adresi ve Kullanıcı Adı boş bırakılamaz.")
            return

        if not db_name or self.db_name_combo.currentIndex() == -1: 
             QMessageBox.warning(self, "Eksik Bilgi", "Lütfen bir veritabanı seçin veya listeleyin.")
             return

        settings_data = {
            "server_address": server_address,
            "username": username,
            "db_name": db_name,
            "products_api_key": api_key, # API anahtarını kaydet
            "scheduler_settings": {
                "enabled": self.scheduler_enabled_checkbox.isChecked(),
                "interval_minutes": self.scheduler_interval_spinbox.value(),
                # "auto_download_missing_images": self.auto_download_images_checkbox.isChecked() # Yeni ayarı kaydet - KALDIRILDI
            },
            "user_preferences": {
                "excluded_group_codes": self.excluded_group_codes_pref
            }
        }

        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(settings_data, f, ensure_ascii=False, indent=4)
            
            if username:
                keyring.set_password(SERVICE_NAME, username, password)
            
            QMessageBox.information(self, "Başarılı", "Tüm ayarlar başarıyla kaydedildi.")
            self.status_bar.showMessage("Tüm ayarlar kaydedildi.", 3000)

        except IOError:
            QMessageBox.critical(self, "Hata", f"Ayarlar {SETTINGS_FILE} dosyasına kaydedilirken bir hata oluştu.")
            self.status_bar.showMessage(f"Ayarlar {SETTINGS_FILE} dosyasına kaydedilemedi!", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Şifre kaydedilirken bir hata oluştu: {e}")
            self.status_bar.showMessage("Şifre kaydedilemedi!", 3000)

    def preview_product_data(self):
        if self.product_load_thread and self.product_load_thread.isRunning():
            QMessageBox.information(self, "İşlem Devam Ediyor", 
                                    "Ürün yükleme işlemi zaten devam ediyor. Lütfen tamamlanmasını bekleyin.")
            return

        self.status_bar.showMessage("Ürün verileri arka planda çekiliyor... Lütfen bekleyin.", 0) # 0 süresiz gösterir
        self.preview_data_button.setEnabled(False) # Butonu devre dışı bırak
        QApplication.processEvents() # Arayüzün güncellenmesini sağla

        self.product_load_thread = QThread(self)
        self.product_loader_worker = ProductLoaderWorker()
        self.product_loader_worker.moveToThread(self.product_load_thread)

        # Sinyal-slot bağlantıları
        self.product_load_thread.started.connect(self.product_loader_worker.run_loading)
        self.product_loader_worker.products_fetched.connect(self._on_products_loaded)
        self.product_loader_worker.error.connect(self._on_product_loading_error)
        self.product_loader_worker.finished.connect(self._on_product_loading_finished) # Bu önemli
        
        # Thread bittiğinde kendini ve worker'ı silmesi için (finished sinyali worker'dan da gelebilir)
        # Bu bağlantıyı _on_product_loading_finished içinde yapmak daha kontrollü olabilir.
        # self.product_load_thread.finished.connect(self.product_load_thread.deleteLater)
        # self.product_loader_worker.finished.connect(self.product_loader_worker.deleteLater)

        self.product_load_thread.start()

    def _on_products_loaded(self, product_list):
        """ProductLoaderWorker'dan ürünler başarıyla geldiğinde çağrılır."""
        self.all_fetched_product_data = product_list
        self.current_product_data = None 
        self.product_table.setRowCount(0)

        if self.all_fetched_product_data:
            self.status_bar.showMessage(f"{len(self.all_fetched_product_data)} adet ürün verisi çekildi. Tablo güncelleniyor...", 0)
            self._update_group_filter_list(self.all_fetched_product_data)
            self.apply_group_code_filter() # Bu _populate_product_table'ı çağıracak
            # populate_product_table sonrası mesaj apply_group_code_filter'da verilecek.
        else:
            QMessageBox.information(self, "Veri Yok", "Veritabanından ürün verisi çekilemedi veya hiç veri yok.")
            self.status_bar.showMessage("Ürün verisi çekilemedi.", 3000)
            self._update_group_filter_list(None)
            self.save_json_button.setEnabled(False)
            self.send_to_api_button.setEnabled(False)
            self.current_product_data = None
            self.product_table.setRowCount(0)
        
        # Yükleme butonu _on_product_loading_finished içinde etkinleştirilecek

    def _on_product_loading_error(self, error_message):
        """ProductLoaderWorker'dan hata sinyali geldiğinde çağrılır."""
        QMessageBox.critical(self, "Ürün Yükleme Hatası", error_message)
        self.status_bar.showMessage(f"Ürün yükleme hatası: {error_message}", 5000)
        # Hata durumunda da butonu aktif et ve thread referanslarını temizle
        self._cleanup_product_loader_thread()
        self.preview_data_button.setEnabled(True)

    def _on_product_loading_finished(self):
        """ProductLoaderWorker işini bitirdiğinde (başarılı veya başarısız) çağrılır."""
        # Bu slot, worker'ın finished sinyaline bağlı.
        # Durum çubuğundaki mesaj _on_products_loaded veya _on_product_loading_error'da zaten ayarlanmış olmalı.
        # Sadece thread'i ve worker'ı temizle, butonu aktif et.
        self._cleanup_product_loader_thread()
        self.preview_data_button.setEnabled(True)
        self.status_bar.showMessage("Ürün yükleme işlemi tamamlandı.", 3000) # Genel bir bitiş mesajı

    def _cleanup_product_loader_thread(self):
        """Product loader thread ve worker nesnelerini temizler."""
        if self.product_loader_worker:
            # self.product_loader_worker.deleteLater() # deleteLater bazen hemen olmaz, None atamak daha garanti
            self.product_loader_worker = None 
        if self.product_load_thread:
            if self.product_load_thread.isRunning():
                self.product_load_thread.quit()
                if not self.product_load_thread.wait(2000): # 2 saniye bekle
                    print("[MainWindow] Ürün yükleme thread'i zamanında durmadı, sonlandırılıyor...")
                    self.product_load_thread.terminate()
                    self.product_load_thread.wait() # Sonlandırmanın bitmesini bekle
            # self.product_load_thread.deleteLater()
            self.product_load_thread = None
        
    def save_previewed_data_to_json(self):
        # Bu fonksiyon Ürünler sayfasındaki self.save_json_button ile tetiklenir.
        if not self.current_product_data:
            self.status_bar.showMessage("Kaydedilecek ürün verisi bulunmuyor.", 3000)
            QMessageBox.warning(self, "Uyarı", "Kaydedilecek veri bulunmuyor. Lütfen önce verileri çekip filtreleyin.")
            return

        result_from_save_function = save_data_to_json(self.current_product_data, "onizlenen_filtrelenmis_urunler.json")
        
        if result_from_save_function:
            self.status_bar.showMessage(f"{len(self.current_product_data)} adet ürün başarıyla 'onizlenen_filtrelenmis_urunler.json' dosyasına kaydedildi.", 5000)
            QMessageBox.information(self, "Başarılı", f"{len(self.current_product_data)} adet ürün başarıyla JSON dosyasına kaydedildi.")
        else:
            self.status_bar.showMessage("Veriler JSON dosyasına kaydedilirken bir hata oluştu.", 5000)
            QMessageBox.critical(self, "Hata", "Veriler JSON dosyasına kaydedilemedi.")

    def send_data_to_api_action(self):
        # Bu fonksiyon Ürünler sayfasındaki self.send_to_api_button ile tetiklenir.
        if not self.current_product_data:
            QMessageBox.warning(self, "Uyarı", "Gönderilecek ürün verisi bulunmuyor.")
            return

        # İlerleme iletişim kutusunu oluştur ve göster
        progress_dialog = QProgressDialog("Veriler API'ye gönderiliyor...", "İptal", 0, 0, self) # 0, 0 belirsiz mod için
        progress_dialog.setWindowTitle("İşlem Sürüyor")
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal) # Diğer pencerelerle etkileşimi engelle
        progress_dialog.setAutoClose(True) # İşlem tamamlandığında otomatik kapan (setRange ile kullanılmazsa manuel kapatılmalı)
        progress_dialog.setMinimumDuration(0) # Hemen göster
        # progress_dialog.setValue(0) # Eğer setRange(0,0) ise setValue gereksiz veya etkisiz olabilir.
        progress_dialog.show()
        QApplication.processEvents() # İletişim kutusunun hemen çizilmesini sağla

        # api_url parametresini DEFAULT_API_URL ile gönderiyoruz
        success, message = send_data_to_web_api(self.current_product_data, api_url=DEFAULT_API_URL)

        progress_dialog.close() # İşlem bittiğinde iletişim kutusunu kapat

        log_file_abs_path = os.path.abspath(LOG_FILE)

        if success:
            QMessageBox.information(self, 
                                    "Başarılı", 
                                    f"{message}\n\nDetaylar için log dosyasına bakabilirsiniz: {log_file_abs_path}")
            self.status_bar.showMessage(f"API Yanıtı: {message}", 5000)
        else:
            QMessageBox.critical(self, 
                                 "API Gönderim Hatası", 
                                 f"Veriler web API'sine gönderilemedi.\nNeden: {message}\n\nLütfen log dosyasını kontrol edin: {log_file_abs_path}")
            self.status_bar.showMessage(f"API Gönderim Hatası: {message}", 8000)
        
        print(f"Log dosyası: {log_file_abs_path}") # Konsola da yazdıralım

    def apply_group_code_filter(self):
        # Bu fonksiyon Ürünler sayfasındaki self.apply_filter_button ile tetiklenir.
        # ve o sayfadaki self.group_code_list_widget'ı kullanır.
        if not self.all_fetched_product_data: # Ham veri yoksa filtreleme yapma
            self.status_bar.showMessage("Filtrelenecek ham ürün verisi bulunmuyor.", 3000)
            self.current_product_data = [] # Filtrelenmiş listeyi de boşalt
            self._populate_product_table(self.current_product_data)
            self.save_json_button.setEnabled(False)
            self.send_to_api_button.setEnabled(False)
            return
        
        selected_groups = []
        newly_excluded_groups = [] # Bu filtreleme sonucu hariç tutulacaklar
        for i in range(self.group_code_list_widget.count()):
            item = self.group_code_list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected_groups.append(item.text())
            else:
                newly_excluded_groups.append(item.text()) # İşaretsiz olanları kaydet
        
        # Kullanıcı tercihini güncelle
        self.excluded_group_codes_pref = newly_excluded_groups
        self._save_user_preferences() # Yeni metodu çağırarak ayarları kaydet

        if not selected_groups and self.group_code_list_widget.count() > 0: 
            self.status_bar.showMessage("Listelemek için en az bir grup kodu seçin. Tercihler kaydedildi.", 4000)
            self._populate_product_table([])
            return
        elif not self.group_code_list_widget.count() > 0:
             # Eğer hiç grup kodu yüklenmediyse (örn. ilk çalıştırma ve veri çekilmedi)
             # populate_product_table boş liste ile çağrılacak ve bir şey yapmayacak.
             # Ya da doğrudan self.current_product_data gösterilebilir (eğer varsa)
             # Şimdilik bir şey yapmıyoruz, tablo zaten boş olmalı veya apply_group_code_filter'ın başındaki
             # current_product_data kontrolü bunu yakalar.
             pass # Veya tabloyu boşalt: self._populate_product_table([])

        filtered_data = [
            product for product in self.all_fetched_product_data # Ham veriden filtrele
            if product.get('GRUP_KODU') in selected_groups
        ]
        
        if not selected_groups and self.group_code_list_widget.count() > 0: # Hiç grup seçilmemişse
            self.current_product_data = [] # Filtrelenmiş veriyi boşalt
        else: # Grup seçimi varsa veya hiç grup listesi yoksa (bu durumda tüm ham veri alınır)
            if not self.group_code_list_widget.count() > 0 and self.all_fetched_product_data:
                 # Hiç grup kodu filtresi yoksa ve ham veri varsa, tüm ham veriyi filtrelenmiş kabul et
                self.current_product_data = self.all_fetched_product_data[:]
            else:
                self.current_product_data = filtered_data

        # Verileri GRUP_KODU'na göre sırala
        if self.current_product_data:
            try:
                self.current_product_data.sort(key=lambda x: str(x.get('GRUP_KODU', '')).lower())
            except Exception as e:
                print(f"Sıralama hatası (Grup Kodu): {e}")

        self._populate_product_table(self.current_product_data)
        
        # Butonların durumunu güncelle
        has_data_to_process = bool(self.current_product_data)
        self.save_json_button.setEnabled(has_data_to_process)
        self.send_to_api_button.setEnabled(has_data_to_process)

        if not has_data_to_process and self.all_fetched_product_data:
            # Ham veri var ama filtre sonucu boş ise
            self.status_bar.showMessage(f"Filtre uygulandı. Gösterilecek ürün bulunamadı. (Hariç tutulanlar: {len(self.excluded_group_codes_pref)})", 5000)
        elif has_data_to_process:
            self.status_bar.showMessage(f"{len(self.current_product_data)} ürün listelendi. (Hariç tutulanlar: {len(self.excluded_group_codes_pref)})", 5000)
        # Eğer self.all_fetched_product_data da yoksa, preview_product_data'daki mesajlar geçerli olur.

    def _save_user_preferences(self):
        '''
        Kullanıcının grup kodu filtre tercihlerini settings.json dosyasına kaydeder.
        Var olan diğer ayarları korur.
        Bu, apply_group_code_filter içinde çağrılır.
        '''
        settings_data = {}
        try:
            # Var olan ayarları oku (bağlantı bilgileri vb. kaybolmasın diye)
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings_data = json.load(f)
        except FileNotFoundError:
            # Dosya yoksa, yeni oluşturulacak. DB ayarları daha önce kaydedilmiş olabilir veya olmayabilir.
            # Bu fonksiyon sadece kullanıcı tercihlerini ekler/günceller.
            pass 
        except json.JSONDecodeError:
            QMessageBox.warning(self, "Ayar Dosyası Hatası", 
                                f"{SETTINGS_FILE} okunamadı (bozuk olabilir). Tercihler kaydedilemedi.")
            return # Kaydetme işlemine devam etme

        # Kullanıcı tercihlerini güncelle veya ekle
        if "user_preferences" not in settings_data:
            settings_data["user_preferences"] = {}
        settings_data["user_preferences"]["excluded_group_codes"] = self.excluded_group_codes_pref

        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(settings_data, f, ensure_ascii=False, indent=4)
            # self.status_bar.showMessage("Filtre tercihleri başarıyla kaydedildi.", 3000) # Zaten apply_group_code_filter'da mesaj var
        except IOError:
            QMessageBox.critical(self, "Hata", 
                                 f"Filtre tercihleri {SETTINGS_FILE} dosyasına kaydedilirken bir hata oluştu.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", 
                                 f"Filtre tercihleri kaydedilirken beklenmedik bir hata oluştu: {e}")

    def _on_group_code_item_changed(self, item):
        """Bir grup kodu öğesinin işaret durumu değiştiğinde çağrılır ve renkini günceller."""
        # Bu self.group_code_list_widget (artık ürünler sayfasında) için geçerli.
        if item.checkState() == Qt.CheckState.Checked:
            item.setForeground(CHECKED_ITEM_COLOR)
        else:
            item.setForeground(UNCHECKED_ITEM_COLOR)

    # Uygulama kapanırken çalışan thread'i durdurmak için
    def closeEvent(self, event):
        if self.product_load_thread and self.product_load_thread.isRunning():
            print("Ürün yükleme işlemi durduruluyor...")
            if self.product_loader_worker:
                self.product_loader_worker.stop() # Worker'a durma sinyali gönder
            self.product_load_thread.quit()
            if not self.product_load_thread.wait(3000): # 3 saniye bekle
                print("Ürün yükleme thread'i zamanında durmadı, sonlandırılıyor...")
                self.product_load_thread.terminate()
                self.product_load_thread.wait() # Sonlandırmanın bitmesini bekle
            print("Ürün yükleme thread'i durduruldu.")
        super().closeEvent(event)

    def _populate_product_table(self, product_list):
        self.product_table.setRowCount(0)
        if not product_list:
            self.status_bar.showMessage("Tabloda gösterilecek ürün bulunamadı.", 3000)
            return
        headers = ["Stok Kodu", "Stok Adı", "Bakiye", "Satış Fiyatı 1", "Grup Kodu", "Barkod 1"]
        self.product_table.setColumnCount(len(headers))
        self.product_table.setHorizontalHeaderLabels(headers)
        for row_idx, product_data in enumerate(product_list):
            self.product_table.insertRow(row_idx)
            col_map = {
                "Stok Kodu": product_data.get('STOK_KODU', ''),
                "Stok Adı": product_data.get('STOK_ADI', ''),
                "Bakiye": to_decimal(product_data.get('BAKIYE', 0)),
                "Satış Fiyatı 1": format_currency_tr(to_decimal(product_data.get('SATIS_FIAT1', 0))),
                "Grup Kodu": product_data.get('GRUP_KODU', ''),
                "Barkod 1": product_data.get('BARKOD1', '')
            }
            for col_idx, header in enumerate(headers):
                item_value = col_map.get(header, '')
                item = QTableWidgetItem(str(item_value))
                if header == "Bakiye" or header == "Satış Fiyatı 1":
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                else:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self.product_table.setItem(row_idx, col_idx, item)
        self.product_table.resizeColumnsToContents()
        if self.product_table.rowCount() > 0:
            self.product_table.scrollToTop()


    def _show_enlarged_image(self, image_path):
        """Tıklanan resmi daha büyük bir diyalogda gösterir."""
        if not os.path.exists(image_path):
            QMessageBox.warning(self, "Resim Bulunamadı", f"Gösterilecek resim dosyası bulunamadı: {image_path}")
            return

        # Önceki diyalog varsa ve hala görünürse kapat
        if self.image_preview_dialog and self.image_preview_dialog.isVisible():
            self.image_preview_dialog.close()
            self.image_preview_dialog.deleteLater() # Bellekten temizle
            self.image_preview_dialog = None

        # Resim hakkında bilgi al (başlık için)
        stok_kodu_label = "Bilinmeyen Ürün"
        # ClickableImageLabel tıklandığında image_path gönderiyor.
        # image_path'ten stok kodunu veya adını almak zor olabilir.
        # Bu yüzden ClickableImageLabel'a ürün bilgilerini de ekleyebiliriz
        # ya da burada bir şekilde bulmaya çalışırız. Şimdilik genel bir başlık.
        
        # image_path'ten dosya adını al, "product_" ve uzantıyı kaldırarak stok kodunu bulmaya çalış
        base_name = os.path.basename(image_path)
        match = re.match(r"product_([a-zA-Z0-9_.-]+)\.(jpg|jpeg|png|gif|webp|bmp)", base_name, re.IGNORECASE)
        if match:
            stok_kodu_label = f"Ürün Kodu: {match.group(1)}"
        else:
            stok_kodu_label = base_name # Sadece dosya adını göster

        self.image_preview_dialog = ImagePreviewDialog(image_path, window_title=stok_kodu_label, parent=self)
        self.image_preview_dialog.show()


    def _find_download_and_save_image(self, stok_kodu: str, stok_adi: str, barkod: str):
        """Belirtilen ürün için resmi bulur, indirir ve kaydeder."""
        if not DUCKDUCKGO_SEARCH_AVAILABLE:
            QMessageBox.warning(self, "Özellik Kısıtlı", 
                                "'duckduckgo_search' kütüphanesi bulunamadı. Bu özellik kullanılamıyor.\n"
                                "Lütfen kurun: pip install duckduckgo-search")
            return

        if not stok_kodu:
            QMessageBox.warning(self, "Eksik Bilgi", "Resim aranacak ürün için stok kodu bulunamadı.")
            return

        self.status_bar.showMessage(f"'{stok_kodu}' için resim aranıyor...", 0)
        QApplication.processEvents() # Arayüzün güncellenmesini sağla

        image_url_found = None
        search_term_used = ""

        # 1. Barkod ile ara
        if barkod:
            search_term_used = barkod
            try:
                with DDGS() as ddgs:
                    results = ddgs.images(
                        keywords=barkod,
                        max_results=5  # Birkaç sonuç alalım, ilk uygun olanı seçeriz
                    )
                    if results:
                        for res_idx, res in enumerate(results):
                            url = res.get('image')
                            if url:
                                print(f"Barkod ({barkod}) için {res_idx+1}. URL bulundu: {url}")
                                # Burada URL'yi doğrudan indirmeye çalışmadan önce
                                # basit bir kontrol yapılabilir (örn. çok kısa mı, bilinen bir placeholder mı)
                                # Şimdilik ilk bulduğumuzu alıyoruz.
                                image_url_found = url
                                break 
            except Exception as e:
                print(f"'{barkod}' ile DuckDuckGo barkod arama hatası: {e}")
                self.status_bar.showMessage(f"'{barkod}' ile arama hatası: {e}", 5000)


        # 2. Ürün adı ile ara (barkodla bulunamazsa veya barkod yoksa)
        if not image_url_found and stok_adi:
            # clean_product_name artık import edilmiyor, bu yüzden bu satırı yorumlayalım veya stok_adi'ni doğrudan kullanalım
            # cleaned_name = clean_product_name(stok_adi)
            cleaned_name = stok_adi # Geçici olarak doğrudan stok_adi kullanılıyor
            search_term_used = cleaned_name + " ürün"
            try:
                with DDGS() as ddgs:
                    results = ddgs.images(
                        keywords=search_term_used,
                        max_results=5
                    )
                    if results:
                        for res_idx, res in enumerate(results):
                            url = res.get('image')
                            if url:
                                print(f"Ürün adı ({search_term_used}) için {res_idx+1}. URL bulundu: {url}")
                                image_url_found = url
                                break
            except Exception as e:
                print(f"'{search_term_used}' ile DuckDuckGo ürün adı arama hatası: {e}")
                self.status_bar.showMessage(f"'{search_term_used}' ile arama hatası: {e}", 5000)
        
        if image_url_found:
            self.status_bar.showMessage(f"'{stok_kodu}' için resim bulundu, indiriliyor: {image_url_found[:70]}...", 0)
            QApplication.processEvents()
            
            # save_image_from_url artık import edilmiyor, bu yüzden bu çağrıyı yorumlayalım.
            # saved_image_path = save_image_from_url(image_url_found, stok_kodu)
            saved_image_path = None # Geçici olarak None atayalım

            if saved_image_path:
                QMessageBox.information(self, "Başarılı", 
                                        f"'{stok_kodu}' için resim başarıyla bulundu ve '{os.path.basename(saved_image_path)}' olarak kaydedildi.")
                self.status_bar.showMessage(f"Resim '{os.path.basename(saved_image_path)}' olarak kaydedildi.", 5000)
                # Tabloyu yenilemek için veriyi yeniden çekip filtrelemek yerine sadece
                # mevcut verilerle tabloyu yeniden oluşturabiliriz veya sadece o satırı güncelleyebiliriz.
                # Şimdilik tüm tabloyu mevcut filtrelenmiş veriyle yenileyelim.
            else:
                # save_image_from_url içinde hata mesajı zaten gösterilmiş olabilir (log veya print ile)
                QMessageBox.warning(self, "İndirme Hatası", 
                                    f"'{stok_kodu}' için resim URL'si bulundu ({image_url_found}) ancak indirilemedi veya kaydedilemedi.\n"
                                    "Lütfen internet bağlantınızı ve konsol loglarını kontrol edin.")
                self.status_bar.showMessage(f"'{stok_kodu}' için resim indirilemedi/kaydedilemedi.", 5000)
        else:
            QMessageBox.information(self, "Bulunamadı", 
                                    f"'{stok_kodu}' (Arama: '{search_term_used}') için DuckDuckGo'da uygun bir resim bulunamadı.")
            self.status_bar.showMessage(f"'{stok_kodu}' için resim bulunamadı.", 5000)

    def _select_all_groups(self):
        """Tüm grup kodlarını seçer ve renklerini günceller."""
        self.group_code_list_widget.blockSignals(True)  # Sinyalleri geçici olarak engelle
        for i in range(self.group_code_list_widget.count()):
            item = self.group_code_list_widget.item(i)
            item.setCheckState(Qt.CheckState.Checked)
            item.setForeground(CHECKED_ITEM_COLOR)
        self.group_code_list_widget.blockSignals(False)  # Sinyalleri tekrar etkinleştir
        self.status_bar.showMessage("Tüm grup kodları seçildi.", 2000)

    def _deselect_all_groups(self):
        """Tüm grup kodlarının seçimini kaldırır ve renklerini günceller."""
        self.group_code_list_widget.blockSignals(True)  # Sinyalleri geçici olarak engelle
        for i in range(self.group_code_list_widget.count()):
            item = self.group_code_list_widget.item(i)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setForeground(UNCHECKED_ITEM_COLOR)
        self.group_code_list_widget.blockSignals(False)  # Sinyalleri tekrar etkinleştir
        self.status_bar.showMessage("Tüm grup kodlarının seçimi kaldırıldı.", 2000)

    def _create_customers_page_from_module(self): # <<< YENİ METOT
        # CustomersPage'e self (MainWindow instance) parent olarak veriliyor.
        # Bu sayede CustomersPage içinden MainWindow'un status_bar gibi elemanlarına erişilebilir.
        self.customers_page_widget = CustomersPage(parent=self)
        self.stacked_widget.addWidget(self.customers_page_widget)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 