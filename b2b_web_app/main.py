from fastapi import FastAPI, HTTPException, Request, Depends, status, Form, Header, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from typing import List, Dict, Optional, Any
import json
import os
import datetime # datetime importu eklendi
import secrets # Güçlü anahtar üretimi için eklendi
import shutil # Dosya işlemleri için eklendi
from passlib.context import CryptContext
from sqlalchemy.orm import Session # SQLAlchemy Session importu eklendi
from pydantic import BaseModel, field_validator # Pydantic BaseModel importu eklendi, field_validator eklendi
from dotenv import load_dotenv # EKLENDİ

# .env dosyasındaki değişkenleri yükle (uygulama başlamadan önce)
load_dotenv() # EKLENDİ

# Veritabanı ve model importları
from . import models # models.py dosyamızı import ediyoruz
from .database import engine, SessionLocal, get_db # database.py'den engine, SessionLocal ve get_db'yi import ediyoruz

# Uygulama başlangıcında veritabanı tablolarını oluştur (eğer yoksa)
# models.Base.metadata.create_all(bind=engine) # ALEMBIC KULLANILDIĞI İÇİN BU SATIR YORUMA ALINDI

# --- Pydantic Şemaları (Schemas) Başlangıcı ---
class OrderItemBase(BaseModel):
    product_code: str
    product_name: str # Frontend'den bu bilgi de gelecek
    barcode: Optional[str] = None # Barkod alanı eklendi
    quantity: int
    unit_price: float

class OrderItemCreate(OrderItemBase):
    pass

class OrderItemResponse(OrderItemBase):
    id: int
    order_id: int
    # barcode alanı OrderItemBase'den miras alınacak

    class Config:
        from_attributes = True # Pydantic V2 için orm_mode yerine

class OrderBase(BaseModel):
    customer_name: str # Optional kaldırıldı, artık zorunlu

    @field_validator('customer_name', mode='before')
    @classmethod
    def set_customer_name_if_none(cls, value):
        if value is None:
            return "Bilinmeyen Cari" # None ise varsayılan bir değer ata
        if isinstance(value, str) and not value.strip(): # Ek kontrol: Boş string veya sadece boşluklardan oluşuyorsa
            return "Bilinmeyen Cari" # Onu da varsayılan değere ata
        return value

class OrderCreate(OrderBase):
    items: List[OrderItemCreate]

    # OrderCreate için de customer_name'in boş olmamasını sağlayalım
    @field_validator('customer_name', mode='before') # 'before' ile ham değeri al
    @classmethod
    def customer_name_must_not_be_empty_for_create(cls, value):
        if not value or (isinstance(value, str) and not value.strip()):
            raise ValueError('Cari adı boş olamaz veya sadece boşluk içeremez.')
        return value

class OrderResponse(OrderBase):
    id: int
    created_at: datetime.datetime
    total_amount: float
    status: models.PyOrderStatusEnum # models.OrderStatusEnum yerine models.PyOrderStatusEnum
    items: List[OrderItemResponse] = []

    class Config:
        from_attributes = True # Pydantic V2 için orm_mode yerine
        # arbitrary_types_allowed = True # Artık gerekmeyebilir

class OrderStatusUpdate(BaseModel):
    status: models.PyOrderStatusEnum # models.OrderStatusEnum yerine models.PyOrderStatusEnum
# --- Pydantic Şemaları (Schemas) Sonu ---

# Templates ve Static dizinlerinin yollarını belirle
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
# ADMIN_CONFIG_FILE yolunu ortam değişkeninden al, yoksa varsayılanı kullan
ADMIN_CONFIG_FILE = os.getenv("ADMIN_CONFIG_PATH", os.path.join(os.path.dirname(BASE_DIR), "admin_config.json"))
DISCOUNT_MATERIALS_DIR = os.path.join(STATIC_DIR, "discount_materials") # İndirim materyalleri için dizin

# --- API Anahtarı Ayarı (Ortam Değişkeninden Oku) ---
PRODUCTS_API_KEY_VALUE = os.environ.get("PRODUCTS_API_KEY")
if not PRODUCTS_API_KEY_VALUE:
    print("UYARI: okPRODUCTS_API_KEY ortam değişkeni bulunamadı.")
    print("Güvenlik için /api/products POST endpoint'i için bu değişkenin ayarlanması ŞİDDETLE tavsiye edilir.")
    print("Geçici, geliştirme amaçlı bir anahtar kullanılacak. Lütfen üretimde bunu KULLANMAYIN ve değiştirin!")
    PRODUCTS_API_KEY_VALUE = "dev-temporary-products-api-key-replace-me"
    print(f"Geliştirme için oluşturulan geçici PRODUCTS_API_KEY: {PRODUCTS_API_KEY_VALUE}")

