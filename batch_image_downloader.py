import pyodbc
import json
import keyring
import os

# Yerel modüllerimizi import edelim
import image_processor 
from helpers import to_decimal # Eğer to_decimal gibi yardımcı fonksiyonlar gerekirse

# DuckDuckGo arama kütüphanesini import etmeyi deneyelim
try:
    from duckduckgo_search import DDGS
    DUCKDUCKGO_SEARCH_AVAILABLE = True
except ImportError:
    DUCKDUCKGO_SEARCH_AVAILABLE = False
    print("Uyarı: 'duckduckgo_search' kütüphanesi bulunamadı. Resim URL'i arama özelliği çalışmayacak.")
    print("Kurmak için: pip install duckduckgo-search")

# --- Ayar Yükleme Fonksiyonları (main_window.py veya data_extractor.py'den uyarlanabilir) ---
# Bu kısım, veritabanı bağlantı ayarlarını nasıl yönettiğinize bağlı olarak ayarlanmalıdır.
# Örnek olarak, main_window.py'deki benzer fonksiyonlar buraya kopyalanabilir veya
# ayar yönetimi için ortak bir modül kullanılabilir.

SETTINGS_FILE = 'settings.json'
SERVICE_NAME = "B2B_App_DB_Credentials"

def load_settings():
    """Ayarları settings.json dosyasından yükler."""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Ayarlar yüklenirken hata: {e}")
    return {}

def get_password(username):
    """Belirtilen kullanıcı adı için şifreyi keyring'den alır."""
    try:
        password = keyring.get_password(SERVICE_NAME, username)
        return password
    except Exception as e:
        print(f"Keyring'den şifre alınırken hata: {e}")
        return None
# --- Ayar Yükleme Fonksiyonları SONU ---

def get_db_connection():
    """Veritabanı bağlantısı kurar ve bağlantı nesnesini döndürür."""
    settings = load_settings()
    if not settings:
        print(f"Hata: Ayarlar '{SETTINGS_FILE}' dosyasından yüklenemedi veya dosya boş.")
        return None
    
    # settings.json'daki anahtar adlarına göre oku
    server = settings.get('server_address') # Doğrudan ana seviyeden oku
    database = settings.get('db_name')      # Doğrudan ana seviyeden oku
    username = settings.get('username')      # Doğrudan ana seviyeden oku
    
    if not all([server, database, username]):
        # Hangi değerin eksik olduğunu daha net belirtelim
        missing_keys = []
        if not server: missing_keys.append('server_address')
        if not database: missing_keys.append('db_name')
        if not username: missing_keys.append('username')
        print(f"Hata: Veritabanı bağlantı ayarları eksik. '{SETTINGS_FILE}' dosyasında şu anahtarlar eksik: {missing_keys}")
        return None

    password = get_password(username)
    if password is None:
        print(f"Hata: '{username}' için şifre keyring'de ({SERVICE_NAME} altında) bulunamadı.")
        return None

    try:
        conn_str = (
            f'DRIVER={{SQL Server}};' # Veya sisteminizdeki uygun sürücü adı: {{ODBC Driver 17 for SQL Server}}
            f'SERVER={server};'
            f'DATABASE={database};'
            f'UID={username};'
            f'PWD={password};'
            f'TrustServerCertificate=yes;'
        )
        conn = pyodbc.connect(conn_str, timeout=5)
        print(f"'{server}' üzerindeki '{database}' veritabanına başarıyla bağlanıldı.")

        # Türkçe karakterler için encoding ayarları
        try:
            print("Veritabanı bağlantısı için encoding ayarları deneniyor (kaynak: cp1254, hedef: utf-8)...")
            # SQL_CHAR (VARCHAR, CHAR vb.) verilerin cp1254 olduğunu varsayıyoruz.
            conn.setdecoding(pyodbc.SQL_CHAR, encoding='cp1254', ctype=pyodbc.SQL_CHAR)
            # SQL_WCHAR (NVARCHAR, NCHAR vb.) verilerin zaten Unicode (örn. UTF-16) olduğunu varsayıyoruz,
            # Python'a geçerken UTF-8 string olması için.
            conn.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-8', ctype=pyodbc.SQL_WCHAR)
            # Python tarafında tüm stringlerin (sorgu sonuçları dahil) UTF-8 olmasını istiyoruz.
            conn.setencoding(encoding='utf-8') 
            print("Encoding ayarları varsayılan olarak uygulandı.")
        except Exception as e:
            print(f"Encoding ayarları yapılırken bir hata oluştu: {e}. Varsayılan ayarlarla devam edilecek.")
            # Hata olsa bile bağlantıyı döndürmeye devam et, belki bazı sürücüler bu ayarları desteklemez
            # veya farklı şekilde yapılandırılması gerekir.

        return conn
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        # Daha detaylı hata mesajı
        driver_errors = [e for e in ex.args[1] if isinstance(e, str)]
        driver_error_message = ", ".join(driver_errors) if driver_errors else "Detay yok"
        print(f"Veritabanı bağlantı hatası: SQLSTATE {sqlstate} - {driver_error_message} - {ex}")
        return None
    except Exception as e:
        print(f"Veritabanı bağlantısı sırasında genel bir hata oluştu: {e}")
        return None

