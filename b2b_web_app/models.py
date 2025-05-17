import datetime
import enum # Standart Python enum importu eklendi
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func # func.now() için eklendi
# from sqlalchemy.ext.declarative import declarative_base # Bu satır artık gereksiz

from .database import Base # database.py dosyasından Base import ediliyor

# Base = declarative_base() # Bu satır kaldırıldı, Base database.py'den geliyor

# Standart Python Enum olarak tanımla
class PyOrderStatusEnum(enum.Enum):
    PENDING = "Yeni Sipariş"
    PROCESSING = "Hazırlanıyor"
    SHIPPED = "Kargolandı"
    DELIVERED = "Teslim Edildi"
    CANCELED = "İptal Edildi"
    RETURNED = "İade Edildi"

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    total_amount = Column(Float, nullable=False)
    # SQLAlchemy sütununda PyOrderStatusEnum'u kullan
    status = Column(SQLEnum(PyOrderStatusEnum, name="order_status_enum", create_constraint=True, validate_strings=True), nullable=False, index=True, default=PyOrderStatusEnum.PENDING)

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Order(id={self.id}, customer_name='{self.customer_name}', status='{self.status.value if self.status else None}')>"

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_code = Column(String(100), nullable=False, index=True)
    product_name = Column(String(255), nullable=False) # Ürün adını da saklayalım
    barcode = Column(String(255), nullable=True) # Barkod alanı eklendi
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")

    def __repr__(self):
        return f"<OrderItem(id={self.id}, product_code='{self.product_code}', quantity={self.quantity})>" 