# --- Müşteri Senkronizasyonu API Anahtarı Ayarı (Ortam Değişkeninden Oku) ---
CUSTOMER_SYNC_API_KEY_VALUE = os.environ.get("SERVER_API_KEY") # SERVER_API_KEY ortam değişkenini kullanıyoruz
if not CUSTOMER_SYNC_API_KEY_VALUE:
    print("UYARI: SERVER_API_KEY (müşteri senkronizasyonu için) ortam değişkeni bulunamadı.")
    print("Güvenlik için /api/update-customer-balances POST endpoint'i için bu değişkenin ayarlanması ŞİDDETLE tavsiye edilir.")
    print("Geçici, geliştirme amaçlı bir anahtar kullanılacak. Lütfen üretimde bunu KULLANMAYIN ve değiştirin!")
    CUSTOMER_SYNC_API_KEY_VALUE = "dev-temporary-customer-sync-api-key-replace-me" # Farklı bir fallback
    print(f"Geliştirme için oluşturulan geçici CUSTOMER_SYNC_API_KEY: {CUSTOMER_SYNC_API_KEY_VALUE}")

app = FastAPI(title="B2B Ürün Servisi", version="0.1.0")

# --- Para Formatlama için Jinja2 Filtresi ---
def format_currency_tr(value):
    try:
        val = float(value)
        # Bilimsel gösterimi (0E-8 gibi) 0.0 olarak ele al
        if abs(val) < 1e-7: 
            val = 0.0
        # Sayıyı formatla: binlik ayırıcı nokta, ondalık ayırıcı virgül, 2 ondalık basamak
        return f"{val:,.2f} ₺".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return value # Hata durumunda orijinal değeri döndür

# --- SECRET_KEY Ayarı (Ortam Değişkeninden Oku) ---
SECRET_KEY = os.environ.get("FASTAPI_SECRET_KEY")
if not SECRET_KEY:
    print("UYARI: FASTAPI_SECRET_KEY ortam değişkeni bulunamadı.")
    print("Güvenlik için üretim ortamında bu değişkenin ayarlanması ŞİDDETLE tavsiye edilir.")
    print("Geçici, geliştirme amaçlı bir anahtar kullanılacak. Lütfen üretimde bunu KULLANMAYIN!")
    SECRET_KEY = secrets.token_hex(32) # Geliştirme için rastgele bir anahtar
    print(f"Geliştirme için oluşturulan geçici SECRET_KEY: {SECRET_KEY}")
    print("Bu anahtarı ortam değişkeni olarak ayarlayabilirsiniz (örnek Linux/Mac için): export FASTAPI_SECRET_KEY='''" + SECRET_KEY + "'''")

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Static dosyaları sunmak için app.mount kullanılır
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Jinja2Templates örneğini oluştur
templates = Jinja2Templates(directory=TEMPLATES_DIR)
# Filtreyi Jinja2 ortamına ekle
templates.env.filters['currency_tr'] = format_currency_tr

# Gelen ürün verilerini saklamak için dosya yolunu ortam değişkeninden al, yoksa varsayılanı kullan
PRODUCTS_FILE = os.getenv("PRODUCTS_FILE_PATH", "received_products.json")

# --- Admin Auth Başlangıcı ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    # Bcrypt versiyon hatası almamak için try-except bloğu eklenebilir,
    # ama create_admin.py'de çalıştıysa burada da çalışması beklenir.
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        print(f"Şifre doğrulanırken hata (verify_password): {e}") # Üretimde loglanmalı
        return False

