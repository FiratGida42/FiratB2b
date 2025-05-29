from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Offline versiyonu için veritabanı URL'sini ayarla
SQLALCHEMY_DATABASE_URL = os.getenv("OFFLINE_DATABASE_URL") # Ortam değişkeninden almayı dene

if SQLALCHEMY_DATABASE_URL is None:
    # Ortam değişkeni yoksa, Offline klasörü içinde bir .db dosyası kullan
    DATABASE_FILE_NAME_LOCAL = "b2b_offline_data.db"
    # BASE_DIR, bu dosyanın bulunduğu 'Offline' klasörünü işaret eder
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, DATABASE_FILE_NAME_LOCAL)}"
    print(f"UYARI: OFFLINE_DATABASE_URL ortam değişkeni bulunamadı! Yerel SQLite kullanılacak: {DATABASE_FILE_NAME_LOCAL}")

print(f"OFFLINE DATABASE: Kullanılacak veritabanı URL'si: {SQLALCHEMY_DATABASE_URL}")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False} # SQLite için gerekli
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 