#!/usr/bin/env python3
"""
B2B Offline Portal Kurulum Scripti
Bu script, offline portal için gerekli klasör yapısını oluşturur,
veritabanını hazırlar ve örnek veri dosyaları oluşturur.
"""

import os
import json
import sqlite3 # Veritabanı kontrolü için (opsiyonel)
from pathlib import Path

# Bu script Offline klasörü içinden çalıştırılacağı için,
# models ve database modüllerini doğrudan import edebiliriz.
try:
    from database import engine, SQLALCHEMY_DATABASE_URL, Base as DatabaseBase
    from models import Base as ModelBase # models.py'deki Base'i de alalım (aynı olmalılar)
except ImportError as e:
    print(f"HATA: Gerekli modüller (database, models) import edilemedi: {e}")
    print("Bu script'i 'Offline' klasörünün içinden çalıştırdığınızdan emin olun.")
    exit(1)

# Bu script'in bulunduğu dizin (Offline klasörü)
BASE_DIR = Path(__file__).resolve().parent

# Ortam değişkeninden veritabanı URL'sini al, yoksa varsayılan SQLite kullan
OFFLINE_DATA_DB_NAME = "b2b_offline_data.db"
OFFLINE_DATABASE_URL = os.environ.get("OFFLINE_DATABASE_URL", f"sqlite:///./{OFFLINE_DATA_DB_NAME}")
DB_FILE_PATH = BASE_DIR / OFFLINE_DATA_DB_NAME # Veritabanı dosyasının tam yolu

print(f"UYARI: OFFLINE_DATABASE_URL ortam değişkeni bulunamadı! Yerel SQLite kullanılacak: {OFFLINE_DATA_DB_NAME}")
print(f"OFFLINE DATABASE: Kullanılacak veritabanı URL'si: {OFFLINE_DATABASE_URL}")


# Static ve templates klasör yolları
STATIC_DIR = BASE_DIR / "static"
CSS_DIR = STATIC_DIR / "css"
JS_DIR = STATIC_DIR / "js"
IMAGES_DIR = STATIC_DIR / "images"
JSON_DATA_DIR = STATIC_DIR / "json_data" # <<<< JSON verilerinin kaydedileceği doğru klasör
FONTS_DIR = CSS_DIR / "fonts" # Bootstrap ikonları için
TEMPLATES_DIR = BASE_DIR / "templates"


def create_folders():
    """Gerekli statik ve template klasörlerini oluşturur."""
    print("\n--- Klasörler Oluşturuluyor ---")
    os.makedirs(STATIC_DIR, exist_ok=True)
    os.makedirs(CSS_DIR, exist_ok=True)
    print(f"✓ Klasör hazır: {CSS_DIR.relative_to(BASE_DIR)}")
    os.makedirs(JS_DIR, exist_ok=True)
    print(f"✓ Klasör hazır: {JS_DIR.relative_to(BASE_DIR)}")
    os.makedirs(IMAGES_DIR, exist_ok=True)
    print(f"✓ Klasör hazır: {IMAGES_DIR.relative_to(BASE_DIR)}")
    os.makedirs(JSON_DATA_DIR, exist_ok=True) # JSON_DATA klasörünü oluştur
    print(f"✓ Klasör hazır: {JSON_DATA_DIR.relative_to(BASE_DIR)}")
    os.makedirs(FONTS_DIR, exist_ok=True) # FONTS klasörünü de oluşturalım (download_assets içinde de var ama burada da olabilir)
    # print(f"✓ Klasör hazır: {FONTS_DIR.relative_to(BASE_DIR)}") # İsteğe bağlı çıktı
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    print(f"✓ Klasör hazır: {TEMPLATES_DIR.relative_to(BASE_DIR)}")


def setup_database():
    """Veritabanı tablolarını oluşturur (SQLAlchemy Base kullanarak)."""
    print("\n--- Veritabanı Hazırlanıyor ---")
    try:
        # Hem database.py'deki hem de models.py'deki Base'in aynı olduğundan emin olalım
        # Genellikle tek bir Base kullanılır ve diğerinden import edilir.
        # Bizim yapımızda models.py, database.py'den Base'i import ediyor.
        ModelBase.metadata.create_all(bind=engine)
        print(f"✓ Veritabanı tabloları '{SQLALCHEMY_DATABASE_URL.replace('sqlite:///', '')}' içinde oluşturuldu/kontrol edildi.")
    except Exception as e:
        print(f"✗ Veritabanı tabloları oluşturulurken hata: {e}")
        print("  SQLAlchemy ve veritabanı sürücülerinizin kurulu olduğundan emin olun.")


