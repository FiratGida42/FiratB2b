import time
import json
import os
import sys
import logging
import schedule
import shutil

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
    # Bu script arka planda sessizce çalışacağı için, import hatası durumunda loga yazmak önemli.
    # Başlangıçta bir log dosyası olmayabilir, bu yüzden konsola da yazdırabiliriz.
    # Ancak ideal olanı, bu scriptin log dosyasını oluşturup oraya yazması.
    # Şimdilik geçici bir print, loglama yapılandırıldıktan sonra bu logger'a taşınacak.
    print(f"FATAL: BackgroundScheduler import hatası: {e}. Script sonlandırılıyor.")
    # Loglama henüz ayarlanmadığı için burada bir log dosyasına yazmak zor.
    # Belki scriptin kendi log dosyasına başlangıçta yazmayı deneyebilir.
    sys.exit(1)

# Arka plan zamanlayıcı script'i için ayrı log dosyası ve yapılandırması
BG_SCHEDULER_LOG_DIR = os.path.join(APP_LOG_DIR) # Ana uygulamanın loglarıyla aynı genel log dizini
BG_SCHEDULER_LOG_FILE_NAME = "background_scheduler.log"
BG_SCHEDULER_LOG_FILE = os.path.join(BG_SCHEDULER_LOG_DIR, BG_SCHEDULER_LOG_FILE_NAME)

# Log dizininin var olduğundan emin ol
if not os.path.exists(BG_SCHEDULER_LOG_DIR):
    try:
        os.makedirs(BG_SCHEDULER_LOG_DIR)
    except OSError as e:
        # Konsola yazdır, çünkü logger henüz ayarlanmamış olabilir
        print(f"UYARI: Arka plan zamanlayıcı log dizini ({BG_SCHEDULER_LOG_DIR}) oluşturulamadı: {e}. Loglar yazılamayabilir.")

# Logger'ı yapılandır
# Bu logger SADECE bu script için olacak.
logger = logging.getLogger("BackgroundScheduler")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s")

# Dosya handler'ı
try:
    file_handler = logging.FileHandler(BG_SCHEDULER_LOG_FILE)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
except Exception as e:
    print(f"Hata: BackgroundScheduler için log dosyası handler'ı oluşturulamadı: {e}")

# Konsol handler'ı (test ve debug için faydalı)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

# En son başarılı güncelleme işinin zaman damgasını saklamak için global değişken
last_successful_update_timestamp = 0.0
# Müşteri senkronizasyonu için son başarılı kaynak dosya zaman damgası
last_synced_customer_file_mtime = 0.0

def perform_actual_update_task(excluded_groups_from_settings=None):
    """
    Asıl veri çekme, işleme ve API'ye gönderme işlemlerini gerçekleştirir.
    Başarılı olursa True, hata durumunda veya veri yoksa False döner (API'ye gönderilecek veri yoksa).
    """
    logger.info("Asıl güncelleme görevi başlatılıyor (perform_actual_update_task).")
    if excluded_groups_from_settings:
        logger.info(f"Ayarlardan gelen hariç tutulacak grup kodları: {excluded_groups_from_settings}")
    else:
        logger.info("Ayarlardan hariç tutulacak grup kodu belirtilmemiş.")
        
    db_conn = None
    try:
        db_conn = get_db_connection()
        if not db_conn:
            logger.error("Veritabanı bağlantısı kurulamadı. Güncelleme iptal edildi.")
            return False

        logger.info("Veritabanı bağlantısı başarılı. Ürün verileri çekiliyor...")
        product_data = fetch_product_data(db_conn, excluded_groups=excluded_groups_from_settings)

        if product_data is None:
            logger.error("fetch_product_data None döndürdü, muhtemelen bir hata oluştu. Güncelleme başarısız.")
            return False
        
        if not product_data:
            logger.info("API'ye gönderilecek ürün verisi bulunmuyor (filtrelenmiş olabilir veya mevcut değil).")
            return True 
        
        logger.info(f"{len(product_data)} adet ürün verisi (muhtemelen filtrelenmiş) çekildi. Web API'sine gönderiliyor...")
        success, message = send_data_to_web_api(product_data)
        if success:
            logger.info(f"Veriler başarıyla Web API'sine gönderildi. API Yanıtı: {message}")
            return True
        else:
            logger.error(f"Veriler Web API'sine gönderilemedi. Detay: {message}")
            return False

    except Exception as e:
        logger.error(f"Güncelleme görevi sırasında (perform_actual_update_task) genel bir hata oluştu: {e}", exc_info=True)
        return False
    finally:
        if db_conn:
            try:
                db_conn.close()
                logger.info("Veritabanı bağlantısı kapatıldı.")
            except Exception as e:
                logger.error(f"Veritabanı bağlantısı kapatılırken hata: {e}")
        logger.info("Asıl güncelleme görevinin (perform_actual_update_task) bu çalışması tamamlandı.")


