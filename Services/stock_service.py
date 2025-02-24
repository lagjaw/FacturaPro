from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from Models.Alert import Alert
from Models.InvoiceProduct import InvoiceProduct
from Models.Product import Product


class StockService:
    def __init__(self, db: Session):
        self.db = db

    async def check_stock_levels(self) -> List[Dict]:
        """Check for products with low stock levels"""
        low_stock_products = self.db.query(Product).filter(
            Product.stock_quantity <= Product.stock_alert_threshold
        ).all()

        alerts = []
        for product in low_stock_products:
            alert = Alert(
                type='low_stock',
                message=f"Low stock alert for {product.name}: {product.stock_quantity} units remaining",
                related_id=product.id,
                related_type='product',
                status='active'
            )
            self.db.add(alert)
            alerts.append({
                "product_id": product.id,
                "name": product.name,
                "current_stock": product.stock_quantity,
                "threshold": product.stock_alert_threshold
            })

        self.db.commit()
        return alerts

    async def check_expired_products(self) -> List[Dict]:
        """Check for expired or soon-to-expire products"""
        current_date = datetime.now()
        expiring_products = self.db.query(Product).filter(
            Product.expiration_date <= current_date
        ).all()

        alerts = []
        for product in expiring_products:
            alert = Alert(
                type='expiration',
                message=f"Product {product.name} has expired on {product.expiration_date}",
                related_id=product.id,
                related_type='product',
                status='active'
            )
            self.db.add(alert)
            alerts.append({
                "product_id": product.id,
                "name": product.name,
                "expiration_date": product.expiration_date
            })

        self.db.commit()
        return alerts

    async def update_stock(self, product_id: str, quantity_change: int, operation: str) -> Dict:
        """Update product stock levels"""
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError("Product not found")

        if operation == 'decrease':
            if product.stock_quantity < abs(quantity_change):
                raise ValueError("Insufficient stock")
            product.stock_quantity -= abs(quantity_change)
        else:
            product.stock_quantity += abs(quantity_change)

        product.updated_at = datetime.now()

        # Check if stock level is below threshold after update
        if product.stock_quantity <= product.stock_alert_threshold:
            alert = Alert(
                type='low_stock',
                message=f"Stock level alert for {product.name}",
                related_id=product.id,
                related_type='product',
                status='active'
            )
            self.db.add(alert)

        self.db.commit()

        return {
            "product_id": product.id,
            "name": product.name,
            "new_stock_level": product.stock_quantity,
            "operation": operation,
            "quantity_changed": quantity_change
        }

    async def get_product_analytics(self, product_id: str) -> Dict:
        """Get analytics for a specific product"""
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError("Product not found")

        # Get total sales quantity
        total_sales = self.db.query(func.sum(InvoiceProduct.quantity)).filter(
            InvoiceProduct.product_id == product_id
        ).scalar() or 0

        # Get average price
        avg_price = self.db.query(func.avg(InvoiceProduct.unit_price)).filter(
            InvoiceProduct.product_id == product_id
        ).scalar() or 0

        return {
            "product_info": {
                "id": product.id,
                "name": product.name,
                "category": product.category.name if product.category else None,
                "supplier": product.supplier.name if product.supplier else None
            },
            "stock_info": {
                "current_stock": product.stock_quantity,
                "alert_threshold": product.stock_alert_threshold,
                "expiration_date": product.expiration_date
            },
            "sales_metrics": {
                "total_units_sold": total_sales,
                "average_price": float(avg_price),
                "total_revenue": float(total_sales * avg_price)
            }
        }

    async def get_category_products(self, category_id: str) -> List[Dict]:
        """Get all products in a category with their stock levels"""
        products = self.db.query(Product).filter(
            Product.category_id == category_id
        ).all()

        return [{
            "id": p.id,
            "name": p.name,
            "stock_quantity": p.stock_quantity,
            "unit_price": float(p.unit_price),
            "status": "low_stock" if p.stock_quantity <= p.stock_alert_threshold else "normal"
        } for p in products]

    async def get_supplier_products(self, supplier_id: str) -> List[Dict]:
        """Get all products from a supplier with their stock levels"""
        products = self.db.query(Product).filter(
            Product.supplier_id == supplier_id
        ).all()

        return [{
            "id": p.id,
            "name": p.name,
            "stock_quantity": p.stock_quantity,
            "unit_price": float(p.unit_price),
            "status": "low_stock" if p.stock_quantity <= p.stock_alert_threshold else "normal"
        } for p in products]
