import sys
import os

from Services.stock_service import StockService
from database import get_db_connection

# Add the parent directory to sys.path to allow imports from sibling directories
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, HTTPException, Query, Path, Body
from fastapi.responses import JSONResponse
from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum
import sqlite3
from contextlib import contextmanager

# Pydantic models for request/response validation
class StockOperation(str, Enum):
    INCREASE = "increase"
    DECREASE = "decrease"

class StockUpdateRequest(BaseModel):
    quantity_change: int = Field(..., gt=0, description="Amount to change the stock by (positive integer)")
    operation: StockOperation = Field(..., description="Operation type: increase or decrease")

    # Updated to use Pydantic V2 configuration
    model_config = {
        "json_schema_extra": {
            "example": {
                "quantity_change": 10,
                "operation": "increase"
            }
        }
    }

router = APIRouter(
    responses={
        404: {"description": "Item not found"},
        500: {"description": "Internal server error"}
    }
)

@contextmanager
def get_stock_service():
    """Context manager for StockService with proper connection management"""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(
                status_code=500,
                detail="Failed to connect to database"
            )
        service = StockService(conn)
        yield service
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize stock service: {str(e)}"
        )
    finally:
        if conn:
            conn.close()

@router.get(
    "/check/low-stock",
    response_model=List[Dict],
    summary="Check Low Stock Products",
    response_description="List of products with low stock levels"
)
async def check_low_stock(
        threshold_override: Optional[int] = Query(
            None,
            description="Optional override for stock alert threshold",
            gt=0
        )
):
    """
    Check for products with low stock levels.

    - Returns a list of products that are below their stock alert threshold
    - Optional threshold override parameter to check against a custom threshold
    - Generates alerts for products below threshold
    """
    try:
        with get_stock_service() as service:
            alerts = await service.check_stock_levels(threshold_override)
            return JSONResponse(
                content={"status": "success", "data": alerts},
                status_code=200
            )
    except sqlite3.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check stock levels: {str(e)}"
        )

@router.get(
    "/check/expired",
    response_model=List[Dict],
    summary="Check Expired Products",
    response_description="List of expired products"
)
async def check_expired_products(
        days_threshold: Optional[int] = Query(
            0,
            description="Days threshold for expiration check",
            ge=0
        )
):
    """
    Check for expired or soon-to-expire products.

    - Returns a list of products that have expired
    - Optional days_threshold parameter to check for products expiring soon
    - Generates alerts for expired products
    """
    try:
        with get_stock_service() as service:
            alerts = await service.check_expired_products(days_threshold)
            return JSONResponse(
                content={"status": "success", "data": alerts},
                status_code=200
            )
    except sqlite3.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check expired products: {str(e)}"
        )

@router.put(
    "/update/{product_id}",
    response_model=Dict,
    summary="Update Product Stock",
    response_description="Updated stock information"
)
async def update_stock(
        product_id: str = Path(..., description="The ID of the product to update"),
        update_data: StockUpdateRequest = Body(...)
):
    """
    Update product stock levels.

    - product_id: ID of the product to update
    - quantity_change: Amount to change the stock by (positive integer)
    - operation: Either 'increase' or 'decrease'

    Returns updated stock information and generates alerts if stock falls below threshold
    """
    try:
        with get_stock_service() as service:
            result = await service.update_stock(
                product_id,
                update_data.quantity_change,
                update_data.operation
            )
            return JSONResponse(
                content={"status": "success", "data": result},
                status_code=200
            )
    except sqlite3.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update stock: {str(e)}"
        )

@router.get(
    "/analytics/product/{product_id}",
    response_model=Dict,
    summary="Get Product Analytics",
    response_description="Detailed product analytics"
)
async def get_product_analytics(
        product_id: str = Path(..., description="The ID of the product to analyze")
):
    """
    Get detailed analytics for a specific product.

    Returns:
    - Product information
    - Current stock levels and thresholds
    - Sales metrics and performance data
    """
    try:
        with get_stock_service() as service:
            analytics = await service.get_product_analytics(product_id)
            return JSONResponse(
                content={"status": "success", "data": analytics},
                status_code=200
            )
    except sqlite3.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get product analytics: {str(e)}"
        )

@router.get(
    "/category/{category_id}",
    response_model=List[Dict],
    summary="Get Category Products",
    response_description="List of products in category"
)
async def get_category_products(
        category_id: str = Path(..., description="The ID of the category"),
        include_inactive: bool = Query(
            False,
            description="Include inactive products in results"
        )
):
    """
    Get all products in a category with their stock levels.

    - Returns list of products with stock information
    - Optional parameter to include inactive products
    - Includes stock status indicators
    """
    try:
        with get_stock_service() as service:
            products = await service.get_category_products(category_id)
            return JSONResponse(
                content={"status": "success", "data": products},
                status_code=200
            )
    except sqlite3.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get category products: {str(e)}"
        )

@router.get(
    "/supplier/{supplier_id}",
    response_model=List[Dict],
    summary="Get Supplier Products",
    response_description="List of products from supplier"
)
async def get_supplier_products(
        supplier_id: str = Path(..., description="The ID of the supplier"),
        include_inactive: bool = Query(
            False,
            description="Include inactive products in results"
        )
):
    """
    Get all products from a supplier with their stock levels.

    - Returns list of products with stock information
    - Optional parameter to include inactive products
    - Includes stock status indicators
    """
    try:
        with get_stock_service() as service:
            products = await service.get_supplier_products(supplier_id)
            return JSONResponse(
                content={"status": "success", "data": products},
                status_code=200
            )
    except sqlite3.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get supplier products: {str(e)}"
        )

@router.get(
    "/summary",
    response_model=Dict,
    summary="Get Stock Summary",
    response_description="Summary of stock status"
)
async def get_stock_summary():
    """
    Get a summary of overall stock status.

    Returns:
    - Total number of products
    - Number of products with low stock
    - Number of expired products
    - Total stock value
    """
    try:
        with get_stock_service() as service:
            low_stock = await service.check_stock_levels()
            expired = await service.check_expired_products()

            return JSONResponse(
                content={
                    "status": "success",
                    "data": {
                        "low_stock_count": len(low_stock),
                        "expired_count": len(expired),
                        "low_stock_items": low_stock,
                        "expired_items": expired
                    }
                },
                status_code=200
            )
    except sqlite3.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get stock summary: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(router, host="0.0.0.0", port=8000)
