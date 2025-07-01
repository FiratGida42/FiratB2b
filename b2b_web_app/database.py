from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Render'daki DATABASE_URL ortam değişkenini al
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

if SQLALCHEMY_DATABASE_URL is None:
    print("UYARI: DATABASE_URL ortam değişkeni bulunamadı! Yerel geliştirme için varsayılan bir yol kullanılacak.")
    # Yerel geliştirme için varsayılan bir yol (proje kökünde b2b_database.db)
    DATABASE_FILE_NAME_LOCAL = "b2b_database.db"
    PROJECT_ROOT_DIRECTORY_LOCAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(PROJECT_ROOT_DIRECTORY_LOCAL, DATABASE_FILE_NAME_LOCAL)}"

print(f"DATABASE.PY: Kullanılacak veritabanı URL\'si: {SQLALCHEMY_DATABASE_URL}")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
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