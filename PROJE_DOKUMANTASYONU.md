# Proje Dokümantasyonu

Bu doküman, B2B projesinin genel yapısını, bileşenlerini, modüllerini ve işleyişini detaylı bir şekilde açıklamaktadır.

## İçindekiler (Geliştirilecek)

- Genel Bakış
- Ana Bileşenler
  - Masaüstü Uygulaması (`main_window.py`)
  - Veri İşleme ve Çekme (`data_extractor.py`)
  - Web Uygulaması (`b2b_web_app/`)
  - Arka Plan Görevleri
  - Yapılandırma Dosyaları
  - Veritabanı
- Kurulum ve Bağımlılıklar
- Kullanılan Teknolojiler

## Ana Bileşenler

### 1. Masaüstü Uygulaması (`main_window.py`)

Bu dosya, B2B projesinin ana masaüstü uygulamasının PyQt6/PySide6 tabanlı kullanıcı arayüzünü (GUI) ve iş mantığını içerir. Uygulama, veritabanı yönetimi, ürün listeleme, kategori yönetimi ve cari hesap işlemleri gibi çeşitli modüllere erişim sağlar.

#### Temel Yapı ve Özellikler:

- **Ana Pencere (`MainWindow` sınıfı):**
    - Uygulamanın ana çerçevesini oluşturur.
    - Sol tarafta bir menü (Ayarlar, Ürünler, Kategoriler, Cariler) ve sağ tarafta seçilen menüye göre değişen bir içerik alanı (`QStackedWidget`) bulunur.
    - Bir menü çubuğu (`QMenuBar`) ve bir durum çubuğu (`QStatusBar`) içerir.
    - Tam ekran modu (F11 ile geçiş) ve Esc ile tam ekrandan çıkma özelliklerine sahiptir.
