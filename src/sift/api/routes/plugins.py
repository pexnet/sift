from fastapi import APIRouter, Depends, HTTPException, status

from sift.api.deps.auth import get_current_admin_user, get_current_user
from sift.config import get_settings
from sift.core.runtime import get_plugin_manager
from sift.db.models import User
from sift.domain.schemas import PluginAreaOut, PluginCapabilityRuntimeCountersOut, PluginStatusOut
from sift.plugins.registry import load_plugin_registry

router = APIRouter()


@router.get("/areas", response_model=list[PluginAreaOut])
async def list_plugin_areas(current_user: User = Depends(get_current_user)) -> list[PluginAreaOut]:
    del current_user

    settings = get_settings()
    manager = get_plugin_manager()
    status_by_id = {snapshot.plugin_id: snapshot for snapshot in manager.get_status_snapshots()}
    registry = load_plugin_registry(settings.plugin_registry_path)

    areas: list[PluginAreaOut] = []
    for entry in registry.plugins:
        if not entry.enabled:
            continue
        if "workspace_area" not in entry.capabilities:
            continue
        if entry.ui is None or entry.ui.area is None:
            continue
        status_snapshot = status_by_id.get(entry.id)
        if status_snapshot is None or not status_snapshot.loaded:
            continue

        ui_area = entry.ui.area
        areas.append(
            PluginAreaOut(
                id=entry.id,
                title=ui_area.title,
                icon=ui_area.icon,
                order=ui_area.order,
                route_key=ui_area.route_key or entry.id,
            )
        )

    return sorted(areas, key=lambda item: (item.order, item.title.lower(), item.id))


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
