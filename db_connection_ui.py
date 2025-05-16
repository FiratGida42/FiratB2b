'''
Veritabanı Bağlantı Arayüzü Modülü

Bu modül, PySide6 kullanarak bir SQL Server veritabanı bağlantı arayüzü sağlar.
Kullanıcıların sunucu bilgilerini girmesine, veritabanlarını listelemesine
ve bağlantı ayarlarını güvenli bir şekilde kaydetmesine olanak tanır.
'''
import sys
import json
import keyring # Şifreleri güvenli saklamak için
import pyodbc  # SQL Server'a bağlanmak için
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
    QMessageBox
)
from PySide6.QtGui import QFont, QScreen # QIcon kaldırıldı, QScreen ortalama için kalabilir
from PySide6.QtCore import Qt # Qt importu kaldırıldı, ana pencerede kullanılıyordu

# Stil ve font ayarlarını ui_styles.py dosyasından al
from ui_styles import MODERN_STYLESHEET, FONT_NAME, FONT_SIZE

SERVICE_NAME = "B2B_App_DB_Credentials" # Keyring için servis adı
SETTINGS_FILE = "settings.json"        # Ayarların kaydedileceği dosya

class DBConnectionUI(QMainWindow):
    '''
    Veritabanı bağlantı bilgilerinin girildiği ve yönetildiği arayüz sınıfı.
    Kullanıcı arayüzü elemanlarını oluşturur, olayları bağlar ve ayarları yönetir.
    '''
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Veritabanı Bağlantı Ayarları")

        self.setup_ui_appearance()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

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

        main_layout.addLayout(form_layout)

        # Butonlar için yatay düzenleyici
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Ayarları Kaydet")
        self.save_button.clicked.connect(self.save_settings)
        button_layout.addWidget(self.save_button)
        button_layout.addStretch() # Butonları sola yaslar
        main_layout.addLayout(button_layout)

        self.load_settings() # Kaydedilmiş ayarları yükle
        self.center_window() # Pencereyi ortala

    def setup_ui_appearance(self):
        '''
        Pencerenin genel görünümünü ve stilini ayarlar.
        Font ve QSS stil şablonunu uygular.
        '''
        self.setMinimumSize(500, 250) # Pencere minimum boyutu
        font = QFont(FONT_NAME, FONT_SIZE)
        self.setFont(font)
        self.setStyleSheet(MODERN_STYLESHEET)

    def center_window(self):
        '''
        Pencereyi açıldığı ekranın ortasına yerleştirir.
        '''
        if self.screen(): # Çoklu ekran desteği için
            screen_geometry = self.screen().geometry()
            center_point = screen_geometry.center()
            frame_geometry = self.frameGeometry()
            frame_geometry.moveCenter(center_point)
            self.move(frame_geometry.topLeft())
        else: # Sadece ana ekran varsa veya ekran bilgisi alınamıyorsa
            # Fallback to centering on the primary screen if available
            primary_screen = QApplication.primaryScreen()
            if primary_screen:
                screen_geometry = primary_screen.geometry()
                center_point = screen_geometry.center()
                frame_geometry = self.frameGeometry()
                frame_geometry.moveCenter(center_point)
                self.move(frame_geometry.topLeft())
            else:
                # If no screen information is available at all, just resize
                self.resize(500, 250) # Or some default size
                # No reliable way to center without screen info
                pass

    def load_settings(self):
        '''
        Kaydedilmiş ayarları settings.json ve keyring'den yükler.
        '''
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings_data = json.load(f)
                self.server_address_input.setText(settings_data.get("server_address", ""))
                self.username_input.setText(settings_data.get("username", ""))
                # Veritabanı adını combobox'a ekle ve seçili yap
                saved_db_name = settings_data.get("db_name")
                if saved_db_name:
                    # Eğer daha önce listelenmemişse ve kaydedilmişse ekle
                    if self.db_name_combo.findText(saved_db_name) == -1:
                        self.db_name_combo.addItem(saved_db_name)
                    self.db_name_combo.setCurrentText(saved_db_name)

                # Şifreyi keyring'den yükle (kullanıcı adı varsa)
                username = settings_data.get("username")
                if username:
                    password = keyring.get_password(SERVICE_NAME, username)
                    if password:
                        self.password_input.setText(password)
            QMessageBox.information(self, "Bilgi", "Ayarlar başarıyla yüklendi.")
        except FileNotFoundError:
            # Ayar dosyası yoksa, bu ilk çalıştırma olabilir, hata vermeye gerek yok.
            # İsteğe bağlı olarak kullanıcıya bilgi verilebilir.
            # QMessageBox.information(self, "Bilgi", f"{SETTINGS_FILE} bulunamadı. İlk çalıştırma olabilir.")
            pass # Dosya yoksa sessizce geç
        except Exception as e:
            QMessageBox.warning(self, "Ayarlar Yüklenemedi", f"Ayarlar yüklenirken bir hata oluştu: {e}")

    def list_databases(self):
        '''
        SQL Server'a bağlanır ve veritabanlarını QComboBox'a yükler.
        '''
        server = self.server_address_input.text()
        user = self.username_input.text()
        # Şifreyi doğrudan input alanından al, keyring burada kullanılmıyor.
        # Keyring sadece şifre saklama ve yükleme içindir.
        password = self.password_input.text() 

        if not server or not user:
            QMessageBox.warning(self, "Eksik Bilgi", "Sunucu Adresi ve Kullanıcı Adı girilmelidir.")
            return

        # ODBC Driver 17 for SQL Server yaygın bir sürücüdür.
        # Eğer farklı bir sürücü kullanılıyorsa, burası güncellenmeli.
        # TrustServerCertificate=yes eklenerek SSL sertifika hataları bazı durumlarda bypass edilebilir (test ortamları için).
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};" +
            f"SERVER={server};" +
            #f"DATABASE={db_name};" # Veritabanı listelemek için spesifik bir db adına gerek yok
            f"UID={user};" +
            f"PWD={password};" +
            f"TrustServerCertificate=yes;" # Geliştirme ortamında sertifika hatalarını önlemek için
        )
        
        try:
            # Bağlantı için timeout belirlemek iyi bir pratiktir.
            with pyodbc.connect(conn_str, timeout=5) as conn:
                with conn.cursor() as cursor:
                    # Sadece kullanıcı veritabanlarını listele (sistem db'lerini hariç tut)
                    cursor.execute("SELECT name FROM sys.databases WHERE name NOT IN ('master', 'tempdb', 'model', 'msdb') ORDER BY name")
                    databases = [row.name for row in cursor.fetchall()]
                    
                    current_db_selection = self.db_name_combo.currentText() # Mevcut seçimi sakla
                    self.db_name_combo.clear() # Önceki listeyi temizle
                    self.db_name_combo.addItems(databases) # Yeni listeyi ekle

                    # Eğer saklanan seçim yeni listede varsa, onu tekrar seç
                    if current_db_selection in databases:
                        self.db_name_combo.setCurrentText(current_db_selection)
                    elif databases: # Değilse ve liste boş değilse ilk elemanı seç
                        self.db_name_combo.setCurrentIndex(0) 

                    if not databases:
                        QMessageBox.information(self, "Bilgi", "Listelenecek kullanıcı veritabanı bulunamadı.")
                    else:
                        QMessageBox.information(self, "Başarılı", "Veritabanları başarıyla listelendi.")

        except pyodbc.Error as ex:
            sqlstate = ex.args[0]
            # Kullanıcıya daha anlaşılır bir hata mesajı göster
            QMessageBox.critical(self, "Veritabanı Listeleme Hatası", f"Bağlantı veya sorgu hatası: {sqlstate} - {ex}")
        except Exception as e:
            QMessageBox.critical(self, "Veritabanı Listeleme Hatası", f"Beklenmedik bir hata oluştu: {e}")

    def save_settings(self):
        '''
        Bağlantı ayarlarını settings.json dosyasına ve şifreyi keyring'e kaydeder.
        '''
        server_address = self.server_address_input.text()
        username = self.username_input.text()
        password = self.password_input.text()
        db_name = self.db_name_combo.currentText() # Seçili veritabanı adını al

        if not server_address or not username:
            QMessageBox.warning(self, "Eksik Bilgi", "Sunucu Adresi ve Kullanıcı Adı boş bırakılamaz.")
            return

        if not db_name or self.db_name_combo.currentIndex() == -1: # Eğer combobox boşsa veya bir şey seçilmemişse
             QMessageBox.warning(self, "Eksik Bilgi", "Lütfen bir veritabanı seçin veya önce veritabanlarını listeleyin.")
             return

        settings_data = {
            "server_address": server_address,
            "username": username,
            "db_name": db_name # db_name'i de kaydet
        }

        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(settings_data, f, ensure_ascii=False, indent=4)
            
            # Şifreyi keyring'e kaydet (kullanıcı adı varsa)
            if username:
                keyring.set_password(SERVICE_NAME, username, password)
            
            QMessageBox.information(self, "Başarılı", "Ayarlar başarıyla kaydedildi.")

        except IOError:
            QMessageBox.critical(self, "Hata", f"Ayarlar {SETTINGS_FILE} dosyasına kaydedilirken bir IO hatası oluştu.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Şifre sistem anahtarlığına kaydedilirken bir hata oluştu: {e}")


# Uygulamayı çalıştırmak için ana blok (artık main_window.py içerisinde)
# if __name__ == '__main__':
#     app = QApplication(sys.argv)
#     window = DBConnectionUI()
#     window.show()
#     sys.exit(app.exec()) 