- **Sayfalar/Modüller:**
    - **Ayarlar Sayfası (`_create_settings_page`):**
        - Veritabanı bağlantı bilgileri (Sunucu Adresi, Kullanıcı Adı, Şifre, Veritabanı Adı) girilir ve `settings.json` dosyasına kaydedilir. Şifreler `keyring` ile güvenli bir şekilde saklanır.
        - Veritabanlarını listeleme özelliği bulunur.
        - Ürünler için Web API anahtarı girilir.
        - Otomatik ürün güncelleme zamanlayıcısının ayarları (etkinleştirme, güncelleme sıklığı) yapılır.
    - **Ürünler Sayfası (`_create_products_page`):**
        - Sol tarafta grup kodu filtreleme listesi (`QListWidget`) bulunur.
        - "Ürün Verilerini Çek ve Önizle" butonu ile veritabanından ürünler çekilir (`ProductLoaderWorker` ile arka planda).
        - Çekilen ürünler bir tabloda (`QTableWidget`) gösterilir.
        - "Önizlenen Veriyi JSON'a Kaydet" (`onizlenen_filtrelenmis_urunler.json`) ve "Verileri Web API'sine Gönder" butonları bulunur.
        - Grup kodlarına göre filtreleme yapılabilir ve bu tercihler `settings.json` dosyasına kaydedilir.
    - **Kategoriler Sayfası (`_create_categories_page`):**
        - Ürün kategorilerini bir ağaç yapısında (`QTreeWidget`) gösterir.
        - `KATEGORI_AGACI` adlı sabit bir Python listesinden statik olarak doldurulur (API'den dinamik yükleme/kaydetme fonksiyonları da mevcuttur ancak mevcut arayüzde bunlar kullanılmıyor gibi görünmektedir).
    - **Cariler Sayfası (`_create_customers_page_from_module`):**
        - Bu sayfa, `customers_module.py` dosyasından `CustomersPage` sınıfı import edilerek oluşturulur.
        - Cari hesapların listelenmesi, filtrelenmesi ve yönetilmesi işlevlerini içerir.
- **Yardımcı Sınıflar:**
    - **`ProductLoaderWorker` (QObject):** Ürün verilerini veritabanından arka planda (ayrı bir `QThread` üzerinde) çekmek için kullanılır, böylece arayüz donmaz.
    - **`ClickableImageLabel` (QLabel):** Ürün resimlerinin üzerine tıklandığında büyütülmüş önizlemesini gösteren `ImagePreviewDialog`'u açar.
    - **`ImagePreviewDialog` (QDialog):** Resimleri büyütülmüş olarak gösteren bir diyalog penceresidir.

#### Önemli Fonksiyonlar ve İş Mantığı:

- **Ayarlar Yönetimi (`load_settings`, `save_settings`):** `settings.json` dosyası üzerinden veritabanı bağlantı bilgileri, API anahtarları, zamanlayıcı ayarları ve kullanıcı tercihleri (hariç tutulan grup kodları) okunur ve kaydedilir.
- **Veri Çekme ve Gösterme (`preview_product_data`, `_on_products_loaded`, `_populate_product_table`):** `data_extractor.py` modülündeki fonksiyonlar kullanılarak ürün verileri çekilir, filtrelenir ve tabloda gösterilir.
- **API Entegrasyonu (`send_data_to_api_action`):** Çekilen ve filtrelenen ürün verileri, `data_extractor.py` üzerinden belirtilen Web API endpoint'ine gönderilir.
- **Filtreleme (`apply_group_code_filter`, `_update_group_filter_list`):** Ürünler sayfasında, kullanıcıların seçtiği grup kodlarına göre ürün listesi filtrelenir. Kullanıcının filtre tercihleri (hariç tutulanlar) kaydedilir.
- **Resim İşleme Entegrasyonu:**
    - `_find_download_and_save_image`: Belirtilen ürün için (barkod veya ürün adıyla `duckduckgo_search` kullanarak) resim arar, bulursa `image_processor.py` üzerinden indirip kaydeder.
    - Tabloda gösterilen ürün resimleri için `ClickableImageLabel` kullanılır.
- **Arka Plan İşlemleri:** Ürün verileri çekilirken arayüzün donmaması için `QThread` ve `QObject` (worker) yapısı kullanılır.
- **Durum Yönetimi:** `QStatusBar` aracılığıyla kullanıcıya işlemler hakkında bilgi verilir.

#### Harici Bağımlılıklar ve Modüller:

- `PySide6` (veya `PyQt6`): Kullanıcı arayüzü için.
- `keyring`: Şifrelerin güvenli saklanması için.
- `pyodbc`: SQL Server veritabanı bağlantısı için.
- `requests`: Web API'lerine istek göndermek için.
- `duckduckgo_search`: Ürün resimlerini internetten aramak için (opsiyonel).
- **Yerel Modüller:**
    - `ui_styles.py`: Arayüz için stil tanımlamaları.
    - `helpers.py`: Yardımcı fonksiyonlar (örn. para formatlama, ondalık dönüşümü).
    - `data_extractor.py`: Veritabanından veri çekme ve API'ye veri gönderme mantığı.
    - `image_processor.py`: Resim temizleme, indirme ve kaydetme işlemleri.
    - `customers_module.py`: Cariler sayfası için ayrı bir modül.

#### Notlar ve Potansiyel İyileştirmeler:

- Kod içerisinde bazı yerlerde `print()` ifadeleri debug amaçlı kullanılmış, bunlar production ortamı için loglama ile değiştirilebilir veya kaldırılabilir.
- Kategoriler sayfası şu anda statik bir yapıdan besleniyor. API entegrasyonu için fonksiyonlar mevcut olsa da, GUI üzerinden kategori ekleme/düzenleme/silme ve API'ye kaydetme işlemleri tam olarak aktif olmayabilir.
- Resim arama özelliği `duckduckgo_search` kütüphanesine bağlıdır ve bu kütüphane kurulu değilse çalışmayacaktır.

### 2. Veri İşleme ve Çekme (`data_extractor.py`)

Bu modül, SQL Server veritabanı ile etkileşim kurmak, ürün ve cari verilerini çekmek, bu verileri işlemek (örn. Türkçe karakter düzeltme, sayısal dönüşümler) ve Web API'sine göndermek için gerekli temel fonksiyonları içerir.

#### Temel Yapı ve Fonksiyonlar:

- **Yapılandırma ve Sabitler:**
    - `LOG_DIR`, `LOG_FILE_NAME`: Loglama için dosya ve dizin yolları.
    - `SERVICE_NAME`: `keyring` servisi için ad.
    - `SETTINGS_FILE`: Bağlantı ayarlarının ve API anahtarlarının saklandığı JSON dosyasının adı (`settings.json`).
    - `DEFAULT_PLACEHOLDER_IMAGE`: Ürün resmi bulunamadığında kullanılacak varsayılan resim yolu.
    - `CHAR_CORRECTION_MAP`: Veritabanından gelen bazı bozuk Türkçe karakterlerin düzeltilmesi için bir eşleme tablosu.
    - `FIELDS_TO_CORRECT`, `NUMERIC_FIELDS_TO_CONVERT`, `CUSTOMER_NUMERIC_FIELDS`: Veri işleme sırasında hangi alanların düzeltileceğini veya dönüştürüleceğini belirten listeler.
    - `DEFAULT_API_URL`: Ürün verilerinin gönderileceği varsayılan Web API endpoint'i.

- **Yardımcı Fonksiyonlar:**
    - `decimal_serializer(obj)`: `Decimal` nesnelerini JSON'a serileştirirken string'e çevirir.
    - `_correct_turkish_characters_in_row(row_dict)`: Veritabanı satırındaki (sözlük) belirtilen alanlardaki Türkçe karakter hatalarını düzeltir.
    - `_convert_numeric_fields_in_row(row_dict, field_list)`: Belirtilen alanlardaki değerleri `Decimal` tipine çevirir.

- **Bağlantı Yönetimi:**
    - `get_db_connection_settings()`: `settings.json` dosyasından sunucu, kullanıcı adı ve veritabanı adını okur.
    - `get_db_connection(caller_info)`: `settings.json` ve `keyring` kullanarak SQL Server'a bir veritabanı bağlantısı kurar. `caller_info` parametresi loglamada bağlantıyı kimin istediğini belirtmek için kullanılır.
    - `load_settings()`: `settings.json` dosyasını yükler.
    - `get_password(username)`: Belirtilen kullanıcı adı için şifreyi `keyring`'den alır.

- **Veri Çekme Fonksiyonları:**
    - `fetch_product_data(connection, excluded_groups=None)`:
        - Veritabanından ürün bilgilerini (stok kodu, stok adı, bakiye, satış fiyatı, grup kodu, barkod) çeker.
        - Belirli grup kodlarını (`KULLANMA`, `INT`, `PALET`) ve bakiyesi sıfır olan ürünleri hariç tutar.
        - `excluded_groups` parametresi ile ek grup kodları da hariç tutulabilir.
        - Çekilen veriler üzerinde Türkçe karakter düzeltmesi ve sayısal alan dönüşümü yapar.
        - Her ürün için `image_processor.download_and_save_image` fonksiyonunu çağırarak (şu anda URL vermeden, sadece yerel kontrol için) bir resim yolu bulmaya çalışır ve bunu `IMAGE_PATH_WEB` alanına ekler. Resim bulunamazsa varsayılan bir yer tutucu resim yolu kullanılır.
    - `fetch_unique_group_codes(db_conn=None)`: `TBLCASABIT` tablosundan, belirli ön eklerle (`GG%`, `135%`) BAŞLAMAYAN cari kodlarına ait benzersiz `GRUP_KODU` değerlerini çeker.
    - `fetch_customer_summary(db_conn=None, selected_group_codes=None)`:
        - `TBLCASABIT` tablosundan temel cari bilgilerini (cari kod, cari isim, borç/alacak/net bakiye, grup kodu) çeker.
        - Cari kodu `GG%` veya `135%` ile başlayanları hariç tutar.
        - `selected_group_codes` parametresi ile belirli grup kodlarına göre filtreleme yapabilir.
        - Sayısal bakiye alanlarını `Decimal` tipine dönüştürür.
        - Cari isimlerini `dbo.TRK()` SQL fonksiyonu ile (muhtemelen Türkçe karakter dönüşümü için) alır.
    - `extract_data_from_db(connection_params)`: Bu fonksiyon `fetch_product_data`'ya benzer şekilde ürün verilerini çeker ancak bağlantı parametrelerini doğrudan alır ve kendi içinde `pyodbc.connect` çağrısı yapar. Türkçe karakter düzeltmeleri ve resim yolu ekleme işlemleri de burada tekrarlanır. (Bu fonksiyonun varlığı `fetch_product_data` ile kısmen örtüşüyor gibi görünüyor ve konsolidasyon düşünülebilir.)

- **Veri Kaydetme ve Gönderme:**
    - `save_data_to_json(data, filename)`: Verilen veriyi (genellikle ürün listesi) belirtilen JSON dosyasına kaydeder. `Decimal` nesnelerini serileştirirken `decimal_serializer` kullanır.
    - `send_data_to_web_api(product_data: list, api_url: str)`: Ürün verilerini (önce `Decimal`'leri string'e çevirerek) `settings.json`'dan okunan API anahtarı ile belirtilen `api_url`'e POST isteği olarak gönderir.

- **Resim URL Bulma (Yer Tutucu):**
    - `find_image_url_for_product(cleaned_product_name, original_stok_adi, stok_kodu)`: Bu fonksiyon, ürün adı veya koduyla bir resim URL'si bulmak için tasarlanmıştır ancak şu anki implementasyonu sadece `None` döndürür. `batch_image_downloader.py` geliştirildikten sonra bu fonksiyonun gerçek bir işlevselliğe sahip olması beklenir.

#### Loglama:

- Modül, `logging` kütüphanesini kullanarak `b2b_web_app/logs/b2b_desktop_app.log` dosyasına INFO ve üzeri seviyedeki logları kaydeder.
- Veritabanı bağlantı hataları, veri çekme hataları ve API gönderme işlemleri detaylı bir şekilde loglanır.

#### Entegrasyonlar:

- `helpers.py`: `to_decimal` ve `format_currency_tr` gibi yardımcı fonksiyonlar için.
- `image_processor.py`: Ürün adlarını temizleme ve resimleri indirme/kaydetme işlemleri için.
- `keyring`: Veritabanı şifrelerini güvenli bir şekilde saklamak ve almak için.
- `requests`: Web API'lerine HTTP istekleri göndermek için.
- `pyodbc`: SQL Server veritabanı ile iletişim kurmak için.

#### Notlar ve Potansiyel İyileştirmeler:

- `extract_data_from_db` fonksiyonunun işlevselliği `fetch_product_data` ile büyük ölçüde örtüşmektedir. Kod tekrarını azaltmak için bu iki fonksiyonun birleştirilmesi veya birinin diğerini kullanması düşünülebilir.
- Türkçe karakter düzeltme (`_correct_turkish_characters_in_row`) ve sayısal alan dönüştürme (`_convert_numeric_fields_in_row`) işlemleri, veri çekme fonksiyonları içinde tutarlı bir şekilde uygulanmaktadır.
- `find_image_url_for_product` fonksiyonunun gerçek bir resim arama mantığı ile implemente edilmesi gerekmektedir (muhtemelen `batch_image_downloader.py` içindeki mantık buraya entegre edilebilir veya oradan çağrılabilir).
- Loglama seviyeleri (örn. DEBUG) ve log mesajlarının detayları projenin ihtiyaçlarına göre daha da geliştirilebilir.

### 3. Web Uygulaması (`b2b_web_app/main.py`)

Bu dosya, projenin FastAPI tabanlı web uygulamasının ana mantığını içerir. Ürünlerin listelenmesi, kullanıcı girişi, sepet işlemleri, sipariş oluşturma ve yönetici API endpoint'lerini barındırır.

#### Temel Yapı ve Özellikler:

- **FastAPI Uygulaması (`app`):**
    - Ana FastAPI örneği oluşturulur.
    - Oturum yönetimi için `SessionMiddleware` eklenir.
    - Statik dosyalar (`/static`) ve Jinja2 şablonları (`/templates`) için yapılandırma yapılır.
- **Pydantic Modelleri (Şemalar):**
    - `OrderItemBase`, `OrderItemCreate`, `OrderItemResponse`: Sipariş kalemlerinin veri yapılarını tanımlar.
    - `OrderBase`, `OrderCreate`, `OrderResponse`: Siparişlerin ana veri yapılarını ve oluşturma/yanıt şemalarını tanımlar.
    - `OrderStatusUpdate`: Sipariş durumunu güncellemek için kullanılır.
    - `field_validator` kullanılarak bazı alanlar için özel doğrulamalar eklenmiştir (örn. `customer_name` boş olamaz).
- **Veritabanı Entegrasyonu:**
    - `b2b_web_app/models.py` (SQLAlchemy modelleri) ve `b2b_web_app/database.py` (veritabanı motoru, oturum oluşturma) dosyaları ile entegrasyon sağlanır.
    - `get_db` dependency'si ile her request için bir veritabanı oturumu elde edilir.
    - Uygulama başladığında FastAPI startup event'i ile tablolar otomatik olarak oluşturulur (`Base.metadata.create_all(bind=engine)`).
    - **Basit SQLAlchemy Yaklaşımı:** Migration sistemleri yerine uygulama her başladığında gerekli tabloları otomatik oluşturur.
- **API Anahtarları ve Güvenlik:**
    - `PRODUCTS_API_KEY_VALUE`: Masaüstü uygulamasından ürün verilerini almak için kullanılan API anahtarı. Ortam değişkeni (`PRODUCTS_API_KEY`) veya `settings.json` üzerinden alınır.
    - `CUSTOMER_SYNC_API_KEY_VALUE`: Cari senkronizasyonu için kullanılan API anahtarı (`SERVER_API_KEY` ortam değişkeninden).
    - `FASTAPI_SECRET_KEY`: Oturum yönetimi için gizli anahtar. Ortam değişkeninden alınır, yoksa rastgele üretilir.
    - `verify_api_key` ve `verify_customer_sync_api_key`: API endpoint'lerini korumak için kullanılan dependency fonksiyonlarıdır. Gelen isteklerde `X-API-Key` başlığını kontrol ederler.
- **Yönetici (Admin) Kimlik Doğrulaması:**
    - `admin_config.json` dosyasında saklanan yönetici kullanıcı adı ve hash'lenmiş şifre ile kimlik doğrulama yapılır.
    - `pwd_context` (Passlib) ile şifre hash'leme ve doğrulama işlemleri gerçekleştirilir.
    - `get_current_admin_user_with_redirect`: Web sayfalarına erişimi kontrol eder, giriş yapılmamışsa `/login` sayfasına yönlendirir.
    - `get_current_admin_user_for_api`: API endpoint'lerine erişimi kontrol eder, giriş yapılmamışsa `HTTP_401_UNAUTHORIZED` hatası döndürür.

#### HTML Sayfaları ve Şablon Motoru (Jinja2):

- **Şablon Dizini (`TEMPLATES_DIR`):** `b2b_web_app/templates`.
- **Statik Dosya Dizini (`STATIC_DIR`):** `b2b_web_app/static`.
- **Jinja2 Filtreleri:**
    - `format_currency_tr`: Para birimi değerlerini Türkçe formatında (örn. 1.234,56 ₺) göstermek için özel bir filtre tanımlanmıştır.
- **Sayfalar:**
    - `/` (Ana Sayfa): `products.html` şablonunu kullanarak ürünleri listeler. Ürünler `received_products.json` dosyasından okunur.
    - `/customer-balances`: `customer_balances.html` şablonunu kullanarak cari bakiyelerini listeler. Veriler `static/json_data/filtrelenen_cariler.json` dosyasından okunur. Yönetici girişi gerektirir.
    - `/cart`: `cart.html` şablonunu kullanarak alışveriş sepetini gösterir.
    - `/orders`: `orders.html` şablonunu kullanarak oluşturulan siparişleri listeler.
    - `/login`: `login.html` şablonunu kullanarak yönetici giriş formunu gösterir.
    - `/admin/me`: `admin_me.html` şablonunu kullanarak yönetici bilgilerini gösterir. Yönetici girişi gerektirir.

#### API Endpoint'leri:

- **Ürünler:**
    - `POST /api/products` (Dependency: `verify_api_key`):
        - Masaüstü uygulamasından gelen ürün listesini alır ve `received_products.json` dosyasına kaydeder.
    - `GET /api/products` (Dependency: `get_current_admin_user_for_api`):
        - `received_products.json` dosyasındaki ürünleri döndürür.
- **Cariler:**
    - `POST /api/update-customer-balances` (Dependency: `verify_customer_sync_api_key`):
        - `background_scheduler_cariler.pyw` betiğinden gelen (filtrelenmiş) cari listesini alır ve `static/json_data/filtrelenen_cariler.json` dosyasına kaydeder.
- **Siparişler (Orders) - Veritabanı Kullanılır:**
    - `POST /api/orders` (Dependency: `get_current_admin_user_for_api`, Response Model: `OrderResponse`):
        - Yeni bir sipariş oluşturur. Sipariş verileri (müşteri adı, ürünler, miktarlar, fiyatlar) veritabanına kaydedilir (`TBLORDERS` ve `TBLORDERITEMS` tabloları).
        - Siparişin toplam tutarını hesaplar.
    - `GET /api/orders` (Dependency: `get_current_admin_user_for_api`, Response Model: `List[OrderResponse]`):
        - Veritabanındaki tüm siparişleri listeler (sayfalama parametreleri `skip` ve `limit` ile).
    - `GET /api/orders/{order_id}` (Dependency: `get_current_admin_user_for_api`, Response Model: `OrderResponse`):
        - Belirli bir siparişin detaylarını getirir.
    - `PUT /api/orders/{order_id}/status` (Dependency: `get_current_admin_user_for_api`, Response Model: `OrderResponse`):
        - Belirli bir siparişin durumunu günceller (örn. "Hazırlanıyor", "Tamamlandı").

#### Diğer Önemli Fonksiyonlar:

- `startup_event()`: Uygulama başladığında çalışır. Şu anda log dosyalarının (`b2b_web_app/logs/`) ve JSON veri dizininin (`b2b_web_app/static/json_data/`) varlığını kontrol eder ve yoksa oluşturur.

#### Harici Bağımlılıklar:

- `fastapi`: Web framework.
- `uvicorn` (veya benzeri bir ASGI sunucusu): Uygulamayı çalıştırmak için.
- `jinja2`: Şablon motoru.
- `python-multipart`: Form verilerini işlemek için (örn. login).
- `passlib[bcrypt]`: Şifre hash'leme.
- `sqlalchemy`: ORM (Veritabanı işlemleri).
- `pydantic`: Veri doğrulama ve serileştirme.
- `python-dotenv`: `.env` dosyasından ortam değişkenlerini yüklemek için.

#### Notlar ve Potansiyel İyileştirmeler:

- API anahtarları ve gizli anahtar gibi hassas bilgiler ortam değişkenlerinden okunmaktadır, bu iyi bir pratiktir.
- Ürün ve cari listeleri şu anda JSON dosyaları üzerinden yönetilmektedir. Büyük veri setleri için bu performans sorunlarına yol açabilir ve veritabanı entegrasyonu (SQLAlchemy modelleri zaten mevcut) daha ölçeklenebilir bir çözüm olabilir.
- Sipariş yönetimi için SQLAlchemy ORM kullanılmaktadır, bu da veritabanı işlemlerini kolaylaştırır.
- Hata yönetimi (HTTPException kullanımı) genel olarak iyidir.
- Frontend (HTML şablonları ve JavaScript) tarafında daha fazla etkileşim ve kullanıcı deneyimi iyileştirmesi yapılabilir.

### 4. Yapılandırma Dosyaları

#### a. `settings.json`

Bu JSON dosyası, hem masaüstü uygulamasının hem de arka plan betiklerinin çalışması için kritik yapılandırma bilgilerini içerir.

```json
{
    "server_address": "FIRAT",
    "username": "sa",
    "db_name": "FIRAT2025",
    "products_api_key": "501033d2ace200fecc597a986e47ebfc",
    "customer_sync_api_key": "test123",
    "scheduler_settings": {
        "enabled": true,
        "interval_minutes": 15
    },
    "user_preferences": {
        "excluded_group_codes": []
    }
}
```

**Alanların Açıklamaları:**

-   **`server_address`**: Bağlanılacak SQL Server örneğinin adı veya adresi.
-   **`username`**: SQL Server bağlantısı için kullanılacak kullanıcı adı.
    -   *Not: Bu kullanıcıya ait şifre, güvenlik nedeniyle bu dosyada saklanmaz; bunun yerine işletim sisteminin `keyring` servisinde (`B2B_App_DB_Credentials` servis adı altında) saklanır.*
-   **`db_name`**: Bağlanılacak veritabanının adı.
-   **`products_api_key`**: Masaüstü uygulamasının (`data_extractor.py` üzerinden) çektiği ürün verilerini web uygulamasına (`b2b_web_app/main.py` içindeki `/api/products` endpoint'ine) göndermek için kullanılan API anahtarı. Bu anahtar, web uygulamasının ortam değişkenlerinde (`PRODUCTS_API_KEY`) veya doğrudan kod içinde tanımlanan değerle eşleşmelidir.
-   **`customer_sync_api_key`**: `background_scheduler_cariler.pyw` betiğinin çektiği cari verilerini web uygulamasına (`b2b_web_app/main.py` içindeki `/api/update-customer-balances` endpoint'ine) göndermek için kullanılan API anahtarı. Bu anahtar, web uygulamasının ortam değişkenlerinde (`SERVER_API_KEY`) tanımlanan değerle eşleşmelidir.
-   **`scheduler_settings`**: Arka plan ürün güncelleme zamanlayıcısı (`background_scheduler.pyw`) için ayarları içerir.
    -   `enabled` (boolean): Zamanlayıcının aktif olup olmadığını belirtir.
    -   `interval_minutes` (integer): Zamanlayıcının ürün verilerini ne kadar sıklıkta (dakika cinsinden) güncelleyeceğini belirtir.
-   **`user_preferences`**: Kullanıcıya özel tercihleri saklar.
    -   `excluded_group_codes` (list of strings): Masaüstü uygulamasında ürünler listelenirken varsayılan olarak hariç tutulacak (işareti kaldırılacak) grup kodlarının bir listesidir.

**Kullanım Alanları:**

-   Masaüstü uygulaması (`main_window.py` ve `data_extractor.py`), veritabanı bağlantısı kurmak, API'ye veri göndermek ve zamanlayıcı ayarlarını okumak için bu dosyayı kullanır.
-   `background_scheduler.pyw` ve `background_scheduler_cariler.pyw` betikleri, API anahtarlarını ve zamanlayıcı ayarlarını (sadece ürünler için) okumak için bu dosyayı kullanır.

### 5. Arka Plan Görevleri (Zamanlayıcılar)

Proje, belirli görevleri düzenli aralıklarla otomatikleştirmek için Python `schedule` kütüphanesini kullanan arka plan betikleri içerir. Bu betikler genellikle `.pyw` uzantılıdır, bu da Windows'ta konsol penceresi olmadan çalışmalarını sağlar.

#### a. Cari Senkronizasyon Betiği (`background_scheduler_cariler.pyw`)

Bu betik, SQL Server veritabanından cari (müşteri) verilerini periyodik olarak çekmek, bu verileri belirli kriterlere göre filtrelemek ve ardından web uygulamasına (`b2b_web_app/main.py`) bir API endpoint'i aracılığıyla göndermekle sorumludur. Web uygulaması da bu verileri `static/json_data/filtrelenen_cariler.json` dosyasına yazar.

**Temel İşleyiş:**

1.  **Yapılandırma Yükleme (`load_configuration` fonksiyonu):**
    *   `settings.json` dosyasını okur.
    *   Özellikle `customer_sync_api_key` değerini alır. Bu anahtar, web uygulamasına veri gönderirken kimlik doğrulama için kullanılır.
    *   Eğer `settings.json` bulunamazsa, geçerli JSON formatında değilse veya API anahtarı eksikse, betik kritik bir hata loglar ve sonlanır.
2.  **Ana Kontrolcü Fonksiyonu (`job_controller_customers`):**
    *   Bu fonksiyon, `schedule` kütüphanesi tarafından belirli aralıklarla (varsayılan olarak 1 dakika) tetiklenir.
    *   Her tetiklendiğinde, kendi özel log dosyasına (`cariler_controller_run_YYYYMMDD_HHMMSS_ffffff.log`) log kaydı yapar.
    *   `perform_customer_data_sync_task` fonksiyonunu çağırarak asıl veri senkronizasyon işlemini başlatır.
3.  **Veri Senkronizasyon Görevi (`perform_customer_data_sync_task` fonksiyonu):**
    *   Her çalıştırıldığında, kendine özel bir log dosyası (`customer_sync_YYYYMMDD_HHMMSS_ffffff.log`) oluşturur.
    *   **Veritabanı Bağlantısı:** `data_extractor.get_db_connection` fonksiyonunu kullanarak SQL Server'a bağlanır.
    *   **Veri Çekme:** `data_extractor.fetch_customer_summary` fonksiyonunu kullanarak tüm cari özet bilgilerini veritabanından çeker.
    *   **Filtreleme:** Çekilen cari verilerini aşağıdaki kriterlere göre filtreler:
        *   **Grup Kodu (`GRUP_KODU`):** Sadece "SERVİS", "TOPTAN" olan veya grup kodu olmayan/boş olan cariler dahil edilir.
        *   **Net Bakiye (`NET_BAKIYE`):** Sadece net bakiyesi (mutlak değer olarak) çok küçük bir değerden (1e-7) büyük olan cariler dahil edilir (yani sıfır veya çok yakın sıfır bakiyeler hariç tutulur).
    *   **API'ye Gönderme:**
        *   Filtrelenmiş cari listesini JSON formatına dönüştürür (`decimal_serializer` kullanılarak `Decimal` türleri de doğru şekilde serileştirilir).
        *   `settings.json`'dan alınan `API_KEY` (`customer_sync_api_key`) ve `RENDER_API_URL` (`https://firatb2b.onrender.com/api/update-customer-balances`) kullanarak `requests.post` ile web uygulamasına gönderir.
        *   İstek başlığında `X-API-Key` olarak API anahtarını ve `Content-Type: application/json` gönderir.
        *   API'den gelen yanıtı (başarılı veya hatalı) loglar.
    *   **Hata Yönetimi:** Veritabanı bağlantı hataları, API istek hataları (HTTP hataları, bağlantı hataları, zaman aşımları) ve diğer genel istisnalar yakalanır ve detaylı olarak loglanır.
    *   **Veritabanı Bağlantısını Kapatma:** İşlem tamamlandığında veya hata oluştuğunda veritabanı bağlantısı kapatılır.
4.  **Zamanlama (`if __name__ == "__main__":` bloğu):**
    *   Betik doğrudan çalıştırıldığında, önce `load_configuration` çağrılır.
    *   `schedule.every(1).minutes.do(job_controller_customers)` ile `job_controller_customers` fonksiyonu her 1 dakikada bir çalışacak şekilde zamanlanır.
    *   İlk senkronizasyonun hemen yapılması için `job_controller_customers()` bir kez doğrudan çağrılır.
    *   Sonsuz bir `while True` döngüsü içinde `schedule.run_pending()` çağrılarak zamanlanmış görevlerin çalışması sağlanır. `time.sleep(1)` ile döngü saniyede bir kontrol yapar.

**Loglama:**

-   Betik, detaylı loglama yapar. Hem ana kontrolcü (`job_controller_customers`) hem de her bir senkronizasyon görevi (`perform_customer_data_sync_task`) çalıştığında, `Logs/Cariler` dizini altına zaman damgalı ayrı log dosyaları oluşturulur.
-   Bu, sorun gidermeyi ve belirli bir çalıştırmanın geçmişini izlemeyi kolaylaştırır.
-   Kritik hatalar (örn. ayar dosyası bulunamaması) `background_scheduler_cariler_CRITICAL_ERROR.log` adlı bir dosyaya da yazılabilir.

**Bağımlılıklar:**

-   `schedule`: Görev zamanlama.
-   `requests`: HTTP istekleri yapmak için.
-   `data_extractor` (proje içi modül): Veritabanı bağlantısı, veri çekme fonksiyonları ve ayar dosyası yolu gibi paylaşılan bileşenler için.

**Önemli Notlar:**

-   Bu betik, `filtrelenen_cariler_yerel.json` adında bir yerel yedek dosya oluşturma işlevselliğini **artık içermemektedir**. Tüm veriler doğrudan API üzerinden web uygulamasına gönderilir.
-   API anahtarı (`customer_sync_api_key`) ve web API URL'si (`RENDER_API_URL`) betiğin doğru çalışması için kritik öneme sahiptir.

#### b. Ürün Güncelleme Betiği (`background_scheduler.pyw`)

Bu betik, `background_scheduler_cariler.pyw`'ye benzer bir yapıya sahip olup, SQL Server veritabanından ürün verilerini periyodik olarak çekmek, bu verileri (isteğe bağlı olarak `settings.json`'da tanımlanan grup kodlarına göre) filtrelemek ve ardından web uygulamasına (`b2b_web_app/main.py` içindeki `/api/products` endpoint'ine) göndermekle sorumludur. Web uygulaması da bu verileri `received_products.json` dosyasına yazar.

**Temel İşleyiş:**

1.  **Yapılandırma ve Loglama Kurulumu:**
    *   `data_extractor` modülünden gerekli fonksiyonları (`get_db_connection`, `fetch_product_data`, `send_data_to_web_api`), ayar dosyası yolunu (`SETTINGS_FILE`) ve log dizinini (`APP_LOG_DIR`) import eder.
    *   İki ana logger tanımlanır:
        *   `main_logger` ("BackgroundSchedulerMain"): Genel zamanlayıcı kontrolcüsü işlemlerini `Logs/background_scheduler_main.log` dosyasına loglar.
        *   `task_logger` ("ProductUpdateTask"): Asıl ürün güncelleme görevi işlemlerini `Logs/product_update_task.log` dosyasına loglar.
    *   Her iki logger da konsola (stdout) da loglama yapar.
2.  **Ana Kontrolcü Fonksiyonu (`job_controller`):**
    *   Bu fonksiyon, `schedule` kütüphanesi tarafından her 1 dakikada bir tetiklenir.
    *   **Ayarları Okuma:** `settings.json` dosyasını okur.
        *   `scheduler_settings` bölümünden zamanlayıcının aktif olup olmadığını (`enabled`) ve güncelleme aralığını (`interval_minutes`) alır.
        *   `user_preferences` bölümünden hariç tutulacak ürün grup kodlarını (`excluded_group_codes`) okur.
    *   **Çalışma Kontrolü:**
        *   Eğer `settings.json`'da `enabled` değeri `false` ise, işlem yapmadan çıkar.
        *   `last_successful_update_timestamp` global değişkeni ile son başarılı güncelleme zamanını takip eder. İstenen `interval_minutes` süresi dolmuşsa veya ilk çalıştırmaysa asıl güncelleme görevini tetikler.
3.  **Asıl Ürün Güncelleme Görevi (`perform_actual_update_task` fonksiyonu):**
    *   `task_logger` kullanarak kendi loglarını tutar.
    *   Parametre olarak `settings.json`'dan okunan `excluded_groups_from_settings` listesini alabilir.
    *   **Veritabanı Bağlantısı:** `data_extractor.get_db_connection` ile SQL Server'a bağlanır.
    *   **Veri Çekme:** `data_extractor.fetch_product_data` fonksiyonunu çağırarak ürün verilerini çeker. Eğer `excluded_groups_from_settings` doluysa, bu grup kodlarına sahip ürünler hariç tutulur.
    *   **API'ye Gönderme:**
        *   Çekilen ve filtrelenen ürün verilerini `data_extractor.send_data_to_web_api` fonksiyonu aracılığıyla web uygulamasına gönderir. Bu fonksiyon, `settings.json`'dan `products_api_key` değerini ve web API URL'sini (`https://firatb2b.onrender.com/api/products`) kullanarak POST isteği yapar.
        *   API'den gelen yanıtı (başarılı veya hatalı) loglar.
    *   **Hata Yönetimi ve Bağlantı Kapatma:** `background_scheduler_cariler.pyw`'dekine benzer şekilde hatalar loglanır ve veritabanı bağlantısı kapatılır.
4.  **Zamanlama (`if __name__ == "__main__":` bloğu):**
    *   Betik doğrudan çalıştırıldığında `schedule.every(1).minutes.do(job_controller)` ile `job_controller` fonksiyonu her 1 dakikada bir çalışacak şekilde zamanlanır.
    *   İlk kontrolün hemen yapılması için `job_controller()` bir kez doğrudan çağrılır.
    *   Sonsuz bir `while True` döngüsü içinde `schedule.run_pending()` çağrılarak zamanlanmış görevlerin çalışması sağlanır.

**Loglama:**

-   Bu betik, `Logs` dizini altında `background_scheduler_main.log` (kontrolcü için) ve `product_update_task.log` (asıl güncelleme görevi için) olmak üzere iki ana log dosyası kullanır. Cari zamanlayıcısının aksine, her çalıştırma için ayrı zaman damgalı log dosyaları oluşturmaz; bunun yerine mevcut log dosyalarına ekleme yapar.

**Bağımlılıklar:**

-   `schedule`: Görev zamanlama.
-   `data_extractor` (proje içi modül): Veritabanı işlemleri, API gönderme fonksiyonları ve ayarlar.

**Önemli Notlar:**

-   Bu betiğin etkinliği ve çalışma sıklığı tamamen `settings.json` dosyasındaki `scheduler_settings` bölümüne bağlıdır.
-   Ürün verileri API'ye gönderildikten sonra web uygulaması tarafından `received_products.json` dosyasına yazılır. Bu dosya, `/` (ana sayfa) tarafından ürünleri listelemek için kullanılır.
-   Masaüstü uygulamasındaki kullanıcı arayüzünden de (`data_extractor` aracılığıyla) manuel olarak ürünler API'ye gönderilebilir. Bu zamanlayıcı, bu işlemi otomatikleştirir.

### 6. Veritabanı Modelleri ve Kurulumu (`b2b_web_app/` altında)

Web uygulaması, sipariş verilerini kalıcı olarak saklamak için bir veritabanı kullanır. SQLAlchemy ORM (Object Relational Mapper) aracılığıyla bu veritabanı ile etkileşim kurar.

#### 🔧 **Basit SQLAlchemy Tablo Yönetimi Sistemi**

Proje, migration sistemleri (Alembic vb.) yerine basit ve güvenilir bir yaklaşım kullanır:

**Otomatik Tablo Oluşturma:**
- Web uygulaması başladığında FastAPI startup event'i tetiklenir
- `Base.metadata.create_all(bind=engine)` komutu çalışarak gerekli tablolar otomatik oluşturulur
- Eğer tablolar zaten varsa, var olanları korur (üzerine yazmaz)

**Manuel Tablo Oluşturma (Yedek):**
- `create_tables.py` standalone script'i ile manuel olarak tablolar oluşturulabilir
- Bu script Alembic'e bağımlı değildir ve bağımsız çalışır

**Avantajları:**
- ✅ Migration dosyaları ve komplekslik yok
- ✅ Deployment sorunları yaşanmaz
- ✅ Basit ve güvenilir sistem
- ✅ Her environment'ta tutarlı çalışır

#### a. Veritabanı Modelleri (`b2b_web_app/models.py`)

Bu dosya, veritabanı tablolarına karşılık gelen Python sınıflarını (SQLAlchemy modelleri) tanımlar.

-   **`Base`**: `b2b_web_app/database.py` dosyasından import edilen ve tüm modellerin miras alacağı temel sınıftır (`declarative_base()` örneği).

-   **`PyOrderStatusEnum(enum.Enum)`**:
    *   Siparişlerin durumlarını tanımlayan standart bir Python `enum` sınıfıdır.
    *   Olası durumlar: `PENDING` ("Yeni Sipariş"), `PROCESSING` ("Hazırlanıyor"), `SHIPPED` ("Kargolandı"), `DELIVERED` ("Teslim Edildi"), `CANCELED` ("İptal Edildi"), `RETURNED` ("İade Edildi").

-   **`Order(Base)` sınıfı (`orders` tablosu):**
    *   Her bir müşteri siparişini temsil eder.
    *   **Alanlar:**
        *   `id` (Integer, Primary Key, Index): Siparişin benzersiz kimliği.
        *   `customer_name` (String(255), Nullable): Siparişi veren müşterinin adı. Boş olabilir.
        *   `created_at` (DateTime, Not Nullable, Server Default: `func.now()`): Siparişin oluşturulma zamanı. Veritabanı tarafında varsayılan olarak o anki zaman damgası atanır.
        *   `total_amount` (Float, Not Nullable): Siparişin toplam tutarı.
        *   `status` (SQLEnum(PyOrderStatusEnum), Not Nullable, Index, Default: `PyOrderStatusEnum.PENDING`): Siparişin durumu. `PyOrderStatusEnum` değerlerini alır ve veritabanında bir enum türü olarak saklanır. Varsayılan değeri "Yeni Sipariş"tir.
    *   **İlişkiler (Relationships):**
        *   `items`: Bu siparişe ait `OrderItem` nesnelerinin bir listesini tutar (`relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")`).
            *   `cascade="all, delete-orphan"`: Bir `Order` silindiğinde, ona bağlı tüm `OrderItem` kayıtlarının da silinmesini sağlar.

-   **`OrderItem(Base)` sınıfı (`order_items` tablosu):**
    *   Bir sipariş içindeki her bir ürün kalemini temsil eder.
    *   **Alanlar:**
        *   `id` (Integer, Primary Key, Index): Sipariş kaleminin benzersiz kimliği.
        *   `order_id` (Integer, Foreign Key to `orders.id`, Not Nullable): Bu kalemin ait olduğu siparişin kimliği.
        *   `product_code` (String(100), Not Nullable, Index): Ürünün stok kodu.
        *   `product_name` (String(255), Not Nullable): Ürünün adı.
        *   `barcode` (String(255), Nullable): Ürünün barkodu. Boş olabilir.
        *   `quantity` (Integer, Not Nullable): Sipariş edilen ürün miktarı.
        *   `unit_price` (Float, Not Nullable): Ürünün birim fiyatı.
    *   **İlişkiler (Relationships):**
        *   `order`: Bu kalemin ait olduğu `Order` nesnesini tutar (`relationship("Order", back_populates="items")`).

**Kullanım:**

-   Bu modeller, `b2b_web_app/main.py` içindeki API endpoint'leri tarafından sipariş oluşturma (`/api/orders POST`), listeleme (`/api/orders GET`), detay görme (`/api/orders/{order_id} GET`) ve durum güncelleme (`/api/orders/{order_id}/status PUT`) işlemleri sırasında SQLAlchemy aracılığıyla veritabanı ile etkileşim kurmak için kullanılır.
-   Modellerdeki değişiklikler web uygulaması yeniden başlatıldığında otomatik olarak veritabanına uygulanır (basit yaklaşım).

#### b. Veritabanı Kurulumu ve Oturum Yönetimi (`b2b_web_app/database.py`)

Bu dosya, SQLAlchemy kullanarak veritabanı bağlantısını kurmak, oturumları (session) yönetmek ve modeller için temel bir `Base` sınıfı sağlamakla görevlidir.

**Temel Bileşenler:**

1.  **`SQLALCHEMY_DATABASE_URL` (str):**
    *   Veritabanına bağlanmak için kullanılacak URL'yi tutar.
    *   Öncelikle `DATABASE_URL` adlı bir ortam değişkeninden bu değeri okumaya çalışır. Bu, genellikle Render gibi platformlarda canlı veritabanı bağlantı bilgisini sağlamak için kullanılır.
    *   Eğer `DATABASE_URL` ortam değişkeni bulunamazsa (yerel geliştirme ortamı varsayılarak), proje kök dizininde `b2p_database.db` adında bir SQLite veritabanı dosyası için bir bağlantı URL'si oluşturur (`sqlite:///path/to/project/b2p_database.db`).
    *   Kullanılacak son veritabanı URL'si konsola basılır.
2.  **`engine` (SQLAlchemy Engine):**
    *   `create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})` ile oluşturulur.
    *   SQLAlchemy'nin veritabanı ile iletişim kurmasını sağlayan çekirdek arayüzdür.
    *   `connect_args={"check_same_thread": False}` argümanı, özellikle SQLite kullanılıyorsa ve FastAPI gibi çoklu thread ortamlarında çalışılıyorsa gereklidir.
3.  **`SessionLocal` (SQLAlchemy sessionmaker):**
    *   `sessionmaker(autocommit=False, autoflush=False, bind=engine)` ile yapılandırılır.
    *   Veritabanı oturumları (session) oluşturmak için bir fabrikadır.
    *   `autocommit=False` ve `autoflush=False` ayarları, veritabanı değişikliklerinin manuel olarak `commit` edilmesini ve `flush` edilmesini sağlar, bu da daha kontrollü bir işlem akışı sunar.
4.  **`Base` (Declarative Base):**
    *   `declarative_base()` çağrısıyla oluşturulur.
    *   `b2b_web_app/models.py` içindeki tüm SQLAlchemy modellerinin (örn. `Order`, `OrderItem`) miras alacağı temel sınıftır. Bu sayede modeller veritabanı tablolarıyla eşleştirilir.
5.  **`get_db()` (Dependency Fonksiyonu):**
    *   FastAPI endpoint'lerinde bir veritabanı oturumu elde etmek için kullanılan bir "dependency"dir.
    *   Bir istek geldiğinde:
        *   `db = SessionLocal()` ile yeni bir veritabanı oturumu oluşturur.
        *   `yield db` ile bu oturumu request handler'a (endpoint fonksiyonuna) sağlar.
        *   Request işlendikten sonra (başarılı ya da hatalı fark etmeksizin) `finally` bloğunda `db.close()` ile oturumu kapatır. Bu, kaynakların düzgün bir şekilde serbest bırakılmasını sağlar.

**Kullanım:**

-   `engine` ve `Base`, `b2b_web_app/models.py` dosyası tarafından modelleri tanımlamak ve veritabanı ile ilişkilendirmek için kullanılır.
-   `SessionLocal`, `get_db` fonksiyonu içinde oturumlar oluşturmak için kullanılır.
-   `get_db` fonksiyonu, `b2b_web_app/main.py` içindeki veritabanı işlemi gerektiren API endpoint'lerine `Depends(get_db)` şeklinde enjekte edilir.
-   Uygulama başladığında `engine` üzerinden `Base.metadata.create_all()` çağrısıyla tablolar otomatik oluşturulur.

### 7. Cari Yönetim Modülü (Masaüstü Arayüzü - `customers_module.py`)

Bu modül, ana masaüstü uygulamasının (`main_window.py`) "Cariler" sekmesinde görüntülenen kullanıcı arayüzünü ve iş mantığını sağlar. Kullanıcıların cari hesapları listelemesine, aramasına, grup kodlarına göre filtrelemesine ve filtrelenmiş sonuçları `filtrelenen_cariler.json` dosyasına kaydetmesine olanak tanır. Bu JSON dosyası daha sonra `background_scheduler_cariler.pyw` tarafından web uygulamasına gönderilmek üzere **kullanılmıyor** (cari betiği doğrudan veritabanından kendi filtresiyle veri alıp gönderiyor), ancak bu dosya web arayüzündeki `/customer-balances` sayfası tarafından doğrudan okunuyor olabilir.

**Temel Kullanıcı Arayüzü Bileşenleri (`CustomersPage(QWidget)` sınıfı):**

-   **Ana Düzen (`QHBoxLayout` ve `QSplitter`):**
    *   Sayfa, yatay bir `QSplitter` ile iki ana panele ayrılmıştır: Sol tarafta grup kodu filtresi, sağ tarafta ise arama, tablo ve eylem butonları.
-   **Sol Panel (Grup Kodu Filtresi):**
    *   `group_code_label` (QLabel): "Grup Kodları Filtresi:" başlığını gösterir.
    *   `group_code_list_widget` (QListWidget): Veritabanından çekilen benzersiz cari grup kodlarını listeler. Kullanıcı buradan birden fazla grup kodu seçerek filtreleme yapabilir.
-   **Sağ Panel (Arama, Tablo, Butonlar):**
    *   `search_input` (QLineEdit): Kullanıcının cari kodu veya adına göre arama yapmasını sağlar. Arama, yazarken dinamik olarak tabloyu filtreler.
    *   `customers_table` (QTableWidget): Filtrelenmiş cari bilgilerini gösterir (Cari Kodu, Cari İsim, Borç Bakiyesi, Alacak Bakiyesi, Net Bakiye, Grup Kodu). Tablo, sütunlara tıklanarak sıralanabilir. Bakiye alanları `NumericTableWidgetItem` özel sınıfı ile sayısal olarak doğru sıralanır ve `helpers.format_currency_tr` ile formatlanır.
    *   `load_button` (QPushButton): "Carileri Yenile/Yükle" butonu, veritabanından tüm cari verilerini yeniden çeker, grup kodu filtresini günceller ve kayıtlı filtre ayarlarını uygular.
    *   `save_json_button` (QPushButton): "JSON Olarak Kaydet" butonu, o anda tabloda görüntülenen (filtrelenmiş) cari verilerini `filtrelenen_cariler.json` dosyasına kaydeder.

**İş Mantığı ve Fonksiyonlar:**

-   **Veritabanı Bağlantısı (`_ensure_db_connection`):**
    *   Modül başlatıldığında ve gerektiğinde `data_extractor.get_db_connection` kullanarak kalıcı bir veritabanı bağlantısı kurmaya çalışır. Bağlantı sorunları kullanıcıya bildirilir.
-   **Veri Yükleme ve Yenileme (`refresh_all_data`):**
    *   `data_extractor.fetch_customer_summary` ile tüm cari verilerini çeker ve `self.all_customers_data` içinde saklar.
    *   Grup kodu listesini (`populate_group_codes_filter`) ve mevcut filtre ayarlarını (`load_filter_settings`) yükler.
    *   `apply_filters` fonksiyonunu çağırarak tabloyu günceller.
    *   Yenileme sonrası, eğer tabloda veri varsa, `save_displayed_data_to_json(silent=True)` çağrılarak `filtrelenen_cariler.json` dosyası otomatik olarak güncellenir.
-   **Tablo Doldurma (`populate_table`):**
    *   Verilen veri listesiyle (filtrelenmiş cariler) `customers_table`'ı doldurur. Bakiye alanları için özel formatlama ve sıralama mantığı kullanılır.
-   **JSON Kaydetme (`save_displayed_data_to_json`):**
    *   `self.currently_displayed_data` (tabloda o an gösterilen veriler) listesini `filtrelenen_cariler.json` dosyasına kaydeder. `Decimal` türleri stringe çevrilir.
    *   Kaydetmeden önce mevcut filtre ayarlarını da (`save_filter_settings`) `customers_filter_settings.json` dosyasına kaydeder.
-   **Filtreleme Mantığı:**
    *   `populate_group_codes_filter()`: `self.all_customers_data` içindeki tüm benzersiz grup kodlarını sol paneldeki `QListWidget`'a ekler.
    *   `get_selected_group_codes()`: Kullanıcının `QListWidget`'tan seçtiği grup kodlarını döndürür.
    *   `filter_table_by_search()`: Sağ paneldeki arama kutusuna girilen metne göre filtreleme yapar.
    *   `apply_filters()`: Hem grup kodu seçimlerini hem de arama kutusundaki metni dikkate alarak `self.all_customers_data` listesini filtreler ve sonucu `populate_table` ile tabloya yansıtır.
-   **Filtre Ayarlarını Kaydetme/Yükleme (`save_filter_settings`, `load_filter_settings`):**
    *   Kullanıcının `group_code_list_widget` üzerinde yaptığı seçimler (hangi grup kodlarının işaretli olduğu) `customers_filter_settings.json` adlı bir dosyaya kaydedilir ve uygulama bir sonraki açılışında veya veri yenilemesinde bu ayarlar geri yüklenerek son kullanılan filtrelerin otomatik uygulanması sağlanır.

**Entegrasyonlar:**

-   `data_extractor.py`: Veritabanından cari verilerini çekmek için (`fetch_customer_summary`, `get_db_connection`).
-   `helpers.py`: Para birimi formatlama (`format_currency_tr`) ve ondalık sayıya çevirme (`to_decimal`) için.
-   `PySide6` (veya `PyQt6`): Kullanıcı arayüzü bileşenleri için.

**Loglama:**

-   Modül, `logging` kütüphanesini kullanarak kendi özel logger'ı (`__name__`) aracılığıyla loglama yapar. Özellikle filtre ayarlarının yüklenmesi ve JSON kaydetme gibi işlemler loglanır.

**Önemli Notlar:**

-   Bu modül, `main_window.py` tarafından bir sekme olarak yüklenir ve ana pencerenin status bar'ına erişimi vardır.
-   `filtrelenen_cariler.json` dosyasının güncellenmesi, bu modülün önemli bir çıktısıdır. Bu dosyanın web uygulaması (`b2b_web_app/main.py` içindeki `/customer-balances` sayfası veya doğrudan `cart.html`/`orders.html` tarafından) okunarak canlı sistemdeki cari listelerini beslediği anlaşılmaktadır.

### 8. Yardımcı Fonksiyonlar Modülü (`helpers.py`)

Bu modül, proje genelinde çeşitli yerlerde kullanılabilecek genel amaçlı yardımcı fonksiyonları barındırır. Şu anda sayısal veri dönüşümü, para birimi formatlama ve tarih formatlama üzerine odaklanmıştır.

**Temel Fonksiyonlar:**

1.  **`to_decimal(value, default=None) -> Decimal | None`:**
    *   Verilen herhangi bir `value` (string, float, int vb.) değeri `Decimal` tipine dönüştürmeye çalışır.
    *   `Decimal` tipine dönüştürmenin temel amacı, özellikle parasal hesaplamalarda float sayılarının neden olabileceği hassasiyet (precision) kayıplarını önlemektir.
    *   Dönüşüm sırasında bir hata (`InvalidOperation`, `ValueError`, `TypeError`) oluşursa, `default` parametresiyle belirtilen değeri (varsayılan olarak `None`) döndürür.
    *   Float değerler önce string'e çevrilir, sonra `Decimal`'e dönüştürülür; bu, float'tan `Decimal`'e doğrudan dönüşümdeki potansiyel hassasiyet sorunlarını engellemeye yardımcı olur.

2.  **`format_currency_tr(value, decimal_places=2, currency_symbol="") -> str`:**
    *   Sayısal bir `value` değerini, Türkiye'de yaygın olarak kullanılan para birimi formatına (binlik ayırıcı olarak nokta `.`, ondalık ayırıcı olarak virgül `,`) uygun bir string olarak formatlar.
    *   Önce `to_decimal` kullanarak gelen değeri `Decimal`'e çevirir. Eğer dönüşüm başarısız olursa veya değer `None` ise boş bir string (`""`) döndürür.
    *   `decimal_places` parametresi ile ondalık basamak sayısını belirler (varsayılan 2).
    *   `currency_symbol` parametresi ile (varsayılan boş string) formatlanmış miktarın sonuna bir para birimi sembolü (örn. "₺") eklenip eklenmeyeceğini ve nasıl ekleneceğini kontrol eder.
    *   **Örnek:** `format_currency_tr(12345.67)` -> `"12.345,67"`
    *   **Örnek:** `format_currency_tr(12345.67, currency_symbol="TL")` -> `"12.345,67 TL"`

3.  **`format_date_tr(date_value, fmt="%d.%m.%Y") -> str`:**
    *   Bir `datetime.datetime` veya `datetime.date` nesnesini, `strftime` formatlama kurallarına göre belirtilen `fmt` (format) string'ine uygun bir string'e çevirir.
    *   Varsayılan format `"%d.%m.%Y"` şeklindedir (örn. "28.05.2024").
    *   Eğer `date_value` geçerli bir tarih/zaman nesnesi değilse veya formatlama sırasında bir `ValueError` oluşursa, `date_value`'nun string temsilini doğrudan döndürür.

**Kullanım Alanları:**

-   `to_decimal`: Özellikle `data_extractor.py` ve `customers_module.py` gibi modüllerde veritabanından gelen veya kullanıcıdan alınan sayısal değerlerin (özellikle fiyatlar, bakiyeler) tutarlı ve doğru bir şekilde işlenmesi için kullanılır.
-   `format_currency_tr`: Masaüstü uygulamasının arayüzünde (`main_window.py`, `customers_module.py`) parasal değerlerin kullanıcıya gösterilmesi ve web uygulamasının şablonlarında (`b2b_web_app/main.py` içindeki Jinja2 filtresi) para formatlaması için kullanılır.
-   `format_date_tr`: Tarih bilgilerinin kullanıcı arayüzünde veya raporlarda standart bir formatta gösterilmesi için kullanılabilir (şu anki projede doğrudan kullanımı belirgin olmayabilir ancak genel bir yardımcıdır).

### 9. Yönetici Kullanıcısı Oluşturma Betiği (`create_admin.py`)

Bu betik, B2B web uygulamasına (`b2b_web_app/main.py`) giriş yapacak olan yönetici (admin) kullanıcısının kimlik bilgilerini oluşturmak ve kaydetmek için kullanılır. Betik, komut satırından interaktif olarak çalıştırılır.

**Temel İşleyiş:**

1.  **Şifre Hashleme Kurulumu:**
    *   `passlib.context.CryptContext` kullanılarak bir şifreleme bağlamı (`pwd_context`) oluşturulur. `bcrypt` algoritması tercih edilir.
2.  **Yapılandırma Dosyası Yolu:**
    *   Yönetici kimlik bilgilerinin kaydedileceği dosyanın adı `CONFIG_FILE` değişkeninde tutulur. Bu değer, `ADMIN_CONFIG_PATH` ortam değişkeninden okunmaya çalışılır; eğer ortam değişkeni tanımlı değilse, varsayılan olarak `admin_config.json` kullanılır.
3.  **Yardımcı Fonksiyonlar:**
    *   `get_password_hash(password)`: Verilen düz metin şifreyi `pwd_context.hash()` kullanarak hash'ler.
    *   `verify_password(plain_password, hashed_password)`: Verilen düz metin şifrenin, daha önce hash'lenmiş bir şifreyle eşleşip eşleşmediğini `pwd_context.verify()` kullanarak kontrol eder (Bu betikte doğrudan kullanılmıyor ancak `b2b_web_app/main.py` içinde kullanılır).
4.  **`create_admin_user()` Fonksiyonu:**
    *   Kullanıcıdan interaktif olarak bir "Admin kullanıcı adı" girmesini ister. Boş bırakılamaz.
    *   Kullanıcıdan `getpass.getpass()` (girişi gizleyerek) bir "Admin şifresi" ve ardından şifrenin onayını girmesini ister. Şifreler eşleşene kadar bu adım tekrarlanır. Şifre boş bırakılamaz.
    *   Girilen şifre `get_password_hash()` ile hash'lenir.
    *   Kullanıcı adı ve hash'lenmiş şifre bir sözlük (`admin_data`) içinde toplanır.
    *   Bu `admin_data` sözlüğü, `CONFIG_FILE` (varsayılan `admin_config.json`) adlı dosyaya JSON formatında, `indent=4` ile okunabilir şekilde yazılır.
    *   Kullanıcıya, oluşturulan dosyayı güvenli bir yerde saklaması ve `.gitignore` dosyasına eklemesi yönünde bir uyarı mesajı gösterilir.
5.  **Ana Çalıştırma Bloğu (`if __name__ == "__main__":`)**
    *   Betik doğrudan çalıştırıldığında, önce `CONFIG_FILE` adında bir dosyanın var olup olmadığını kontrol eder.
    *   **Dosya Varsa:** Kullanıcıya dosyanın zaten var olduğu ve içindeki kullanıcı adı bilgisi gösterilir. Yeni bir kullanıcı oluşturup mevcut dosyanın üzerine yazmak isteyip istemediği sorulur ("evet"/"hayır").
        *   Kullanıcı "evet" derse, `create_admin_user()` fonksiyonu çağrılır.
        *   Kullanıcı "hayır" derse, işlem iptal edilir.
    *   **Dosya Yoksa:** Doğrudan `create_admin_user()` fonksiyonu çağrılarak yeni bir yönetici kullanıcısı oluşturulur.
    *   Dosya okuma sırasında beklenmedik bir hata oluşursa, bu hata yakalanır ve kullanıcıya bilgi verildikten sonra yine de `create_admin_user()` çağrılır.

**Kullanım Amacı:**

-   Web uygulamasının `/login` sayfası üzerinden yönetici girişi yapılabilmesi için gerekli olan kullanıcı adı ve (hash'lenmiş) şifreyi içeren `admin_config.json` dosyasını oluşturmaktır.
-   `b2b_web_app/main.py` içindeki `get_admin_credentials()` fonksiyonu bu dosyı okuyarak yönetici kimlik bilgilerini alır ve giriş denemelerini doğrulamak için kullanır.

**Güvenlik Notları:**

-   Bu betik, şifreyi `bcrypt` gibi güçlü bir hash algoritmasıyla hash'leyerek saklar, bu iyi bir güvenlik pratiğidir.
-   Oluşturulan `admin_config.json` dosyası hassas bilgiler (kullanıcı adı ve hash'lenmiş şifre) içerdiğinden, yetkisiz erişime karşı korunmalı ve kesinlikle sürüm kontrol sistemlerine (örn. Git) gönderilmemelidir. Betiğin de belirttiği gibi `.gitignore` dosyasına eklenmelidir.

### 10. Web Uygulaması HTML Şablonları (`b2b_web_app/templates/`)

Web uygulaması, kullanıcı arayüzünü oluşturmak için Jinja2 şablon motoruyla işlenen HTML dosyalarını kullanır. Bu şablonlar, dinamik verileri göstermek ve kullanıcı etkileşimlerini sağlamak için hem sunucu tarafı değişkenlerini hem de istemci tarafı JavaScript'ini yoğun bir şekilde kullanır.

**Genel Bakış ve Temel Şablonlar:**

-   **`layout.html` (Varsa):** Genellikle projelerde ortak başlık, altbilgi, navigasyon menüsü gibi tüm sayfalarda tekrarlanan HTML yapılarını içeren bir temel şablon bulunur. Diğer şablonlar bu temel şablonu genişletir (`{% extends "layout.html" %}`). (Bu projede açıkça `layout.html` görülmese de, benzer bir yapı veya her şablonda ortak HTML başlıkları olabilir.)

-   **`products.html` (`/` endpoint'i):**
    *   Ana ürün listeleme sayfasıdır.
    *   Sunucu tarafından `received_products.json` dosyasından okunan ürün verileriyle doldurulur.
    *   Ürünleri genellikle bir liste veya kart görünümünde sergiler; ürün adı, fiyatı, resmi (`static/images/` altından) ve sepete ekleme butonu gibi bilgileri içerir.
    *   JavaScript ile sepete ekleme mantığını yönetebilir.

-   **`cart.html` (`/cart` endpoint'i):**
    *   Alışveriş sepeti sayfasını temsil eder.
    *   **Müşteri Seçimi:** JavaScript kullanarak (muhtemelen `filtrelenen_cariler.json` veya bir API endpoint'inden) müşteri listesini çeker ve kullanıcıya bir müşteri seçme olanağı sunar (örn. Select2 ile geliştirilmiş bir dropdown).
    *   **Sepet İçeriği:** JavaScript ile yönetilen, sepete eklenmiş ürünlerin listesini, miktarlarını, birim fiyatlarını ve toplam tutarı gösterir.
    *   **Sipariş Oluşturma:** "Siparişi Tamamla" veya benzeri bir buton, `saveOrderAndProceed` gibi bir JavaScript fonksiyonunu tetikler. Bu fonksiyon, sepet içeriğini ve seçilen müşteri bilgilerini toplayarak `/api/orders` (POST) endpoint'ine gönderir.

-   **`orders.html` (`/orders` endpoint'i):**
    *   Kullanıcının (veya yöneticinin) daha önce oluşturduğu siparişleri listeler.
    *   JavaScript kullanarak `/api/orders` (GET) endpoint'inden sipariş verilerini çeker ve bir tablo veya liste halinde gösterir.
    *   Sipariş ID'si, müşteri adı, oluşturulma tarihi, toplam tutar ve sipariş durumu gibi bilgileri içerebilir.
    *   Sipariş detaylarını görüntüleme veya sipariş durumunu (yönetici için) güncelleme gibi ek işlevlere sahip olabilir.
    *   Yeni bir sipariş oluşturma arayüzü için müşteri seçimi dropdown'ı da barındırabilir (benzer şekilde `cart.html`'deki gibi müşteri verilerini çeker).

-   **`customer_balances.html` (`/customer-balances` endpoint'i, Yönetici Korumalı):**
    *   Cari hesap bakiyelerini listelemek için kullanılır.
    *   Sunucu tarafında (`b2b_web_app/main.py` içindeki `view_customer_balances` fonksiyonu) `static/json_data/filtrelenen_cariler.json` dosyasından müşteri verilerini okur ve bu verileri şablona göndererek tabloyu oluşturur.
    *   Bu sayfa genellikle yönetici kimlik doğrulaması gerektirir.

-   **`login.html` (`/login` endpoint'i):**
    *   Web uygulamasına yönetici girişi yapmak için kullanılan formu içerir.
    *   Kullanıcı adı ve şifre giriş alanları bulunur.
    *   Form gönderildiğinde, verileri `/login` (POST) endpoint'ine yollar. Başarılı giriş sonrası genellikle `/admin/me` veya başka bir korumalı sayfaya yönlendirme yapılır.

-   **`admin_me.html` (`/admin/me` endpoint'i, Yönetici Korumalı):**
    *   Giriş yapmış yöneticinin bilgilerini veya yöneticiye özel bir karşılama sayfasını gösterir.
    *   Diğer yönetici işlevlerine bağlantılar içerebilir.

**Genel JavaScript Kullanımı:**

-   **Dinamik Veri Yükleme:** Birçok şablon, sayfa yüklendikten sonra veya kullanıcı etkileşimleriyle `fetch` API'sini kullanarak sunucudaki JSON dosyalarından (örn. `filtrelenen_cariler.json`, `received_products.json`) veya API endpoint'lerinden (örn. `/api/orders`) veri çeker.
-   **DOM Manipülasyonu:** Çekilen verilerle HTML tablolarını, listelerini veya diğer elementlerini dinamik olarak oluşturur ve günceller.
-   **Kullanıcı Etkileşimi:** Buton tıklamaları, form gönderimleri, arama kutusu girişleri gibi kullanıcı eylemlerini dinler ve bunlara yanıt verir.
-   **API İstekleri:** Özellikle sepet işlemleri ve sipariş oluşturma gibi durumlarda sunucuya veri göndermek (POST, PUT) veya veri almak (GET) için API endpoint'leriyle iletişim kurar.
-   **Harici Kütüphaneler:** Projede Select2 gibi JavaScript kütüphaneleri, kullanıcı arayüzü elemanlarını (örn. aranabilir dropdownlar) zenginleştirmek için kullanılmaktadır.

**Stil ve Statik Dosyalar:**

-   Şablonlar, `b2b_web_app/static/css/` altında bulunan CSS dosyalarıyla stillendirilir.
-   JavaScript dosyaları genellikle `b2b_web_app/static/js/` altında bulunur veya doğrudan HTML içine gömülür.
-   Ürün resimleri gibi diğer statik varlıklar `b2b_web_app/static/images/` altından sunulur.

### 11. Masaüstü Uygulaması Stil Tanımlamaları (`ui_styles.py`)

Bu modül, B2B masaüstü uygulamasının kullanıcı arayüzü (GUI) elemanlarının görünümünü ve hissini iyileştirmek için Qt Style Sheets (QSS) tanımlamalarını içerir.

**Temel Yapı:**

-   **`FONT_NAME` (str):** Uygulama genelinde kullanılması hedeflenen yazı tipi adını tutar (örn. "Lucida Console"). Ancak mevcut QSS içinde bu değişken doğrudan kullanılmamış, `font-size` tanımlamaları ayrı olarak yapılmıştır.
-   **`FONT_SIZE` (int):** Uygulama genelinde kullanılması hedeflenen temel yazı tipi boyutunu (punto olarak) tutar (örn. 10).
-   **`MODERN_STYLESHEET` (str):**
    *   Uygulamanın ana QSS string'ini içerir.
    *   Bu stil sayfası, çeşitli Qt widget'larının (arayüz elemanlarının) görünümünü özelleştirmek için kullanılır.

**Stil Tanımlanan Widget'lar ve Özellikler:**

-   **`QMainWindow`:**
    *   Arka plan rengi (açık gri: `#f0f0f0`).
-   **`QLabel`:**
    *   Yazı tipi boyutu (`10pt`).
    *   Metin rengi (koyu gri: `#333333`).
-   **`QLineEdit`, `QComboBox` (Giriş Alanları ve Açılır Listeler):**
    *   Kenarlık, iç boşluk (padding), köşe yuvarlaklığı (border-radius).
    *   Yazı tipi boyutu (`10pt`).
    *   Arka plan rengi (beyaz: `#ffffff`).
    *   Odaklanıldığında (`:focus`) kenarlık rengi (mavi: `#0078d7`).
    *   `QComboBox` için açılır ok (`::drop-down`, `::down-arrow`) ile ilgili bazı temel stil ayarlamaları (varsayılan oku kullanma eğiliminde).
-   **`QPushButton` (Butonlar):**
    *   Arka plan rengi (ana eylem mavisi: `#0078d7`).
    *   Yazı rengi (beyaz).
    *   Kenarlık yok, iç boşluk, yazı tipi boyutu (`10pt`), köşe yuvarlaklığı.
    *   Fare üzerine gelince (`:hover`) ve basıldığında (`:pressed`) farklı arka plan renkleri.
-   **`QListWidget` (Genel Sol Menü Listesi):**
    *   Arka plan rengi (menü için özel gri: `#e8ecf0`).
    *   Kenarlık yok, yazı tipi boyutu (`11pt`).
    *   Her bir öğe (`::item`) için iç boşluk, öğeler arası ayırıcı çizgi, metin rengi.
    *   Fare üzerine gelindiğinde (`::item:hover`) ve seçildiğinde (`::item:selected`) farklı arka plan ve metin renkleri.
    *   Seçili öğe için sol tarafta belirgin bir kenarlık.
-   **`QListWidget#productGroupFilterList` (Ürünler Sayfası - Grup Kodu Filtre Listesi):**
    *   Sol menüdeki genel `QListWidget` stilinden biraz farklılaşan, `objectName` ile hedeflenmiş özel stiller.
    *   Farklı padding, yazı tipi boyutu (`10pt`).
    *   Seçili öğe (`::item:selected`) için daha açık bir arka plan rengi (`#cce5ff`) ve farklı metin rengi.

## 12. Tablo Oluşturma Script'i (`create_tables.py`)

Bu standalone script, web uygulamasından bağımsız olarak veritabanı tablolarını manuel oluşturmak için kullanılır.

#### Temel İşleyiş:

- **Bağımsız Çalışma:** Alembic veya web uygulamasına bağımlı değildir
- **Environment Detection:** `DATABASE_URL` ortam değişkenini kontrol eder
- **Fallback Mechanism:** Ortam değişkeni yoksa yerel SQLite dosyası kullanır
- **SQLAlchemy Integration:** `Base.metadata.create_all()` ile tablolar oluşturulur

#### Kullanım:

```bash
python create_tables.py
```

#### Çıktı Örneği:

```
CREATE_TABLES: Manuel tablo oluşturma işlemi başlatılıyor...
CREATE_TABLES: Veritabanı URL'si: sqlite:///C:\path\to\b2b_database.db
CREATE_TABLES: Tablolar oluşturuluyor...
✅ CREATE_TABLES: Tablolar başarıyla oluşturuldu!
CREATE_TABLES: İşlem tamamlandı.
```

## 13. Sistem Değişiklikleri ve Güncellemeler

### 🚀 **Alembic'den SQLAlchemy Otomatik Tablo Oluşturmaya Geçiş**

**Kaldırılan Bileşenler:**
- `alembic/` klasörü ve tüm migration dosyaları
- `alembic.ini` konfigürasyon dosyası
- `requirements.txt`'den `alembic` ve `mako` paketleri
- `init_db.py` (artık gereksiz)

**Eklenen Bileşenler:**
- FastAPI startup event ile otomatik tablo oluşturma
- `create_tables.py` standalone script'i
- `.renderignore` dosyası (Poetry'yi devre dışı bırakmak için)
- `runtime.txt` dosyası (Python runtime belirtmek için)

**Deployment Komutları:**
- **Build Command:** `echo "Using pip instead of poetry"`
- **Start Command:** `pip install -r requirements.txt && python -m uvicorn b2b_web_app.main:app --host 0.0.0.0 --port $PORT`

**Avantajlar:**
- ✅ Migration sorunları tamamen eliminasyonu
- ✅ Deployment kompleksitesinin azalması
- ✅ Basit ve güvenilir sistem
- ✅ Yeni environment'larda hızlı kurulum
- ✅ Alembic dependency'si olmadığı için daha az hata riski

--- 