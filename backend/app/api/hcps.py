from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from backend.app.db.session import get_db
from backend.app.db.models import HCP, Product
from backend.app.schemas.hcp import HCP as HCPSchema
from backend.app.schemas.interaction import Product as ProductSchema
from backend.app.api.auth import get_current_user

router = APIRouter()

@router.get("/api/hcps", response_model=List[HCPSchema])
def get_hcps(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    return db.query(HCP).all()

@router.get("/api/products", response_model=List[ProductSchema])
def get_products(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    return db.query(Product).all()
