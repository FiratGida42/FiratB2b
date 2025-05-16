## ✅ YAPILAN İŞLEMLER

### 🧩 VERİTABANI BAĞLANTI ARAYÜZÜ ve ANA PANEL (Desktop – Admin Panel)
- [x] PySide6 arayüzü `main_window.py` olarak ana uygulama için oluşturuldu.
- [x] `db_connection_ui.py` sadece bağlantı ayar arayüzü için sadeleştirildi (şu an aktif kullanılmıyor, ana panel kendi ayar girişlerini içeriyor).
- [x] Ana panelde aşağıdaki alanları içeren bir form hazırlandı:
    - [x] Server Adresi (textbox)
    - [x] Kullanıcı Adı (textbox)
    - [x] Şifre (passwordbox)
    - [x] "Veritabanı Adı" alanı (combo box, sunucudan çekiyor)
- [x] "Veritabanlarını Listele" butonu eklendi ve işlevsel hale getirildi.
- [x] "Ayarları Kaydet" butonu eklendi → Ayarlar `settings.json` dosyasına (şifre `keyring` ile işletim sistemi deposuna) yazılıyor.
- [x] Veritabanlarını dinamik olarak listeleyen SQL sorgusu entegre edildi (`pyodbc` kullanıldı).
- [x] **Bağlantı testi:** "Veritabanlarını Listele" butonu, girilen ayarlarla veritabanına bağlanmayı deneyerek dolaylı bir test sağlar. Başarılı listeleme, bağlantının çalıştığını gösterir.
- [x] **Ek UI İyileştirmeleri ve İşlevler:**
    - [x] Arayüz ekranın ortasında ve normal boyutta açılıyor.
    - [x] Kurumsal ve modern bir görünüm için QSS stil şablonu uygulandı.
    - [x] Font seçimi yapıldı ("Lucida Console").
    - [x] Stil tanımlamaları (`ui_styles.py`) ayrı bir dosyaya taşındı.
    - [x] Çekilen ürün verileri `QTableWidget` üzerinde önizleniyor.
    - [x] Önizlenen (filtrelenmiş) veriyi JSON dosyasına kaydetme butonu eklendi.
    - [x] Sol panelde grup kodlarına göre dinamik filtreleme eklendi:
        - [x] Benzersiz grup kodları listeleniyor (checkbox ile).
        - [x] Seçili olmayan grup kodları farklı renkte (gri) gösteriliyor.
        - [x] Filtre seçimleri (`settings.json`'a kaydediliyor) uygulama yeniden başlatıldığında hatırlanıyor.
    - [x] Tablodaki ürünler varsayılan olarak "Grup Kodu"na göre sıralanıyor.
    - [x] Durum çubuğunda işlem bilgileri ve listelenen ürün sayısı gösteriliyor.
    - [x] Üst menü çubuğu eklendi ("Dosya" menüsü altında "Tam Ekran Aç/Kapat (F11)" ve "Çıkış (Ctrl+Q)").
    - [x] Esc tuşu ile tam ekrandan çıkış özelliği eklendi.
    - [x] Sağ üst köşeye ek bir "Çıkış" butonu eklendi.
    - [x] Tam ekrandan çıkıldığında pencerenin görev çubuğunu örtmemesi sağlandı.

### 📦 VERİ YAPISI ve VERİ KAYNAĞI (`data_extractor.py`)
- [x] SQL Server veritabanından kullanılacak tablolar ve alanlar belirlendi.
    - Ana Tablolar: `TBLSTSABIT`, `SenkronixStokBakiye` (BAKIYE için)
    - Çekilecek Alanlar: `STOK_KODU`, `STOK_ADI`, `BAKIYE`, `SATIS_FIAT1`, `GRUP_KODU`, `BARKOD1`
- [x] Ana bilgisayardan verileri çekmek için Python scripti (`data_extractor.py`) geliştirildi:
    - [x] Script test edildi ve SQL sorgusu doğrulandı.
    - [x] Türkçe karakter hataları (`Ý`, `Þ`, `Ð`) düzeltildi.
    - [x] Sayısal alanlar (`BAKIYE`, `SATIS_FIAT1`) `Decimal` tipine çevrildi.
    - [x] Verileri çekmek için kullanılacak bağlantı bilgileri `settings.json`'dan (ve `keyring`'den) okunuyor.
    - [x] SQL sorgusunda `GRUP_KODU` için 'KULLANMA', 'INT', 'PALET' filtrelemesi ve `BAKIYE <> 0` filtrelemesi eklendi.
    - [x] `GRUP_KODU` filtrelemesinde olası baştaki/sondaki boşluklar `RTRIM(LTRIM())` ile temizlendi.
