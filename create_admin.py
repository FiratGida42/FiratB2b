import json
import getpass
from passlib.context import CryptContext

# Şifre hash'leme için context (bcrypt algoritmasını kullanacağız)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
CONFIG_FILE = "admin_config.json"

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_admin_user():
    print("Admin kullanıcısı oluşturuluyor...")
    username = input("Admin kullanıcı adını girin: ").strip()
    while not username:
        print("Kullanıcı adı boş olamaz.")
        username = input("Admin kullanıcı adını girin: ").strip()

    while True:
        password = getpass.getpass("Admin şifresini girin: ")
        if not password:
            print("Şifre boş olamaz.")
            continue
        password_confirm = getpass.getpass("Admin şifresini tekrar girin: ")
        if password == password_confirm:
            break
        else:
            print("Şifreler eşleşmiyor. Lütfen tekrar deneyin.")

    hashed_password = get_password_hash(password)

    admin_data = {
        "admin_username": username,
        "admin_hashed_password": hashed_password
    }

    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(admin_data, f, ensure_ascii=False, indent=4)
        print(f"Admin kullanıcısı başarıyla '{CONFIG_FILE}' dosyasına kaydedildi.")
        print("LÜTFEN BU DOSYAYI GÜVENLİ BİR YERDE SAKLAYIN VE .gitignore DOSYANIZA EKLEYİN!")
    except IOError:
        print(f"HATA: '{CONFIG_FILE}' dosyasına yazılırken bir sorun oluştu.")

if __name__ == "__main__":
    # Eğer dosya zaten varsa, üzerine yazmak isteyip istemediğini sor
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
            print(f"UYARI: '{CONFIG_FILE}' dosyası zaten mevcut ve '{existing_data.get('admin_username')}' kullanıcısını içeriyor.")
            overwrite = input("Üzerine yazmak ve yeni bir admin kullanıcısı oluşturmak istiyor musunuz? (evet/hayır): ").strip().lower()
            if overwrite == 'evet':
                create_admin_user()
            else:
                print("İşlem iptal edildi.")
    except FileNotFoundError:
        create_admin_user()
    except Exception as e:
        print(f"Beklenmedik bir hata oluştu: {e}")
        create_admin_user() # Hata durumunda yine de oluşturmayı dene veya daha iyi bir hata yönetimi yap 