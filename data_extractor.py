'''
Veri Çekme Modülü

Bu modül, SQL Server'dan ürün verilerini çekmek için gerekli fonksiyonları içerir.
'''
import pyodbc
import json
import keyring
import os
import requests # requests kütüphanesini import et
from helpers import to_decimal, format_currency_tr # format_currency_tr eklendi
from decimal import Decimal # Decimal tipi için import eklendi (eğer __main__ dışında kullanılacaksa)
import image_processor # image_processor.py dosyamız
import logging # logging modülünü import et

# Decimal nesnelerini JSON'a serileştirmek için yardımcı fonksiyon
def decimal_serializer(obj):
    if isinstance(obj, Decimal):
        return str(obj) # veya float(obj) - string genellikle daha güvenlidir kayıp yaşamamak için
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

# Loglama yapılandırması
LOG_DIR = "b2b_web_app/logs"  # Log klasörünün yolu
LOG_FILE_NAME = "b2b_desktop_app.log" # Log dosyasının adı
LOG_FILE = os.path.join(LOG_DIR, LOG_FILE_NAME) # Tam log dosyası yolu

# Log dizininin var olduğundan emin ol, yoksa oluştur
if not os.path.exists(LOG_DIR):
    try:
        os.makedirs(LOG_DIR)
        print(f"Log dizini oluşturuldu: {LOG_DIR}") # Bilgilendirme için konsola yazdır
    except OSError as e:
        print(f"Log dizini oluşturulamadı ({LOG_DIR}): {e}")
        # Hata durumunda loglamayı mevcut dizine yönlendirebilir veya programı durdurabilirsiniz.
        # Şimdilik, hata olursa loglama varsayılan yere (veya hiç) yapılmayabilir.
        # Bu durumu daha robust hale getirmek isteyebilirsiniz.

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        # logging.StreamHandler() # Konsola da loglamak isterseniz bu satırı aktif edin
    ]
)

# db_connection_ui.py'deki sabitlerle aynı olmalı veya merkezi bir yerden alınmalı
SERVICE_NAME = "B2B_App_DB_Credentials"
SETTINGS_FILE = "settings.json"
DEFAULT_PLACEHOLDER_IMAGE = "images/urun_yok.png" # Varsayılan yer tutucu resim yolu

# Türkçe karakter düzeltme eşlemesi
CHAR_CORRECTION_MAP = {
    'Ý': 'İ', 'ý': 'i',
    'Þ': 'Ş', 'þ': 'ş',
    'Ð': 'Ğ', 'ð': 'ğ'
    # İhtiyaç duyulursa başka sorunlu karakterler ve düzeltmeleri eklenebilir
}

# Karakter düzeltmesi uygulanacak alanlar
FIELDS_TO_CORRECT = ['STOK_ADI', 'GRUP_KODU']
# Sayısal alanlar Decimal'e çevrilecek
NUMERIC_FIELDS_TO_CONVERT = ['BAKIYE', 'SATIS_FIAT1']

# Cari özet için sayısal alanlar (fetch_customer_summary için)
CUSTOMER_NUMERIC_FIELDS = ["BORC_BAKIYESI", "ALACAK_BAKIYESI", "NET_BAKIYE"]

def _correct_turkish_characters_in_row(row_dict):
    """Belirtilen alanlardaki Türkçe karakter hatalarını düzeltir."""
    for key, value in row_dict.items():
        if key in FIELDS_TO_CORRECT and isinstance(value, str):
            corrected_value = value
            for problematic_char, correct_char in CHAR_CORRECTION_MAP.items():
                corrected_value = corrected_value.replace(problematic_char, correct_char)
            row_dict[key] = corrected_value
    return row_dict

def _convert_numeric_fields_in_row(row_dict, field_list=NUMERIC_FIELDS_TO_CONVERT):
    """Belirtilen sayısal alanları (field_list kullanarak) Decimal tipine çevirir."""
    for key in field_list:
        if key in row_dict:
            # to_decimal None dönerse None olarak bırak, aksi halde Decimal olur.
            row_dict[key] = to_decimal(row_dict[key]) 
    return row_dict

