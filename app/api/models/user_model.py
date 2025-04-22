# app/api/models/user_model.py
import enum
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Boolean, Enum, DateTime, func

from app.utils.postgresql_db_util import db_util

base = db_util.base


class UserRoleModel(str, enum.Enum):
    VENDOR = "vendor"
    DRIVER = "driver"
    CUSTOMER = "customer"


class UserModel(base):

    __tablename__ = 'users'
    __table_args__ = ({'schema': 'public'})

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False, index=True)
    email = Column(String, nullable=True, index=True)
    role = Column(Enum(UserRoleModel), nullable=False)

    # Relationships
    vendor_deliveries = relationship("DeliveryModel", back_populates="vendor",
                                     foreign_keys="DeliveryModel.vendor_id")
    driver_deliveries = relationship("DeliveryModel", back_populates="driver",
                                     foreign_keys="DeliveryModel.driver_id")
    customer_deliveries = relationship("DeliveryModel", back_populates="customer",
                                       foreign_keys="DeliveryModel.customer_id")

    # Additional fields for different roles
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


    def to_dict(self):
        """
        Convert the object to a dictionary.
        :return:
        """
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    def __repr__(self):
        return f"<User id={self.id} name={self.name} phone={self.phone} role={self.role}>"