def sync_customer_data_for_web():
    """
    Masaüstü uygulamasından gelen `filrelenen_cariler.json` dosyasını okur
    ve web uygulamasının kullanacağı `available_customers.json` dosyasına kopyalar.
    Yalnızca kaynak dosya daha yeniyse veya hedef dosya yoksa kopyalama yapar.
    """
    global last_synced_customer_file_mtime
    logger.info("Müşteri verisi senkronizasyon görevi (sync_customer_data_for_web) tetiklendi.")

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings_data = json.load(f)
    except Exception as e:
        logger.error(f"'{SETTINGS_FILE}' okunurken hata (sync_customer_data_for_web): {e}", exc_info=True)
        return

    sync_settings = settings_data.get("customer_sync_settings", {})
    is_enabled = sync_settings.get("enabled", False)
    source_file_name = sync_settings.get("source_file_relative_to_root")
    target_dir_name = sync_settings.get("target_directory_relative_to_root")
    target_file_name = sync_settings.get("target_filename")

    if not is_enabled:
        logger.info("Müşteri verisi senkronizasyonu (settings.json) etkin değil.")
        return

    if not all([source_file_name, target_dir_name, target_file_name]):
        logger.error("Müşteri senkronizasyon ayarları eksik (source_file_relative_to_root, target_directory_relative_to_root, veya target_filename). İşlem yapılamıyor.")
        return

    # BASE_DIR, background_scheduler.pyw dosyasının bulunduğu yer (proje kök dizini varsayılıyor)
    source_file_path = os.path.join(BASE_DIR, source_file_name)
    target_directory_path = os.path.join(BASE_DIR, target_dir_name)
    target_file_path = os.path.join(target_directory_path, target_file_name)

    logger.debug(f"Kaynak müşteri dosyası: {source_file_path}")
    logger.debug(f"Hedef müşteri dosyası: {target_file_path}")

    if not os.path.exists(source_file_path):
        logger.warning(f"Kaynak müşteri dosyası ({source_file_path}) bulunamadı. Senkronizasyon yapılamıyor.")
        return

    try:
        source_file_mtime = os.path.getmtime(source_file_path)
    except OSError as e:
        logger.error(f"Kaynak dosyanın ({source_file_path}) son değiştirilme zamanı alınamadı: {e}")
        return

    # Optimizasyon: Eğer kaynak dosya değişmemişse kopyalama yapma
    if source_file_mtime <= last_synced_customer_file_mtime and os.path.exists(target_file_path):
        logger.info(f"Kaynak müşteri dosyası ({source_file_name}) değişmemiş. Kopyalama atlanıyor.")
        return

    # Hedef dizini oluştur (varsa hata vermez)
    try:
        os.makedirs(target_directory_path, exist_ok=True)
        logger.info(f"Hedef dizin ({target_directory_path}) kontrol edildi/oluşturuldu.")
    except OSError as e:
        logger.error(f"Hedef dizin ({target_directory_path}) oluşturulurken hata: {e}", exc_info=True)
        return

    # Dosyayı kopyala
    try:
        shutil.copy2(source_file_path, target_file_path) # copy2 metadata'yı da kopyalar (örn: mtime)
        logger.info(f"Müşteri verileri başarıyla '{source_file_path}' dosyasından '{target_file_path}' dosyasına kopyalandı.")
        last_synced_customer_file_mtime = os.path.getmtime(target_file_path) # Kopyalanan dosyanın mtime'ını al
    except Exception as e:
        logger.error(f"Müşteri verileri kopyalanırken hata oluştu (kaynak: {source_file_path}, hedef: {target_file_path}): {e}", exc_info=True)


