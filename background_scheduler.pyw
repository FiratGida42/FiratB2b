import time
import json
import os
import sys
import logging
import schedule
import copy
from decimal import Decimal

# Proje kök dizinini sys.path'e ekle
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

try:
    from data_extractor import (
        get_db_connection, 
        fetch_product_data, 
        send_data_to_web_api,
        SETTINGS_FILE,
        LOG_DIR as APP_LOG_DIR
    )
except ImportError as e:
    print(f"FATAL: BackgroundScheduler import hatası: {e}. Script sonlandırılıyor.")
    sys.exit(1)

# Log dizini
LOG_BASE_DIR = os.path.join(APP_LOG_DIR) # APP_LOG_DIR, data_extractor'dan geliyor

# Ana log dosyası adı
MAIN_LOG_FILE_NAME = "background_scheduler_main.log"
MAIN_LOG_FILE = os.path.join(LOG_BASE_DIR, MAIN_LOG_FILE_NAME)

# Görev log dosyası adı
TASK_LOG_FILE_NAME = "product_update_task.log"
TASK_LOG_FILE = os.path.join(LOG_BASE_DIR, TASK_LOG_FILE_NAME)

if not os.path.exists(LOG_BASE_DIR):
    try:
        os.makedirs(LOG_BASE_DIR)
    except OSError as e:
        print(f"UYARI: Log dizini ({LOG_BASE_DIR}) oluşturulamadı: {e}. Loglar yazılamayabilir.")

# Standart formatlayıcı
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s")

# Ana Zamanlayıcı Logger'ı
main_logger = logging.getLogger("BackgroundSchedulerMain")
main_logger.setLevel(logging.INFO)
try:
    main_file_handler = logging.FileHandler(MAIN_LOG_FILE)
    main_file_handler.setFormatter(formatter)
    main_logger.addHandler(main_file_handler)
except Exception as e:
    print(f"Hata: Main logger için log dosyası handler'ı ({MAIN_LOG_FILE}) oluşturulamadı: {e}")

main_stream_handler = logging.StreamHandler(sys.stdout)
main_stream_handler.setFormatter(formatter)
main_logger.addHandler(main_stream_handler)

# Ürün Güncelleme Görevi Logger'ı
task_logger = logging.getLogger("ProductUpdateTask")
task_logger.setLevel(logging.INFO)
try:
    task_file_handler = logging.FileHandler(TASK_LOG_FILE)
    task_file_handler.setFormatter(formatter)
    task_logger.addHandler(task_file_handler)
except Exception as e:
    print(f"Hata: Task logger için log dosyası handler'ı ({TASK_LOG_FILE}) oluşturulamadı: {e}")

task_stream_handler = logging.StreamHandler(sys.stdout) # Görev loglarını da konsolda görelim
task_stream_handler.setFormatter(formatter)
task_logger.addHandler(task_stream_handler)

last_successful_update_timestamp = 0.0

def perform_actual_update_task(excluded_groups_from_settings=None):
    task_logger.info("Asıl güncelleme görevi başlatılıyor (perform_actual_update_task).")
    if excluded_groups_from_settings:
        task_logger.info(f"Ayarlardan gelen hariç tutulacak grup kodları: {excluded_groups_from_settings}")
    else:
        task_logger.info("Ayarlardan hariç tutulacak grup kodu belirtilmemiş.")
        
    db_conn = None
    try:
        db_conn = get_db_connection() # Bu fonksiyon kendi içinde loglama yapabilir (data_extractor)
        if not db_conn:
            task_logger.error("Veritabanı bağlantısı kurulamadı. Güncelleme iptal edildi.")
            return False

        task_logger.info("Veritabanı bağlantısı başarılı. Ürün verileri çekiliyor...")
        # fetch_product_data kendi loglarını data_extractor üzerinden tutuyor olmalı
        product_data = fetch_product_data(db_conn, excluded_groups=excluded_groups_from_settings)

        if product_data is None:
            task_logger.error("fetch_product_data None döndürdü, muhtemelen bir hata oluştu. Güncelleme başarısız.")
            return False
        
        if not product_data:
            task_logger.info("API'ye gönderilecek ürün verisi bulunmuyor (filtrelenmiş olabilir veya mevcut değil).")
            return True 
        
        task_logger.info(f"{len(product_data)} adet ürün verisi (muhtemelen filtrelenmiş) çekildi. Web API'sine gönderiliyor...")
        # send_data_to_web_api kendi loglarını data_extractor üzerinden tutuyor olmalı
        success, message = send_data_to_web_api(product_data)
        if success:
            task_logger.info(f"Veriler başarıyla Web API'sine gönderildi. API Yanıtı: {message}")
            return True
        else:
            task_logger.error(f"Veriler Web API'sine gönderilemedi. Detay: {message}")
            return False

    except Exception as e:
        task_logger.error(f"Güncelleme görevi sırasında (perform_actual_update_task) genel bir hata oluştu: {e}", exc_info=True)
        return False
    finally:
        if db_conn:
            try:
                db_conn.close()
                task_logger.info("Veritabanı bağlantısı kapatıldı.")
            except Exception as e:
                task_logger.error(f"Veritabanı bağlantısı kapatılırken hata: {e}")
        task_logger.info("Asıl güncelleme görevinin (perform_actual_update_task) bu çalışması tamamlandı.")

