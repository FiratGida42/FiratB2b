import time
import json
import os
import sys
import logging
import schedule
from datetime import datetime

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
    # Konsol yoksa hatayı dosyaya yazmayı dene
    try:
        with open(os.path.join(BASE_DIR, "background_scheduler_CRITICAL_ERROR.log"), "w") as f_err:
            f_err.write(f"FATAL: BackgroundScheduler import hatası: {e}. Script sonlandırılıyor.\n")
    except:
        pass
    sys.exit(1)

# Log dizini
LOG_BASE_DIR = os.path.join(APP_LOG_DIR) 

# Global sabit log dosyası adları artık kullanılmayacak
# MAIN_LOG_FILE_NAME = "background_scheduler_main.log"
# MAIN_LOG_FILE = os.path.join(LOG_BASE_DIR, MAIN_LOG_FILE_NAME)
# TASK_LOG_FILE_NAME = "product_update_task.log"
# TASK_LOG_FILE = os.path.join(LOG_BASE_DIR, TASK_LOG_FILE_NAME)

if not os.path.exists(LOG_BASE_DIR):
    try:
        os.makedirs(LOG_BASE_DIR)
    except OSError as e:
        # .pyw için print yerine başlangıçta hata log dosyasına yazılabilir
        pass

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s")

# Ana Zamanlayıcı Logger'ı - FileHandler'ı artık global olarak eklenmeyecek
main_logger = logging.getLogger("BackgroundSchedulerMain")
main_logger.setLevel(logging.INFO)
main_logger.propagate = False # Yayılım zaten kapalıydı, teyit ediliyor

# main_logger.info(f"TASK_LOG_FILE tam yolu: ...") # Bu artık geçerli değil, dinamik olacak

# Global FileHandler try-except bloğu kaldırıldı
# try:
#     main_file_handler = logging.FileHandler(MAIN_LOG_FILE, mode='a', encoding='utf-8') 
#     main_file_handler.setFormatter(formatter)
#     main_logger.addHandler(main_file_handler)
#     main_logger.info(f"Ana logger için FileHandler ({MAIN_LOG_FILE}) başarıyla eklendi.")
# except Exception as e:
#     error_message = f"KRİTİK HATA: Ana logger için FileHandler ({os.path.abspath(MAIN_LOG_FILE)}) oluşturulamadı/eklenemedi: {e}"
#     print(error_message) # .pyw'de bu görünmeyebilir
#     # main_logger'a loglamaya çalışmak döngüye sokabilir eğer handler yoksa, bu yüzden sadece print.
#     # Eğer başlangıçta bir yere acil durum logu yazılıyorsa oraya da yazılabilir.

main_stream_handler = logging.StreamHandler(sys.stdout) # Konsol çıktısı için (geliştirme/debug)
main_stream_handler.setFormatter(formatter)
main_logger.addHandler(main_stream_handler)


# Ürün Güncelleme Görevi Global Logger'ı - Artık FileHandler almayacak, her çalıştırmada kendi logger'ını kullanacak
# task_logger = logging.getLogger("ProductUpdateTask") # Bu global logger artık kullanılmayabilir
# task_logger.setLevel(logging.INFO)
# task_logger.propagate = False # Yayılım zaten kapalıydı

# Global task_file_handler try-except bloğu kaldırıldı


last_successful_update_timestamp = 0.0