def get_db_connection_settings():
    '''settings.json dosyasından sunucu, kullanıcı adı ve veritabanı adını okur.'''
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)
            return settings.get("server_address"), settings.get("username"), settings.get("db_name")
    except FileNotFoundError:
        print(f"Hata: {SETTINGS_FILE} dosyası bulunamadı.")
        return None, None, None
    except json.JSONDecodeError:
        print(f"Hata: {SETTINGS_FILE} dosyası geçerli bir JSON formatında değil.")
        return None, None, None
    except Exception as e:
        print(f"{SETTINGS_FILE} okunurken beklenmedik bir hata oluştu: {e}")
        return None, None, None

def get_db_connection(caller_info: str = "Unknown"):
    '''SQL Server'a bağlantı kurar ve bağlantı nesnesini döndürür.'''
    server, user, db_name = get_db_connection_settings()
    if not server or not user or not db_name:
        logging.error(f"get_db_connection (called by {caller_info}): Bağlantı ayarları eksik.")
        return None

    password = keyring.get_password(SERVICE_NAME, user)
    if password is None:
        logging.error(f"get_db_connection (called by {caller_info}): '{user}' için şifre keyring'de bulunamadı.")
        return None

    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};" 
        f"SERVER={server};"
        f"DATABASE={db_name};"
        f"UID={user};"
        f"PWD={password};"
        f"TrustServerCertificate=yes;"
    )
    
    conn = None
    try:
        conn = pyodbc.connect(conn_str, timeout=5)
        logging.info(f"get_db_connection (called by {caller_info}): Veritabanına başarıyla bağlanıldı ({server}/{db_name}).")
        return conn 
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        logging.error(f"get_db_connection (called by {caller_info}): Veritabanı bağlantı hatası: {sqlstate} - {ex}")
        return None
    except Exception as e:
        logging.error(f"get_db_connection (called by {caller_info}): Bağlantı sırasında beklenmedik bir hata oluştu: {e}")
        return None

DEFAULT_API_URL = "https://firatb2b.onrender.com/api/products"

