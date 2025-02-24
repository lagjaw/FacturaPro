from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from Models.Category import Category
from Models.Product import Product
from Models.Supplier import Supplier


class ProductService:
    def __init__(self, db: Session):
        self.db = db

    async def update_product_category_and_supplier(
        self,
        product_id: str,
        category_id: str,
        supplier_id: str
    ) -> Dict:
        """Update product's category and supplier"""
        product = self.db.query(Product).filter_by(id=product_id).first()
        if not product:
            raise ValueError(f"Product with id {product_id} not found.")

        category = self.db.query(Category).filter_by(id=category_id).first()
        if not category:
            raise ValueError(f"Category with id {category_id} not found.")

        supplier = self.db.query(Supplier).filter_by(id=supplier_id).first()
        if not supplier:
            raise ValueError(f"Supplier with id {supplier_id} not found.")

        product.category_id = category.id
        product.supplier_id = supplier.id
        product.updated_at = datetime.utcnow()

        self.db.commit()

        return {
            "id": product.id,
            "name": product.name,
            "category": {
                "id": category.id,
                "name": category.name
            },
            "supplier": {
                "id": supplier.id,
                "name": supplier.name
            },
            "updated_at": product.updated_at
        }

    async def get_product_details(self, product_id: str) -> Dict:
        """Get detailed product information including category and supplier"""
        product = self.db.query(Product).filter_by(id=product_id).first()
        if not product:
            raise ValueError(f"Product with id {product_id} not found.")

        return {
            "id": product.id,
            "name": product.name,
            "stock_quantity": product.stock_quantity,
            "unit_price": float(product.unit_price),
            "category": {
                "id": product.category.id,
                "name": product.category.name
            } if product.category else None,
            "supplier": {
                "id": product.supplier.id,
                "name": product.supplier.name
            } if product.supplier else None,
            "expiration_date": product.expiration_date,
            "stock_alert_threshold": product.stock_alert_threshold,
            "created_at": product.created_at,
            "updated_at": product.updated_at
        }

    async def list_products(
        self,
        category_id: Optional[str] = None,
        supplier_id: Optional[str] = None,
        low_stock_only: bool = False
    ) -> List[Dict]:
        """List products with optional filtering"""
        query = self.db.query(Product)

        if category_id:
            query = query.filter(Product.category_id == category_id)
        if supplier_id:
            query = query.filter(Product.supplier_id == supplier_id)
        if low_stock_only:
            query = query.filter(Product.stock_quantity <= Product.stock_alert_threshold)

        products = query.all()

        return [{
            "id": p.id,
            "name": p.name,
            "stock_quantity": p.stock_quantity,
            "unit_price": float(p.unit_price),
            "category": {
                "id": p.category.id,
                "name": p.category.name
            } if p.category else None,
            "supplier": {
                "id": p.supplier.id,
                "name": p.supplier.name
            } if p.supplier else None,
            "status": "low_stock" if p.stock_quantity <= p.stock_alert_threshold else "normal"
        } for p in products]