def cleanup_old_logs(log_directory_to_clean, days_to_retain):
    run_timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    cleanup_logger_name = f"LogCleanupRun_{run_timestamp_str}"
    cleanup_logger = logging.getLogger(cleanup_logger_name)
    cleanup_logger.setLevel(logging.INFO)
    cleanup_logger.propagate = False

    current_cleanup_log_file_name = f"log_cleanup_run_{run_timestamp_str}.log"
    current_cleanup_log_path = os.path.join(LOG_BASE_DIR, current_cleanup_log_file_name)
    
    cleanup_file_handler = None
    try:
        cleanup_file_handler = logging.FileHandler(current_cleanup_log_path, mode='a', encoding='utf-8')
        cleanup_file_handler.setFormatter(formatter) 
        cleanup_logger.addHandler(cleanup_file_handler)

        cleanup_logger.info(f"Log temizleme görevi başlatılıyor. Hedef klasör: {log_directory_to_clean}, Saklanacak gün sayısı: {days_to_retain} (Bu süreden eski olanlar silinecek).")
        
        if not os.path.isdir(log_directory_to_clean):
            cleanup_logger.error(f"Belirtilen log klasörü bulunamadı: {log_directory_to_clean}")
            return

        cutoff_seconds = days_to_retain * 24 * 60 * 60
        current_time_seconds = time.time()
        files_deleted_count = 0
        errors_count = 0

        for filename in os.listdir(log_directory_to_clean):
            file_path = os.path.join(log_directory_to_clean, filename)
            
            if not os.path.isfile(file_path):
                continue

            if filename == current_cleanup_log_file_name: # Kendi log dosyasını silme
                continue

            try:
                file_mod_time = os.path.getmtime(file_path)
                if (current_time_seconds - file_mod_time) > cutoff_seconds:
                    os.remove(file_path)
                    cleanup_logger.info(f"Silindi ({days_to_retain} günden eski): {file_path}")
                    files_deleted_count += 1
            except Exception as e:
                cleanup_logger.error(f"Dosya silinirken hata oluştu ({file_path}): {e}")
                errors_count += 1
        
        cleanup_logger.info(f"Log temizleme tamamlandı. Silinen dosya sayısı: {files_deleted_count}, Karşılaşılan hata sayısı: {errors_count}.")

    except Exception as e_outer:
        log_target = cleanup_logger if cleanup_file_handler and cleanup_logger.hasHandlers() else main_logger
        log_target.error(f"Log temizleme görevi sırasında genel bir hata: {e_outer}", exc_info=True)
    finally:
        if cleanup_file_handler:
            cleanup_logger.removeHandler(cleanup_file_handler)
            cleanup_file_handler.close()

def run_log_cleanup_job():
    main_logger.info(f"Log temizleme görevi (run_log_cleanup_job) tetiklendi. LOG_BASE_DIR: {LOG_BASE_DIR}")
    cleanup_old_logs(log_directory_to_clean=LOG_BASE_DIR, days_to_retain=1)

