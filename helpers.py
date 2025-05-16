'''
Yardımcı Fonksiyonlar Modülü (helpers.py)

Bu modül, proje genelinde kullanılabilecek sayı ve tarih formatlama gibi 
yardımcı fonksiyonları içerir.
'''
from decimal import Decimal, InvalidOperation
from datetime import datetime, date

# --- Sayısal Veri Dönüşümü ---
def to_decimal(value, default=None):
    """
    Verilen bir değeri Decimal tipine dönüştürür.
    Dönüşüm sırasında bir hata oluşursa 'default' değeri döndürülür (varsayılan: None).
    Float değerlerde hassasiyet kaybını önlemek için önce string'e çevirir.
    """
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return default

# --- Para Birimi Formatlama ---
def format_currency_tr(value, decimal_places=2, currency_symbol=""):
    """
    Sayısal bir değeri, belirtilen formatta Türk Lirası para birimi olarak formatlar.
    Örnek: 1234.56 -> "1.234,56"
    Dönüşüm başarısız olursa boş string döndürür.
    """
    dec_value = to_decimal(value, default=None) # Önce Decimal'e çevir
    if dec_value is None:
        return "" # Hatalı veya None değer için boş string

    # İstenen ondalık basamağa göre string olarak formatla (yuvarlama dahil)
    # Bu, ondalık ayıracı olarak nokta kullanır.
    formatted_str_value = "{:.{prec}f}".format(dec_value, prec=decimal_places)

    parts = formatted_str_value.split('.')
    integer_part_str = parts[0]
    fractional_part_str = parts[1] if len(parts) > 1 and decimal_places > 0 else ""

    # Tam sayı kısmına binlik ayıracı (.) ekle
    sign = '-' if integer_part_str.startswith('-') else ''
    if sign:
        integer_part_str = integer_part_str[1:]

    segments = []
    while len(integer_part_str) > 3:
        segments.insert(0, integer_part_str[-3:])
        integer_part_str = integer_part_str[:-3]
    segments.insert(0, integer_part_str)
    formatted_integer = sign + '.'.join(segments)

    if decimal_places > 0:
        if currency_symbol: # Eğer sembol varsa boşlukla ekle
            return f"{formatted_integer},{fractional_part_str} {currency_symbol}"
        else: # Sembol yoksa boşluksuz ekle
            return f"{formatted_integer},{fractional_part_str}"
    else:
        if currency_symbol: # Eğer sembol varsa boşlukla ekle
            return f"{formatted_integer} {currency_symbol}"
        else: # Sembol yoksa boşluksuz ekle
            return f"{formatted_integer}"

# --- Tarih Formatlama ---
def format_date_tr(date_value, fmt="%d.%m.%Y"):
    """
    Bir datetime.date veya datetime.datetime nesnesini, belirtilen formatta string'e çevirir.
    Varsayılan format: "dd.MM.yyyy".
    Formatlama başarısız olursa orijinal değeri string olarak döndürür.
    """
    if isinstance(date_value, (datetime, date)):
        try:
            return date_value.strftime(fmt)
        except ValueError:
            # Geçersiz format string'i veya tarih nesnesi için hata durumu
            return str(date_value) 
    # String veya diğer tipler için şimdilik doğrudan string'e çevir
    # Gerekirse string tarihleri parse etmek için ek mantık eklenebilir.
    return str(date_value) 