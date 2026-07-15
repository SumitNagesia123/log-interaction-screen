import datetime as dt_module
from sqlalchemy import Column, Integer, String, DateTime, Date, Text, Boolean, ForeignKey, Float, Table
from sqlalchemy.orm import relationship
from backend.app.db.session import Base

# Many-to-many relationship table between Interactions and Products discussed
interaction_products = Table(
    "interaction_products",
    Base.metadata,
    Column("interaction_id", Integer, ForeignKey("interactions.id", ondelete="CASCADE"), primary_key=True),
    Column("product_id", Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
)

class HCP(Base):
    __tablename__ = "hcps"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    specialty = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    created_at = Column(DateTime, default=dt_module.datetime.utcnow)

    # Relationships
    interactions = relationship("Interaction", back_populates="hcp")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True, unique=True)
    therapeutic_area = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=dt_module.datetime.utcnow)

class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    hcp_id = Column(Integer, ForeignKey("hcps.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(50), nullable=False)  # Visit, Call, Email, Sample Drop, Conference
    datetime = Column(DateTime, default=dt_module.datetime.utcnow)
    discussion_notes = Column(Text, nullable=True)
    sentiment = Column(String(50), nullable=True)  # Positive, Neutral, Negative
    attendees = Column(Text, nullable=True)
    materials_shared = Column(Text, nullable=True)
    follow_up_required = Column(Boolean, default=False)
    follow_up_date = Column(Date, nullable=True)
    follow_up_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=dt_module.datetime.utcnow)

    updated_at = Column(DateTime, default=dt_module.datetime.utcnow, onupdate=dt_module.datetime.utcnow)

    # Relationships
    hcp = relationship("HCP", back_populates="interactions")
    products = relationship("Product", secondary=interaction_products)
    samples = relationship("InteractionSample", back_populates="interaction", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="interaction", cascade="all, delete-orphan")

class InteractionSample(Base):
    __tablename__ = "interaction_samples"

    id = Column(Integer, primary_key=True, index=True)
    interaction_id = Column(Integer, ForeignKey("interactions.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, default=0)

    # Relationships
    interaction = relationship("Interaction", back_populates="samples")
    product = relationship("Product")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    interaction_id = Column(Integer, ForeignKey("interactions.id", ondelete="CASCADE"), nullable=True)
    changed_by = Column(String(255), default="Sales Rep")
    action = Column(String(50), nullable=False)  # CREATE, UPDATE
    field_name = Column(String(100), nullable=True)  # Name of the field edited
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    source = Column(String(50), nullable=False)  # ai, manual
    confidence_score = Column(Float, nullable=True)  # Confidence score if extracted by AI
    timestamp = Column(DateTime, default=dt_module.datetime.utcnow)

    # Relationships
    interaction = relationship("Interaction", back_populates="audit_logs")