def fetch_product_data(connection, excluded_groups=None):
    '''
    Belirlenen ürün verilerini SQL Server'dan çeker, Türkçe karakter düzeltmesi yapar,
    sayısal alanları Decimal tipine dönüştürür ve her ürün için IMAGE_PATH_WEB ekler.
    Eğer excluded_groups listesi verilirse, bu gruplara ait ürünler sorguya dahil edilmez.
    '''
    if connection is None:
        print("fetch_product_data: Veritabanı bağlantısı None.")
        logging.warning("fetch_product_data çağrıldı ancak veritabanı bağlantısı None.")
        return None

    base_query = """
    SELECT
        ts.STOK_KODU,
        ts.STOK_ADI,
        ssb.BAKIYE,
        ts.SATIS_FIAT1,
        RTRIM(LTRIM(ts.GRUP_KODU)) AS GRUP_KODU, -- GRUP_KODU burada temizleniyor
        ts.BARKOD1
    FROM
        TBLSTSABIT ts
    LEFT JOIN
        SenkronixStokBakiye ssb ON ts.STOK_KODU = ssb.STOK_KODU COLLATE Turkish_CI_AS
    WHERE
        ssb.BAKIYE <> 0
        AND RTRIM(LTRIM(ts.GRUP_KODU)) NOT IN ('KULLANMA', 'INT', 'PALET')
        AND ts.STOK_KODU IS NOT NULL
        AND ts.STOK_KODU <> ''
    """
    
    params = []
    additional_conditions = []

    if excluded_groups and isinstance(excluded_groups, list) and len(excluded_groups) > 0:
        # excluded_groups listesindeki her bir grup için bir soru işareti (?) oluştur
        placeholders = ', '.join(['?' for _ in excluded_groups])
        additional_conditions.append(f"RTRIM(LTRIM(ts.GRUP_KODU)) NOT IN ({placeholders})")
        params.extend(excluded_groups)
        logging.info(f"fetch_product_data: Şu gruplar hariç tutulacak: {excluded_groups}")

    if additional_conditions:
        query = f"{base_query} AND {' AND '.join(additional_conditions)}"
    else:
        query = base_query
    
    logging.debug(f"fetch_product_data SQL Sorgusu: {query}")
    if params:
        logging.debug(f"fetch_product_data SQL Parametreleri: {params}")
        
    results = []
    try:
        cursor = connection.cursor()
        cursor.execute(query, params) # Parametreleri sorguya güvenli bir şekilde ekle
        
        columns = [column[0] for column in cursor.description]
        
        for row_idx, row_values in enumerate(cursor.fetchall()):
            row_dict = dict(zip(columns, row_values))
            
            # Türkçe karakter ve sayısal alan dönüşümlerini yap
            corrected_row_dict = _correct_turkish_characters_in_row(row_dict)
            converted_row_dict = _convert_numeric_fields_in_row(corrected_row_dict)

            # Resim yolunu ekle
            stok_kodu_str = str(converted_row_dict.get('STOK_KODU', '')).strip()
            stok_adi_raw = converted_row_dict.get('STOK_ADI', '') # Zaten düzeltilmiş olmalı
            
            # image_processor.clean_product_name ürün adını arama için temizler.
            # find_image_url_for_product şu anda None döndürüyor.
            # Bu, batch_image_downloader.py geliştirildikten sonra anlamlı olacak.
            # Şimdilik, download_and_save_image'ı None URL ile çağırarak sadece yerel varlık kontrolü yapacağız.
            # cleaned_stok_adi = image_processor.clean_product_name(stok_adi_raw) 
            # image_url_found = find_image_url_for_product(cleaned_stok_adi, stok_adi_raw, stok_kodu_str)
            
            # Doğrudan None URL ile çağırarak yerel resmi kontrol et/kullan
            image_path_web = image_processor.download_and_save_image(None, stok_kodu_str)
            
            if not image_path_web:
                image_path_web = DEFAULT_PLACEHOLDER_IMAGE # images/urun_yok.png
            
            converted_row_dict['IMAGE_PATH_WEB'] = image_path_web
            results.append(converted_row_dict)
            
            # Her 50 üründe bir ilerleme mesajı (isteğe bağlı)
            # if (row_idx + 1) % 50 == 0:
            #     print(f"  {row_idx + 1} ürün işlendi (resim yolları eklendi)...")

        print(f"{len(results)} adet ürün verisi çekildi ve resim yolları eklendi.")
        return results
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        print(f"Veri çekme sırasında SQL hatası (fetch_product_data): {sqlstate} - {ex}")
        logging.error(f"Veri çekme sırasında SQL hatası (fetch_product_data): {sqlstate} - {ex}. Sorgu: {query}, Parametreler: {params}", exc_info=True)
        return None
    except Exception as e:
        print(f"Veri çekme sırasında beklenmedik bir hata oluştu (fetch_product_data): {e}")
        logging.error(f"Veri çekme sırasında beklenmedik bir hata (fetch_product_data): {e}. Sorgu: {query}, Parametreler: {params}", exc_info=True)
        return None
    # finally bloğu burada olmamalı, bağlantıyı çağıran yer kapatmalı

