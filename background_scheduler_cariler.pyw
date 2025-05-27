import time
import json
import os
import sys
import logging
import schedule
import shutil # Dosya kopyalama ve silme işlemleri için
import requests # API istekleri için eklendi
from decimal import Decimal # JSON'a Decimal yazarken gerekebilir
from datetime import datetime # Zaman damgalı log dosyası adları için
# from dotenv import load_dotenv # .env kullanılmayacağı için kaldırıldı

# Proje kök dizinini sys.path'e ekle
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# load_dotenv() # .env kullanılmayacağı için kaldırıldı

# API Anahtarı ve Render URL için global değişkenler
API_KEY = None
RENDER_API_URL = "https://firatb2b.onrender.com/api/update-customer-balances"

# Ana dizinde (yerelde) oluşturulacak/güncellenecek JSON dosyası (yedek veya test amaçlı kalabilir)
SOURCE_JSON_FILE_NAME = "filtrelenen_cariler_yerel.json" # API'ye gönderildiği için adı değiştirildi
SOURCE_JSON_PATH = os.path.join(BASE_DIR, SOURCE_JSON_FILE_NAME)

# Render API endpoint URL'si ve API anahtarı için ayarlar
RENDER_API_URL = "https://firatb2b.onrender.com/api/update-customer-balances"
# API Anahtarını settings.json'dan okumak için bir fonksiyon veya doğrudan data_extractor'dan import edilebilir
# Şimdilik data_extractor'daki SETTINGS_FILE'ı kullanacağız

try:
    from data_extractor import (
        get_db_connection,
        fetch_customer_summary, # Carileri çekmek için bu fonksiyonu kullanacağız
        SETTINGS_FILE, # settings.json dosya yolu
        LOG_DIR as APP_LOG_DIR,
        decimal_serializer # Yeni eklenen serializer fonksiyonu
    )
except ImportError as e:
    # Eğer bu script .pyw olarak doğrudan çalıştırılıyorsa ve konsol yoksa,
    # hatayı bir dosyaya yazdırmayı deneyebiliriz.
    try:
        with open(os.path.join(BASE_DIR, "background_scheduler_cariler_CRITICAL_ERROR.log"), "w") as f_err:
            f_err.write(f"FATAL: BackgroundSchedulerCariler import hatası: {e}. Script sonlandırılıyor.\n")
            f_err.write(f"BASE_DIR: {BASE_DIR}\n")
            f_err.write(f"sys.path: {sys.path}\n")
    except:
        pass # Log dosyasına yazılamıyorsa yapacak bir şey yok
    sys.exit(1) # Script'i sonlandır

# Log dizini
LOG_BASE_DIR = os.path.join(APP_LOG_DIR) 

# Ana log dosyası adı - ARTIK KULLANILMAYACAK, HER KONTROLCÜ ÇALIŞMASI İÇİN AYRI OLUŞTURULACAK
# MAIN_LOG_FILE_NAME = "background_scheduler_cariler_main.log"
# MAIN_LOG_FILE = os.path.join(LOG_BASE_DIR, MAIN_LOG_FILE_NAME)

# Görev log dosyası adı - ARTIK KULLANILMAYACAK, HER ÇALIŞMA İÇİN AYRI OLUŞTURULACAK
# TASK_LOG_FILE_NAME = "customer_sync_task.log"
# TASK_LOG_FILE = os.path.join(LOG_BASE_DIR, TASK_LOG_FILE_NAME)

if not os.path.exists(LOG_BASE_DIR):
    try:
        os.makedirs(LOG_BASE_DIR)
    except OSError as e:
        # print(f"UYARI: Log dizini ({LOG_BASE_DIR}) oluşturulamadı: {e}. Loglar yazılamayabilir.")
        # .pyw için print yerine başlangıçta log dosyasına yazılabilir.
        pass

# WEB_APP_STATIC_JSON_DIR kontrolü artık burada gerekmeyebilir, API'ye gönderiliyor.
# if not os.path.exists(WEB_APP_STATIC_JSON_DIR):
#     try:
#         os.makedirs(WEB_APP_STATIC_JSON_DIR)
#     except OSError as e:
#         pass


# Standart formatlayıcı
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s")

# Ana Zamanlayıcı Logger'ı
main_logger = logging.getLogger("BackgroundSchedulerCarilerMain")
main_logger.setLevel(logging.INFO)
# Global main_file_handler artık ayarlanmayacak
# try:
#     main_file_handler = logging.FileHandler(MAIN_LOG_FILE, encoding='utf-8')
#     main_file_handler.setFormatter(formatter)
#     main_logger.addHandler(main_file_handler)
# except Exception as e:
#     pass 

