from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv # .env dosyasını okumak için (opsiyonel ama iyi pratik)

load_dotenv() # Ortam değişkenlerini .env dosyasından yükle (varsa)

# Veritabanı URL'sini ortam değişkeninden al, yoksa varsayılan bir yerel yol kullan
# Render.com'da DATABASE_URL ortam değişkeni ayarlı olmalı ve /mnt/data/... yolunu göstermeli
DEFAULT_SQLITE_DB_NAME = "b2b_database.db" # Varsayılan dosya adı (eğer ortam değişkeni yoksa)
DEFAULT_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DATABASE_URL = f"sqlite:///{os.path.join(DEFAULT_PROJECT_ROOT, DEFAULT_SQLITE_DB_NAME)}"

# DATABASE_URL ortam değişkenini kullan, eğer ayarlanmamışsa yerel geliştirmede DEFAULT_DATABASE_URL'yi kullan
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

# SQLAlchemy engine'i oluştur
# connect_args={"check_same_thread": False} sadece SQLite için gereklidir.
# FastAPI'nin aynı thread'de birden fazla istek yapabilmesi için.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Veritabanı session'ı için bir SessionLocal sınıfı oluştur
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Modellerimizin miras alacağı Base sınıfı
Base = declarative_base()

# Veritabanı session'ını almak için bir dependency (FastAPI endpoint'lerinde kullanılacak)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Ekran çıktısı için (sadece geliştirme/debug amaçlı, üretimde kaldırılabilir)
print(f"SQLAlchemy engine, şu veritabanına bağlanıyor: {SQLALCHEMY_DATABASE_URL}") 