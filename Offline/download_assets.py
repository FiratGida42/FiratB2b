import os
import requests
from urllib.parse import urlparse
from pathlib import Path

# Hedef ana klasör (bu script'in bulunduğu dizin)
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
CSS_DIR = STATIC_DIR / "css"
JS_DIR = STATIC_DIR / "js"
FONTS_DIR = CSS_DIR / "fonts" # Bootstrap ikonları için
JSON_DATA_DIR = STATIC_DIR / "json_data" # DataTables TR dil dosyası için

# Klasörlerin varlığını kontrol et ve yoksa oluştur
os.makedirs(CSS_DIR, exist_ok=True)
os.makedirs(JS_DIR, exist_ok=True)
os.makedirs(FONTS_DIR, exist_ok=True)
os.makedirs(JSON_DATA_DIR, exist_ok=True)

# İndirilecek Kütüphaneler
assets = {
    "css": [
        "https://bootswatch.com/5/yeti/bootstrap.min.css",
        "https://cdnjs.cloudflare.com/ajax/libs/select2/4.0.13/css/select2.min.css",
        "https://cdnjs.cloudflare.com/ajax/libs/select2-bootstrap-5-theme/1.3.0/select2-bootstrap-5-theme.min.css",
        "https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css",
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css", # Font dosyaları için önemli notu unutma
        "https://cdnjs.cloudflare.com/ajax/libs/lightgallery/2.7.1/css/lightgallery.min.css",
        "https://cdnjs.cloudflare.com/ajax/libs/lightgallery/2.7.1/css/lg-zoom.min.css",
    ],
    "js": [
        "https://cdnjs.cloudflare.com/ajax/libs/jquery/3.7.1/jquery.min.js", # jQuery 3.7.0 veya 3.7.1
        "https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js", # Bootstrap 5.3.0, 5.3.1 veya 5.3.2
        "https://cdnjs.cloudflare.com/ajax/libs/select2/4.0.13/js/select2.full.min.js",
        "https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js",
        "https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js",
        "https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.5.28/jspdf.plugin.autotable.min.js", # veya daha güncel bir sürüm
        "https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js",
        "https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js",
        "https://cdnjs.cloudflare.com/ajax/libs/lightgallery/2.7.1/lightgallery.min.js",
        "https://cdnjs.cloudflare.com/ajax/libs/lightgallery/2.7.1/plugins/zoom/lg-zoom.min.js",
    ],
    "json": [ # DataTables Türkçe dil dosyası
        {"url": "https://cdn.datatables.net/plug-ins/1.13.6/i18n/tr.json", "path": JSON_DATA_DIR / "tr.json"}
    ],
    "fonts": [ # Bootstrap icon font dosyaları
        {"url": "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/fonts/bootstrap-icons.woff", "path": FONTS_DIR / "bootstrap-icons.woff"},
        {"url": "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/fonts/bootstrap-icons.woff2", "path": FONTS_DIR / "bootstrap-icons.woff2"},
    ]
}

def download_file(url, destination_path):
    try:
        print(f"İndirme deneniyor: {url} -> {destination_path.relative_to(BASE_DIR)}")
        response = requests.get(url, stream=True)
        response.raise_for_status()  # HTTP hataları için
        with open(destination_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"✓ Başarıyla indirildi ve kaydedildi: {destination_path.relative_to(BASE_DIR)}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"X Hata oluştu ({url}): {e}")
        return False

print("download_assets.py script'i başlatılıyor...")
print("Gerekli CSS/JS Kütüphaneleri İndiriliyor...")
print(f"Çalışma Dizini: {BASE_DIR}")
print(f"Hedef Statik Klasör: {STATIC_DIR.relative_to(BASE_DIR)}")

download_count = 0

print("\n--- CSS Dosyaları İndiriliyor ---")
for url in assets["css"]:
    file_name = os.path.basename(urlparse(url).path)
    if download_file(url, CSS_DIR / file_name):
        download_count +=1

print("\n--- JS Dosyaları İndiriliyor ---")
for url in assets["js"]:
    file_name = os.path.basename(urlparse(url).path)
    if download_file(url, JS_DIR / file_name):
        download_count +=1

print("\n--- JSON Veri Dosyaları İndiriliyor ---")
for item in assets["json"]:
    if download_file(item["url"], item["path"]):
        download_count += 1

print("\n--- Font Dosyaları İndiriliyor (Bootstrap Icons) ---")
for item in assets["fonts"]:
    if download_file(item["url"], item["path"]):
        download_count +=1

print("\n--- İndirme İşlemi Tamamlandı ---")
print(f"Başarıyla İndirilen Dosya Sayısı: {download_count}")
if (len(assets["css"]) + len(assets["js"]) + len(assets["json"]) + len(assets["fonts"])) == download_count:
    print("Tüm dosyalar başarıyla indirildi!")
else:
    print(f"Bazı dosyalar indirilemedi. Lütfen yukarıdaki hataları kontrol edin. Toplam {len(assets['css']) + len(assets['js']) + len(assets['json']) + len(assets['fonts'])} dosyadan {download_count} tanesi indirildi.")

print("\nℹ️  ÖNEMLİ NOT (Bootstrap Icons CSS):")
print("Eğer `bootstrap-icons.css` dosyasını manuel olarak düzenlediyseniz veya")
print("font dosyalarının yolu CSS içinde göreceli (`../fonts/bootstrap-icons.woff2`) ise,")
print(f"`Offline/static/css/fonts/` klasörüne indirdiğimiz fontlar doğru çalışacaktır.")
print("Eğer CSS dosyası fontları farklı bir yoldan (örn: CDN) bekliyorsa, CSS'i de düzenlemeniz gerekebilir.")
print("Mevcut script fontları `static/css/fonts/` altına indirmiştir.")
