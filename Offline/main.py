import json
import os
from fastapi import FastAPI, Request, HTTPException, Depends, status, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import List, Optional, Dict, Any

# Veritabanı ve Modeller (Çevrimdışı sürümde doğrudan JSON veya basit veritabanı kullanılacak)
# from sqlalchemy.orm import Session
# from . import models, database # Gerçek veritabanı bağlantısı online versiyonda kalacak

# Ortam değişkeninden veritabanı URL'sini al, yoksa varsayılan SQLite kullan
# Bu çevrimdışı sürümde, bu DB esas olarak siparişlerin geçici saklanması (sync öncesi) için olabilir.
# Ana veri (ürünler, cariler) JSON'dan gelecek.
OFFLINE_DATA_DB_NAME = "b2b_offline_data.db"
OFFLINE_DATABASE_URL = os.environ.get("OFFLINE_DATABASE_URL", f"sqlite:///./{OFFLINE_DATA_DB_NAME}")

print(f"OFFLINE DATABASE (Geçici Saklama): Kullanılacak veritabanı URL'si: {OFFLINE_DATABASE_URL}")

# Veritabanı engine ve session (Sadece gerekirse, örn: sipariş kuyruğu için)
# models.Base.metadata.create_all(bind=database.engine) # Tabloları oluştur

app = FastAPI(
    title="B2B Offline Portal",
    version="1.0.0",
    description="Fırat Toptan B2B Portalı - Çevrimdışı Sürüm"
)

# Static dosyalar (CSS, JS, Resimler, İndirilen Kütüphaneler)
# static klasörü Offline klasörünün içinde olmalı (Offline/static)
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Jinja2 Templates
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# --- Helper Fonksiyonlar ---
def load_json_data(file_path: str) -> List[Dict[str, Any]]:
    """Belirtilen yoldan JSON dosyasını yükler."""
    full_path = BASE_DIR / "static" / "json_data" / file_path
    if not full_path.exists():
        print(f"UYARI: JSON dosyası bulunamadı: {full_path}")
        return []
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"HATA: JSON dosyası okunurken hata ({full_path}): {e}")
        return []

def get_current_admin_user(request: Request) -> Optional[str]:
    """Cookie'den mevcut admin kullanıcı adını alır (basit simülasyon)."""
    return request.cookies.get("admin_user")

# Para formatlama Jinja2 filtresi
def currency_tr(value: Any) -> str:
    try:
        val = float(value)
        return f"{val:,.2f} ₺".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return str(value)

templates.env.filters['currency_tr'] = currency_tr


# --- Admin Auth (Basit Cookie Tabanlı Simülasyon) ---
# Gerçek bir uygulamada daha güvenli bir yöntem kullanılmalıdır.
ADMIN_USERNAME = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASS", "admin123")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login") # Aslında token kullanmıyoruz, sadece FastAPI için

@app.post("/login", response_class=HTMLResponse)
async def login_for_access_token(request: Request, username: str = Form(...), password: str = Form(...)):
    error_message = None
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        response.set_cookie(key="admin_user", value=username, httponly=True, samesite="lax")
        print(f"Admin girişi başarılı: {username}")
        return response
    else:
        print(f"Admin girişi başarısız denemesi: Kullanıcı adı '{username}'")
        error_message = "Geçersiz kullanıcı adı veya şifre."
    return templates.TemplateResponse("login.html", {"request": request, "title": "Admin Girişi", "error_message": error_message})

@app.get("/logout", response_class=RedirectResponse)
async def logout(request: Request):
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("admin_user")
    print("Admin çıkışı yapıldı.")
    return response

# --- Sayfa Endpoint'leri ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # Ürünler sayfası ana sayfa olacak
    admin_user = get_current_admin_user(request)
    # products.html'in artık /api/products yerine /static/json_data/received_products.json kullanması gerekiyor.
    # Bu veri doğrudan template'e gönderilmeyecek, JS tarafından fetch edilecek.
    return templates.TemplateResponse("products.html", {"request": request, "title": "Ürün Kataloğu", "admin_user": admin_user})

@app.get("/products", response_class=HTMLResponse) # Alias for /
async def read_products_page(request: Request):
    admin_user = get_current_admin_user(request)
    return templates.TemplateResponse("products.html", {"request": request, "title": "Ürün Kataloğu", "admin_user": admin_user})


@app.get("/cart", response_class=HTMLResponse)
async def read_cart(request: Request):
    admin_user = get_current_admin_user(request)
    # Sepet verisi localStorage'dan JS ile yönetilecek
    return templates.TemplateResponse("cart.html", {"request": request, "title": "Sepetim", "admin_user": admin_user})

@app.get("/orders", response_class=HTMLResponse)
async def read_orders_page(request: Request):
    admin_user = get_current_admin_user(request)
    # Siparişler /api/orders'dan JS ile çekilecek ve SW tarafından yönetilecek
    return templates.TemplateResponse("orders.html", {"request": request, "title": "Siparişlerim", "admin_user": admin_user})

@app.get("/customer-balances", response_class=HTMLResponse)
async def read_customer_balances(request: Request):
    admin_user = get_current_admin_user(request)
    customers_data = load_json_data("filtrelenen_cariler.json")
    # Veriyi İSME göre sırala (Türkçe karakterleri de dikkate alarak)
    try:
        customers_data.sort(key=lambda x: (x.get("CARI_ISIM") or "").lower().replace('ı', 'i').replace('ş','s').replace('ğ','g').replace('ü','u').replace('ö','o').replace('ç','c'))
    except Exception as e:
        print(f"Cari sıralama hatası: {e}")

    return templates.TemplateResponse("customer_balances.html", {
        "request": request,
        "title": "Cari Hesap Bakiyeleri",
        "customers": customers_data,
        "admin_user": admin_user
    })

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if get_current_admin_user(request): # Zaten giriş yapmışsa ana sayfaya yönlendir
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("login.html", {"request": request, "title": "Admin Girişi"})