def find_image_url_via_search_ai(cleaned_product_name: str, original_stok_adi: str, stok_kodu: str, barkod: str | None) -> str | None:
    """
    Temizlenmiş ürün adını veya barkodu kullanarak (DuckDuckGo ile) bir resim URL'i bulmaya çalışır.
    Önce barkod ile arama yapar, bulunamazsa ürün adıyla devam eder.
    Bu fonksiyon, basit bir örnek sunar ve ilk bulunan görseli almaya çalışır.
    Daha gelişmiş AI tabanlı seçim için bu fonksiyonun iyileştirilmesi gerekir.
    """
    if not DUCKDUCKGO_SEARCH_AVAILABLE:
        print(f"  [UYARI] duckduckgo_search kütüphanesi kurulu olmadığı için resim aranamıyor.")
        return None

    search_term_used = ""

    # 1. Barkod ile arama yapmayı dene
    if barkod and barkod.strip():
        search_query_barcode = f"{barkod.strip()} ürün"
        print(f"  [DUCKDUCKGO BARKOD ARAMA] '{search_query_barcode}' için resim URL'i aranıyor (STOK_KODU: {stok_kodu})...")
        search_term_used = f"Barkod: {barkod.strip()}"
        try:
            with DDGS() as ddgs:
                results = ddgs.images(
                    keywords=search_query_barcode,
                    region='wt-wt',
                    safesearch='moderate',
                    max_results=3 # Barkod aramasında daha az sonuç yeterli olabilir
                )
                if results:
                    first_image_url = results[0].get('image')
                    if first_image_url:
                        print(f"    DuckDuckGo'dan barkod ({barkod.strip()}) ile bulunan ilk resim URL'i: {first_image_url}")
                        return first_image_url
                    else:
                        print(f"    DuckDuckGo barkod ({barkod.strip()}) arama sonuçlarında geçerli bir resim URL'i bulunamadı.")
                else:
                    print(f"    DuckDuckGo'da barkod ({barkod.strip()}) ile resim bulunamadı.")
        except Exception as e:
            print(f"  [DUCKDUCKGO BARKOD ARAMA HATA] Barkod ile resim aranırken bir hata oluştu: {e}")
        # Barkodla bulunamazsa ürün adıyla devam etmesi için aşağı düşer
    
    # 2. Ürün adıyla arama yap (barkodla bulunamadıysa veya barkod yoksa)
    if not cleaned_product_name and not (barkod and barkod.strip()): # Eğer barkod da yoksa ve ürün adı da yoksa boşuna arama
        print(f"  [UYARI] Hem barkod hem de ürün adı boş olduğu için arama yapılamıyor (STOK_KODU: {stok_kodu}).")
        return None
    
    if not cleaned_product_name: # Sadece barkod vardı ama bulunamadı, ürün adı yoksa buradan çık
         print(f"  [BİLGİ] Barkod ile resim bulunamadı ve ürün adı da mevcut değil (STOK_KODU: {stok_kodu}).")
         return None

    search_query_name = f"{cleaned_product_name} ürün resmi"
    search_type_message = "ürün adıyla"
    if search_term_used: # Daha önce barkodla arama denendiğini belirt
        search_type_message = f"barkodla bulunamadığı için {search_type_message}"
        
    print(f"  [DUCKDUCKGO ÜRÜN ADI ARAMA] '{search_query_name}' için {search_type_message} resim URL'i aranıyor (STOK_KODU: {stok_kodu})...")
    search_term_used = f"Ürün Adı: {cleaned_product_name}"

    try:
        with DDGS() as ddgs:
            results = ddgs.images(
                keywords=search_query_name,
                region='wt-wt',
                safesearch='moderate',
                size=None,  # None, Small, Medium, Large, Wallpaper
                # color=None, # Monochromatic, Color
                # type_image=None, # photo, clipart, gif, transparent, line
                # layout=None, # Square, Tall, Wide
                # license_image=None, # Any, CreativeCommons, PublicDomain, Share, ShareCommercially
                max_results=5 # İlk birkaç sonucu alıp değerlendirebilirsiniz
            )
            if results:
                # Şimdilik ilk resmi alalım. 
                # Daha akıllı bir seçim için (örneğin resim boyutları, anahtar kelime eşleşmesi vb.)
                # burada ek mantık gerekebilir.
                first_image_url = results[0].get('image')
                if first_image_url:
                    print(f"    DuckDuckGo'dan {search_term_used} ile bulunan ilk resim URL'i: {first_image_url}")
                    # İsteğe bağlı: Bulunan URL'nin gerçekten bir resim olup olmadığını kontrol etmek için
                    # requests.head(first_image_url, timeout=5).headers.get('Content-Type', '').startswith('image/')
                    # gibi bir kontrol eklenebilir, ancak bu işlemi yavaşlatabilir.
                    return first_image_url
                else:
                    print(f"    DuckDuckGo'da {search_term_used} ile resim bulunamadı.")
            else:
                print(f"    DuckDuckGo'da {search_term_used} ile resim bulunamadı.")
    except Exception as e:
        print(f"  [DUCKDUCKGO ÜRÜN ADI HATA] {search_term_used} ile resim aranırken bir hata oluştu: {e}")
    
    return None