main_stream_handler = logging.StreamHandler(sys.stdout) # .pyw için bu çok görünür olmayabilir
main_stream_handler.setFormatter(formatter)
main_logger.addHandler(main_stream_handler)

# Cari Senkronizasyon Görevi Logger'ı - ARTIK GLOBAL OLARAK AYARLANMAYACAK
# task_logger = logging.getLogger("CustomerSyncTask")
# task_logger.setLevel(logging.INFO)
# try:
#     task_file_handler = logging.FileHandler(TASK_LOG_FILE, encoding='utf-8')
#     task_file_handler.setFormatter(formatter)
#     task_logger.addHandler(task_file_handler)
# except Exception as e:
#     # print(f"Hata: Task logger için log dosyası handler'ı ({TASK_LOG_FILE}) oluşturulamadı: {e}")
#     pass

# task_stream_handler = logging.StreamHandler(sys.stdout) 
# task_stream_handler.setFormatter(formatter)
# task_logger.addHandler(task_stream_handler)

last_successful_sync_timestamp = 0.0

# settings.json'dan yapılandırmayı (API anahtarı dahil) yüklemek için fonksiyon
def load_configuration():
    global API_KEY # Global API_KEY değişkenini güncellemek için
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            API_KEY = settings.get("customer_sync_api_key")
            if not API_KEY:
                main_logger.critical(f"KRİTİK HATA: 'customer_sync_api_key' {SETTINGS_FILE} dosyasında bulunamadı veya boş. Script çalıştırılamıyor.")
                return False
            main_logger.info(f"API Anahtarı {SETTINGS_FILE} dosyasından başarıyla yüklendi.")
            return True
    except FileNotFoundError:
        main_logger.critical(f"KRİTİK HATA: Ayarlar dosyası ({SETTINGS_FILE}) bulunamadı. Script çalıştırılamıyor.")
        return False
    except json.JSONDecodeError:
        main_logger.critical(f"KRİTİK HATA: Ayarlar dosyası ({SETTINGS_FILE}) geçerli bir JSON formatında değil. Script çalıştırılamıyor.")
        return False
    except Exception as e:
        main_logger.critical(f"KRİTİK HATA: Ayarlar dosyası ({SETTINGS_FILE}) okunurken beklenmedik bir hata oluştu: {e}. Script çalıştırılamıyor.", exc_info=True)
        return False