def get_admin_credentials() -> Optional[dict]:
    """
    Admin kimlik bilgilerini admin_config.json dosyasından okur.
    Başarılı olursa bir sözlük, hata durumunda None döndürür.
    """
    if not os.path.exists(ADMIN_CONFIG_FILE):
        # Eğer ADMIN_CONFIG_FILE ortam değişkeninden geliyorsa ve dosya yoksa, 
        # bu, create_admin.py'nin henüz çalıştırılmadığı anlamına gelebilir.
        # Veya yol yanlışsa. Yolun doğruluğu create_admin.py ve ortam değişkeni ayarıyla sağlanmalı.
        print(f"UYARI: Admin yapılandırma dosyası ({ADMIN_CONFIG_FILE}) bulunamadı. Admin girişi çalışmayacak.")
        print("Lütfen `create_admin.py` script'ini çalıştırarak bir admin kullanıcısı oluşturun.")
        return None
    try:
        with open(ADMIN_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Beklenen anahtarların varlığını kontrol edebiliriz
            if "admin_username" in data and "admin_hashed_password" in data: # Anahtar isimlerini admin_config.json'daki ile eşleştir
                return data
            else:
                print(f"HATA: Admin yapılandırma dosyasında beklenen anahtarlar ('admin_username', 'admin_hashed_password') eksik: {ADMIN_CONFIG_FILE}")
                return None
    except json.JSONDecodeError:
        print(f"HATA: Admin yapılandırma dosyası bozuk (JSON Decode Hatası): {ADMIN_CONFIG_FILE}")
        return None
    except Exception as e:
        print(f"Admin config dosyası okunurken genel hata: {e}")
        return None

async def get_current_admin_user_with_redirect(request: Request):
    """
    Session'da admin kullanıcısı yoksa /login'e yönlendirir, varsa kullanıcı adını döndürür.
    """
    admin_user = request.session.get("admin_user")
    if not admin_user:
        # Giriş yapılmamışsa login sayfasına yönlendir.
        # İsteğin geldiği URL'yi 'next' parametresi olarak ekleyebiliriz,
        # böylece başarılı girişten sonra kullanıcı aynı sayfaya dönebilir.
        # current_path = request.url.path
        # if current_path != "/login": # Sonsuz döngüyü engellemek için
        #     return RedirectResponse(url=f"/login?next={current_path}", status_code=status.HTTP_303_SEE_OTHER)
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return admin_user

async def get_current_admin_user_for_api(request: Request):
    """
    Session'da admin kullanıcısı yoksa HTTPException fırlatır, varsa kullanıcı adını döndürür.
    API endpoint'leri için kullanılır.
    """
    admin_user = request.session.get("admin_user")
    if not admin_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return admin_user

# --- API Anahtarı Doğrulama Dependency'si ---
async def verify_api_key(x_api_key: str = Header(None)):
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API Key header missing")
    if x_api_key != PRODUCTS_API_KEY_VALUE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API Key")
    return True

# --- Müşteri Senkronizasyonu API Anahtarı Doğrulama Dependency'si ---
async def verify_customer_sync_api_key(x_api_key: str = Header(None)):
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API Key header missing")
    if x_api_key != CUSTOMER_SYNC_API_KEY_VALUE: # CUSTOMER_SYNC_API_KEY_VALUE kullanılıyor
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API Key for Customer Sync") # Hata mesajını özelleştirebiliriz
    return True

# --- Admin Auth Sonu ---

@app.post("/api/products", dependencies=[Depends(verify_api_key)])
async def receive_products_api(products: List[Dict]):
    """
    Yeni ürün verilerini alır ve sunucu tarafında bir JSON dosyasına kaydeder.
    Masaüstü uygulamasından gelen ürün listesini kabul eder.
    """
    products_file_path = os.getenv("PRODUCTS_FILE_PATH", "received_products.json") # Tekrar alıyoruz çünkü global PRODUCTS_FILE değişmeyebilir
    if not products:
        raise HTTPException(status_code=400, detail="Ürün listesi boş olamaz.")
    try:
        # Gelen veriyi doğrudan JSON dosyasına yazalım (var olanın üzerine yazar)
        with open(products_file_path, "w", encoding="utf-8") as f: # products_file_path kullan
            json.dump(products, f, ensure_ascii=False, indent=4)
        print(f"{len(products)} adet ürün verisi alındı ve {products_file_path} dosyasına kaydedildi.") # products_file_path kullan
        return {"message": f"{len(products)} adet ürün başarıyla alındı ve kaydedildi."}
    except Exception as e:
        print(f"Veri kaydedilirken hata oluştu: {e}")
        raise HTTPException(status_code=500, detail=f"Ürünler kaydedilemedi: {str(e)}")

@app.get("/api/products")
async def get_products_api(current_user: str = Depends(get_current_admin_user_for_api)):
    """
    Kaydedilmiş ürün verilerini sunar. Giriş yapmış admin kullanıcısı gerektirir.
    """
    products_file_path = os.getenv("PRODUCTS_FILE_PATH", "received_products.json") # Tekrar alıyoruz
    try:
        with open(products_file_path, "r", encoding="utf-8") as f: # products_file_path kullan
            products = json.load(f)
        return products
    except FileNotFoundError:
        print(f"'{products_file_path}' bulunamadı. Boş ürün listesi döndürülüyor.") # products_file_path kullan
        return []
    except Exception as e:
        print(f"Veri okunurken hata oluştu: {e}")
        raise HTTPException(status_code=500, detail=f"Ürünler okunamadı: {str(e)}")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    admin_user = request.session.get("admin_user")
    if not admin_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    
    # Kullanıcı giriş yapmışsa, şablonu render et
    # products.html şablonunu render et ve request nesnesini context içinde gönder.
    # Şablon içinde /api/products endpoint'inden veri çekilecek (JavaScript ile).
    return templates.TemplateResponse("products.html", {
        "request": request, 
        "title": "Ürün Kataloğu",
        "admin_user": admin_user
    })

@app.get("/customer-balances", response_class=HTMLResponse)
async def view_customer_balances(request: Request, current_user: str = Depends(get_current_admin_user_with_redirect)):
    customers_data = []
    available_customers_file_path = os.path.join(STATIC_DIR, "json_data", "filtrelenen_cariler.json")

    try:
        if os.path.exists(available_customers_file_path):
            with open(available_customers_file_path, "r", encoding="utf-8") as f:
                customers_data = json.load(f)
            
            # Bakiye parsing ve sıralama için yardımcı fonksiyon
            def parse_bakiye_for_sort(bakiye_str):
                try:
                    # "0E-8" gibi bilimsel gösterimleri float olarak doğru parse eder
                    return float(bakiye_str)
                except (ValueError, TypeError):
                    return 0.0 # Hata durumunda veya null ise 0 kabul et

            # NET_BAKIYE'ye göre büyükten küçüğe sırala
            customers_data.sort(key=lambda x: parse_bakiye_for_sort(x.get("NET_BAKIYE", "0")), reverse=True)

        else:
            print(f"UYARI: Cari bakiye dosyası bulunamadı: {available_customers_file_path}")
    except Exception as e:
        print(f"HATA: Cari bakiye dosyası okunurken hata: {e}")
        # Hata durumunda boş liste ile devam et, template hatayı uygun şekilde göstermeli

    return templates.TemplateResponse("customer_balances.html", {
        "request": request,
        "title": "Cari Bakiyeler",
        "admin_user": current_user, # admin_user yerine current_user (dependency'den gelen)
        "customers": customers_data
    })

@app.get("/cart", response_class=HTMLResponse)
async def view_cart(request: Request):
    admin_user = request.session.get("admin_user")
    if not admin_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    # cart.html şablonunu render et ve request nesnesini context içinde gönder.
    return templates.TemplateResponse("cart.html", {
        "request": request, 
        "title": "Sepetim",
        "admin_user": admin_user
    })

@app.get("/orders", response_class=HTMLResponse)
async def view_orders(request: Request):
    admin_user = request.session.get("admin_user")
    if not admin_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    
    return templates.TemplateResponse("orders.html", {
        "request": request, 
        "title": "Siparişlerim",
        "admin_user": admin_user
    })

@app.get("/login", response_class=HTMLResponse, tags=["Admin"])
async def login_form(request: Request):
    if request.session.get("admin_user"):
        return RedirectResponse(url="/admin/me", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login", tags=["Admin"])
async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    admin_creds_dict = get_admin_credentials()
    error_message = "Kullanıcı adı veya şifre hatalı."

    if admin_creds_dict:
        stored_username = admin_creds_dict.get("admin_username")
        hashed_password = admin_creds_dict.get("admin_hashed_password")
        if stored_username == username and hashed_password and verify_password(password, hashed_password):
            request.session["admin_user"] = username
            # Başarılı giriş sonrası / (ana sayfaya) yönlendir
            # next_url = request.query_params.get("next", "/") # Eğer next parametresi varsa oraya yönlendir
            return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    # Başarısız giriş, login formunu hata mesajıyla tekrar göster
    return templates.TemplateResponse("login.html", {"request": request, "error_message": error_message}, status_code=status.HTTP_401_UNAUTHORIZED)

@app.get("/logout", tags=["Admin"])
async def logout(request: Request):
    request.session.pop("admin_user", None)
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/admin/me", response_class=HTMLResponse, tags=["Admin"])
async def read_admin_me_protected(request: Request, current_user: str = Depends(get_current_admin_user_with_redirect)):
    """
    Kimliği doğrulanmış mevcut admin kullanıcısının admin paneli sayfasını gösterir.
    Giriş yapılmamışsa /login'e yönlendirir.
    """
    return templates.TemplateResponse("admin_me.html", {"request": request, "username": current_user})

@app.on_event("startup")
async def startup_event():
    if not os.path.exists(ADMIN_CONFIG_FILE):
        print(f"UYARI: '{ADMIN_CONFIG_FILE}' bulunamadı. Admin girişi çalışmayacak.")
        print("Lütfen ana dizindeki 'create_admin.py' script'ini çalıştırarak bir admin kullanıcısı oluşturun.")
    else:
        admin_check = get_admin_credentials()
        if admin_check:
            print(f"'{ADMIN_CONFIG_FILE}' bulundu ve geçerli. Admin: {admin_check.get('admin_username')}")
        else:
            print(f"UYARI: '{ADMIN_CONFIG_FILE}' bulundu ancak okunamadı veya formatı bozuk.")

    # Masaüstü uygulamasından gelen verilerin saklandığı dosya için kontrol
    if not os.path.exists(PRODUCTS_FILE):
        print(f"Bilgi: Web arayüzü için başlangıç ürün verisi ('{PRODUCTS_FILE}') bulunamadı.")
        print(f"Masaüstü uygulaması veri gönderdiğinde ('/api/products' POST) bu dosya oluşturulacaktır.")
    else:
        print(f"Mevcut ürün veri dosyası: '{PRODUCTS_FILE}' bulundu.")

# --- Sipariş API Uç Noktaları Başlangıcı ---

@app.post("/api/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED, tags=["Orders"])
async def create_order(
    order_data: OrderCreate, 
    db: Session = Depends(get_db), 
    current_user: str = Depends(get_current_admin_user_for_api) # Admin koruması
):
    """
    Yeni bir sipariş oluşturur.

    - **customer_name**: Siparişi veren cari/firma adı (opsiyonel).
    - **items**: Sipariş kalemlerinin listesi.
        - **product_code**: Ürün stok kodu.
        - **product_name**: Ürün adı.
        - **quantity**: Miktar.
        - **unit_price**: Birim fiyat.
    """
    if not order_data.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sipariş kalemleri boş olamaz.")

    db_order = models.Order(
        customer_name=order_data.customer_name,
        status=models.PyOrderStatusEnum.PENDING # Yeni sipariş için durum
        # total_amount daha sonra hesaplanacak
    )
    
    calculated_total_amount = 0.0
    order_items_to_create = []

    # Ürünlerin barkodlarını almak için product_file_path'ı kullan
    # Bu, her sipariş oluşturmada dosyayı okuyacaktır, büyük veri setlerinde optimize edilebilir (örn. başlangıçta yükle)
    products_data_for_barcode = []
    products_file_path = os.getenv("PRODUCTS_FILE_PATH", "received_products.json")
    if os.path.exists(products_file_path):
        try:
            with open(products_file_path, "r", encoding="utf-8") as f_products:
                products_data_for_barcode = json.load(f_products)
        except Exception as e_read_products:
            print(f"Barkodları almak için ürünler dosyası ({products_file_path}) okunurken hata: {e_read_products}")
            # Hata durumunda barkodlar boş kalır ama sipariş oluşturmaya devam eder

    for item_data in order_data.items:
        if item_data.quantity <= 0 or item_data.unit_price < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Geçersiz miktar veya fiyat: {item_data.product_code}"
            )
        
        item_total = item_data.quantity * item_data.unit_price
        calculated_total_amount += item_total
        
        # Ürünün barkodunu bul
        found_barcode = None
        if products_data_for_barcode:
            product_in_file = next((p for p in products_data_for_barcode if p.get("STOK_KODU") == item_data.product_code), None)
            if product_in_file:
                found_barcode = product_in_file.get("BARKOD1") # received_products.json'daki barkod alanı adı

        db_order_item = models.OrderItem(
            product_code=item_data.product_code,
            product_name=item_data.product_name,
            barcode=found_barcode, # Bulunan barkodu ata
            quantity=item_data.quantity,
            unit_price=item_data.unit_price
            # order_id ataması, db_order veritabanına eklendikten sonra
            # veya db_order.items.append() ile otomatik olarak yapılır.
        )
        order_items_to_create.append(db_order_item)

    db_order.total_amount = calculated_total_amount
    db_order.items.extend(order_items_to_create) # İlişkiyi kurar ve order_id'leri ayarlar

    try:
        db.add(db_order)
        db.commit()
        db.refresh(db_order) # db_order'ı ve ilişkili items'ları ID'ler ve diğer DB tarafından üretilen değerlerle günceller
        return db_order
    except Exception as e:
        db.rollback()
        # Gerçek bir uygulamada burada daha detaylı loglama ve hata yönetimi yapılmalı
        print(f"Sipariş oluşturulurken veritabanı hatası: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Sipariş oluşturulamadı.")

@app.get("/api/orders", response_model=List[OrderResponse], tags=["Orders"])
async def list_orders(
    skip: int = 0, # Sayfalama için başlangıç noktası
    limit: int = 100, # Sayfalama için kayıt sayısı
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_admin_user_for_api) # Admin koruması
):
    """
    Sistemdeki tüm siparişleri listeler (sayfalamalı).
    Admin yetkisi gerektirir.
    """
    orders = db.query(models.Order).order_by(models.Order.created_at.desc()).offset(skip).limit(limit).all()
    return orders

@app.get("/api/orders/{order_id}", response_model=OrderResponse, tags=["Orders"])
async def get_order_details(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_admin_user_for_api) # Admin koruması
):
    """
    Belirli bir siparişin detaylarını getirir.
    Admin yetkisi gerektirir.
    """
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if db_order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sipariş bulunamadı.")
    return db_order