def create_sample_json_data():
    """Örnek ürün ve müşteri JSON dosyalarını oluşturur."""
    print("\n--- Örnek JSON Verileri Oluşturuluyor ---")
    
    sample_customers = [
        {"CARI_KOD": "M001", "CARI_ISIM": "Örnek Müşteri A.Ş.", "BORC_BAKIYESI": 1250.75, "ALACAK_BAKIYESI": 0, "NET_BAKIYE": 1250.75, "GRUP_KODU": "Grup1"},
        {"CARI_KOD": "M002", "CARI_ISIM": "Test Cari Ltd. Şti.", "BORC_BAKIYESI": 0, "ALACAK_BAKIYESI": 550.00, "NET_BAKIYE": -550.00, "GRUP_KODU": "Grup2"},
        {"CARI_KOD": "M003", "CARI_ISIM": "Deneme Market", "BORC_BAKIYESI": 340.00, "ALACAK_BAKIYESI": 100.00, "NET_BAKIYE": 240.00, "GRUP_KODU": "Grup1"},
    ]
    customers_file_path = JSON_DATA_DIR / "filtrelenen_cariler.json"
    try:
        with open(customers_file_path, 'w', encoding='utf-8') as f:
            json.dump(sample_customers, f, ensure_ascii=False, indent=4)
        print(f"✓ Örnek müşteri verisi oluşturuldu: {customers_file_path.relative_to(BASE_DIR)}")
    except Exception as e:
        print(f"X HATA: Örnek müşteri verisi oluşturulamadı ({customers_file_path}): {e}")

    sample_products = [
        {"STOK_KODU": "URUN001", "STOK_ADI": "Çevrimdışı Test Ürünü 1", "GRUP_KODU": "GIDA", "BARKOD1": "869000000001", "BAKIYE": 50, "SATIS_FIAT1": 15.99, "IMAGE_PATH_WEB": "images/urun_placeholder_1.png"},
        {"STOK_KODU": "URUN002", "STOK_ADI": "Çevrimdışı Test Ürünü 2", "GRUP_KODU": "ICECEK", "BARKOD1": "869000000002", "BAKIYE": 25, "SATIS_FIAT1": 7.50, "IMAGE_PATH_WEB": "images/urun_placeholder_2.png"},
        {"STOK_KODU": "URUN003", "STOK_ADI": "Çevrimdışı Test Ürünü 3 (Stok Yok)", "GRUP_KODU": "TEMIZLIK", "BARKOD1": "869000000003", "BAKIYE": 0, "SATIS_FIAT1": 22.00, "IMAGE_PATH_WEB": "images/urun_placeholder_3.png"},
        {"STOK_KODU": "URUN004", "STOK_ADI": "Süper Uzun İsimli Bir Çevrimdışı Ürün Denemesi Yapılıyor Bakalım Nasıl Görünecek", "GRUP_KODU": "GIDA", "BARKOD1": "869000000004", "BAKIYE": 100, "SATIS_FIAT1": 12.75, "IMAGE_PATH_WEB": "images/urun_yok.png"},
    ]
    products_file_path = JSON_DATA_DIR / "received_products.json"
    try:
        with open(products_file_path, 'w', encoding='utf-8') as f:
            json.dump(sample_products, f, ensure_ascii=False, indent=4)
        print(f"✓ Örnek ürün verisi oluşturuldu: {products_file_path.relative_to(BASE_DIR)}")
    except Exception as e:
        print(f"X HATA: Örnek ürün verisi oluşturulamadı ({products_file_path}): {e}")


