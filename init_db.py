#!/usr/bin/env python3
"""
Render deployment için Alembic bypass init script
Bu script, Alembic migration sorunlarını bypass ederek direkt SQLAlchemy ile tabloları oluşturur.
"""

import os
import sys
import sqlite3
from pathlib import Path

# Proje kök dizinini sys.path'e ekle
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from b2b_web_app.models import Base
from sqlalchemy import create_engine

def init_database():
    """Veritabanını initialize et"""
    
    # Database URL'i al (database.py'daki mantığı kopyala)
    database_url = os.getenv("DATABASE_URL")
    
    if database_url is None:
        print("INIT_DB: DATABASE_URL ortam değişkeni bulunamadı! Yerel geliştirme için varsayılan bir yol kullanılacak.")
        # Yerel geliştirme için varsayılan bir yol (proje kökünde b2b_database.db)
        DATABASE_FILE_NAME_LOCAL = "b2b_database.db"
        PROJECT_ROOT_DIRECTORY_LOCAL = os.path.dirname(os.path.abspath(__file__))
        database_url = f"sqlite:///{os.path.join(PROJECT_ROOT_DIRECTORY_LOCAL, DATABASE_FILE_NAME_LOCAL)}"
    
    print(f"INIT_DB: Veritabanı URL'si: {database_url}")
    
    # SQLite dosya path'ini çıkar
    if database_url.startswith("sqlite:///"):
        db_path = database_url.replace("sqlite:///", "")
        print(f"INIT_DB: Veritabanı dosya yolu: {db_path}")
        
        # Veritabanı dizinini oluştur (yoksa)
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
            print(f"INIT_DB: Veritabanı dizini oluşturuldu: {db_dir}")
        
        # Eğer veritabanı dosyası varsa ve alembic_version tablosu varsa temizle
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # alembic_version tablosunu kontrol et
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version';")
                if cursor.fetchone():
                    print("INIT_DB: Eski alembic_version tablosu bulundu, siliniyor...")
                    cursor.execute("DROP TABLE alembic_version;")
                    conn.commit()
                    print("INIT_DB: alembic_version tablosu silindi.")
                
                conn.close()
            except Exception as e:
                print(f"INIT_DB: Alembic_version temizleme hatası (devam ediliyor): {e}")
    
    # SQLAlchemy engine oluştur
    engine = create_engine(database_url)
    
    # Tabloları oluştur
    print("INIT_DB: Tablolar oluşturuluyor...")
    Base.metadata.create_all(bind=engine)
    print("INIT_DB: Tablolar başarıyla oluşturuldu!")
    
    # Alembic version'ı stamp et (opsiyonel)
    try:
        # Son migration revision'ımızı al
        # Bu, yerel geliştirmede oluşturduğumuz migration'ın ID'si
        latest_revision = "6fb004696272"  # Bu bizim yeni migration'ımızın ID'si
        
        conn = sqlite3.connect(db_path if database_url.startswith("sqlite:///") else ":memory:")
        cursor = conn.cursor()
        
        # Alembic version tablosunu oluştur ve stamp et
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alembic_version (
                version_num VARCHAR(32) NOT NULL,
                CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
            );
        """)
        
        # Mevcut revision'ı sil ve yeni olanı ekle
        cursor.execute("DELETE FROM alembic_version;")
        cursor.execute("INSERT INTO alembic_version (version_num) VALUES (?);", (latest_revision,))
        
        conn.commit()
        conn.close()
        
        print(f"INIT_DB: Alembic version {latest_revision} olarak stamp edildi.")
        
    except Exception as e:
        print(f"INIT_DB: Alembic stamping hatası (devam ediliyor): {e}")
    
    print("INIT_DB: Veritabanı initialization tamamlandı!")

if __name__ == "__main__":
    print("INIT_DB: Veritabanı initialization başlatılıyor...")
    init_database()
    print("INIT_DB: İşlem tamamlandı.") 