@app.put("/api/orders/{order_id}/status", response_model=OrderResponse, tags=["Orders"])
async def update_order_status(
    order_id: int,
    status_update: OrderStatusUpdate, # Yeni durumu Pydantic modeli ile al
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_admin_user_for_api) # Admin koruması
):
    """
    Belirli bir siparişin durumunu günceller (örn: 'Yeni Sipariş' -> 'Hazırlanıyor').
    Admin yetkisi gerektirir.
    """
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if db_order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sipariş bulunamadı.")
    
    # Gelen string değeri OrderStatusEnum üyesine çevirmeye gerek yok, Pydantic zaten yapıyor.
    # Ancak, eğer Pydantic modeli kullanmasaydık, gelen string'i enum'a çevirmemiz gerekirdi:
    # try:
    #     new_status_enum = models.PyOrderStatusEnum(status_update.status) # PyOrderStatusEnum olarak güncellendi
    # except ValueError:
    #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Geçersiz sipariş durumu: {status_update.status}")

    db_order.status = status_update.status # Pydantic modeli sayesinde bu zaten enum tipinde olmalı
    
    try:
        db.commit()
        db.refresh(db_order)
        return db_order
    except Exception as e:
        db.rollback()
        print(f"Sipariş durumu güncellenirken veritabanı hatası (ID: {order_id}): {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Sipariş durumu güncellenemedi.")

