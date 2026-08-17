from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_tenant_id
from app.core.database import get_db
from app.models.tenant import Tenant
from app.schemas.tenant import TenantOut

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("/current", response_model=TenantOut)
def get_current_tenant(tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db)) -> TenantOut:
    """Tenant users can only ever fetch their own tenant -- id comes from the JWT, never the client."""
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant
