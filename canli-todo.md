# B2B Web Uygulaması Canlıya Alma Yapılacaklar Listesi

## A. Hazırlık ve Güvenlik

-   [x] **Ortam Değişkenleri Yönetimi (`.env` dosyası):**
    -   [x] `python-dotenv` kütüphanesini `requirements.txt` dosyasına ekle.
    -   [x] (Önerilir: Proje için gerekli değişkenleri belgeleyen `env.example` dosyası oluşturun)
    -   [x] Proje ana dizinine `.gitignore` dosyasına `.env` satırını ekle.
    -   [x] `b2b_web_app/main.py` dosyasına `load_dotenv()` çağrısını ekle.
    -   [x] Yerel geliştirme için Windows ortam değişkenleri kullanıldı.
-   [ ] **Güçlü Gizli Anahtar ve API Anahtarı Belirleme:**
    -   [ ] Canlı sunucu için `FASTAPI_SECRET_KEY` üret (örneğin `openssl rand -hex 32` ile) ve güvenli bir yerde sakla (Render'da ortam değişkeni olarak ayarlanacak).
    -   [ ] Canlı sunucu için `PRODUCTS_API_KEY` belirle ve güvenli bir yerde sakla (Render'da ortam değişkeni olarak ayarlanacak).
-   [x] **`requirements.txt` Güncelleme:**
    -   [x] `requirements.txt` dosyasının güncel ve canlı ortam için gerekli tüm kütüphaneleri (fastapi, uvicorn[standard], python-dotenv, passlib[bcrypt], SQLAlchemy, alembic, jinja2, python-multipart vb.) içerdiğinden emin ol.

## B. Sunucu Kurulumu ve Veritabanı (Render.com PaaS ile)

-   [ ] **Canlı Sunucu Ortamı Hazırlığı (Render):**
    -   [x] Uygun bir sunucu seç (VPS, PaaS vb.). (Render PaaS seçildi)
    -   [ ] Render.com üzerinde bir hesap oluştur.
    -   [ ] Render'da yeni bir "Web Service" oluşturmaya başla.
-   [ ] **Proje Dosyalarını Sunucuya Aktarma (Render):**
    -   [ ] Projeyi bir Git sağlayıcısına (GitHub, GitLab, Bitbucket) yükle (eğer henüz değilse).
    -   [ ] Render'daki Web Service'i bu Git reposuna bağla.
-   [ ] **Bağımlılıkları Kurma (Render otomatik yapar):**
    -   [ ] Render, `requirements.txt` dosyasını otomatik olarak algılayıp bağımlılıkları kuracaktır. (Dağıtım sırasında kontrol edilecek)
-   [ ] **Ortam Değişkenlerini Sunucuda Ayarlama (Render Arayüzünden):**
    -   [ ] Render servis ayarlarında "Environment" bölümüne git.
    -   [ ] Canlı ortam için `FASTAPI_SECRET_KEY` değerini ekle.
    -   [ ] Canlı ortam için `PRODUCTS_API_KEY` değerini ekle.
    -   [ ] SQLite veritabanı dosyasının yolu için `DATABASE_PATH` (örn: `/mnt/data/b2b_app.sqlite3`) ortam değişkeni ekle.
    -   [ ] Admin config dosyasının yolu için `ADMIN_CONFIG_PATH` (örn: `/mnt/data/admin_config.json`) ortam değişkeni ekle.
    -   [ ] Ürünler JSON dosyasının yolu için `PRODUCTS_FILE_PATH` (örn: `/mnt/data/received_products.json`) ortam değişkeni ekle.
    -   [ ] Gerekirse diğer ortam değişkenlerini (örn: `PYTHON_VERSION=3.9` gibi) ekle.
-   [ ] **Kalıcı Depolama Ayarları (Render Disks):**
    -   [ ] Render servis ayarlarında "Disks" bölümüne git.
    -   [ ] `DATABASE_PATH`, `ADMIN_CONFIG_PATH` ve `PRODUCTS_FILE_PATH` için kullanılacak bir kalıcı disk oluştur (örn: Mount Path: `/mnt/data`, Size: 1GB).
-   [ ] **Kodda Dosya Yollarını Ortam Değişkenlerinden Okuma:**
    -   [ ] `b2b_web_app/database.py` içindeki `SQLALCHEMY_DATABASE_URL`'i `DATABASE_PATH` ortam değişkeninden okuyacak şekilde güncelle.
    -   [ ] `b2b_web_app/main.py` içindeki `ADMIN_CONFIG_FILE` yolunu `ADMIN_CONFIG_PATH` ortam değişkeninden okuyacak şekilde güncelle.
    -   [ ] `b2b_web_app/main.py` içindeki `PRODUCTS_FILE` yolunu `PRODUCTS_FILE_PATH` ortam değişkeninden okuyacak şekilde güncelle.
    -   [ ] `create_admin.py` script'inin `ADMIN_CONFIG_PATH` ortam değişkeninden `admin_config.json` yolunu okuyacak şekilde güncelle.
-   [ ] **Başlangıç Komutları (Render Build & Start Commands):**
    -   [ ] Render "Build Command": `pip install --upgrade pip && pip install -r requirements.txt && alembic upgrade head`
    -   [ ] Render "Start Command": `gunicorn -w 4 -k uvicorn.workers.UvicornWorker b2b_web_app.main:app --bind 0.0.0.0:$PORT`
-   [ ] **Admin Kullanıcısı Oluşturma (Canlıda - İlk Dağıtım Sonrası):**
    -   [ ] `create_admin.py` script'ini (ortam değişkenlerinden doğru yolu okuyacak şekilde güncellenmiş haliyle) Render'ın "Shell" özelliğini kullanarak ilk dağıtımdan sonra bir kerelik çalıştır.

## C. Uygulamayı Çalıştırma ve Erişilebilir Hale Getirme (Render ile)

-   [ ] **Uygulama Dağıtımı ve Test:**
    -   [ ] Render'da ilk dağıtımı (deploy) başlat.
    -   [ ] Dağıtım loglarını kontrol et (build hataları, Alembic hataları vb.).
    -   [ ] Uygulamanın `onrender.com` adresinden çalıştığını test et.
-   [ ] **HTTPS (Render Otomatik Sağlar):**
    -   [x] Render, varsayılan olarak `onrender.com` alt alan adıyla HTTPS sağlar. (Kontrol edilecek)
-   [ ] **Özel Alan Adı (Custom Domain - İsteğe Bağlı):**
    -   [ ] Kendi özel alan adını kullanmak istersen, Render arayüzünden ekleyip DNS ayarlarını yap.

## D. Son Kontroller ve Bakım

-   [ ] **Loglama ve Hata Takibi (Render Logları):**
    -   [ ] Render arayüzünden uygulama loglarını takip et.
-   [ ] **Güvenlik Duvarı (Render Yönetir):**
    -   [x] Render platformu gelen trafiği yönetir. (Temel güvenlik sağlanır)
-   [ ] **Mobil Paylaşım Testi (HTTPS Sonrası):**
    -   [ ] Uygulama HTTPS üzerinden çalışırken mobil cihazlarda dosya paylaşım özelliğini tekrar test et.
-   [ ] **Yedekleme Stratejisi (Kalıcı Disk):**
    -   [ ] Render'daki kalıcı diskin yedeklenmesi konusunu araştır veya manuel yedekleme yöntemleri düşün (örn: periyodik olarak dosyaları indirme).

--- 