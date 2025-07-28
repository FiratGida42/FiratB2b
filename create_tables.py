#!/usr/bin/env python3
"""
Render deployment için basit tablo oluşturma script'i
Alembic olmadan direkt SQLAlchemy ile tabloları oluşturur.
"""

import os
import sys

# Proje kök dizinini sys.path'e ekle
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import create_engine
from b2b_web_app.models import Base

def create_tables():
    """Tabloları oluştur"""
    
    # Database URL'i al
    database_url = os.getenv("DATABASE_URL")
    
    if database_url is None:
        print("CREATE_TABLES: DATABASE_URL ortam değişkeni bulunamadı! Yerel geliştirme için varsayılan bir yol kullanılacak.")
        DATABASE_FILE_NAME_LOCAL = "b2b_database.db"
        PROJECT_ROOT_DIRECTORY_LOCAL = os.path.dirname(os.path.abspath(__file__))
        database_url = f"sqlite:///{os.path.join(PROJECT_ROOT_DIRECTORY_LOCAL, DATABASE_FILE_NAME_LOCAL)}"
    
    print(f"CREATE_TABLES: Veritabanı URL'si: {database_url}")
    
    # SQLAlchemy engine oluştur
    engine = create_engine(database_url)
    
    # Tabloları oluştur
    print("CREATE_TABLES: Tablolar oluşturuluyor...")
    Base.metadata.create_all(bind=engine)
    print("CREATE_TABLES: Tablolar başarıyla oluşturuldu!")

if __name__ == "__main__":
    print("CREATE_TABLES: Tablo oluşturma işlemi başlatılıyor...")
    create_tables()
    print("CREATE_TABLES: İşlem tamamlandı.") 