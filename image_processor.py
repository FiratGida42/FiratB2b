import re
import os
import requests
from urllib.parse import urlparse

def clean_product_name(product_name: str) -> str:
    """
    Ürün adını arama motorları için temizler.
    Örnek: "TENEKE COCA COLA TENEKE ( 250 ML ) *24*" -> "TENEKE COCA COLA TENEKE ( 250 ML )"
    """
    if not product_name:
        return ""
    
    # Parantez içlerini ve parantezleri kaldır
    # name = re.sub(r'\s*\([^)]*\)\s*', '', product_name) # Bu satır kaldırılacak veya yorumlanacak
    name = product_name # Değişiklik: Başlangıçta ismi olduğu gibi al
    
    # Yıldız (*) ile başlayan kısımları kaldır (genellikle koli adedi)
    name = re.sub(r'\s*\*.*', '', name)
    
    # Çoklu boşlukları tek boşluğa indir ve baştaki/sondaki boşlukları kaldır
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def get_file_extension_from_url(url: str, response_headers: dict) -> str:
    """URL veya HTTP yanıt başlıklarından dosya uzantısını belirler."""
    # Önce URL'den dosya yolunu parse etmeyi dene
    parsed_url = urlparse(url)
    path = parsed_url.path
    if '.' in path:
        ext = path.split('.')[-1].lower()
        # Yaygın resim formatları
        if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']:
            return ext
    
    # URL'den çıkaramazsak Content-Type başlığına bak
    content_type = response_headers.get('Content-Type', '').lower()
    if 'image/jpeg' in content_type:
        return 'jpg'
    elif 'image/png' in content_type:
        return 'png'
    elif 'image/gif' in content_type:
        return 'gif'
    elif 'image/webp' in content_type:
        return 'webp'
    elif 'image/bmp' in content_type:
        return 'bmp'
    
    # Varsayılan olarak .jpg kullan
    return 'jpg'