def job_controller():
    """
    Ayarları okur ve `interval_minutes`'a göre asıl güncelleme işini tetikler.
    Bu fonksiyon, schedule kütüphanesi tarafından düzenli (örn. her dakika) çağrılır.
    """
    global last_successful_update_timestamp
    logger.info("Zamanlayıcı kontrolcüsü (job_controller) tetiklendi.")

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings_data = json.load(f)
    except FileNotFoundError:
        logger.error(f'{SETTINGS_FILE} bulunamadı. Kontrol işlemi yapılamıyor.')
        return
    except json.JSONDecodeError:
        logger.error(f'{SETTINGS_FILE} geçerli bir JSON formatında değil. Kontrol işlemi yapılamıyor.')
        return
    except Exception as e:
        logger.error(f"'{SETTINGS_FILE}' okunurken beklenmedik bir hata: {e}")
        return

    scheduler_settings = settings_data.get("scheduler_settings", {})
    is_enabled = scheduler_settings.get("enabled", False)
    interval_minutes = scheduler_settings.get("interval_minutes", 30) 
    if not isinstance(interval_minutes, (int, float)) or interval_minutes <= 0:
        logger.warning(f"Ayarlardaki interval_minutes ({interval_minutes}) geçersiz, varsayılan 30 dk kullanılacak.")
        interval_minutes = 30

    # Excluded group codes'u settings.json'dan oku.
    excluded_group_codes = []
    user_preferences = settings_data.get("user_preferences", {}) # "user_preferences" anahtarını oku
    if "excluded_group_codes" in user_preferences:
        excluded_group_codes = user_preferences.get("excluded_group_codes", [])
        logger.info(f"'{SETTINGS_FILE}' içindeki 'user_preferences' altından 'excluded_group_codes' okundu: {excluded_group_codes}")
    # Eski kontrol (ui_settings veya root) artık gerekli değil, çünkü doğru yeri biliyoruz.
    # Ancak bir yedek olarak bırakılabilir veya tamamen kaldırılabilir. Şimdilik basitleştirelim:
    # elif "excluded_group_codes" in settings_data: # Root seviyesinde kontrol et (Artık bu duruma bakmıyoruz)
    #     excluded_group_codes = settings_data.get("excluded_group_codes", [])
    #     logger.info(f"Root seviyesinden 'excluded_group_codes' okundu: {excluded_group_codes}")
    else:
        logger.info(f"Ayarlarda ({SETTINGS_FILE} -> user_preferences) 'excluded_group_codes' bulunamadı. Filtreleme yapılmayacak.")

    if not isinstance(excluded_group_codes, list):
        logger.warning(f"Ayarlardaki 'excluded_group_codes' bir liste değil ({type(excluded_group_codes)}), boş liste olarak kullanılacak.")
        excluded_group_codes = []

    logger.info(f"Ayarlar okundu: Etkin = {is_enabled}, İstenen Güncelleme Aralığı = {interval_minutes} dk, Hariç Tutulan Gruplar: {excluded_group_codes}")

    if not is_enabled:
        logger.info("Otomatik güncelleme (settings.json) etkin değil. Asıl işlem yapılmayacak.")
        return

    current_time = time.time()
    elapsed_seconds_since_last_run = current_time - last_successful_update_timestamp
    required_seconds_for_interval = interval_minutes * 60

    logger.debug(f"Son başarılı çalışmadan bu yana geçen süre: {elapsed_seconds_since_last_run:.0f} saniye.")
    logger.debug(f"İstenen aralık: {required_seconds_for_interval:.0f} saniye ({interval_minutes} dk).")

    if elapsed_seconds_since_last_run >= required_seconds_for_interval:
        logger.info(f"Gerekli aralık ({interval_minutes} dk) geçti veya ilk çalıştırma. Asıl güncelleme görevi başlatılıyor.")
        
        update_successful = perform_actual_update_task(excluded_groups_from_settings=excluded_group_codes)
        
        if update_successful:
            logger.info("Asıl güncelleme görevi başarıyla tamamlandı. Son çalışma zamanı güncellendi.")
            last_successful_update_timestamp = current_time
        else:
            logger.warning("Asıl güncelleme görevi başarısız oldu veya tamamlanamadı. Son çalışma zamanı güncellenmedi, bir sonraki kontrolde tekrar denenebilir.")
    else:
        remaining_seconds = required_seconds_for_interval - elapsed_seconds_since_last_run
        logger.info(f"İstenen aralık ({interval_minutes} dk) henüz geçmedi. Kalan süre yaklaşık {remaining_seconds / 60:.1f} dk. Bu döngüde asıl işlem yapılmayacak.")

