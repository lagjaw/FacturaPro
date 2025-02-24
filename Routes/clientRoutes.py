from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Dict, Optional, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import logging
from database import get_db_session
from Services.client_service import ClientService
import sqlite3

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter(tags=["clients"])

class ClientCategory(str, Enum):
    STANDARD = "standard"
    KEY_ACCOUNT = "key_account"
    INACTIVE = "inactive"

class ClientBase(BaseModel):
    name: str = Field(..., description="Client name")
    email: str = Field(..., description="Client email")
    phone: str = Field(..., description="Client phone number")
    address: str = Field(..., description="Client address")
    category: ClientCategory = Field(default=ClientCategory.STANDARD, description="Client category")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Example Company",
                "email": "contact@example.com",
                "phone": "+1234567890",
                "address": "123 Business Street",
                "category": "standard"
            }
        }
    }

# Dependency to get service with db session
async def get_client_service():
    """Async dependency to get client service with proper session management"""
    session = None
    try:
        session = get_db_session()
        service = ClientService(session)
        yield service
    except Exception as e:
        logger.error(f"Error creating client service: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize client service: {str(e)}"
        )
    finally:
        if session:
            try:
                session.close()
            except Exception as e:
                logger.error(f"Error closing database session: {e}")

@router.post("/")
async def create_client(
    client: ClientBase,
    service: ClientService = Depends(get_client_service)
):
    """Create a new client"""
    try:
        client_data = client.model_dump()
        result = await service.create_client(client_data)
        return {
            "status": "success",
            "message": "Client created successfully",
            "client": result
        }
    except sqlite3.IntegrityError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Client with this email already exists: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error creating client: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create client: {str(e)}"
        )

@router.put("/{client_id}")
async def update_client(
    client_id: str,
    client: ClientBase,
    service: ClientService = Depends(get_client_service)
):
    """Update client information"""
    try:
        client_data = client.model_dump()
        result = await service.update_client(client_id, client_data)
        if not result:
            raise HTTPException(status_code=404, detail="Client not found")
        return {
            "status": "success",
            "message": "Client updated successfully",
            "client": result
        }
    except sqlite3.IntegrityError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Update violates unique constraints: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error updating client: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update client: {str(e)}"
        )

@router.get("/")
async def get_all_clients(
    service: ClientService = Depends(get_client_service)
):
    """Get list of all clients with their metrics"""
    try:
        return await service.get_client_status()
    except Exception as e:
        logger.error(f"Error getting clients: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get clients: {str(e)}"
        )

@router.get("/{client_id}")
async def get_client(
    client_id: str,
    service: ClientService = Depends(get_client_service)
):
    """Get specific client details"""
    try:
        client = await service.get_client_by_id(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        return client
    except Exception as e:
        logger.error(f"Error getting client: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get client: {str(e)}"
        )

@router.put("/{client_id}/status")
async def update_client_status(
    client_id: str,
    status: ClientCategory = Query(..., description="New status (standard, key_account, inactive)"),
    service: ClientService = Depends(get_client_service)
):
    """Update client status"""
    try:
        success = await service.update_client_status(client_id, status.value)
        if not success:
            raise HTTPException(status_code=404, detail="Client not found")
        return {
            "status": "success",
            "message": "Client status updated successfully",
            "new_status": status.value
        }
    except Exception as e:
        logger.error(f"Error updating client status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update client status: {str(e)}"
        )

@router.get("/{client_id}/revenue")
async def get_client_revenue(
    client_id: str,
    service: ClientService = Depends(get_client_service)
):
    """Get client's semi-annual revenue"""
    try:
        revenue_data = await service.get_semiannual_revenue(client_id)
        return revenue_data
    except Exception as e:
        logger.error(f"Error getting client revenue: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get client revenue: {str(e)}"
        )

@router.get("/key-accounts")
async def get_key_accounts(
    service: ClientService = Depends(get_client_service)
):
    """Get list of key accounts"""
    try:
        return await service.get_key_accounts()
    except Exception as e:
        logger.error(f"Error getting key accounts: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get key accounts: {str(e)}"
        )

@router.get("/{client_id}/dashboard")
async def get_client_dashboard(
    client_id: str,
    service: ClientService = Depends(get_client_service)
):
    """Get complete client dashboard"""
    try:
        dashboard = await service.create_client_dashboard(client_id)
        if not dashboard:
            raise HTTPException(status_code=404, detail="Client not found")
        return dashboard
    except Exception as e:
        logger.error(f"Error getting client dashboard: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get client dashboard: {str(e)}"
        )

@router.get("/{client_id}/payment-history")
async def get_client_payment_history(
    client_id: str,
    service: ClientService = Depends(get_client_service)
):
    """Get client's payment history"""
    try:
        return await service.get_payment_history(client_id)
    except Exception as e:
        logger.error(f"Error getting payment history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get payment history: {str(e)}"
        )

@router.get("/{client_id}/payment-delays")
async def get_client_payment_delays(
    client_id: str,
    service: ClientService = Depends(get_client_service)
):
    """Get client's payment delay analysis"""
    try:
        return await service.analyze_payment_delays(client_id)
    except Exception as e:
        logger.error(f"Error analyzing payment delays: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze payment delays: {str(e)}"
        )