def extract_data_from_db(connection_params):
    server = connection_params.get('server')
    database = connection_params.get('database')
    username = connection_params.get('username')
    # Şifre artık doğrudan connection_params'tan gelmiyor, keyring'den alınıyor.
    # Ancak, main_window.py'nin bu fonksiyonu çağırırken şifreyi keyring'den alıp
    # connection_params'a eklemesi daha tutarlı olabilir. Şimdilik get_password kullanalım.
    password = get_password(username) 

    if not all([server, database, username, password]):
        missing = [k for k,v in {'server':server, 'database':database, 'username':username, 'password':password}.items() if not v]
        print(f"Veritabanı bağlantı bilgileri eksik: {missing}. Lütfen ayarları kontrol edin.")
        return []

    products = []
    try:
        conn_str = (
            f'DRIVER={{SQL Server}};'
            f'SERVER={server};'
            f'DATABASE={database};'
            f'UID={username};'
            f'PWD={password};'
            f'TrustServerCertificate=yes;' 
        )
        conn = pyodbc.connect(conn_str, timeout=10)
        cursor = conn.cursor()
        query = """
        SELECT 
            RTRIM(LTRIM(s.STOK_KODU)) AS STOK_KODU, 
            s.STOK_ADI, 
            b.BAKIYE, 
            f.SATIS_FIAT1, 
            s.GRUP_KODU, 
            s.BARKOD1
        FROM TBLSTSABIT s
        LEFT JOIN SenkronixStokBakiye b ON RTRIM(LTRIM(s.STOK_KODU)) = RTRIM(LTRIM(b.STOK_KODU))
        LEFT JOIN TBLSTOKFIAT f ON RTRIM(LTRIM(s.STOK_KODU)) = RTRIM(LTRIM(f.STOK_KODU)) AND f.ACIKLAMA = 'SATIS_FIAT1' -- veya f.FIATNO = 1 gibi bir koşul
        WHERE 
            RTRIM(LTRIM(s.GRUP_KODU)) NOT IN ('KULLANMA', 'INT', 'PALET') 
            AND b.BAKIYE <> 0
            AND RTRIM(LTRIM(s.STOK_KODU)) <> '' 
        ORDER BY s.GRUP_KODU, s.STOK_KODU;
        """
        cursor.execute(query)
        
        for row in cursor.fetchall():
            try:
                stok_adi_raw = row.STOK_ADI
                grup_kodu_raw = row.GRUP_KODU

                stok_adi_corrected = stok_adi_raw.replace('Ý','İ').replace('Þ','Ş').replace('Ð','Ğ') if stok_adi_raw else ''
                grup_kodu_corrected = grup_kodu_raw.replace('Ý','İ').replace('Þ','Ş').replace('Ð','Ğ') if grup_kodu_raw else ''
                
                stok_kodu_str = str(row.STOK_KODU).strip()
                cleaned_stok_adi = image_processor.clean_product_name(stok_adi_corrected)
                
                image_url_found = find_image_url_for_product(cleaned_stok_adi, stok_adi_corrected, stok_kodu_str)
                image_path_web = image_processor.download_and_save_image(image_url_found, stok_kodu_str)
                
                if not image_path_web:
                    image_path_web = DEFAULT_PLACEHOLDER_IMAGE

                product_data = {
                    'STOK_KODU': stok_kodu_str,
                    'STOK_ADI': stok_adi_corrected,
                    'BAKIYE': to_decimal(row.BAKIYE),
                    'SATIS_FIAT1': to_decimal(row.SATIS_FIAT1),
                    'GRUP_KODU': grup_kodu_corrected,
                    'BARKOD1': row.BARKOD1.strip() if row.BARKOD1 else '',
                    'IMAGE_PATH_WEB': image_path_web
                }
                products.append(product_data)
            except Exception as e:
                stok_kodu_debug = row.STOK_KODU if hasattr(row, 'STOK_KODU') and row.STOK_KODU else 'Bilinmiyor'
                print(f"Satır işlenirken hata (STOK_KODU: {stok_kodu_debug}): {e}")
                continue
        
        conn.close()

    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        print(f"Veritabanı hatası (extract_data_from_db): {sqlstate} - {ex}")
    except Exception as e:
        print(f"Veri çekme sırasında genel bir hata (extract_data_from_db): {e}")
    
    return products

def save_data_to_json(data, filename="urun_verileri_onizleme.json"):
    """Veriyi JSON dosyasına kaydeder. Decimal tiplerini stringe çevirir."""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4, default=decimal_serializer)
        
        print(f"{filename} dosyasına {len(data)} kayıt başarıyla yazıldı.")
        logging.info(f"{filename} dosyasına {len(data)} kayıt başarıyla yazıldı.")
        return True
    except Exception as e:
        print(f"JSON dosyasına yazılırken hata: {e}")
        return False

