import json
import os
import sys
import logging
import time # Olası yeniden denemeler veya zamanlamalar için eklenebilir, şimdilik direkt kullanılmıyor.

# Proje kök dizinini sys.path\'e ekleyerek data_extractor ve helpers\'ı import edebilmek için
# Bu script\'in proje kök dizininde olduğunu varsayıyoruz.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

try:
    from data_extractor import (
        get_db_connection, 
        fetch_product_data, 
        send_data_to_web_api,
        SETTINGS_FILE, # data_extractor\'dan SETTINGS_FILE sabitini alalım
        LOG_DIR as APP_LOG_DIR # data_extractor\'daki log dizinini karışmaması için farklı bir isimle alalım
    )
    from helpers import to_decimal # Eğer gerekirse
except ImportError as e:
    print(f"Hata: Gerekli modüller import edilemedi. Script muhtemelen proje kök dizininde değil veya PYTHONPATH ayarlanmamış: {e}")
    sys.exit(1)

# Zamanlayıcı script\'i için ayrı log dosyası ve yapılandırması
SCHEDULER_LOG_DIR = os.path.join(APP_LOG_DIR) # Ana uygulamanın loglarıyla aynı dizinde olsun
SCHEDULER_LOG_FILE_NAME = "scheduler.log"
SCHEDULER_LOG_FILE = os.path.join(SCHEDULER_LOG_DIR, SCHEDULER_LOG_FILE_NAME)

# Log dizininin var olduğundan emin ol (data_extractor.py bunu zaten yapmalı ama yine de kontrol edelim)
if not os.path.exists(SCHEDULER_LOG_DIR):
    try:
        os.makedirs(SCHEDULER_LOG_DIR)
    except OSError as e:
        # Eğer log dizini oluşturulamazsa, bu ciddi bir sorun, en azından konsola yazdıralım.
        # Gerçek bir uygulamada bu durum için daha iyi bir hata yönetimi gerekebilir.
        print(f"UYARI: Zamanlayıcı log dizini ({SCHEDULER_LOG_DIR}) oluşturulamadı: {e}. Loglar yazılamayabilir.")
        # Alternatif olarak, script\'in çalışmasını engelleyebilirsiniz veya varsayılan bir yere log atmayı deneyebilirsiniz.

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s",
    handlers=[
        logging.FileHandler(SCHEDULER_LOG_FILE),
        logging.StreamHandler() # Konsola da loglayalım ki zamanlayıcı çalıştığında görebilelim
    ],
    force=True # Mevcut root logger yapılandırmasının üzerine yazmayı zorla
)
logger = logging.getLogger("SchedulerScript")


def run_scheduled_update():
    logger.info("Zamanlanmış güncelleme script\'i başlatıldı.")

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings_data = json.load(f)
    except FileNotFoundError:
        logger.error(f"{SETTINGS_FILE} bulunamadı. Güncelleme işlemi yapılamıyor.")
        return
    except json.JSONDecodeError:
        logger.error(f"{SETTINGS_FILE} geçerli bir JSON formatında değil. Güncelleme işlemi yapılamıyor.")
        return
    except Exception as e:
        logger.error(f"{SETTINGS_FILE} okunurken beklenmedik bir hata: {e}")
        return

    scheduler_settings = settings_data.get("scheduler_settings", {})
    is_enabled = scheduler_settings.get("enabled", False)
    # interval_minutes = scheduler_settings.get("interval_minutes", 30) # Bu script için doğrudan kullanılmıyor.

    if not is_enabled:
        logger.info("Otomatik güncelleme ayarı etkin değil. İşlem yapılmayacak.")
        return

    logger.info("Otomatik güncelleme etkin. Veri çekme ve gönderme işlemi başlatılıyor.")
    
    db_conn = None # Bağlantıyı başta None olarak tanımla
    try:
        db_conn = get_db_connection()
        if not db_conn:
            logger.error("Veritabanı bağlantısı kurulamadı. Güncelleme iptal edildi.")
            return

        logger.info("Veritabanı bağlantısı başarılı. Ürün verileri çekiliyor...")
        product_data = fetch_product_data(db_conn)

        if product_data is None: # fetch_product_data None dönerse (hata veya veri yok)
            logger.warning("fetch_product_data \'None\' döndürdü. API\'ye gönderilecek veri yok veya bir hata oluştu.")
            # API\'ye göndermeden önce product_data\'nın boş olup olmadığını kontrol etmek iyi bir pratik.
            # send_data_to_web_api zaten boş listeyi handle ediyor ama burada da loglayabiliriz.
            if not product_data: # Eğer product_data gerçekten boş bir liste ise (None değilse)
                 logger.info("Çekilecek aktif ürün bulunamadı.")
            # return # Eğer None ise veya boşsa burada durabiliriz, send_data_to_web_api de bunu yapar.

        if not product_data: # Hem None hem de boş liste durumunu kapsar
            logger.info("API\'ye gönderilecek ürün verisi bulunmuyor (çekilemedi veya mevcut değil).")
        else:
            logger.info(f"{len(product_data)} adet ürün verisi çekildi. Web API\'sine gönderiliyor...")
            success, message = send_data_to_web_api(product_data) # DEFAULT_API_URL kullanılır
            if success:
                logger.info(f"Veriler başarıyla Web API\'sine gönderildi. Sunucu mesajı: {message}")
            else:
                logger.error(f"Veriler Web API\'sine gönderilemedi. Hata: {message}")

    except Exception as e:
        logger.error(f"Zamanlanmış güncelleme sırasında genel bir hata oluştu: {e}", exc_info=True)
    finally:
        if db_conn:
            try:
                db_conn.close()
                logger.info("Veritabanı bağlantısı kapatıldı.")
            except Exception as e:
                logger.error(f"Veritabanı bağlantısı kapatılırken hata: {e}")
        logger.info("Zamanlanmış güncelleme script\'i tamamlandı.")

if __name__ == "__main__":
    print(f"Scheduler script manually invoked. Logging to: {SCHEDULER_LOG_FILE}")
    run_scheduled_update() 