def create_placeholder_icons():
    """PWA için örnek ikon dosyaları oluşturur."""
    print("\n--- Örnek İkonlar Oluşturuluyor ---")
    icon_content = b'' # Boş byte dizisi, veya basit bir PNG başlığı eklenebilir
    icon192_path = IMAGES_DIR / "icon-192.png"
    icon512_path = IMAGES_DIR / "icon-512.png"
    try:
        if not icon192_path.exists():
            with open(icon192_path, 'wb') as f: f.write(icon_content)
            print(f"✓ Placeholder oluşturuldu: {icon192_path.relative_to(BASE_DIR)}")
        else:
            print(f"✓ İkon zaten var: {icon192_path.relative_to(BASE_DIR)}")

        if not icon512_path.exists():
            with open(icon512_path, 'wb') as f: f.write(icon_content)
            print(f"✓ Placeholder oluşturuldu: {icon512_path.relative_to(BASE_DIR)}")
        else:
            print(f"✓ İkon zaten var: {icon512_path.relative_to(BASE_DIR)}")
        print("  Lütfen manifest.json dosyasında belirtilen gerçek PNG ikonlarını bu klasöre ekleyin.")
    except Exception as e:
        print(f"X HATA: Placeholder ikonlar oluşturulurken hata: {e}")


def create_offline_html_page():
    """Offline fallback HTML sayfasını oluşturur."""
    print("\n--- Offline HTML Sayfası Oluşturuluyor ---")
    offline_html_content = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Çevrimdışı - B2B Portalı</title>
    <link rel="manifest" href="/static/manifest.json">
    <meta name="theme-color" content="#212529">
    <style>
        body { font-family: sans-serif; margin: 0; padding: 20px; text-align: center; background-color: #f8f9fa; color: #343a40;}
        .container { max-width: 600px; margin: 50px auto; padding: 30px; background-color: #fff; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);}
        h1 { color: #dc3545; }
        p { font-size: 1.1em; }
        a { color: #007bff; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1><img src="/static/images/Logo.png" alt="Logo" style="max-height: 50px; margin-bottom:15px;"><br>Çevrimdışısınız</h1>
        <p>İnternet bağlantınız yok gibi görünüyor veya istenen sayfa önbellekte bulunamadı.</p>
        <p>Lütfen internet bağlantınızı kontrol edin ve tekrar deneyin.</p>
        <p><a href="/">Ana Sayfaya Dönmeyi Dene</a></p>
    </div>
    <script>
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', () => {
                navigator.serviceWorker.register('/static/sw.js');
            });
        }
    </script>
</body>
</html>
"""
    offline_page_path = TEMPLATES_DIR / "offline.html" # HTML şablonu olarak templates altına
    # veya static altına da konabilir: offline_page_path = STATIC_DIR / "offline.html"
    # sw.js'deki caches.match('/static/offline.html') buna göre ayarlanmalı. Şimdilik templates'e koyalım.
    try:
        with open(offline_page_path, 'w', encoding='utf-8') as f:
            f.write(offline_html_content)
        print(f"✓ Offline HTML sayfası oluşturuldu: {offline_page_path.relative_to(BASE_DIR)}")
    except Exception as e:
        print(f"X HATA: Offline HTML sayfası oluşturulamadı ({offline_page_path}): {e}")


def main():
    print("🚀 B2B Offline Portal Kurulum Scripti Başlatılıyor...")
    print(f"   Çalışma Dizini: {BASE_DIR}\n")

    create_folders()
    setup_database()
    create_sample_json_data()
    create_placeholder_icons()
    create_offline_html_page()

    print("\n✅ Kurulum tamamlandı!")
    print("\n📋 Sonraki Adımlar:")
    print("1. `Offline/download_assets.py` script'ini çalıştırarak gerekli CSS/JS kütüphanelerini indirin.")
    print("   (python download_assets.py)")
    print("2. `b2b_web_app/templates/` içindeki HTML dosyalarını `Offline/templates/` klasörüne kopyalayın.")
    print("   Bu HTML'lerdeki CDN linklerini yerel `/static/...` yollarıyla güncelleyin ve PWA için manifest linki ekleyin.")
    print("3. `Offline/static/images/` klasörüne `icon-192.png` ve `icon-512.png` dosyalarını ekleyin.")
    print("4. Ana proje dizininde `admin_config.json` dosyasının olduğundan emin olun veya `create_admin.py` çalıştırın.")
    print("5. Uygulamayı başlatmak için `Offline` klasöründeyken terminale şunu yazın:")
    print("   uvicorn main:app --reload --host 0.0.0.0 --port 8001")
    print("\n🌐 Tarayıcıda `http://localhost:8001` adresine gidin.")

if __name__ == "__main__":
    main() 