def send_data_to_web_api(product_data: list, api_url: str = DEFAULT_API_URL) -> tuple[bool, str]:
    settings = load_settings() # Ayarları yükle
    PRODUCTS_API_KEY_VALUE = settings.get("products_api_key") # settings.json'dan oku

    if not PRODUCTS_API_KEY_VALUE:
        logging.error("KRİTİK HATA: PRODUCTS_API_KEY, settings.json dosyasında bulunamadı veya boş.")
        logging.warning("Lütfen settings.json dosyasına 'products_api_key': 'DEĞERİNİZ' şeklinde ekleyin.")
        # Ortam değişkeni fallback'ini kaldırabilir veya bırakabilirsiniz, ama settings.json öncelikli olmalı.
        # PRODUCTS_API_KEY_VALUE = os.environ.get("PRODUCTS_API_KEY") # Fallback
        # if not PRODUCTS_API_KEY_VALUE:
        #     logging.warning("Ortam değişkeni olarak da PRODUCTS_API_KEY bulunamadı.")
        #     PRODUCTS_API_KEY_VALUE = "dev-temporary-products-api-key-replace-me"
        return False, "API Anahtarı settings.json dosyasında bulunamadı. Lütfen ayarları kontrol edin."

    if not product_data:
        message = "Gönderilecek ürün verisi bulunmuyor."
        logging.warning(message)
        return False, message

    # Decimal nesnelerini string'e çevir (JSON için)
    data_for_json = []
    for item_dict in product_data:
        processed_item = {}
        for key, value in item_dict.items():
            if isinstance(value, Decimal):
                processed_item[key] = str(value)
            # IMAGE_PATH_WEB için özel bir işlem gerekmiyor, zaten string olmalı
            else:
                processed_item[key] = value
        data_for_json.append(processed_item)
    
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": PRODUCTS_API_KEY_VALUE  # API anahtarını header'a ekle
    }
    item_count = len(data_for_json)
    logging.info(f"\'{api_url}\' adresine {item_count} adet ürün gönderilmeye çalışılıyor (API Anahtarı ile)...")

    # --- TEST İÇİN GEÇİCİ GECİKME KALDIRILIYOR ---
    # print("DEBUG: API isteği öncesi 2 saniye bekleniyor...")
    # time.sleep(2) # 2 saniyelik gecikme
    # print("DEBUG: Bekleme bitti, API isteği gönderiliyor.")
    # --- TEST İÇİN GEÇİCİ GECİKME SONU ---

    try:
        response = requests.post(api_url, json=data_for_json, headers=headers, timeout=30)
        response.raise_for_status()  # HTTP 4xx veya 5xx durum kodlarında bir HTTPError fırlatır

        # Başarılı yanıt
        response_data = response.json() # API'den gelen JSON yanıtını al
        success_message = response_data.get("message", f"{item_count} ürün başarıyla gönderildi, ancak API'den özel mesaj alınamadı.")
        logging.info(f"Veri başarıyla gönderildi. API Yanıtı: {success_message}. HTTP Durumu: {response.status_code}")
        return True, success_message

    except requests.exceptions.ConnectionError as e:
        error_message = f"API bağlantı hatası ({api_url}): {e}"
        logging.error(error_message)
        return False, error_message
    except requests.exceptions.Timeout as e:
        error_message = f"API isteği zaman aşımına uğradı ({api_url}): {e}"
        logging.error(error_message)
        return False, error_message
    except requests.exceptions.HTTPError as e:
        # HTTPError durumunda, response içeriğini de loglamaya çalışalım (eğer varsa)
        error_content = ""
        if e.response is not None:
            try:
                error_content = e.response.json() # JSON yanıtı varsa onu al
            except json.JSONDecodeError:
                error_content = e.response.text # JSON değilse text olarak al
        error_message = f"API HTTP hatası ({api_url}): {e}. Durum Kodu: {e.response.status_code if e.response else 'N/A'}. Yanıt: {error_content}"
        logging.error(error_message)
        return False, f"API Hatası (Kod: {e.response.status_code if e.response else 'N/A'}): Daha fazla detay için logları kontrol edin."
    except requests.exceptions.RequestException as e:
        # Diğer tüm requests kütüphanesi hataları için
        error_message = f"API isteğinde genel bir hata oluştu ({api_url}): {e}"
        logging.error(error_message)
        return False, error_message
    except Exception as e:
        # Beklenmedik diğer hatalar
        error_message = f"Veri gönderimi sırasında beklenmedik bir hata oluştu: {e}"
        logging.exception(error_message) # exception metodu stack trace'i de loglar
        return False, error_message

def load_settings():
    """Ayarları settings.json dosyasından yükler."""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                # print(f"Ayarlar yüklendi: {settings}") # Debug için
                return settings
    except Exception as e:
        print(f"Ayarlar yüklenirken hata: {e}")
    return {}

