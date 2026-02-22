from fastapi import APIRouter, Depends, HTTPException, status

from sift.api.deps.auth import get_current_admin_user
from sift.config import get_settings
from sift.core.runtime import get_plugin_manager
from sift.db.models import User
from sift.domain.schemas import PluginCapabilityRuntimeCountersOut, PluginStatusOut

router = APIRouter()


@router.get("/status", response_model=list[PluginStatusOut])
async def list_plugin_status(current_user: User = Depends(get_current_admin_user)) -> list[PluginStatusOut]:
    del current_user

    settings = get_settings()
    if not settings.plugin_diagnostics_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plugin diagnostics disabled")

    manager = get_plugin_manager()
    return [
        PluginStatusOut(
            plugin_id=snapshot.plugin_id,
            enabled=snapshot.enabled,
            loaded=snapshot.loaded,
            capabilities=snapshot.capabilities,
            startup_validation_status=snapshot.startup_validation_status,
            last_error=snapshot.last_error,
            unavailable_reason=snapshot.unavailable_reason,
            runtime_counters={
                capability: PluginCapabilityRuntimeCountersOut(**counters)
                for capability, counters in snapshot.runtime_counters.items()
            },
            last_updated_at=snapshot.last_updated_at,
        )
        for snapshot in manager.get_status_snapshots()
    ]