def perform_customer_data_sync_task():
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    per_run_logger_name = f"CustomerSyncTaskRun_{timestamp_str}"
    per_run_logger = logging.getLogger(per_run_logger_name)
    per_run_logger.setLevel(logging.INFO)
    per_run_logger.propagate = False

    current_run_log_file_name = f"customer_sync_{timestamp_str}.log"
    current_run_log_path = os.path.join(LOG_BASE_DIR, current_run_log_file_name)

    run_file_handler = None
    try:
        run_file_handler = logging.FileHandler(current_run_log_path, encoding='utf-8')
        run_file_handler.setFormatter(formatter)
        per_run_logger.addHandler(run_file_handler)

        # Bu mesaj main_logger'a değil, kendi özel per_run_logger'ına gidecek.
        # main_logger.info(f"Cari senkronizasyon görevi başlatılıyor. Detaylar için bkz: {current_run_log_file_name}")
        # Yukarıdaki loglama job_controller_customers tarafından yapılacak.
        per_run_logger.info(f"Cari veri senkronizasyon görevi başlatılıyor (Detay log dosyası: {current_run_log_file_name}).")
    
        # 1. Mevcut dosyaları sil (hem kaynakta hem hedefte)
        for file_path in [SOURCE_JSON_PATH]:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    per_run_logger.info(f"Mevcut dosya silindi: {file_path}")
                except OSError as e:
                    per_run_logger.error(f"Dosya silinemedi: {file_path}. Hata: {e}")

        db_conn = None
        per_run_logger.info("Veritabanı bağlantısı kuruluyor...")
        db_conn = get_db_connection(caller_info=f"BackgroundSchedulerCariler_Run_{timestamp_str}")
        if not db_conn:
            per_run_logger.error("Veritabanı bağlantısı kurulamadı. Senkronizasyon iptal edildi.")
            return False, current_run_log_file_name

        per_run_logger.info("Veritabanı bağlantısı başarılı. Cari özet verileri çekiliyor...")
        all_customer_data_from_db = fetch_customer_summary(db_conn=db_conn) 

        if all_customer_data_from_db is None:
            per_run_logger.error("fetch_customer_summary None döndürdü. Veri çekilemedi veya bir hata oluştu.")
            return False, current_run_log_file_name
        
        if not all_customer_data_from_db:
            per_run_logger.info("Veritabanından senkronize edilecek cari verisi bulunamadı.")
            all_customer_data_for_api = []
            filtered_customer_data_for_api_and_local_backup = []
        else:
            per_run_logger.info(f"{len(all_customer_data_from_db)} adet cari verisi çekildi. Şimdi filtreleniyor...")
            
            # Tüm cariler API için ayrı bir listede tutulacak (filtresiz)
            all_customer_data_for_api = all_customer_data_from_db # Orijinal, filtresiz liste
            
            # Filtrelenmiş cari verisi (hem API'ye hem yerel yedeklemeye gidecek)
            filtered_customer_data_for_api_and_local_backup = []
            allowed_group_codes = ["SERVÝS", "TOPTAN", None, ""] # İzin verilen grup kodları (None ve boş string dahil)
            
            for customer in all_customer_data_from_db: # Filtreleme için orijinal listeyi kullan
                grup_kodu = customer.get("GRUP_KODU")
                net_bakiye_str = customer.get("NET_BAKIYE", "0")

                try:
                    # "0E-8" gibi bilimsel gösterimleri ve normal sayıları float'a çevir
                    net_bakiye_float = float(net_bakiye_str)
                except (ValueError, TypeError):
                    net_bakiye_float = 0.0 # Hatalı veya eksikse 0 kabul et
                
                # Grup kodu kontrolü
                is_group_allowed = False
                if grup_kodu is None or grup_kodu.strip() == "": # None veya sadece boşluklardan oluşanlar "" olarak kabul edilir
                    is_group_allowed = True
                elif isinstance(grup_kodu, str) and grup_kodu.upper() in [agc.upper() if agc else "" for agc in allowed_group_codes if agc]: # Büyük/küçük harf duyarsız kontrol
                    is_group_allowed = True

                # Bakiye kontrolü (0 olmayanlar)
                is_bakiye_valid = abs(net_bakiye_float) > 1e-7 # Kayan nokta hassasiyeti için epsilon kontrolü

                if is_group_allowed and is_bakiye_valid:
                    filtered_customer_data_for_api_and_local_backup.append(customer)
            
            per_run_logger.info(f"Filtreleme sonrası {len(filtered_customer_data_for_api_and_local_backup)} adet cari kaldı (filtrelenmiş liste).")
            per_run_logger.info(f"API'ye gönderilecek toplam cari sayısı (filtresiz liste): {len(all_customer_data_for_api)}.")
            # customer_data = filtered_customer_data # Eski satır, artık iki ayrı liste var

        # İsteğe bağlı: Filtrelenmiş veriyi yerel bir dosyaya yedek olarak kaydet
        per_run_logger.info(f"Filtrelenmiş cari verileri yerel yedek olarak {SOURCE_JSON_PATH} dosyasına kaydediliyor...")
        try:
            # Yerel yedekleme için sadece filtrelenmiş olanı kullan
            with open(SOURCE_JSON_PATH, "w", encoding="utf-8") as f_source:
                json.dump(filtered_customer_data_for_api_and_local_backup, f_source, ensure_ascii=False, indent=4, default=decimal_serializer)
            per_run_logger.info(f"Filtrelenmiş cari verileri başarıyla yerel yedek dosyasına ({SOURCE_JSON_PATH}) kaydedildi.")
        except IOError as e:
            per_run_logger.warning(f"Yerel yedek dosyasına ({SOURCE_JSON_PATH}) yazılırken hata (bu işlem API gönderimini engellemez): {e}")
        except TypeError as e:
            per_run_logger.warning(f"Yerel yedek için JSON serileştirme hatası ({SOURCE_JSON_PATH}) (API gönderimini engellemez): {e}.")

        # API anahtarı artık global değişkenden okunacak (load_configuration ile yüklendi)
        if not API_KEY:
            per_run_logger.error("API anahtarı yüklenemedi (settings.json kontrol edin). Canlı sunucuya veri gönderilemiyor.")
            return False, current_run_log_file_name
        
        headers = {
            "X-API-Key": API_KEY, # Global API_KEY kullanılıyor
            "Content-Type": "application/json"
        }

        # API'ye gönderilecek payload'ı hazırla
        api_payload = {
            "all_customers": all_customer_data_for_api,
            "filtered_customers": filtered_customer_data_for_api_and_local_backup
        }

        per_run_logger.info(f"Hazırlanan API payload'ı {RENDER_API_URL} adresine gönderiliyor ({len(all_customer_data_for_api)} filtresiz, {len(filtered_customer_data_for_api_and_local_backup)} filtrelenmiş cari)...")
        try:
            # api_payload doğrudan JSON serileştirilebilir bir Python dict olmalı.
            # json.dumps ile stringe çevirip data= parametresi ile gönderebiliriz ya da doğrudan json= parametresi ile dict/list.
            # `requests` kütüphanesi json parametresini otomatik olarak application/json olarak serialize eder.
            # ANCAK Decimal tipi için özel serializer kullanmamız gerekiyor.
            payload_json_string = json.dumps(api_payload, ensure_ascii=False, default=decimal_serializer)
            response = requests.post(RENDER_API_URL, headers=headers, data=payload_json_string, timeout=60) # Timeout artırıldı
            response.raise_for_status() # HTTP 4xx veya 5xx hatalarında exception fırlatır
            
            per_run_logger.info(f"Veriler başarıyla API'ye gönderildi. Sunucu yanıtı ({response.status_code}): {response.json()}")
            return True, current_run_log_file_name
        
        except requests.exceptions.HTTPError as http_err:
            error_content = "Bilinmiyor"
            try:
                error_content = http_err.response.json() # Sunucudan gelen JSON hatasını almaya çalış
            except json.JSONDecodeError:
                error_content = http_err.response.text # JSON değilse text olarak al
            per_run_logger.error(f"API'ye veri gönderilirken HTTP hatası ({http_err.response.status_code}): {error_content}")
            return False, current_run_log_file_name
        except requests.exceptions.ConnectionError as conn_err:
            per_run_logger.error(f"API'ye bağlanırken hata (Bağlantı Hatası): {conn_err}")
            return False, current_run_log_file_name
        except requests.exceptions.Timeout as timeout_err:
            per_run_logger.error(f"API isteği zaman aşımına uğradı: {timeout_err}")
            return False, current_run_log_file_name
        except requests.exceptions.RequestException as req_err:
            per_run_logger.error(f"API isteği sırasında genel bir hata oluştu: {req_err}")
            return False, current_run_log_file_name
        except Exception as e:
            per_run_logger.error(f"API'ye veri gönderilirken beklenmedik bir hata oluştu: {e}", exc_info=True)
            return False, current_run_log_file_name

    except Exception as e:
        log_target = per_run_logger if run_file_handler and per_run_logger.hasHandlers() else main_logger
        log_target.error(f"Cari senkronizasyon görevi sırasında genel bir hata oluştu: {e}", exc_info=True)
        # Hata durumunda da log dosyasının adını döndürmeye çalışalım, eğer oluşturulduysa
        return False, current_run_log_file_name if run_file_handler else None
    finally:
        if db_conn:
            try:
                db_conn.close()
                if run_file_handler and per_run_logger.hasHandlers():
                    per_run_logger.info("Veritabanı bağlantısı kapatıldı.")
            except Exception as e:
                if run_file_handler and per_run_logger.hasHandlers():
                    per_run_logger.error(f"Veritabanı bağlantısı kapatılırken hata: {e}")
        
        if run_file_handler and per_run_logger.hasHandlers():
            per_run_logger.info("Cari veri senkronizasyon görevinin bu çalışması tamamlandı.")

        if run_file_handler:
            per_run_logger.removeHandler(run_file_handler)
            run_file_handler.close()