@app.get("/admin/me", response_class=HTMLResponse)
async def admin_me_page(request: Request):
    admin_user = get_current_admin_user(request)
    if not admin_user:
        return RedirectResponse(url="/login?next=/admin/me", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("admin_me.html", {"request": request, "title": "Admin Paneli", "username": admin_user})


# --- API Endpoint'leri (Çevrimdışı odaklı) ---

# Ürünler API'si artık statik JSON dosyasından beslenecek (sw.js'in cache etmesi için)
# products.html direkt /static/json_data/received_products.json dosyasını fetch edecek.
# Bu yüzden /api/products endpoint'i çevrimdışı sürümde gerekmeyebilir,
# ancak uyumluluk veya gelecekteki esneklik için bırakılabilir.
@app.get("/api/products")
async def get_products_api():
    products = load_json_data("received_products.json")
    if not products:
        print("UYARI: /api/products çağrıldı ama received_products.json boş veya yok.")
    # STOK_ADI'na göre Türkçe karakterleri dikkate alarak sırala
    try:
        products.sort(key=lambda x: (x.get("STOK_ADI") or "").lower().replace('ı', 'i').replace('ş','s').replace('ğ','g').replace('ü','u').replace('ö','o').replace('ç','c'))
    except Exception as e:
        print(f"Ürün API sıralama hatası: {e}")
    return products

# Müşteriler API'si (filtrelenen_cariler.json)
@app.get("/api/customers")
async def get_customers_api():
    customers = load_json_data("filtrelenen_cariler.json")
    if not customers:
        print("UYARI: /api/customers çağrıldı ama filtrelenen_cariler.json boş veya yok.")
    # CARI_ISIM'e göre Türkçe karakterleri dikkate alarak sırala
    try:
        customers.sort(key=lambda x: (x.get("CARI_ISIM") or "").lower().replace('ı', 'i').replace('ş','s').replace('ğ','g').replace('ü','u').replace('ö','o').replace('ç','c'))
    except Exception as e:
        print(f"Müşteri API sıralama hatası: {e}")
    return customers


# Siparişler API'si (Çevrimdışı senaryoda bu daha karmaşık olacak)
# POST /api/orders: Yeni sipariş alır. SW bunu yakalayıp IndexedDB'ye yazabilir.
# GET /api/orders: Mevcut siparişleri listeler. SW bunu IndexedDB'den okuyabilir.

# Bu şimdilik basit bir placeholder, SW ve IndexedDB entegrasyonu ile geliştirilmeli.
# Geçici olarak siparişleri bellekte tutabilir veya basit bir JSON dosyasına yazabiliriz (test için).
# Ama en doğru çözüm IndexedDB olacaktır.
_OFFLINE_ORDERS_DB = [] # Çok basit bellek içi sipariş saklama (test için)

@app.post("/api/orders")
async def create_offline_order(request: Request, order_data: Dict[str, Any]): # Pydantic model yerine Dict kullanalım basitlik için
    # Normalde burada Pydantic modeli ile veri doğrulaması yapılır.
    # order_data: { customer_code: str, customer_name: str, items: [{product_code, product_name, quantity, unit_price, barcode}]}
    print(f"POST /api/orders (offline) alındı: {order_data.get('customer_name')}")

    # SW bu isteği yakalayıp IndexedDB'ye yazmalı.
    # Eğer SW yoksa veya bu isteği pas geçerse, burası çalışır.
    # Burada basitçe belleğe ekleyelim (çok ilkel, sadece test amaçlı)
    new_order_id = len(_OFFLINE_ORDERS_DB) + 1
    created_at = order_data.get("created_at") # cart.html'den gelmeli
    order_to_store = {
        "id": new_order_id,
        "customer_code": order_data.get("customer_code"),
        "customer_name": order_data.get("customer_name"),
        "customer_details": order_data.get("customer_details"), # cart.html'den gelmeli
        "items": order_data.get("items", []),
        "total_amount": sum(item.get('quantity',0) * item.get('unit_price',0) for item in order_data.get("items", [])),
        "status": order_data.get("status", "PENDING_SYNC"), # cart.html'den gelmeli
        "created_at": created_at if created_at else datetime.utcnow().isoformat() # Eğer yoksa şimdi oluştur
    }
    _OFFLINE_ORDERS_DB.append(order_to_store)
    print(f"Sipariş geçici olarak belleğe eklendi (ID: {new_order_id}). SW tarafından senkronize edilmeli.")
    # SW'ye yanıt olarak siparişin kaydedildiğini (belki geçici ID ile) döndürebiliriz.
    return JSONResponse(content=order_to_store, status_code=201)


@app.get("/api/orders")
async def get_offline_orders(request: Request):
    # Bu da SW tarafından IndexedDB'den okunarak yönetilmeli.
    # Şimdilik bellekten okuyalım.
    print(f"GET /api/orders (offline) çağrıldı. Bellekteki sipariş sayısı: {len(_OFFLINE_ORDERS_DB)}")
    # Tarihe göre tersten sırala (en yeni en üstte)
    sorted_orders = sorted(_OFFLINE_ORDERS_DB, key=lambda x: x.get('created_at', ''), reverse=True)
    return JSONResponse(content=sorted_orders)


# Pathlib importunu ekleyelim
from pathlib import Path
from datetime import datetime # created_at için

if __name__ == "__main__":
    # Bu kısım uvicorn ile çalıştırırken kullanılmaz, doğrudan python main.py ile test için.
    # import uvicorn
    # uvicorn.run(app, host="0.0.0.0", port=8001)
    pass