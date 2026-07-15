from pydantic import BaseModel, Field
from typing import List, Optional
import datetime as dt_module
from backend.app.schemas.hcp import HCP

class ProductBase(BaseModel):
    name: str
    therapeutic_area: Optional[str] = None
    description: Optional[str] = None

class Product(ProductBase):
    id: int
    created_at: dt_module.datetime

    class Config:
        from_attributes = True

class InteractionSampleBase(BaseModel):
    product_id: int
    quantity: int

class InteractionSampleCreate(InteractionSampleBase):
    pass

class InteractionSample(InteractionSampleBase):
    id: int
    interaction_id: int
    product: Product

    class Config:
        from_attributes = True

class InteractionBase(BaseModel):
    hcp_id: int
    type: str  # Visit, Call, Email, Sample Drop, Conference
    datetime: Optional[dt_module.datetime] = None
    discussion_notes: Optional[str] = None
    sentiment: Optional[str] = None  # Positive, Neutral, Negative
    attendees: Optional[str] = None
    materials_shared: Optional[str] = None
    follow_up_required: bool = False
    follow_up_date: Optional[dt_module.date] = None
    follow_up_notes: Optional[str] = None

class InteractionCreate(InteractionBase):
    product_ids: List[int] = []
    samples: List[InteractionSampleCreate] = []

class InteractionUpdate(BaseModel):
    hcp_id: Optional[int] = None
    type: Optional[str] = None
    datetime: Optional[dt_module.datetime] = None
    discussion_notes: Optional[str] = None
    sentiment: Optional[str] = None
    attendees: Optional[str] = None
    materials_shared: Optional[str] = None
    follow_up_required: Optional[bool] = None
    follow_up_date: Optional[dt_module.date] = None
    follow_up_notes: Optional[str] = None
    product_ids: Optional[List[int]] = None
    samples: Optional[List[InteractionSampleCreate]] = None
    source: Optional[str] = "manual"  # manual or ai
    confidence_score: Optional[float] = None

class AuditLog(BaseModel):
    id: int
    interaction_id: Optional[int] = None
    changed_by: str
    action: str
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    source: str
    confidence_score: Optional[float] = None
    timestamp: dt_module.datetime

    class Config:
        from_attributes = True

# Metadata containing source ("ai" | "manual") and confidence score for each field
class FieldMetadata(BaseModel):
    source: str = "manual"  # "ai" or "manual"
    confidence: float = 1.0

class InteractionMetadata(BaseModel):
    hcp_id: FieldMetadata = Field(default_factory=FieldMetadata)
    type: FieldMetadata = Field(default_factory=FieldMetadata)
    datetime: FieldMetadata = Field(default_factory=FieldMetadata)
    discussion_notes: FieldMetadata = Field(default_factory=FieldMetadata)
    sentiment: FieldMetadata = Field(default_factory=FieldMetadata)
    attendees: FieldMetadata = Field(default_factory=FieldMetadata)
    materials_shared: FieldMetadata = Field(default_factory=FieldMetadata)
    follow_up_required: FieldMetadata = Field(default_factory=FieldMetadata)
    follow_up_date: FieldMetadata = Field(default_factory=FieldMetadata)
    follow_up_notes: FieldMetadata = Field(default_factory=FieldMetadata)
    product_ids: FieldMetadata = Field(default_factory=FieldMetadata)
    samples: FieldMetadata = Field(default_factory=FieldMetadata)

class InteractionResponse(BaseModel):
    id: int
    hcp_id: int
    hcp: HCP
    type: str
    datetime: dt_module.datetime
    discussion_notes: Optional[str] = None
    sentiment: Optional[str] = None
    attendees: Optional[str] = None
    materials_shared: Optional[str] = None
    follow_up_required: bool
    follow_up_date: Optional[dt_module.date] = None
    follow_up_notes: Optional[str] = None
    products: List[Product] = []
    samples: List[InteractionSample] = []
    metadata_fields: Optional[InteractionMetadata] = None  # To represent source & confidence of each field
    created_at: dt_module.datetime
    updated_at: dt_module.datetime

    class Config:
        from_attributes = True
