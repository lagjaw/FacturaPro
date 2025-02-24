from fastapi import APIRouter, HTTPException, Body, Path, Query, Depends
from typing import List, Dict, Optional
from pydantic import BaseModel, Field, condecimal
from decimal import Decimal
from sqlalchemy.orm import Session
from Services.product_service import ProductService
from database import get_db_connection

router = APIRouter(tags=["products"])


# Pydantic models
class ProductUpdate(BaseModel):
    category_id: str = Field(..., description="ID of the category to assign")
    supplier_id: str = Field(..., description="ID of the supplier to assign")

    model_config = {
        "json_schema_extra": {
            "example": {
                "category_id": "123e4567-e89b-12d3-a456-426614174000",
                "supplier_id": "123e4567-e89b-12d3-a456-426614174001"
            }
        }
    }


class ProductResponse(BaseModel):
    id: str
    name: str
    stock_quantity: int
    unit_price: condecimal(decimal_places=2)
    category: Optional[Dict[str, str]]
    supplier: Optional[Dict[str, str]]
    status: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Product Name",
                "stock_quantity": 100,
                "unit_price": "99.99",
                "category": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "name": "Category Name"
                },
                "supplier": {
                    "id": "123e4567-e89b-12d3-a456-426614174001",
                    "name": "Supplier Name"
                },
                "status": "normal"
            }
        }
    }


def get_product_service(db: Session = Depends(get_db_connection)) -> ProductService:
    return ProductService(db)


@router.put("/products/{product_id}/category-supplier", response_model=Dict)
async def update_product_category_and_supplier(
        product_id: str = Path(..., description="ID of the product to update"),
        update_data: ProductUpdate = Body(...),
        service: ProductService = Depends(get_product_service)
):
    """
    Update a product's category and supplier.

    - Updates category and supplier assignments
    - Validates that all IDs exist
    - Returns updated product details
    """
    try:
        result = await service.update_product_category_and_supplier(
            product_id=product_id,
            category_id=update_data.category_id,
            supplier_id=update_data.supplier_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update product: {str(e)}"
        )


@router.get("/products/{product_id}", response_model=Dict)
async def get_product_details(
        product_id: str = Path(..., description="ID of the product to retrieve"),
        service: ProductService = Depends(get_product_service)
):
    """
    Get detailed product information.

    - Returns complete product details
    - Includes category and supplier information
    - Shows stock status and alerts
    """
    try:
        result = await service.get_product_details(product_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get product details: {str(e)}"
        )


@router.get("/products", response_model=List[ProductResponse])
async def list_products(
        category_id: Optional[str] = Query(None, description="Filter by category ID"),
        supplier_id: Optional[str] = Query(None, description="Filter by supplier ID"),
        low_stock_only: bool = Query(False, description="Show only products with low stock"),
        service: ProductService = Depends(get_product_service)
):
    """
    List products with optional filtering.

    - Can filter by category and supplier
    - Option to show only low stock products
    - Returns list of products with basic information
    - Includes stock status indicators
    """
    try:
        products = await service.list_products(
            category_id=category_id,
            supplier_id=supplier_id,
            low_stock_only=low_stock_only
        )
        return products
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list products: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(router, host="0.0.0.0", port=8000)