def download_and_save_image(image_url: str | None, stok_kodu: str, save_dir: str = "b2b_web_app/static/images") -> str | None:
    """
    Verilen URL'den resmi indirir ve belirtilen klasöre stok kodu ile kaydeder.
    Eğer resim zaten mevcutsa, indirme yapmaz ve mevcut dosyanın yolunu döndürür.
    Başarılı olursa, kaydedilen/mevcut resmin web uygulaması için göreli yolunu döndürür.
    Örn: "images/product_ABC01.jpg"
    Eğer image_url None ise ve resim mevcut değilse None döner.
    """
    if not stok_kodu:
        print("Hata: Stok kodu belirtilmemiş.")
        return None

    # Stok kodunu dosya adı için güvenli hale getir
    safe_stok_kodu = re.sub(r'[^a-zA-Z0-9_.-]', '_', stok_kodu)
    base_filename_no_ext = f"product_{safe_stok_kodu}"
    
    # Web uygulaması için göreli yolun başlangıcı (örn: "images")
    relative_web_dir = os.path.basename(save_dir)

    # Öncelikle mevcut bir resim var mı diye kontrol et
    common_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']
    for ext in common_extensions:
        existing_filename = f"{base_filename_no_ext}.{ext}"
        full_existing_path = os.path.join(save_dir, existing_filename)
        if os.path.exists(full_existing_path):
            # print(f"Resim zaten mevcut: {full_existing_path}")
            return os.path.join(relative_web_dir, existing_filename).replace('\\', '/')

    # Resim mevcut değilse ve indirme URL'i verilmemişse, burada dur.
    if not image_url:
        # print(f"İndirilecek URL yok ve mevcut resim bulunamadı: {stok_kodu}")
        return None

    # Resim mevcut değil ve URL var, indirmeyi dene
    try:
        os.makedirs(save_dir, exist_ok=True) # Klasör yoksa oluştur
        
        # print(f"Resim indiriliyor: {image_url} -> {stok_kodu}")
        response = requests.get(image_url, stream=True, timeout=15) # Timeout süresi artırıldı
        response.raise_for_status() 

        extension_from_download = get_file_extension_from_url(image_url, response.headers)
        final_filename = f"{base_filename_no_ext}.{extension_from_download}"
        full_save_path = os.path.join(save_dir, final_filename)
        
        with open(full_save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # print(f"Resim başarıyla kaydedildi: {full_save_path}")
        return os.path.join(relative_web_dir, final_filename).replace('\\', '/')

    except requests.exceptions.Timeout:
        print(f"Hata: Resim indirilemedi (Timeout {image_url}).")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Hata: Resim indirilemedi ({image_url}). Sebep: {e}")
        return None
    except IOError as e:
        # full_save_path burada tanımlı olmayabilir eğer hata daha önce oluştuysa.
        # Bu yüzden genel bir mesaj verilebilir veya path'i try bloğunun başında tanımlamak gerekebilir.
        print(f"Hata: Resim dosyası yazılamadı. Sebep: {e}")
        return None
    except Exception as e:
        print(f"Resim indirme/kaydetme sırasında bilinmeyen bir hata oluştu: {e}")
        return None

if __name__ == '__main__':
    # Test için örnek kullanımlar
    test_name1 = "TENEKE COCA COLA TENEKE ( 250 ML ) *24*"
    cleaned_name1 = clean_product_name(test_name1)
    print(f"Orijinal: '{test_name1}' -> Temizlenmiş: '{cleaned_name1}'")

    # Test için save_dir oluşturalım
    test_save_dir = "test_image_downloads"
    # os.makedirs(test_save_dir, exist_ok=True) # download_and_save_image zaten oluşturuyor

    # 1. Var olmayan resmi indirme testi
    sample_url_1 = "https://via.placeholder.com/150/0000FF/808080?Text=YeniResim1"
    stok_kodu_1 = "TEST001_YENI"
    print(f"\nTest 1: {stok_kodu_1} için resim indirme...")
    saved_path_1 = download_and_save_image(sample_url_1, stok_kodu_1, save_dir=test_save_dir)
    if saved_path_1:
        print(f"İndirildi/Kaydedildi: {saved_path_1}")
        # Aynı resmi tekrar çağıralım, bu sefer indirmemeli
        print(f"Test 1.1: {stok_kodu_1} için tekrar çağrı (mevcut olmalı)...")
        saved_path_1_check = download_and_save_image(sample_url_1, stok_kodu_1, save_dir=test_save_dir)
        print(f"Mevcut dosya yolu: {saved_path_1_check}")
    else:
        print(f"Resim indirilemedi: {stok_kodu_1}")

    # 2. URL olmadan mevcut resmi kontrol etme (yukarıdaki resim artık var olmalı)
    print(f"\nTest 2: {stok_kodu_1} için URL olmadan kontrol (mevcut olmalı)...")
    existing_path_check = download_and_save_image(None, stok_kodu_1, save_dir=test_save_dir)
    if existing_path_check:
        print(f"Mevcut dosya bulundu: {existing_path_check}")
    else:
        print(f"Mevcut dosya bulunamadı: {stok_kodu_1}")

    # 3. URL olmadan var olmayan resmi kontrol etme
    stok_kodu_3 = "TEST003_YOK"
    print(f"\nTest 3: {stok_kodu_3} için URL olmadan kontrol (mevcut olmamalı)...")
    non_existing_path = download_and_save_image(None, stok_kodu_3, save_dir=test_save_dir)
    if non_existing_path:
        print(f"Hata! Olmayan dosya bulundu: {non_existing_path}")
    else:
        print(f"Mevcut olmayan dosya doğru şekilde bulunamadı: {stok_kodu_3}")

    # 4. Geçersiz URL ile indirme testi
    sample_url_invalid = "https://invalid-url-for-testing.com/image.jpg"
    stok_kodu_4 = "TEST004_INVALID_URL"
    print(f"\nTest 4: {stok_kodu_4} için geçersiz URL ile indirme...")
    saved_path_4 = download_and_save_image(sample_url_invalid, stok_kodu_4, save_dir=test_save_dir)
    if saved_path_4:
        print(f"Hata! Geçersiz URL'den resim indirildi: {saved_path_4}")
    else:
        print(f"Geçersiz URL'den resim doğru şekilde indirilemedi: {stok_kodu_4}")
        
    print("\nTestler tamamlandı. Lütfen 'test_image_downloads' klasörünü kontrol edin.") 