# --- Sipariş API Uç Noktaları Sonu ---

# --- Yeni API Endpoint'i: Cari Bakiyelerini Güncelleme ---
@app.post("/api/update-customer-balances", dependencies=[Depends(verify_customer_sync_api_key)])
async def update_customer_balances_api(customer_balances: List[Dict]):
    """
    Yeni cari bakiye verilerini alır ve sunucu tarafında filtrelenen_cariler.json dosyasına kaydeder.
    Yerel `background_scheduler_cariler.pyw` script'inden gelen cari listesini kabul eder.
    """
    # STATIC_DIR global olarak tanımlı, dosya yolunu bununla oluşturacağız
    # b2b_web_app/static/json_data/filtrelenen_cariler.json
    target_file_name = "filtrelenen_cariler.json"
    target_dir = os.path.join(STATIC_DIR, "json_data")
    customer_balances_file_path = os.path.join(target_dir, target_file_name)

    if not customer_balances: # Gelen liste boş olabilir, bu bir hata değil, boş dosya oluştururuz.
        print("Bilgi: Boş cari bakiye listesi alındı. Mevcut dosya (varsa) silinip boş dosya oluşturulacak.")
        # pass # Ya da bir şey yapmayabiliriz, isteğe bağlı

    try:
        # Hedef dizinin var olduğundan emin ol (Render'da ilk dağıtımda olmayabilir)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            print(f"Hedef dizin ({target_dir}) oluşturuldu.")

        # Gelen veriyi doğrudan JSON dosyasına yazalım (var olanın üzerine yazar)
        with open(customer_balances_file_path, "w", encoding="utf-8") as f:
            json.dump(customer_balances, f, ensure_ascii=False, indent=4)
        print(f"{len(customer_balances)} adet cari bakiye verisi alındı ve {customer_balances_file_path} dosyasına kaydedildi.")
        return {"message": f"{len(customer_balances)} adet cari bakiye başarıyla alındı ve kaydedildi."}
    except Exception as e:
        print(f"Cari bakiye verileri kaydedilirken hata oluştu: {e}")
        # Yerel script'e daha detaylı hata bilgisi vermek için hata mesajını döndürebiliriz.
        raise HTTPException(status_code=500, detail=f"Cari bakiyeleri kaydedilemedi: {str(e)}")

