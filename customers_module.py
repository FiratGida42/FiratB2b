from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLabel,
    QMessageBox,
    QApplication,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QSplitter,
    QFileDialog
)
from PySide6.QtCore import Qt
from data_extractor import fetch_customer_summary, get_db_connection # get_db_connection da gerekebilir
from helpers import format_currency_tr, to_decimal # Bakiye formatlama için
import json # Eklendi
from decimal import Decimal # Eklendi
import copy # Eklendi
import os # Eklendi
import logging # Eklendi

# Bu modül için logger oluştur
logger = logging.getLogger(__name__)
# Eğer ana uygulamada basicConfig yapılmadıysa ve DEBUG logları konsolda görünsün isteniyorsa:
# logging.basicConfig(level=logging.DEBUG) # Bu satır genellikle ana scriptte bir kere yapılır.

class NumericTableWidgetItem(QTableWidgetItem):
    def __init__(self, numeric_value, display_text):
        super().__init__(display_text) # DisplayRole için metni ayarlar
        self.numeric_value = numeric_value # Asıl sayısal değeri sakla

    def __lt__(self, other):
        if isinstance(other, NumericTableWidgetItem):
            # numeric_value None olabilir, bu durumu ele almamız gerekebilir
            # Şimdilik None olmadığını varsayalım ya da Decimal ise karşılaştırılabilir
            if self.numeric_value is None and other.numeric_value is None:
                return False # İkisi de None ise eşit kabul edilebilir (sıralama için)
            if self.numeric_value is None:
                return True # None değerler en küçük kabul edilsin (veya False en büyük)
            if other.numeric_value is None:
                return False # Diğeri None ise bu ondan büyük (veya True küçük)
            return self.numeric_value < other.numeric_value
        return super().__lt__(other) # Farklı türler için varsayılan karşılaştırma

class CustomersPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.all_customers_data = [] # Tüm carileri tutmak için
        self.currently_displayed_data = [] # Tabloda o an gösterilen filtrelenmiş veriyi tutmak için
        self.db_connection = None # Kalıcı bağlantı için
        self.filter_settings_file = "customers_filter_settings.json" # Ayar dosyası adı
        # logger.debug(f"Ayar dosyası yolu: {os.path.abspath(self.filter_settings_file)}")
        logger.info(f"Ayar dosyası yolu: {os.path.abspath(self.filter_settings_file)}") # INFO seviyesine çekildi
        self._setup_ui()
        self._ensure_db_connection() # Başlangıçta bağlantıyı kurmayı dene
        # self.load_customer_data() # Başlangıçta tüm veriyi yüklemek için refresh_all_data kullanılacak

    def _ensure_db_connection(self):
        if not self.db_connection or self.db_connection.closed:
            self.db_connection = get_db_connection(caller_info="CustomersPage")
            if not self.db_connection:
                if self.parent_window and hasattr(self.parent_window, 'status_bar'):
                    self.parent_window.status_bar.showMessage("Cari modülü: Veritabanı bağlantısı kurulamadı!", 5000)
                QMessageBox.critical(self, "Veritabanı Hatası", 
                                     "Cari modülü için veritabanı bağlantısı kurulamadı. Lütfen ana ayarlardan bağlantıyı kontrol edin.")
            elif self.parent_window and hasattr(self.parent_window, 'status_bar'):
                 self.parent_window.status_bar.showMessage("Cari modülü: Veritabanı bağlantısı hazır.", 2000)
        return self.db_connection

    def _setup_ui(self):
        # Ana layout (yatayda splitter ile ikiye bölünecek)
        main_horizontal_layout = QHBoxLayout(self)
        self.splitter = QSplitter(Qt.Orientation.Horizontal) # Yatay splitter

        # Sol Taraf: Grup Kodu Filtresi
        left_panel_widget = QWidget()
        left_layout = QVBoxLayout(left_panel_widget)
        left_layout.setContentsMargins(5, 5, 5, 5)
        left_layout.setSpacing(5)
        
        self.group_code_label = QLabel("Grup Kodları Filtresi:")
        self.group_code_list_widget = QListWidget()
        self.group_code_list_widget.setSelectionMode(QListWidget.SelectionMode.MultiSelection) # Çoklu seçim
        self.group_code_list_widget.itemSelectionChanged.connect(self.on_group_code_selection_changed)
        
        left_layout.addWidget(self.group_code_label)
        left_layout.addWidget(self.group_code_list_widget)
        left_panel_widget.setMinimumWidth(200) # Sol panele minimum genişlik verildi
        
        self.splitter.addWidget(left_panel_widget)

        # Sağ Taraf: Arama, Tablo ve Butonlar
        right_panel_widget = QWidget()
        right_layout = QVBoxLayout(right_panel_widget)
        right_layout.setContentsMargins(5, 5, 5, 5)
        right_layout.setSpacing(10)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Cari Kodu veya Adı ile ara...")
        self.search_input.textChanged.connect(self.filter_table_by_search)
        search_layout.addWidget(self.search_input)
        right_layout.addLayout(search_layout)

        self.customers_table = QTableWidget()
        self.customers_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.customers_table.setAlternatingRowColors(True)
        self.customers_table.setSortingEnabled(True)
        self.customers_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        right_layout.addWidget(self.customers_table, 1)

        action_layout = QHBoxLayout()
        self.load_button = QPushButton("Carileri Yenile/Yükle")
        self.load_button.clicked.connect(self.refresh_all_data)
        action_layout.addWidget(self.load_button)

        self.save_json_button = QPushButton("JSON Olarak Kaydet") # Yeni buton
        self.save_json_button.clicked.connect(self.save_displayed_data_to_json) # Sinyal bağlantısı
        action_layout.addWidget(self.save_json_button) # Layout'a ekle

        action_layout.addStretch()
        right_layout.addLayout(action_layout)
        
        self.splitter.addWidget(right_panel_widget)
        main_horizontal_layout.addWidget(self.splitter)
        # Splitter'ın başlangıç boyutlarını ayarla (sol panel: 200, sağ panel: kalan)
        # self.splitter.setSizes([200, self.width() - 200 - main_horizontal_layout.spacing()]) # Dinamik ayar için
        self.splitter.setSizes([200, 800]) # Başlangıç boyutları güncellendi

    def refresh_all_data(self):
        if not self._ensure_db_connection(): # Bağlantıyı kontrol et/kur
            return

        if self.parent_window and hasattr(self.parent_window, 'status_bar'):
            self.parent_window.status_bar.showMessage("Cari verileri yükleniyor...", 0) # Süresiz
        QApplication.processEvents() # Arayüzün güncellenmesini sağla

        # fetch_customer_summary db_conn parametresi ile çağrılıyor
        fetched_data = fetch_customer_summary(db_conn=self.db_connection)

        if fetched_data is not None:
            self.all_customers_data = fetched_data
            self.populate_group_codes_filter() # Grup kodlarını doldur
            self.load_filter_settings()      # Kayıtlı filtreleri yükle
            self.apply_filters() # Filtreleri uygula (bu tabloyu da doldurur)

            # JSON dosyasını otomatik olarak kaydet
            if self.currently_displayed_data:
                logger.info("Veriler yenilendi, filtrelenen_cariler.json otomatik olarak güncelleniyor.")
                self.save_displayed_data_to_json(silent=True) # Sessiz kaydet
            else:
                logger.info("Yenileme sonrası gösterilecek filtrelenmiş cari verisi bulunmadığından JSON dosyası güncellenmedi.")

            if self.parent_window and hasattr(self.parent_window, 'status_bar'):
                # Kullanıcıya hem yükleme hem de dosya güncelleme bilgisini tek mesajda verelim.
                message = f"{len(self.all_customers_data)} cari kaydı yüklendi."
                if self.currently_displayed_data: # Eğer json güncellendiyse mesaja ekle
                    message += " Web için senkronizasyon dosyası güncellendi."
                else:
                    message += " Web için senkronizasyon dosyası güncellenmedi (filtrelenmiş veri yok)."
                self.parent_window.status_bar.showMessage(message, 5000)
        else:
            self.customers_table.setRowCount(0)
            self.customers_table.setColumnCount(0)
            msg = "Cari verileri çekilemedi. Veritabanı bağlantısını veya logları kontrol edin."
            if self.parent_window and hasattr(self.parent_window, 'status_bar'):
                self.parent_window.status_bar.showMessage(msg, 5000)
            QMessageBox.warning(self, "Veri Yükleme Hatası", msg)

    def populate_table(self, data_to_show):
        self.customers_table.setRowCount(0) # Önce tabloyu temizle
        self.currently_displayed_data = data_to_show # Gösterilecek veriyi sakla
        
        if not data_to_show:
            self.customers_table.setColumnCount(0) # Başlıkları da temizle
            return

        # Sütun başlıklarını veriden al (fetch_customer_summary dict listesi döndürür)
        # İlk satırın anahtarlarını başlık olarak kullan
        headers_map = {
            "CARI_KOD": "Cari Kodu",
            "CARI_ISIM": "Cari İsim",
            "BORC_BAKIYESI": "Borç Bakiyesi",
            "ALACAK_BAKIYESI": "Alacak Bakiyesi",
            "NET_BAKIYE": "Net Bakiye",
            "GRUP_KODU": "Grup Kodu"
        }
        # Verideki sırayla başlıkları al, map'te varsa onu kullan, yoksa orijinal adı kullan
        actual_headers_from_data = list(data_to_show[0].keys())
        display_headers = [headers_map.get(h, h) for h in actual_headers_from_data]

        self.customers_table.setColumnCount(len(display_headers))
        self.customers_table.setHorizontalHeaderLabels(display_headers)

        for row_idx, customer_data in enumerate(data_to_show):
            self.customers_table.insertRow(row_idx)
            for col_idx, header_key in enumerate(actual_headers_from_data):
                raw_value = customer_data.get(header_key)
                item_value_str = ""
                item = QTableWidgetItem()

                if header_key in ["BORC_BAKIYESI", "ALACAK_BAKIYESI", "NET_BAKIYE"]:
                    decimal_value = to_decimal(raw_value)
                    item_value_str = format_currency_tr(decimal_value)
                    item = NumericTableWidgetItem(decimal_value, item_value_str)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                else:
                    item_value_str = str(raw_value if raw_value is not None else "")
                    item = QTableWidgetItem(item_value_str)
                
                self.customers_table.setItem(row_idx, col_idx, item)

        self.customers_table.resizeColumnsToContents()
        if self.customers_table.columnCount() > 1:
             self.customers_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch) # Cari İsmi genişlesin
        
        # Tablo dolduktan sonra status bar mesajını güncelle (opsiyonel, apply_filters'da yapılabilir)
        # if self.parent_window and hasattr(self.parent_window, 'status_bar'):
        #     self.parent_window.status_bar.showMessage(f"{len(data_to_show)} kayıt gösteriliyor.", 2000)

    def save_displayed_data_to_json(self, silent=False):
        if not self.currently_displayed_data:
            if not silent: # Sadece sessiz değilse mesaj göster
                QMessageBox.information(self, "Bilgi", "Kaydedilecek veri bulunmuyor. Lütfen önce carileri yükleyin ve filtreleyin.")
            else:
                logger.info("Kaydedilecek filtrelenmiş cari verisi bulunmuyor (otomatik kaydetme).")
            return

        file_path = "filtrelenen_cariler.json" 

        self.save_filter_settings()
        logger.info("JSON kaydetme işlemi öncesinde filtre ayarları da kaydedildi.")

        data_to_save = copy.deepcopy(self.currently_displayed_data)
        
        for item in data_to_save: 
            for key, value in item.items():
                if isinstance(value, Decimal):
                    item[key] = str(value)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=4)
            
            logger.info(f"Veriler başarıyla {file_path} dosyasına kaydedildi (silent={silent}).") # Log mesajı eklendi
            if not silent: # Sadece sessiz değilse mesaj göster
                QMessageBox.information(self, "Başarılı", f"Veriler başarıyla {file_path} dosyasına kaydedildi.")

        except IOError as e:
            logger.error(f"Dosya kaydedilirken IO Hatası (dosya: {file_path}): {e}", exc_info=True) # Log eklendi
            if not silent:
                QMessageBox.critical(self, "Kayıt Hatası", f"Dosya kaydedilirken bir hata oluştu: {e}")
        except Exception as e:
            logger.error(f"Dosya kaydedilirken beklenmedik hata (dosya: {file_path}): {e}", exc_info=True) # Log eklendi
            if not silent:
                QMessageBox.critical(self, "Kayıt Hatası", f"Beklenmedik bir hata oluştu: {e}")

    def filter_table_by_search(self):
        # Bu fonksiyon doğrudan tabloyu doldurmak yerine apply_filters'ı çağıracak
        self.apply_filters()
        # search_text = self.search_input.text().lower().strip()
        # if not self.all_customers_data:
        #     return

        # if not search_text:
        #     self.populate_table(self.all_customers_data)
        #     return

        # filtered_data = []
        # for customer in self.all_customers_data:
        #     kod = str(customer.get("CARI_KOD", "")).lower()
        #     isim = str(customer.get("CARI_ISIM", "")).lower()
        #     if search_text in kod or search_text in isim:
        #         filtered_data.append(customer)
        
        # self.populate_table(filtered_data)
        # if self.parent_window and hasattr(self.parent_window, 'status_bar'):
        #     self.parent_window.status_bar.showMessage(f"{len(filtered_data)} cari bulundu.", 2000)

    def populate_group_codes_filter(self):
        self.group_code_list_widget.clear()
        if not self.all_customers_data:
            return

        unique_group_codes = set()
        has_empty_group_code_customers = False
        for customer in self.all_customers_data:
            code = str(customer.get("GRUP_KODU", "") or "").strip()
            if code:
                unique_group_codes.add(code)
            else:
                has_empty_group_code_customers = True
        
        all_group_codes_for_list = sorted(list(unique_group_codes))

        if has_empty_group_code_customers:
            # "[Boş]" seçeneğini belirli bir yerde (örneğin, listenin başında veya sonunda)
            # veya alfabetik sırada istiyorsanız, ona göre ekleyebilirsiniz.
            # Şimdilik alfabetik sıraya dahil olması için normal listeye ekleyip tekrar sıralıyoruz
            # veya özel bir sabit isimle en başa/sona ekleyebiliriz.
            # Kullanıcı "Boş ADI ALTINDA" dediği için bunu bir grup adı gibi düşünüp
            # alfabetik sıraya dahil edebiliriz ya da özel bir kategori olarak en üste koyabiliriz.
            # Şimdilik listenin başına ekleyelim, daha görünür olması için.
            all_group_codes_for_list.insert(0, "[Boş]") # En başa ekle


        # all_group_codes = sorted(list(set(
        #     str(customer.get("GRUP_KODU", "") or "").strip() 
        #     for customer in self.all_customers_data if str(customer.get("GRUP_KODU", "") or "").strip()
        # ))) # Bu kısım yukarıdaki mantıkla değiştirildi.

        if not all_group_codes_for_list: # Hem dolu hem boş kod yoksa
            # self.group_code_label.setVisible(False)
            # self.group_code_list_widget.setVisible(False)
            # self.splitter.widget(0).setVisible(False) 
            pass


        for code in all_group_codes_for_list: # Güncellenmiş listeyi kullan
            item = QListWidgetItem(code)
            self.group_code_list_widget.addItem(item)
        
        # if all_group_codes_for_list and not self.splitter.widget(0).isVisible():
            # self.group_code_label.setVisible(True)
            # self.group_code_list_widget.setVisible(True)
            # self.splitter.widget(0).setVisible(True)


    def apply_filters(self):
        if not self.all_customers_data:
            self.populate_table([])
            return

        search_text = self.search_input.text().lower().strip()
        selected_group_codes_texts = self.get_selected_group_codes()

        filtered_data = self.all_customers_data

        # Grup Kodu Filtresi
        if selected_group_codes_texts:
            show_empty_groups = "[Boş]" in selected_group_codes_texts
            actual_selected_codes = [code for code in selected_group_codes_texts if code != "[Boş]"]
            
            temp_filtered_data = []
            for customer in filtered_data:
                customer_group_code = str(customer.get("GRUP_KODU", "") or "").strip()
                
                # Eğer "[Boş]" seçiliyse ve carinin grup kodu gerçekten boşsa, ekle
                if show_empty_groups and not customer_group_code:
                    temp_filtered_data.append(customer)
                    continue # Bu cari için diğer grup kodu kontrolüne gerek yok
                
                # Eğer carinin grup kodu seçili gerçek grup kodlarından biriyse, ekle
                if actual_selected_codes and customer_group_code in actual_selected_codes:
                    temp_filtered_data.append(customer)
            
            filtered_data = temp_filtered_data


        # Arama Çubuğu Filtresi
        if search_text:
            filtered_data = [
                customer for customer in filtered_data
                if search_text in str(customer.get("CARI_KOD", "")).lower() or \
                   search_text in str(customer.get("CARI_ISIM", "")).lower()
            ]
        
        self.populate_table(filtered_data)
        
        status_message = f"{len(filtered_data)} kayıt bulundu."
        if not search_text and not selected_group_codes_texts:
            status_message = f"{len(self.all_customers_data)} toplam cari."
        elif not search_text and selected_group_codes_texts:
            status_message = f"{len(filtered_data)} kayıt (grup filtresi aktif)."
        elif search_text and not selected_group_codes_texts:
            status_message = f"{len(filtered_data)} kayıt (arama filtresi aktif)."


        if self.parent_window and hasattr(self.parent_window, 'status_bar'):
            self.parent_window.status_bar.showMessage(status_message, 3000)

    def closeEvent(self, event):
        """ Pencere kapandığında veritabanı bağlantısını kapatır ve ayarları kaydeder """
        logger.info("CustomersPage closeEvent çağrıldı.")
        # self.save_filter_settings() # AYARLAR ARTIK BURADA KAYDEDİLMEYECEK
        if self.db_connection:
            try:
                self.db_connection.close()
                if self.parent_window and hasattr(self.parent_window, 'status_bar'):
                    self.parent_window.status_bar.showMessage("Cari modülü: Veritabanı bağlantısı kapatıldı.", 2000)
            except Exception as e:
                if self.parent_window and hasattr(self.parent_window, 'status_bar'):
                    self.parent_window.status_bar.showMessage(f"Cari modülü: Bağlantı kapatılırken hata: {e}", 3000)
        super().closeEvent(event)
        logger.info("TestMainWindow closeEvent tamamlandı.")

    def on_group_code_selection_changed(self):
        # Seçim değiştiğinde müşteri verilerini yeniden yükle
        # Bu metod, grup listesindeki seçim değiştiğinde load_customer_data'yı çağırır.
        # self.load_customer_data() # Bunun yerine apply_filters çağrılacak
        self.apply_filters()

    def get_selected_group_codes(self):
        selected_items = self.group_code_list_widget.selectedItems()
        return [item.text() for item in selected_items]

    def save_filter_settings(self):
        settings = {
            'search_text': self.search_input.text(),
            'selected_groups': self.get_selected_group_codes()
        }
        try:
            with open(self.filter_settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
            # print(f"Filtre ayarları {self.filter_settings_file} dosyasına kaydedildi.") # İsteğe bağlı log
            if self.parent_window and hasattr(self.parent_window, 'status_bar'):
                 self.parent_window.status_bar.showMessage(f"Filtre ayarları {self.filter_settings_file} dosyasına kaydedildi.", 2000)
            # logger.debug(f"Filtre ayarları {os.path.abspath(self.filter_settings_file)} dosyasına kaydedildi: {settings}")
            logger.info(f"Filtre ayarları {os.path.abspath(self.filter_settings_file)} dosyasına kaydedildi: {settings}") # INFO seviyesine çekildi
        except IOError as e:
            # print(f"DEBUG: Filtre ayarları kaydedilemedi: {e}") # LOG
            logger.error(f"Filtre ayarları kaydedilemedi: {e}", exc_info=True) # Hata detayını da ekle
            if self.parent_window and hasattr(self.parent_window, 'status_bar'):
                 self.parent_window.status_bar.showMessage(f"Filtre ayarları kaydedilemedi: {e}", 3000)

    def load_filter_settings(self):
        # logger.debug(f"Filtre ayarları yükleniyor: {os.path.abspath(self.filter_settings_file)}")
        logger.info(f"Filtre ayarları yükleniyor: {os.path.abspath(self.filter_settings_file)}") # INFO seviyesine çekildi
        if not os.path.exists(self.filter_settings_file):
            # logger.debug(f"Filtre ayar dosyası bulunamadı: {os.path.abspath(self.filter_settings_file)}")
            logger.info(f"Filtre ayar dosyası bulunamadı: {os.path.abspath(self.filter_settings_file)}") # INFO seviyesine çekildi
            return

        try:
            with open(self.filter_settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            
            self.search_input.setText(settings.get('search_text', ''))
            
            saved_selected_groups = settings.get('selected_groups', [])
            if saved_selected_groups:
                # QListWidget'taki öğelerin seçili durumunu ayarla
                for i in range(self.group_code_list_widget.count()):
                    item = self.group_code_list_widget.item(i)
                    if item and item.text() in saved_selected_groups:
                        item.setSelected(True)
                    # else: # Diğerlerinin seçimini kaldırmak istiyorsak (zaten clearSelection ile yapılabilir)
                        # item.setSelected(False) # Bu satır gereksiz olabilir, çünkü liste yeniden dolduruluyor
                                               # veya seçim modu zaten multiple ise sadece ilgili olanlar seçilir.
            
            # logger.debug(f"Filtre ayarları yüklendi: {settings}")
            logger.info(f"Filtre ayarları yüklendi: {settings}") # INFO seviyesine çekildi

        except (IOError, json.JSONDecodeError) as e:
            # print(f"DEBUG: Filtre ayarları yüklenemedi: {e}") # LOG
            logger.error(f"Filtre ayarları yüklenemedi: {e}", exc_info=True) # Hata detayını da ekle
            # Bozuk dosyayı silmeyi veya yeniden adlandırmayı düşünebilirsiniz.
            if self.parent_window and hasattr(self.parent_window, 'status_bar'):
                 self.parent_window.status_bar.showMessage(f"Filtre ayarları yüklenemedi: {e}", 3000)


if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow

    app = QApplication(sys.argv)
    class TestMainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Cari Modülü Test")
            self.customer_page_widget = CustomersPage(self)
            self.setCentralWidget(self.customer_page_widget)
            self.status_bar = self.statusBar() 
            self.setGeometry(100, 100, 900, 700)
            # logger.debug("TestMainWindow oluşturuldu.")
            logger.info("TestMainWindow oluşturuldu.") # INFO seviyesine çekildi

        def closeEvent(self, event):
            # logger.debug("TestMainWindow closeEvent çağrıldı.")
            logger.info("TestMainWindow closeEvent çağrıldı.") # INFO seviyesine çekildi
            # CustomersPage'in closeEvent'ini de çağırmak için
            if hasattr(self, 'customer_page_widget') and self.customer_page_widget:
                 # logger.debug("TestMainWindow -> self.customer_page_widget.closeEvent(event) çağrılıyor")
                 logger.info("TestMainWindow -> self.customer_page_widget.closeEvent(event) çağrılıyor") # INFO seviyesine çekildi
                 self.customer_page_widget.closeEvent(event) 
            super().closeEvent(event)
            # logger.debug("TestMainWindow closeEvent tamamlandı.")
            logger.info("TestMainWindow closeEvent tamamlandı.") # INFO seviyesine çekildi

    window = TestMainWindow()
    window.show()
    sys.exit(app.exec()) 