def perform_actual_update_task(excluded_groups_from_settings=None, job_controller_main_logger=None):
    # job_controller_main_logger, job_controller'ın o anki file handler'ını kullanan logger'ı
    # Bu fonksiyon kendi log dosyasını oluşturacağı için buna gerek kalmayabilir.
    # Ya da başlangıç/bitiş gibi çok temel bilgileri oraya yazabilir. Şimdilik kendi logger'ına odaklansın.

    run_timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    run_logger_name = f"ProductUpdateRun_{run_timestamp_str}"
    run_logger = logging.getLogger(run_logger_name)
    run_logger.setLevel(logging.INFO)
    run_logger.propagate = False # Bu çalıştırmaya özel loglar başka yere gitmesin

    current_run_log_file_name = f"product_update_task_run_{run_timestamp_str}.log"
    current_run_log_path = os.path.join(LOG_BASE_DIR, current_run_log_file_name)
    
    run_file_handler = None
    try:
        run_file_handler = logging.FileHandler(current_run_log_path, mode='a', encoding='utf-8')
        run_file_handler.setFormatter(formatter)
        run_logger.addHandler(run_file_handler)

        run_logger.info(f"Asıl ürün güncelleme görevi başlatılıyor (Detay log: {current_run_log_file_name}).")
        if excluded_groups_from_settings:
            run_logger.info(f"Ayarlardan gelen hariç tutulacak grup kodları: {excluded_groups_from_settings}")
        else:
            run_logger.info("Ayarlardan hariç tutulacak grup kodu belirtilmemiş.")
        
        db_conn = None
        db_conn = get_db_connection(caller_info=f"ProductUpdateRun_{run_timestamp_str}")
        if not db_conn:
            run_logger.error("Veritabanı bağlantısı kurulamadı. Güncelleme iptal edildi.")
            return False, current_run_log_file_name # Log dosyasının adını döndür

        run_logger.info("Veritabanı bağlantısı başarılı. Ürün verileri çekiliyor...")
        product_data = fetch_product_data(db_conn, excluded_groups=excluded_groups_from_settings)

        if product_data is None:
            run_logger.error("fetch_product_data None döndürdü, muhtemelen bir hata oluştu. Güncelleme başarısız.")
            return False, current_run_log_file_name
        
        if not product_data:
            run_logger.info("API'ye gönderilecek ürün verisi bulunmuyor (filtrelenmiş olabilir veya mevcut değil).")
            # Başarılı sayılabilir, çünkü yapılacak bir şey yoktu.
            # Ancak job_controller'ın bunu bilmesi için log dosyasını yine de döndürelim.
            return True, current_run_log_file_name 
        
        run_logger.info(f"{len(product_data)} adet ürün verisi (muhtemelen filtrelenmiş) çekildi. Web API'sine gönderiliyor...")
        
        # Detaylı ürün loglama (önceki DEBUG bloğu)
        run_logger.info("--- DEBUG: product_data loglama BAŞLANGIÇ ---")
        if product_data and isinstance(product_data, list) and len(product_data) > 0:
            run_logger.info(f"product_data listesi {len(product_data)} eleman içeriyor.")
            try:
                for i in range(min(len(product_data), 3)):
                    item_str = str(product_data[i])
                    run_logger.info(f"Örnek product_data[{i}]: {item_str}")
                    image_path = product_data[i].get('IMAGE_PATH_WEB', 'BULUNAMADI')
                    stok_kodu = product_data[i].get('STOK_KODU', 'BULUNAMADI')
                    run_logger.info(f"Detaylı: product_data[{i}] STOK_KODU: {stok_kodu}, IMAGE_PATH_WEB: {image_path}")
            except Exception as e_log:
                run_logger.error(f"product_data loglanırken hata oluştu: {e_log}")
        elif product_data is None: # Bu koşul yukarıda zaten handle edildi ama yine de bulunsun.
            run_logger.info("product_data None olarak geldi.")
        elif not isinstance(product_data, list):
            run_logger.info(f"product_data bir liste değil, tipi: {type(product_data)}")
        else: # Boş liste durumu
            run_logger.info("product_data boş bir liste.")
        run_logger.info("--- DEBUG: product_data loglama BİTİŞ ---")

        success, message = send_data_to_web_api(product_data) # Bu fonksiyon data_extractor_logger kullanır
        if success:
            run_logger.info(f"Veriler başarıyla Web API'sine gönderildi. API Yanıtı: {message}")
            return True, current_run_log_file_name
        else:
            run_logger.error(f"Veriler Web API'sine gönderilemedi. Detay: {message}")
            return False, current_run_log_file_name

    except Exception as e:
        # Eğer run_logger ve handler'ı kurulduysa oraya logla, yoksa main_logger'a (konsola)
        log_target = run_logger if run_file_handler and run_logger.hasHandlers() else main_logger
        log_target.error(f"Güncelleme görevi sırasında (perform_actual_update_task) genel bir hata oluştu: {e}", exc_info=True)
        return False, current_run_log_file_name if run_file_handler else "log_dosyasi_olusturulamadi"
    finally:
        if db_conn:
            try:
                db_conn.close()
                if run_file_handler and run_logger.hasHandlers(): # Handler varsa logla
                     run_logger.info("Veritabanı bağlantısı kapatıldı.")
            except Exception as e:
                if run_file_handler and run_logger.hasHandlers():
                     run_logger.error(f"Veritabanı bağlantısı kapatılırken hata: {e}")
        
        if run_file_handler and run_logger.hasHandlers(): # Handler varsa logla
            run_logger.info("Asıl ürün güncelleme görevinin (perform_actual_update_task) bu çalışması tamamlandı.")

        # Her çalıştırmada oluşturulan handler'ı kaldır ve kapat
        if run_file_handler:
            run_logger.removeHandler(run_file_handler)
            run_file_handler.close()