def get_password(username):
    """Belirtilen kullanıcı adı için şifreyi keyring'den alır."""
    if not username:
        print("Şifre almak için kullanıcı adı belirtilmedi.")
        return None
    try:
        password = keyring.get_password(SERVICE_NAME, username)
        # print(f"'{username}' için şifre keyring'den alındı.") # Debug için
        return password
    except Exception as e:
        print(f"Keyring'den şifre alınırken hata ({SERVICE_NAME} - {username}): {e}")
        return None

# (KULLANICI TARAFINDAN GELİŞTİRİLECEK YER)
def find_image_url_for_product(cleaned_product_name: str, original_stok_adi: str, stok_kodu: str) -> str | None:
    """
    (KULLANICI TARAFINDAN GELİŞTİRİLECEK YER - batch_image_downloader.py'deki ile benzer)
    Temizlenmiş ürün adını kullanarak (örneğin DuckDuckGo + AI ile) bir resim URL'i bulur.
    Bu fonksiyon, sizin özel mantığınızı içerecektir.
    Şimdilik test için None döndürür.
    """
    # print(f"  [FIND IMAGE URL YER TUTUCUSU] '{cleaned_product_name}' için resim URL'i aranıyor (STOK_KODU: {stok_kodu})...")
    # Gerçek implementasyonunuz burada olacak.
    # Örnek:
    # if "COCA COLA" in cleaned_product_name.upper():
    #     return "https://www.example.com/images/coca_cola.jpg" 
    return None # Şimdilik her zaman None

def fetch_unique_group_codes(db_conn=None):
    """
    TBLCASABIT tablosundan, 'GG' ve '135' ile BAŞLAMAYAN cari kodlarına ait
    benzersiz GRUP_KODU değerlerini çeker.
    Eğer dışarıdan bir db_conn verilmezse, kendi bağlantısını kurar ve kapatır.
    """
    close_conn_locally = False
    if db_conn is None:
        db_conn = get_db_connection(caller_info="fetch_unique_group_codes")
        if not db_conn:
            logging.error("fetch_unique_group_codes: Veritabanı bağlantısı kurulamadı.")
            return [] # Bağlantı yoksa boş liste dön
        close_conn_locally = True

    group_codes = []
    try:
        with db_conn.cursor() as cursor:
            sql_query = """
            SELECT DISTINCT
                RTRIM(LTRIM(ISNULL(CB.GRUP_KODU, ''))) AS GRUP_KODU
            FROM
                dbo.TBLCASABIT CB
            WHERE
                CB.CARI_KOD NOT LIKE 'GG%'
                AND CB.CARI_KOD NOT LIKE '135%'
            ORDER BY
                GRUP_KODU;
            """
            cursor.execute(sql_query)
            group_codes = [row.GRUP_KODU for row in cursor.fetchall() if row.GRUP_KODU] # Sadece boş olmayanları al
        logging.info(f"Başarıyla {len(group_codes)} adet benzersiz grup kodu çekildi.")
        return group_codes
    except pyodbc.Error as err:
        logging.error(f"Benzersiz grup kodları çekilirken SQL Hatası: {err}")
        return []
    except Exception as e:
        logging.error(f"Benzersiz grup kodları çekilirken beklenmedik hata: {e}")
        return []
    finally:
        if close_conn_locally and db_conn:
            try:
                db_conn.close()
            except Exception as e:
                logging.error(f"fetch_unique_group_codes: Veritabanı bağlantısı kapatılırken hata: {e}")

