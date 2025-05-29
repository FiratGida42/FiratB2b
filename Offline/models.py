import datetime
import enum
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func # func.now() için

# database.py içindeki Base'i import et
from database import Base

# Sipariş Durumları için Python Enum
class PyOrderStatusEnum(enum.Enum):
    PENDING = "Yeni Sipariş"
    PROCESSING = "Hazırlanıyor"
    SHIPPED = "Kargolandı"
    DELIVERED = "Teslim Edildi"
    CANCELED = "İptal Edildi"
    RETURNED = "İade Edildi"

class Order(Base):
    __tablename__ = "offline_orders" # Online tablo ile karışmaması için farklı isim

    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String(255), nullable=True) # Boş olabilir veya "Bilinmeyen Cari"
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    total_amount = Column(Float, nullable=False, default=0.0)
    # SQLAlchemy Enum sütunu PyOrderStatusEnum'u kullanır
    status = Column(SQLEnum(PyOrderStatusEnum, name="offline_order_status_enum", create_constraint=True, validate_strings=True), 
                    nullable=False, 
                    index=True, 
                    default=PyOrderStatusEnum.PENDING)

    # OrderItem ile ilişki (cascade silme ve yetim bırakmama aktif)
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Order(id={self.id}, customer_name='{self.customer_name}', status='{self.status.value if self.status else None}')>"

class OrderItem(Base):
    __tablename__ = "offline_order_items" # Online tablo ile karışmaması için farklı isim

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("offline_orders.id"), nullable=False) # offline_orders.id'ye referans
    product_code = Column(String(100), nullable=False, index=True)
    product_name = Column(String(255), nullable=False) # Ürün adını da saklayalım
    barcode = Column(String(255), nullable=True) # Barkod alanı
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)

    # Order ile ilişki
    order = relationship("Order", back_populates="items")

    def __repr__(self):
        return f"<OrderItem(id={self.id}, product_code='{self.product_code}', quantity={self.quantity})>"

# Ek Not: Eğer online ve offline veritabanları arasında senkronizasyon yapılacaksa,
# ID çakışmalarını önlemek için UUID gibi global benzersiz ID'ler kullanmak daha iyi olabilir.
# Şimdilik basit tutmak adına Integer ID'ler kullanıldı. 