def ensure_discount_materials_dir():
    """İndirim materyalleri dizininin var olduğundan emin olur, yoksa oluşturur."""
    if not os.path.exists(DISCOUNT_MATERIALS_DIR):
        os.makedirs(DISCOUNT_MATERIALS_DIR)
        print(f"Dizin oluşturuldu: {DISCOUNT_MATERIALS_DIR}")

@app.get("/discounts", response_class=HTMLResponse, tags=["Discounts"])
async def view_discounts(request: Request, current_user: str = Depends(get_current_admin_user_with_redirect)):
    ensure_discount_materials_dir()
    materials = []
    try:
        for filename in os.listdir(DISCOUNT_MATERIALS_DIR):
            if os.path.isfile(os.path.join(DISCOUNT_MATERIALS_DIR, filename)):
                materials.append({
                    "name": filename,
                    "url": f"/static/discount_materials/{filename}"
                })
    except Exception as e:
        print(f"İndirim materyalleri listelenirken hata: {e}")
        # Hata durumunda boş liste ile devam et

    # Butonun gösterilip gösterilmeyeceğini belirlemek için resim dosyalarını filtrele
    image_materials_for_button = []
    allowed_image_extensions = (".jpg", ".jpeg", ".png", ".gif")
    for material in materials:
        if material['name'].lower().endswith(allowed_image_extensions):
            image_materials_for_button.append(material)
    
    return templates.TemplateResponse("discounts.html", {
        "request": request,
        "title": "İndirim Materyalleri",
        "admin_user": current_user,
        "materials": sorted(materials, key=lambda x: x['name']), # Ada göre sırala
        "image_materials_for_button": image_materials_for_button # Filtrelenmiş resim listesini şablona gönder
    })