def fetch_customer_summary(db_conn=None, selected_group_codes=None): # selected_group_codes eklendi
    """
    dbo.TBLCASABIT tablosundan temel cari bilgilerini çeker.
    CARI_KODU 'GG' veya '135' ile başlayanları hariç tutar.
    Eğer selected_group_codes listesi verilirse, sadece o grup kodlarına ait carileri çeker.
    Eğer dışarıdan bir db_conn verilmezse, kendi bağlantısını kurar ve kapatır.
    """
    close_conn_locally = False
    if db_conn is None:
        db_conn = get_db_connection(caller_info="fetch_customer_summary")
        if not db_conn:
            logging.error("fetch_customer_summary: Veritabanı bağlantısı kurulamadı.")
            return None 
        close_conn_locally = True

    customers = []
    try:
        with db_conn.cursor() as cursor:
            base_sql_query = """
            SELECT
                CB.CARI_KOD,
                dbo.TRK(CB.CARI_ISIM) AS CARI_ISIM,
                ISNULL(CB.CM_BORCT, 0) AS BORC_BAKIYESI,
                ISNULL(CB.CM_ALACT, 0) AS ALACAK_BAKIYESI,
                (ISNULL(CB.CM_BORCT, 0) - ISNULL(CB.CM_ALACT, 0)) AS NET_BAKIYE,
                CB.GRUP_KODU
            FROM
                dbo.TBLCASABIT CB
            """
            
            params = []
            where_clauses = ["CB.CARI_KOD NOT LIKE 'GG%'", "CB.CARI_KOD NOT LIKE '135%'"]

            if selected_group_codes: # Eğer seçili grup kodu varsa
                if isinstance(selected_group_codes, list) and len(selected_group_codes) > 0:
                    placeholders = ', '.join(['?' for _ in selected_group_codes])
                    where_clauses.append(f"CB.GRUP_KODU IN ({placeholders})")
                    params.extend(selected_group_codes)
            
            if where_clauses:
                full_sql_query = f"{base_sql_query} WHERE {' AND '.join(where_clauses)} ORDER BY CB.CARI_ISIM;"
            else: # Bu durum pek olası değil çünkü CARI_KOD filtreleri her zaman var
                full_sql_query = f"{base_sql_query} ORDER BY CB.CARI_ISIM;"

            if params:
                cursor.execute(full_sql_query, params)
            else:
                cursor.execute(full_sql_query)
                
            columns = [column[0] for column in cursor.description]
            for row in cursor.fetchall():
                row_dict = dict(zip(columns, row))
                # Cari için Türkçe karakter düzeltmesi (eğer gerekiyorsa - şimdilik atlandı, alanlar bilinmiyor)
                # row_dict = _correct_turkish_characters_in_row(row_dict) # Hangi alanlar için?
                # Cari için sayısal alan dönüşümü
                row_dict = _convert_numeric_fields_in_row(row_dict, field_list=CUSTOMER_NUMERIC_FIELDS)
                customers.append(row_dict)
        logging.info(f"Başarıyla {len(customers)} adet cari özeti çekildi (Grup Filtresi: {selected_group_codes if selected_group_codes else 'Yok'}).")
        return customers
    except pyodbc.Error as err:
        logging.error(f"Cari özetleri çekilirken SQL Hatası: {err}. Sorgu: {full_sql_query if 'full_sql_query' in locals() else 'Tanımsız'}")
        return None
    except Exception as e:
        logging.error(f"Cari özetleri çekilirken beklenmedik hata: {e}. Sorgu: {full_sql_query if 'full_sql_query' in locals() else 'Tanımsız'}")
        return None
    finally:
        if close_conn_locally and db_conn:
            try:
                db_conn.close()
            except Exception as e:
                logging.error(f"fetch_customer_summary: Veritabanı bağlantısı kapatılırken hata: {e}")

if __name__ == '__main__':
    # Test amaçlı
    # test_conn = get_db_connection()
    # if test_conn:
    #     print("Veritabanı bağlantısı başarılı.")
    #     # product_data = fetch_product_data(test_conn)
    #     # if product_data:
    #     #     print(f"{len(product_data)} ürün çekildi.")
    #     #     # print(product_data[0]) # İlk ürünü yazdır
    #     # else:
    #     #     print("Ürün verisi çekilemedi.")
    #     customer_data = fetch_customer_summary(test_conn)
    #     if customer_data:
    #         print(f"{len(customer_data)} cari özeti çekildi.")
    #         if customer_data:
    #             print(customer_data[0]) # İlk cariyi yazdır
    #     else:
    #         print("Cari özeti verisi çekilemedi.")
    #     test_conn.close()
    # else:
    #     print("Veritabanı bağlantısı kurulamadı.")
    pass # Ana blok boş kalmasın diye pass eklendi

# ... ( extract_data_from_db ve diğerleri burada devam etmeli ) ... 