- [x] `data_extractor.py` scriptine, çekilen verileri JSON formatında dosyaya yazma özelliği eklendi (`save_data_to_json`).
- [x] Genel yardımcı fonksiyonlar (`to_decimal`, `format_currency_tr`, `format_date_tr`) için `helpers.py` modülü oluşturuldu.

## 📝 YAPILACAK İŞLEMLER

### 🧩 DESKTOP ADMIN PANELİ İYİLEŞTİRMELERİ
- [ ] **Veri Tablosu İyileştirmeleri (Opsiyonel):**
    - [x] Sütun başlıklarına tıklayarak tabloyu o sütuna göre sıralama özelliği.
    - [x] `STOK_KODU` veya `STOK_ADI` için basit bir arama/filtreleme çubuğu.
- [ ] **Sol Panel Grup Filtresi İyileştirmeleri (Opsiyonel):**
    - [ ] "Tümünü Seç" / "Seçimi Kaldır" butonları.
    - [x] Grup kodlarını aramak için küçük bir filtre kutusu (çok fazla grup kodu olursa kullanışlı olur).

### 🔄 VERİYİ B2B SİTESİNE GÖNDERME MEKANİZMASI
- [x] Ana bilgisayardaki script (`data_extractor.py` veya ana panel üzerinden tetiklenecek bir fonksiyon) verileri aldıktan ve JSON/SQLite'a kaydettikten sonra:
    - [x] Web sunucusuna gönderme (birini seç):
        - [ ] FTP ile.
        - [x] REST API endpoint'e POST et (tavsiye edilir).
    - [x] Gönderilen verilerin doğruluğunu kontrol et.

### 🌐 B2B WEB SİTESİ
- [x] Python tabanlı web uygulaması (örneğin Flask veya FastAPI + HTML/JS).
- [x] Mobil uyumlu responsive arayüz (Bootstrap veya Tailwind).
- [x] Aşağıdaki sayfalar yapılsın:
    - [x] Ana Sayfa
    - [x] Ürün Listesi (filtreleme, arama, sıralama)
- [ ] Web sitesi dışarıdan erişilebilir olacak şekilde host edilecek.
- [ ] Web sitesi, SQLite veya gelen JSON veriyi okuyarak güncel verileri gösterecek.

### 🧪 TEST & KONTROL
- [x] SQL Server'da örnek veriyle test et. (`data_extractor.py` ve arayüz ile yapıldı)
- [x] Arayüzden bağlantı yapılıyor mu? ("Veritabanlarını Listele" butonu ile dolaylı olarak test ediliyor)
- [x] Veriler doğru dışa aktarılıyor mu? (JSON formatında filtrelenmiş aktarım yapıldı)
- [x] Web sitesine gelen veriler yansıyor mu?
- [x] Mobil cihazdan erişim sorunsuz mu?

### 🛠️ GELECEKTEKİ ADIMLAR (Opsiyonel ama planlanabilir)
- [ ] PostgreSQL geçiş planı hazırla.
- [ ] Sunucuya zamanlanmış veri gönderimi (cron-job veya scheduler).
- [ ] Web sitesine kullanıcı girişi ve yetkilendirme modülü.
- [ ] Çoklu dil desteği.
- [ ] Görsel yükleme ve gösterim mekanizması. (Not: Web'de mevcut görseller gösteriliyor, düzenli güncelleniyor. Yeni görsel yükleme/yönetim arayüzü ayrıca değerlendirilebilir.)