def job_controller_customers():
    # global last_successful_sync_timestamp # Artık kullanılmıyor

    # Her job_controller_customers çalışması için dinamik olarak main_logger'a file handler ekle
    controller_timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    controller_log_file_name = f"cariler_controller_run_{controller_timestamp_str}.log"
    controller_log_path = os.path.join(LOG_BASE_DIR, controller_log_file_name)
    
    controller_file_handler = None
    original_main_logger_handlers = list(main_logger.handlers) # Orijinal handlerları sakla (özellikle stream handler)
    
    try:
        controller_file_handler = logging.FileHandler(controller_log_path, encoding='utf-8')
        controller_file_handler.setFormatter(formatter)
        main_logger.addHandler(controller_file_handler)

        main_logger.info(f"Cari zamanlayıcı kontrolcüsü (job_controller_customers) tetiklendi. Bu çalıştırmanın logları: {controller_log_file_name}")

        is_enabled = True 
        interval_minutes_customers = 1 

        main_logger.info(f"Cari senkronizasyon ayarları: Etkin = {is_enabled}, Güncelleme Aralığı = {interval_minutes_customers} dk")

        if not is_enabled:
            main_logger.info("Cari senkronizasyonu (bu script içinde) etkin değil. Asıl işlem yapılmayacak.")
            return

        # current_time = time.time() # last_successful_sync_timestamp ile kullanılmıyor
        
        # Bu log mesajı artık perform_customer_data_sync_task içinde değil, burada main_logger ile atılacak.
        # perform_customer_data_sync_task çağrılmadan önce hangi detay log dosyasının kullanılacağı burada belirtilir.
        # Ancak perform_customer_data_sync_task kendi log dosyasını kendi içinde oluşturuyor ve adını biliyor.
        # Bu yüzden, o fonksiyonun kendi log dosyasının adını döndürmesini ve burada loglamasını sağlayabiliriz.
        # VEYA: perform_customer_data_sync_task çağrılırken ana log dosyasının adını parametre olarak alır
        # ve kendi başlangıç mesajını oraya yazar. Şimdilik basit tutalım.
        main_logger.info(f"Zamanlama periyodu doldu. Cari senkronizasyon görevi (`perform_customer_data_sync_task`) başlatılıyor...")

        sync_successful, detail_log_file_name = perform_customer_data_sync_task()
        
        if sync_successful:
            main_logger.info(f"Cari senkronizasyon görevi başarıyla tamamlandı. Detaylar için bkz: {detail_log_file_name}")
        else:
            main_logger.warning(f"Cari senkronizasyon görevi başarısız oldu veya tamamlanamadı. Detaylar için bkz: {detail_log_file_name if detail_log_file_name else 'oluşturulamayan görev log dosyası'}")

    except Exception as e:
        main_logger.error(f"job_controller_customers sırasında genel bir hata: {e}", exc_info=True)
    finally:
        if controller_file_handler:
            main_logger.removeHandler(controller_file_handler)
            controller_file_handler.close()
        # Orijinal handlerları geri yükleme (eğer sadece ekleme/çıkarma yapıyorsak ve
        # main_logger örneği her zaman aynıysa bu şart olmayabilir, ama temiz bir pratiktir).
        # Ancak, schedule farklı threadlerde çalıştırıyorsa bu karmaşıklaşabilir.
        # Şimdilik basitçe remove yapıyoruz.