def job_controller():
    global last_successful_update_timestamp
    
    controller_timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    controller_log_file_name = f"bgs_main_controller_run_{controller_timestamp_str}.log"
    controller_log_path = os.path.join(LOG_BASE_DIR, controller_log_file_name)
    
    controller_file_handler = None
    try:
        controller_file_handler = logging.FileHandler(controller_log_path, mode='a', encoding='utf-8')
        controller_file_handler.setFormatter(formatter)
        main_logger.addHandler(controller_file_handler) # Bu çalıştırmaya özel handler'ı ekle

        main_logger.info(f"Zamanlayıcı kontrolcüsü (job_controller) tetiklendi. (Log dosyası: {controller_log_file_name})")

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

        user_preferences = settings_data.get("user_preferences", {})
        excluded_group_codes = user_preferences.get("excluded_group_codes", [])
        main_logger.info(f"Ayarlar okundu: Etkin = {is_enabled}, İstenen Güncelleme Aralığı = {interval_minutes} dk, Hariç Tutulan Gruplar: {excluded_group_codes}")

        if not is_enabled:
            main_logger.info("Otomatik güncelleme (settings.json) etkin değil. Asıl işlem yapılmayacak.")
            return

        current_time = time.time()
        elapsed_seconds_since_last_run = current_time - last_successful_update_timestamp
        required_seconds_for_interval = interval_minutes * 60

        if elapsed_seconds_since_last_run >= required_seconds_for_interval:
            main_logger.info(f"Gerekli aralık ({interval_minutes} dk) geçti veya ilk çalıştırma. Asıl güncelleme görevi (`perform_actual_update_task`) başlatılıyor.")
            
            update_successful, task_log_file = perform_actual_update_task(excluded_groups_from_settings=excluded_group_codes)
            
            if update_successful:
                main_logger.info(f"Asıl güncelleme görevi başarıyla tamamlandı. Detaylar için bkz: {task_log_file}. Son çalışma zamanı güncellendi.")
                last_successful_update_timestamp = current_time
            else:
                main_logger.warning(f"Asıl güncelleme görevi başarısız oldu veya tamamlanamadı. Detaylar için bkz: {task_log_file}. Son çalışma zamanı güncellenmedi.")
        else:
            remaining_seconds = required_seconds_for_interval - elapsed_seconds_since_last_run
            main_logger.info(f"İstenen aralık ({interval_minutes} dk) henüz geçmedi. Kalan süre yaklaşık {remaining_seconds / 60:.1f} dk. Bu döngüde asıl işlem yapılmayacak.")

    except Exception as e_controller:
        main_logger.error(f"job_controller sırasında beklenmedik bir hata: {e_controller}", exc_info=True)
    finally:
        if controller_file_handler:
            main_logger.removeHandler(controller_file_handler)
            controller_file_handler.close()


if __name__ == "__main__":
    # __main__ bloğundaki ilk loglar sadece konsola gider (StreamHandler sayesinde)
    # Eğer job_controller çağrılmadan önce dosya loglaması isteniyorsa, burada da geçici bir handler kurulabilir.
    main_logger.info(f"Arka Plan Ürün Zamanlayıcı (dinamik log dosyaları ile) manuel olarak başlatıldı.")
    
    schedule.every(1).minutes.do(job_controller) # job_controller her 1 dakikada bir çağrılır
    main_logger.info(f"Ana ürün güncelleme kontrolcüsü (`job_controller`) her 1 dakikada bir çalışacak şekilde zamanlandı.")

    # Log temizleme görevi için zamanlama (her gün sabah 03:00'te)
    schedule.every().day.at("03:00").do(run_log_cleanup_job)
    main_logger.info(f"Log temizleme görevi (`run_log_cleanup_job`) her gün saat 03:00'te çalışacak şekilde zamanlandı.")

    main_logger.info("İlk kontrol (job_controller) hemen tetikleniyor...")
    job_controller() 

    # İsteğe bağlı: Başlangıçta bir log temizleme çalışması (test için veya hemen temizlik için)
    # main_logger.info("Başlangıçta log temizleme görevi bir kerelik tetikleniyor...")
    # run_log_cleanup_job()

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
        main_logger.info(f"Arka Plan Ürün Zamanlayıcı sonlandırılıyor.") 