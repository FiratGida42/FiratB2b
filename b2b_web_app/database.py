from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Projenin ana dizinini bul
# __file__ -> b2b_web_app/database.py
# os.path.dirname(__file__) -> b2b_web_app
# os.path.dirname(os.path.dirname(__file__)) -> ana proje dizini
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_FILE_NAME = "b2b_app.sqlite3"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(PROJECT_ROOT, DATABASE_FILE_NAME)}"

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