def job_controller():
    global last_successful_update_timestamp
    main_logger.info("Zamanlayıcı kontrolcüsü (job_controller) tetiklendi.")

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings_data = json.load(f)
    except FileNotFoundError:
        main_logger.error(f'{SETTINGS_FILE} bulunamadı. Kontrol işlemi yapılamıyor.')
        return
    except json.JSONDecodeError:
        main_logger.error(f'{SETTINGS_FILE} geçerli bir JSON formatında değil. Kontrol işlemi yapılamıyor.')
        return
    except Exception as e:
        main_logger.error(f"'{SETTINGS_FILE}' okunurken beklenmedik bir hata: {e}")
        return

    scheduler_settings = settings_data.get("scheduler_settings", {})
    is_enabled = scheduler_settings.get("enabled", False)
    interval_minutes = scheduler_settings.get("interval_minutes", 30) 
    if not isinstance(interval_minutes, (int, float)) or interval_minutes <= 0:
        main_logger.warning(f"Ayarlardaki interval_minutes ({interval_minutes}) geçersiz, varsayılan 30 dk kullanılacak.")
        interval_minutes = 30

    excluded_group_codes = []
    user_preferences = settings_data.get("user_preferences", {})
    if "excluded_group_codes" in user_preferences:
        excluded_group_codes = user_preferences.get("excluded_group_codes", [])
        main_logger.info(f"'{SETTINGS_FILE}' içindeki 'user_preferences' altından 'excluded_group_codes' okundu: {excluded_group_codes}")
    else:
        main_logger.info(f"Ayarlarda ({SETTINGS_FILE} -> user_preferences) 'excluded_group_codes' bulunamadı. Filtreleme yapılmayacak.")

    if not isinstance(excluded_group_codes, list):
        main_logger.warning(f"Ayarlardaki 'excluded_group_codes' bir liste değil ({type(excluded_group_codes)}), boş liste olarak kullanılacak.")
        excluded_group_codes = []

    main_logger.info(f"Ayarlar okundu: Etkin = {is_enabled}, İstenen Güncelleme Aralığı = {interval_minutes} dk, Hariç Tutulan Gruplar: {excluded_group_codes}")

    if not is_enabled:
        main_logger.info("Otomatik güncelleme (settings.json) etkin değil. Asıl işlem yapılmayacak.")
        return

    current_time = time.time()
    elapsed_seconds_since_last_run = current_time - last_successful_update_timestamp
    required_seconds_for_interval = interval_minutes * 60

    main_logger.debug(f"Son başarılı çalışmadan bu yana geçen süre: {elapsed_seconds_since_last_run:.0f} saniye.")
    main_logger.debug(f"İstenen aralık: {required_seconds_for_interval:.0f} saniye ({interval_minutes} dk).")

    if elapsed_seconds_since_last_run >= required_seconds_for_interval:
        main_logger.info(f"Gerekli aralık ({interval_minutes} dk) geçti veya ilk çalıştırma. Asıl güncelleme görevi başlatılıyor.")
        
        # perform_actual_update_task kendi loglarını task_logger ile tutacak
        update_successful = perform_actual_update_task(excluded_groups_from_settings=excluded_group_codes)
        
        if update_successful:
            main_logger.info("Asıl güncelleme görevi başarıyla tamamlandı. Son çalışma zamanı güncellendi.")
            last_successful_update_timestamp = current_time
        else:
            main_logger.warning("Asıl güncelleme görevi başarısız oldu veya tamamlanamadı. Son çalışma zamanı güncellenmedi, bir sonraki kontrolde tekrar denenebilir.")
    else:
        remaining_seconds = required_seconds_for_interval - elapsed_seconds_since_last_run
        main_logger.info(f"İstenen aralık ({interval_minutes} dk) henüz geçmedi. Kalan süre yaklaşık {remaining_seconds / 60:.1f} dk. Bu döngüde asıl işlem yapılmayacak.")

if __name__ == "__main__":
    main_logger.info(f"Arka Plan Zamanlayıcı ({MAIN_LOG_FILE_NAME} ve {TASK_LOG_FILE_NAME} ile) manuel olarak başlatıldı.")
    
    main_logger.info("Zamanlayıcı kuruluyor: `job_controller` her 1 dakikada bir çalışacak.")
    schedule.every(1).minutes.do(job_controller)
    main_logger.info(f"Ana ürün güncelleme kontrolcüsü (`job_controller`) her {1} dakikada bir çalışacak şekilde zamanlandı.")

    main_logger.info("İlk kontrol (job_controller) hemen tetikleniyor...")
    job_controller() 

    main_logger.info("Zamanlayıcı döngüsü başlatılıyor. Çıkmak için Ctrl+C.")
    try:
        while True:
            schedule.run_pending()
            time.sleep(1) 
    except KeyboardInterrupt:
        main_logger.info("Kullanıcı tarafından sonlandırıldı (Ctrl+C).")
    except Exception as e:
        main_logger.error(f"Ana zamanlayıcı döngüsünde beklenmedik hata: {e}", exc_info=True)
    finally:
        main_logger.info(f"Arka Plan Zamanlayıcı sonlandırılıyor.") 