if __name__ == "__main__":
    # İlk olarak yapılandırmayı (API anahtarı dahil) yükle
    if not load_configuration():
        # Hata zaten load_configuration içinde loglandı.
        # print() ile konsola da yazdırılmış olabilir veya doğrudan çıkılmış olabilir.
        # Burada sadece script'in sonlandığından emin olalım.
        critical_error_log_path = os.path.join(BASE_DIR, "background_scheduler_cariler_CRITICAL_ERROR.log")
        # load_configuration içinde zaten kritik hata loglanıyor, bu satır tekrar yazdırır.
        # Belki sadece print ile kullanıcıya bilgi verip çıkmak yeterli.
        print(f"KRİTİK HATA: Yapılandırma (settings.json) yüklenemedi veya API anahtarı eksik. Detaylar için logları kontrol edin. Script sonlandırılıyor.")
        # Emin olmak için bir daha loglayalım (opsiyonel, load_configuration zaten yapıyor)
        # with open(critical_error_log_path, "a", encoding="utf-8") as f_err:
        #     f_err.write(f"{datetime.now().isoformat()} - KRİTİK HATA: __main__ içinde load_configuration başarısız oldu.\\n")
        sys.exit(1) # Hata kodu ile çık

    # İlk başlangıç logları sadece konsola gidecek (main_logger'da global file handler yok)
    main_logger.info(f"Arka Plan CARİ Zamanlayıcı (dinamik log dosyaları ile) başlatıldı.")
    
    sync_interval_minutes = 1 
    
    schedule.every(sync_interval_minutes).minutes.do(job_controller_customers)
    main_logger.info(f"Cari kontrolcü görevi (`job_controller_customers`) her {sync_interval_minutes} dakikada bir çalışacak şekilde zamanlandı.")

    main_logger.info("İlk kontrolcü görevi (`job_controller_customers`) hemen tetikleniyor...")
    job_controller_customers()

    main_logger.info("Zamanlayıcı döngüsü başlatılıyor. Çıkmak için Ctrl+C.")
    try:
        while True:
            schedule.run_pending()
            time.sleep(1) 
    except KeyboardInterrupt:
        main_logger.info("Kullanıcı tarafından sonlandırıldı (Ctrl+C).")
    except Exception as e:
        main_logger.error(f"Ana cari zamanlayıcı döngüsünde beklenmedik hata: {e}", exc_info=True)
    finally:
        main_logger.info(f"Arka Plan CARİ Zamanlayıcı sonlandırılıyor.") 