def batch_download_product_images():
    """
    Veritabanındaki ürünler için resimleri toplu olarak indirir/kontrol eder.
    """
    conn = get_db_connection()
    if not conn:
        print("Veritabanı bağlantısı kurulamadığı için işlem iptal edildi.")
        return

    cursor = conn.cursor()
    
    # data_extractor.py'deki sorguya benzer bir sorgu.
    # İhtiyaçlarınıza göre (örneğin sadece aktif ürünler vb.) güncelleyebilirsiniz.
    # Şimdilik TBLSTSABIT'ten STOK_KODU ve STOK_ADI alalım.
    query = """
    SELECT 
        s.STOK_KODU, 
        s.STOK_ADI,
        ISNULL(s.BARKOD1, '') as BARKOD1 -- BARKOD1 alanını ekledik, NULL ise boş string
    FROM TBLSTSABIT s
    WHERE 
        s.GRUP_KODU NOT IN ('KULLANMA', 'INT', 'PALET') 
        AND EXISTS (SELECT 1 FROM SenkronixStokBakiye b WHERE b.STOK_KODU = s.STOK_KODU AND b.BAKIYE <> 0)
        AND RTRIM(LTRIM(s.STOK_KODU)) <> '' 
        -- AND s.STOK_KODU = '000002' -- Test için tek bir ürünle sınırlayabilirsiniz
    ORDER BY s.STOK_KODU;
    """

    try:
        print("\nÜrünler çekiliyor ve resimler işleniyor...")
        cursor.execute(query)
        products_processed = 0
        images_downloaded_or_found = 0
        
        for row in cursor.fetchall():
            stok_kodu = row.STOK_KODU.strip()
            stok_adi = row.STOK_ADI.strip() if row.STOK_ADI else ""
            barkod = row.BARKOD1.strip() if row.BARKOD1 else None # Barkodu al
            products_processed += 1

            print(f"\nİşleniyor: STOK_KODU='{stok_kodu}', STOK_ADI='{stok_adi}', BARKOD='{barkod if barkod else ''}'")

            cleaned_name = image_processor.clean_product_name(stok_adi)
            print(f"  Temizlenmiş Ad: '{cleaned_name}'")

            # 1. Adım: Mevcut bir resim var mı diye kontrol et (URL vermeden)
            # Bu adım image_processor.download_and_save_image içine zaten entegre edildi.
            # O yüzden doğrudan URL bulma ve indirme adımına geçebiliriz.
            # image_path = image_processor.download_and_save_image(None, stok_kodu)
            # if image_path:
            #    print(f"  Mevcut resim bulundu: {image_path}")
            #    images_downloaded_or_found += 1
            #    continue # Bir sonraki ürüne geç

            # 2. Adım: AI/Arama modülü ile resim URL'i bul
            # (KULLANICI TARAFINDAN GELİŞTİRİLECEK YER)
            image_url_found = find_image_url_via_search_ai(cleaned_name, stok_adi, stok_kodu, barkod)

            if image_url_found:
                print(f"  Bulunan Resim URL'i: {image_url_found}")
                # 3. Adım: Resmi indir ve kaydet (veya mevcutsa kullan)
                saved_image_path = image_processor.download_and_save_image(image_url_found, stok_kodu)
                if saved_image_path:
                    print(f"  Resim başarıyla işlendi/bulundu: {saved_image_path}")
                    images_downloaded_or_found += 1
                else:
                    print(f"  Uyarı: Resim URL'i ({image_url_found}) bulundu ancak indirilemedi/kaydedilemedi.")
            else:
                # Eğer find_image_url_via_search_ai None döndürürse, download_and_save_image'ı
                # None URL ile çağırarak sadece varlık kontrolü yapmasını sağlayabiliriz (ki zaten yapıyor).
                # Ancak burada find_image_url_via_search_ai'nin None döndürmesi "URL bulunamadı" demek.
                # Mevcut resim kontrolü zaten download_and_save_image içinde en başta yapılıyor.
                print(f"  Bu ürün için AI/Arama ile resim URL'i bulunamadı.")
                # İsteğe bağlı: URL bulunamasa bile sadece yerel varlık kontrolü için çağrı
                # local_check = image_processor.download_and_save_image(None, stok_kodu)
                # if local_check:
                #    print(f"  Ancak yerelde bir resim bulundu: {local_check}")
                #    images_downloaded_or_found += 1
                # else:
                #    print(f"  Yerelde de resim yok.")


        print(f"\nİşlem Tamamlandı. Toplam {products_processed} ürün işlendi.")
        print(f"Toplam {images_downloaded_or_found} resim indirildi veya mevcut olarak bulundu.")

    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        print(f"SQL sorgusu çalıştırılırken hata: {sqlstate} - {ex}")
    except Exception as e:
        print(f"Resim indirme işlemi sırasında genel bir hata: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()
            print("Veritabanı bağlantısı kapatıldı.")

if __name__ == '__main__':
    batch_download_product_images() 