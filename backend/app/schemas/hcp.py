from pydantic import BaseModel, EmailStr
from typing import Optional
import datetime as dt_module

class HCPBase(BaseModel):
    name: str
    specialty: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None

class HCPCreate(HCPBase):
    pass

class HCP(HCPBase):
    id: int
    created_at: dt_module.datetime

    class Config:
        from_attributes = True