if __name__ == "__main__":
    logger.info(f"Arka Plan Zamanlayıcı ({BG_SCHEDULER_LOG_FILE_NAME}) manuel olarak başlatıldı.")
    
    # job_controller fonksiyonunu her dakika çalışacak şekilde zamanla.
    # Bu fonksiyon, settings.json'daki interval_minutes'ı ve son çalışma zamanını kontrol ederek
    # asıl güncelleme işini (perform_actual_update_task) gerekirse tetikleyecektir.
    
    # Örnek: Her 1 dakikada bir ayarları ve zamanı kontrol et.
    logger.info("Zamanlayıcı kuruluyor: `job_controller` her 1 dakikada bir çalışacak.")
    schedule.every(1).minutes.do(job_controller)
    logger.info(f"Ana ürün güncelleme kontrolcüsü (`job_controller`) her {1} dakikada bir çalışacak şekilde zamanlandı.")

    # Müşteri verisi senkronizasyon görevini zamanla
    _check_interval = 60 # Varsayılan değer
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f_settings:
            _settings_data_for_sync_interval = json.load(f_settings)
        _sync_settings = _settings_data_for_sync_interval.get("customer_sync_settings", {})
        if _sync_settings: # Ayarlar varsa içinden oku
            _check_interval = _sync_settings.get("check_interval_seconds", 60) 
            if not isinstance(_check_interval, (int, float)) or _check_interval <= 0:
                logger.warning(f"customer_sync_settings içindeki check_interval_seconds ({_check_interval}) geçersiz, varsayılan 60 sn kullanılacak.")
                _check_interval = 60
            logger.info(f"Müşteri senkronizasyon ayarları okundu: check_interval_seconds = {_check_interval}")
        else:
            logger.warning(f"'{SETTINGS_FILE}' içinde `customer_sync_settings` bölümü bulunamadı. Müşteri senkronizasyonu için varsayılan {_check_interval}sn aralığı kullanılacak.")
        
        schedule.every(_check_interval).seconds.do(sync_customer_data_for_web)
        logger.info(f"Müşteri senkronizasyon görevi (`sync_customer_data_for_web`) her {_check_interval} saniyede bir çalışacak şekilde zamanlandı.")

    except Exception as e:
        logger.error(f"Müşteri senkronizasyon görevi zamanlanırken {SETTINGS_FILE} okunamadı veya ayar hatası: {e}. Varsayılan 60sn aralığı ile zamanlama deneniyor.", exc_info=True)
        schedule.every(60).seconds.do(sync_customer_data_for_web) 
        logger.info("Müşteri senkronizasyon görevi (`sync_customer_data_for_web`) hata nedeniyle varsayılan 60 saniye aralığı ile zamanlandı.")

    # Başlangıçta hemen bir kez çalıştırarak ayarları ve zamanı kontrol etsin.
    logger.info("İlk kontrol (job_controller) hemen tetikleniyor...")
    job_controller() 
    logger.info("İlk müşteri verisi senkronizasyonu (sync_customer_data_for_web) hemen tetikleniyor...")
    sync_customer_data_for_web() # Bu çağrının kesinlikle yapıldığından emin olalım

    logger.info("Zamanlayıcı döngüsü başlatılıyor. Çıkmak için Ctrl+C.")
    try:
        while True:
            schedule.run_pending()
            time.sleep(1) 
    except KeyboardInterrupt:
        logger.info("Kullanıcı tarafından sonlandırıldı (Ctrl+C).")
    except Exception as e:
        logger.error(f"Ana zamanlayıcı döngüsünde beklenmedik hata: {e}", exc_info=True)
    finally:
        logger.info(f"Arka Plan Zamanlayıcı ({BG_SCHEDULER_LOG_FILE_NAME}) sonlandırılıyor.") 