'''
Ana Arayüz Modülü
'''
import sys
import json
import keyring
import pyodbc
import os
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
    QSpinBox
)
from PySide6.QtGui import QIcon, QFont, QScreen, QAction, QColor
from PySide6.QtCore import Qt

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

SERVICE_NAME = "B2B_App_DB_Credentials"
SETTINGS_FILE = "settings.json"

PRODUCT_DATA_HEADERS = ["Stok Kodu", "Stok Adı", "Bakiye", "Satış Fiyatı 1", "Grup Kodu", "Barkod 1"]

# Renk Tanımlamaları
CHECKED_ITEM_COLOR = QColor("black")      # İşaretli öğeler için varsayılan renk
UNCHECKED_ITEM_COLOR = QColor("gray")     # İşaretsiz öğeler için gri renk

# JSON dosyasının adı (data_extractor.py'deki ile aynı olmalı)
LAST_PREVIEWED_JSON_FILE = "onizlenen_filtrelenmis_urunler.json"

class MainWindow(QMainWindow):
    '''
    Ana uygulama penceresi.
    '''
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Veritabanı Yönetim Paneli")
        self.all_fetched_product_data = None # Veritabanından çekilen tüm ham ürünler
        self.current_product_data = None     # Filtrelenmiş, tabloda gösterilen ve işlem yapılacak ürünler
        self.excluded_group_codes_pref = []

        self.setup_ui_appearance()
        self._create_menu_bar()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_app_layout = QHBoxLayout(central_widget)
        main_app_layout.setContentsMargins(10, 10, 10, 10) # Kenar boşlukları biraz azaltıldı
        main_app_layout.setSpacing(10)

        # --- Sol Panel (Grup Kodu Filtresi) ---
        left_panel_widget = QWidget() # Sol panel için bir QWidget
        left_panel_layout = QVBoxLayout(left_panel_widget)
        left_panel_layout.setContentsMargins(5, 5, 5, 5)
        left_panel_layout.setSpacing(10)
        
        filter_label = QLabel("Grup Kodu Filtresi:")
        left_panel_layout.addWidget(filter_label)

        self.group_code_list_widget = QListWidget()
        left_panel_layout.addWidget(self.group_code_list_widget, 1)
        self.group_code_list_widget.itemChanged.connect(self._on_group_code_item_changed)

        self.apply_filter_button = QPushButton("Filtreyi Uygula")
        self.apply_filter_button.clicked.connect(self.apply_group_code_filter)
        left_panel_layout.addWidget(self.apply_filter_button)

        left_panel_widget.setMinimumWidth(180)
        left_panel_widget.setMaximumWidth(250) # Sol panele bir genişlik sınırı
        main_app_layout.addWidget(left_panel_widget, 0) # Sol panel genişlemesin (stretch faktörü 0)

        # --- Sağ Panel (Ana İçerik) ---
        right_panel_widget = QWidget()
        right_panel_layout = QVBoxLayout(right_panel_widget)
        right_panel_layout.setContentsMargins(5, 5, 5, 5)
        right_panel_layout.setSpacing(10)

        # --- Sağ Üst Köşeye Çıkış Butonu --- (YENİ)
        exit_button_bar_layout = QHBoxLayout()
        exit_button_bar_layout.addStretch(1) # Butonu sağa itmek için stretch
        self.top_right_exit_button = QPushButton("Çıkış")
        self.top_right_exit_button.setToolTip("Uygulamayı Kapat (Ctrl+Q)")
        self.top_right_exit_button.setFixedSize(80, 28) # Butona sabit bir boyut verelim
        self.top_right_exit_button.clicked.connect(self.close)
        exit_button_bar_layout.addWidget(self.top_right_exit_button)
        right_panel_layout.addLayout(exit_button_bar_layout) # Sağ panelin en üstüne ekle

        # Bağlantı Ayarları Formu (Sağ Panele Taşındı)
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
        right_panel_layout.addLayout(form_layout)

        # --- Zamanlayıcı Ayarları (Bağlantı Ayarlarının Altına) ---
        scheduler_group_label = QLabel("Otomatik Ürün Güncelleme Ayarları:")
        scheduler_group_label.setStyleSheet("font-weight: bold; margin-top: 10px;") # Biraz boşluk ve vurgu
        right_panel_layout.addWidget(scheduler_group_label)

        scheduler_form_layout = QFormLayout()
        scheduler_form_layout.setHorizontalSpacing(10)
        scheduler_form_layout.setVerticalSpacing(10)

        self.scheduler_enabled_checkbox = QCheckBox("Otomatik Güncellemeyi Etkinleştir")
        scheduler_form_layout.addRow(self.scheduler_enabled_checkbox)

        self.scheduler_interval_spinbox = QSpinBox()
        self.scheduler_interval_spinbox.setMinimum(15)    # Minimum 15 dakika
        self.scheduler_interval_spinbox.setMaximum(1440)  # Maksimum 24 saat (1440 dakika)
        self.scheduler_interval_spinbox.setValue(30)      # Varsayılan 30 dakika
        self.scheduler_interval_spinbox.setSuffix(" dakika")
        scheduler_form_layout.addRow(QLabel("Güncelleme Sıklığı:"), self.scheduler_interval_spinbox)
        
        right_panel_layout.addLayout(scheduler_form_layout)
        # --- Zamanlayıcı Ayarları Sonu ---

        # Ana Kontrol Butonları (Sağ Panele Taşındı)
        control_buttons_layout = QHBoxLayout()
        self.save_button = QPushButton("Tüm Ayarları Kaydet")
        self.save_button.clicked.connect(self.save_settings)
        control_buttons_layout.addWidget(self.save_button)
        control_buttons_layout.addStretch()
        right_panel_layout.addLayout(control_buttons_layout)

        # Veri Çekme Butonları (Sağ Panele Taşındı)
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
        right_panel_layout.addLayout(data_action_layout)

        # Ürün Veri Tablosu (Sağ Panele Taşındı)
        self.product_table = QTableWidget()
        self.product_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers) 
        self.product_table.setAlternatingRowColors(True)
        self.product_table.setSortingEnabled(True) # Sütun sıralamayı etkinleştir
        right_panel_layout.addWidget(self.product_table, 1) # Tablo sağ panelde dikeyde genişlesin

        main_app_layout.addWidget(right_panel_widget, 1) # Sağ panel genişlesin (stretch faktörü 1)

        # Durum Çubuğu (QMainWindow'a ait, layout'a eklenmez)
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Hazır.")

        self.load_settings()
        
        # Başlangıçta tam ekran yerine normal boyutta ve ortalanmış göster
        self.show() # Önce pencereyi göster
        screen = QApplication.primaryScreen()
        if screen:
            available_geometry = screen.availableGeometry()
            # Varsayılan bir başlangıç boyutu (örneğin, setup_ui_appearance içindeki minimum boyutlar veya kullanılabilir alanın bir yüzdesi)
            # self.setMinimumSize(1000, 700) zaten setup_ui_appearance içinde ayarlı
            # İstersek buradaki minimum boyutları kullanabilir veya yeni bir yüzde belirleyebiliriz.
            initial_width = self.minimumWidth() # veya int(available_geometry.width() * 0.75)
            initial_height = self.minimumHeight() # veya int(available_geometry.height() * 0.75)
            self.resize(initial_width, initial_height)
            
            frame_geometry = self.frameGeometry()
            frame_geometry.moveCenter(available_geometry.center())
            self.move(frame_geometry.topLeft())
        else: # Ekran bilgisi alınamazsa, sadece göster
            self.resize(1000,700) # Varsayılan bir boyut
            # self.show() zaten yukarıda çağrıldı.

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

    def load_settings(self):
        '''
        Kaydedilmiş ayarları settings.json ve keyring'den yükler.
        Kullanıcı tercihleri (hariç tutulan grup kodları) ve zamanlayıcı ayarlarını da yükler.
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
                username_for_keyring = settings_data.get("username")
                if username_for_keyring:
                    password = keyring.get_password(SERVICE_NAME, username_for_keyring)
                    if password:
                        self.password_input.setText(password)
                
                user_prefs = settings_data.get("user_preferences", {})
                self.excluded_group_codes_pref = user_prefs.get("excluded_group_codes", [])

                scheduler_settings = settings_data.get("scheduler_settings", {})
                self.scheduler_enabled_checkbox.setChecked(scheduler_settings.get("enabled", False))
                self.scheduler_interval_spinbox.setValue(scheduler_settings.get("interval_minutes", 30))

                self.status_bar.showMessage("Ayarlar, kullanıcı tercihleri ve zamanlayıcı ayarları yüklendi.", 3000)
        
        except FileNotFoundError:
            self.status_bar.showMessage(f"{SETTINGS_FILE} bulunamadı. İlk çalıştırma olabilir.", 3000)
            self.excluded_group_codes_pref = []
            self.scheduler_enabled_checkbox.setChecked(False)
            self.scheduler_interval_spinbox.setValue(30)
        except Exception as e:
            QMessageBox.warning(self, "Ayarlar Yüklenemedi", f"Ayarlar yüklenirken bir hata oluştu: {e}")
            self.status_bar.showMessage("Ayarlar yüklenemedi!", 3000)
            self.excluded_group_codes_pref = []
            self.scheduler_enabled_checkbox.setChecked(False)
            self.scheduler_interval_spinbox.setValue(30)
        finally:
            # Ayarlar yüklendikten sonra (veya hata durumunda bile) grup filtresini dosyadan doldurmayı dene
            # ve tabloyu başlangıçta boşalt/güncelle.
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
        
        # Başlangıçta tablo boş olsun veya apply_group_code_filter() ile dolacaksa o karar versin.
        # Şimdilik tabloyu boşaltalım, veri çekilince dolsun.
        if not initial_data_loaded: # Eğer dosyadan veri yüklenmediyse tabloyu kesin boşalt
             self.current_product_data = None
             self.all_fetched_product_data = None # Başlangıçta ham veri de yok
             self.product_table.setRowCount(0)
             self.save_json_button.setEnabled(False)
             self.send_to_api_button.setEnabled(False)

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
        server = self.server_address_input.text()
        user = self.username_input.text()
        password = self.password_input.text() 

        if not server or not user:
            QMessageBox.warning(self, "Eksik Bilgi", "Sunucu Adresi ve Kullanıcı Adı girilmelidir.")
            return

        self.status_bar.showMessage(f"{server} sunucusundaki veritabanları listeleniyor...", 3000)

        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};" +
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

    def save_settings(self):
        '''
        Bağlantı ayarlarını, zamanlayıcı ayarlarını ve kullanıcı filtre tercihlerini settings.json dosyasına 
        ve şifreyi keyring'e kaydeder.
        '''
        server_address = self.server_address_input.text()
        username = self.username_input.text()
        password = self.password_input.text()
        db_name = self.db_name_combo.currentText()

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
            "scheduler_settings": {
                "enabled": self.scheduler_enabled_checkbox.isChecked(),
                "interval_minutes": self.scheduler_interval_spinbox.value()
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
        self.status_bar.showMessage("Ürün verileri çekiliyor...", 5000)
        QApplication.processEvents()

        db_conn = get_data_db_connection()

        if db_conn:
            # fetch_product_data artık excluded_groups parametresi almıyor (background için eklendi)
            # GUI'deki fetch her zaman tümünü çekmeli, filtreleme sonra yapılır.
            self.all_fetched_product_data = fetch_product_data(db_conn) 
            db_conn.close() 
            
            self.current_product_data = None 
            self.product_table.setRowCount(0)

            if self.all_fetched_product_data is not None:
                self.status_bar.showMessage(f"{len(self.all_fetched_product_data)} adet ham ürün verisi çekildi.", 5000)
                
                # Grup kodu filtresini doldur (ham veriye göre)
                self._update_group_filter_list(self.all_fetched_product_data) # Yeni yardımcı fonksiyonu kullan

                # Filtreyi başlangıçta uygula (artık grup kodları yüklendi)
                self.apply_group_code_filter() 
            else:
                QMessageBox.information(self, "Veri Yok", "Veritabanından ürün verisi çekilemedi veya hiç veri yok.")
                self.status_bar.showMessage("Ürün verisi çekilemedi.", 3000)
                self._update_group_filter_list(None) # Veri yoksa filtreyi temizle/boş göster
                self.save_json_button.setEnabled(False)
                self.send_to_api_button.setEnabled(False)
                self.current_product_data = None # Emin olmak için
                self.product_table.setRowCount(0)
        else:
            QMessageBox.critical(self, "Bağlantı Hatası", "Veritabanı bağlantısı kurulamadı. Lütfen ayarları kontrol edin.")
            self.status_bar.showMessage("Veritabanı bağlantısı başarısız!", 3000)
            self._update_group_filter_list(None) # Bağlantı yoksa filtreyi temizle/boş göster
            self.save_json_button.setEnabled(False)
            self.send_to_api_button.setEnabled(False)
            self.current_product_data = None
            self.product_table.setRowCount(0)

    def _populate_product_table(self, product_list):
        self.product_table.setRowCount(0)
        if not product_list:
            return

        self.product_table.setRowCount(len(product_list))
        self.product_table.setColumnCount(len(PRODUCT_DATA_HEADERS))
        self.product_table.setHorizontalHeaderLabels(PRODUCT_DATA_HEADERS)

        for row_idx, product_dict in enumerate(product_list):
            stok_kodu = product_dict.get('STOK_KODU', '')
            self.product_table.setItem(row_idx, 0, QTableWidgetItem(str(stok_kodu)))
            
            stok_adi = product_dict.get('STOK_ADI', '')
            self.product_table.setItem(row_idx, 1, QTableWidgetItem(str(stok_adi)))
            
            bakiye = product_dict.get('BAKIYE')
            bakiye_str = format_currency_tr(bakiye, decimal_places=2, currency_symbol='') if bakiye is not None else ""
            item_bakiye = QTableWidgetItem(bakiye_str)
            item_bakiye.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.product_table.setItem(row_idx, 2, item_bakiye)

            satis_fiyat1 = product_dict.get('SATIS_FIAT1')
            satis_fiyat1_str = format_currency_tr(satis_fiyat1, currency_symbol='') if satis_fiyat1 is not None else ""
            item_satis_fiyat1 = QTableWidgetItem(satis_fiyat1_str)
            item_satis_fiyat1.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.product_table.setItem(row_idx, 3, item_satis_fiyat1)

            grup_kodu = product_dict.get('GRUP_KODU', '')
            self.product_table.setItem(row_idx, 4, QTableWidgetItem(str(grup_kodu)))

            barkod1 = product_dict.get('BARKOD1', '')
            self.product_table.setItem(row_idx, 5, QTableWidgetItem(str(barkod1)))

        self.product_table.resizeColumnsToContents()

    def save_previewed_data_to_json(self):
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
        """Bir grup kodu öğesinin işaret durumu değiştiğinde çağrılır ve rengini günceller."""
        if item.checkState() == Qt.CheckState.Checked:
            item.setForeground(CHECKED_ITEM_COLOR)
        else:
            item.setForeground(UNCHECKED_ITEM_COLOR)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 