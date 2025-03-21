from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Dict, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field
import logging
from database import get_db_session
from Services.client_service import ClientService

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

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Example Company",
                "email": "contact@example.com",
                "phone": "+1234567890",
                "address": "123 Business Street",
                "category": "standard"
            }
        }

# Dependency to get service with db session
async def get_client_service() -> ClientService:
    """Async dependency to get client service with proper session management"""
    async with get_db_session() as session:
        service = ClientService(session)
        yield service

@router.post("/")
async def create_client(
    client: ClientBase,
    service: ClientService = Depends(get_client_service)
):
    """Create a new client"""
    try:
        client_data = client.dict()  # Convert Pydantic model to dictionary
        result = await service.create_client(client_data)
        return {
            "status": "success",
            "message": "Client created successfully",
            "client": result
        }
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
        client_data = client.dict()  # Convert Pydantic model to dictionary
        result = await service.update_client(client_id, client_data)
        if not result:
            raise HTTPException(status_code=404, detail="Client not found")
        return {
            "status": "success",
            "message": "Client updated successfully",
            "client": result
        }
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

@router.get("/key-accounts", response_model=List[Dict])
async def get_key_accounts(
    service: ClientService = Depends(get_client_service)
):
    """Get list of key accounts"""

    try:
        key_accounts = await service.get_key_accounts()
        if not key_accounts:
            logger.info("No key accounts found.")
            raise HTTPException(status_code=404, detail="No key accounts found")
        logger.info(f"Retrieved {len(key_accounts)} key accounts successfully.")
        return {
            "status": "success",
            "data": key_accounts
        }
    
    except HTTPException as http_exc:
        # Re-raise HTTP exceptions to maintain the status code
        logger.error(f"HTTP error occurred: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Error getting key accounts: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get key accounts. Please try again later."
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
    

@router.delete("/{client_id}", response_model=Dict[str, Any])
async def delete_client(
    client_id: str,
    service: ClientService = Depends(get_client_service)
):
    """Delete a client by ID"""
    try:
        success = await service.delete_client(client_id)
        if not success:
            raise HTTPException(status_code=404, detail="Client not found")
        return {
            "status": "success",
            "message": "Client deleted successfully"
        }
    except Exception as e:
        logger.error(f"Error deleting client: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete client: {str(e)}"
        )

@router.get("/search", response_model=List[Dict[str, Any]])
async def search_clients(
    name: Optional[str] = Query(None, description="Client name to search for"),
    email: Optional[str] = Query(None, description="Client email to search for"),
    status: Optional[ClientCategory] = Query(None, description="Client status to filter by"),
    service: ClientService = Depends(get_client_service)
):
    """Search for clients based on name, email, or status"""
    try:
        clients = await service.search_clients(name=name, email=email, status=status)
        return {
            "status": "success",
            "clients": clients
        }
    except Exception as e:
        logger.error(f"Error searching clients: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search clients: {str(e)}"
        )

@router.get("/{client_id}/alerts", response_model=List[Dict[str, Any]])
async def get_client_alerts(
    client_id: str,
    service: ClientService = Depends(get_client_service)
):
    """Get alerts associated with a specific client"""
    try:
        alerts = await service.get_client_alerts(client_id)
        return {
            "status": "success",
            "alerts": alerts
        }
    except Exception as e:
        logger.error(f"Error getting alerts for client {client_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get alerts for client: {str(e)}"
        )