@app.post("/upload-discount-material", tags=["Discounts"])
async def upload_discount_material(
    request: Request, 
    file: UploadFile = File(...), 
    current_user: str = Depends(get_current_admin_user_for_api) # API olduğu için _for_api kullandık
):
    ensure_discount_materials_dir()
    
    allowed_content_types = ["image/jpeg", "image/png", "image/gif", "application/pdf"]
    if file.content_type not in allowed_content_types:
        # Bu hatayı kullanıcıya göstermek için normalde bir mesaj sistemi (örn: flash messages) kullanılır.
        # Şimdilik basit bir HTTPException veya loglama yapabiliriz.
        # Ya da template'e bir hata mesajı parametresi ekleyip yönlendirebiliriz.
        # Basitlik adına şimdilik loglayıp devam edelim, idealde kullanıcıya bilgi verilmeli.
        print(f"UYARI: Geçersiz dosya türü yüklendi: {file.filename} ({file.content_type})")
        # raise HTTPException(status_code=400, detail=f"Geçersiz dosya türü. İzin verilenler: {', '.join(allowed_content_types)}")

    # Güvenlik için dosya adını temizle (isteğe bağlı ama önerilir)
    # filename = secrets.token_hex(8) + "_" + file.filename.replace(" ", "_") # Daha güvenli bir adlandırma
    filename = file.filename.replace(" ", "_") # Basitçe boşlukları değiştir
    file_path = os.path.join(DISCOUNT_MATERIALS_DIR, filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"Dosya başarıyla yüklendi: {file_path}")
    except Exception as e:
        print(f"Dosya kaydedilirken hata oluştu ({file_path}): {e}")
        # Hata durumunda kullanıcıya bilgi verilmeli.
        # raise HTTPException(status_code=500, detail="Dosya yüklenirken bir sorun oluştu.")
    finally:
        file.file.close()
        
    return RedirectResponse(url="/discounts", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/view-pdf/{pdf_name}", response_class=HTMLResponse, tags=["Discounts"])
async def view_pdf_page(
    request: Request, 
    pdf_name: str, 
    current_user: str = Depends(get_current_admin_user_with_redirect)
):
    # Güvenlik önlemi: pdf_name içinde yol manipülasyonu olmamasını kontrol et (örn: "..")
    if ".." in pdf_name or "/" in pdf_name or "\\" in pdf_name:
        raise HTTPException(status_code=400, detail="Geçersiz PDF adı.")

    pdf_path = os.path.join(DISCOUNT_MATERIALS_DIR, pdf_name)
    if not os.path.isfile(pdf_path):
        raise HTTPException(status_code=404, detail="PDF dosyası bulunamadı.")

    # PDF dosyasının public URL'ini oluştur (static mount üzerinden) ve genişliğe sığdırma parametresini dene
    pdf_url = f"/static/discount_materials/{pdf_name}#view=FitH"
    
    return templates.TemplateResponse("view_pdf.html", {
        "request": request,
        "title": f"PDF Görüntüleyici: {pdf_name}",
        "admin_user": current_user,
        "pdf_name": pdf_name,
        "pdf_url": pdf_url
    })

@app.post("/delete-discount-material/{material_name}", tags=["Discounts"])
async def delete_discount_material_file(
    request: Request, 
    material_name: str, 
    current_user: str = Depends(get_current_admin_user_for_api) # Admin koruması
):
    # Güvenlik önlemi: material_name içinde yol manipülasyonu olmamasını kontrol et
    if ".." in material_name or "/" in material_name or "\\" in material_name:
        # Kullanıcıya bir mesaj göstermek için session flash mesajları kullanılabilir
        # Şimdilik basit bir yönlendirme yapalım veya hata loglayalım.
        print(f"UYARI: Geçersiz materyal adı silme denemesi: {material_name}")
        return RedirectResponse(url=request.url_for("view_discounts"), status_code=status.HTTP_303_SEE_OTHER)

    file_path = os.path.join(DISCOUNT_MATERIALS_DIR, material_name)
    
    if os.path.isfile(file_path):
        try:
            os.remove(file_path)
            print(f"Dosya başarıyla silindi: {file_path}")
            # Başarı mesajı için flash mesaj eklenebilir
        except Exception as e:
            print(f"Dosya silinirken hata oluştu ({file_path}): {e}")
            # Hata mesajı için flash mesaj eklenebilir
    else:
        print(f"Silinecek dosya bulunamadı: {file_path}")
        # Dosya bulunamadı mesajı için flash mesaj eklenebilir

    return RedirectResponse(url=request.url_for("view_discounts"), status_code=status.HTTP_303_SEE_OTHER)

@app.get("/view-discount-images", response_class=HTMLResponse, tags=["Discounts"])
async def view_discount_images_page(
    request: Request, 
    current_user: str = Depends(get_current_admin_user_with_redirect)
):
    ensure_discount_materials_dir()
    image_materials = []
    allowed_image_extensions = (".jpg", ".jpeg", ".png", ".gif")
    try:
        for filename in os.listdir(DISCOUNT_MATERIALS_DIR):
            if os.path.isfile(os.path.join(DISCOUNT_MATERIALS_DIR, filename)) and filename.lower().endswith(allowed_image_extensions):
                image_materials.append({
                    "name": filename,
                    "url": f"/static/discount_materials/{filename}"
                })
    except Exception as e:
        print(f"İndirim görselleri listelenirken hata: {e}")
        # Hata durumunda boş liste ile devam et
    
    return templates.TemplateResponse("view_discount_images.html", {
        "request": request,
        "title": "İndirim Görselleri Galerisi",
        "admin_user": current_user,
        "image_materials": sorted(image_materials, key=lambda x: x['name']) # Ada göre sırala
    })

if __name__ == "__main__":
    import uvicorn
    # Normalde bu dosya doğrudan çalıştırılmaz, uvicorn ile komut satırından çalıştırılır.
    # Örn: uvicorn b2b_web_app.main:app --reload
    print("FastAPI uygulamasını çalıştırmak için terminalde şu komutu kullanın:")
    print("uvicorn b2b_web_app.main:app --reload --host 0.0.0.0 --port 8000")
    # uvicorn.run(app, host="0.0.0.0", port=8000) # Direkt çalıştırma genellikle geliştirme için --reload ile yapılır. 