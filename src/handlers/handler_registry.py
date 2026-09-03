# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# File: src/handlers/handler_registry.py
# Author: Gabriel Moraes
# Date: 2026-08-31

"""
Handler Registration Registry (SOLID: SRP & Composition Root).

Encapsulates the wiring and registration of all command handlers into the IPC Command Router.
"""

from typing import Any, Callable, Optional

from src.ipc.command_router import IpcCommandRouter
from src.handlers.system_handler import SystemCommandHandler
from src.handlers.map_handler import MapCommandHandler
from src.handlers.source_handler import SourceCommandHandler
from src.handlers.database_handler import DatabaseCommandHandler
from src.handlers.dialog_handler import SystemDialogHandler
from src.infrastructure.dialog_service import NativeDialogService
from src.infrastructure.network_service import NetworkService
from src.services.data_inspection_service import DataInspectionService


def register_default_command_handlers(
    router: IpcCommandRouter,
    controller: Any,
    app_state: Any,
    event_emitter: Callable[[str, Any], None],
    on_shutdown: Optional[Callable[[], None]] = None,
    map_service: Optional[Any] = None,
    dialog_service: Optional[NativeDialogService] = None,
    network_service: Optional[NetworkService] = None,
    data_inspection_service: Optional[DataInspectionService] = None,
    importer_factory: Optional[Callable[[Any], Any]] = None,
    postgres_worker_factory: Optional[Callable[[], Any]] = None,
    postgres_manager_factory: Optional[Callable[[], Any]] = None,
) -> None:
    """
    Composition helper that registers all standard command handlers into the router.
    """
    system_handler = SystemCommandHandler(controller, on_shutdown=on_shutdown)
    map_handler = MapCommandHandler(app_state, map_service=map_service)
    source_handler = SourceCommandHandler(app_state)
    db_handler = DatabaseCommandHandler(
        controller,
        event_emitter,
        data_inspection_service=data_inspection_service,
        importer_factory=importer_factory,
        postgres_worker_factory=postgres_worker_factory,
        postgres_manager_factory=postgres_manager_factory,
    )
    dialog_handler = SystemDialogHandler(
        dialog_service=dialog_service, network_service=network_service
    )

    # 1. System Actions
    router.register("ping", system_handler.handle_ping)
    router.register("get_system_status", system_handler.handle_get_system_status)
    router.register("start_optimization", system_handler.handle_start_optimization)
    router.register("stop_optimization", system_handler.handle_stop_optimization)
    router.register("start_offline_bootstrap", system_handler.handle_start_offline_bootstrap)
    router.register("stop_offline_bootstrap", system_handler.handle_stop_offline_bootstrap)
    router.register("start_online_operation", system_handler.handle_start_online_operation)
    router.register("stop_online_operation", system_handler.handle_stop_online_operation)
    router.register("explain_buffer", system_handler.handle_explain_buffer)
    router.register("explain_local", system_handler.handle_explain_local)
    router.register("explain_global", system_handler.handle_explain_global)
    router.register("hot_swap_model", system_handler.handle_hot_swap_model)
    router.register("get_process_health", system_handler.handle_get_process_health)
    router.register("shutdown", system_handler.handle_shutdown)


    # 2. Map Actions
    router.register("load_map", map_handler.handle_load_map)
    router.register("get_topology", map_handler.handle_get_topology)

    # 3. Source Actions
    router.register("get_sources", source_handler.handle_get_sources)
    router.register("add_source", source_handler.handle_add_source)
    router.register("associate_source", source_handler.handle_associate_source)
    router.register("toggle_origin", source_handler.handle_toggle_origin)
    router.register("remove_source", source_handler.handle_remove_source)

    # 4. Database Actions
    router.register("inspect_parquet", db_handler.handle_inspect_parquet)
    router.register("import_parquet", db_handler.handle_import_parquet)
    router.register("test_db_connection", db_handler.handle_test_db_connection)
    router.register("initialize_db", db_handler.handle_initialize_db)
    router.register("get_database_config", db_handler.handle_get_database_config)
    router.register("disconnect_db", db_handler.handle_disconnect_db)
    router.register("get_telemetry_config", db_handler.handle_get_telemetry_config)
    router.register("save_telemetry_config", db_handler.handle_save_telemetry_config)

    # 5. Dialog and Diagnostics
    router.register("pick_file", dialog_handler.handle_pick_file)
    router.register("get_network_info", dialog_handler.handle_get_network_info)


__all__ = ["register_default_command_handlers"]
