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
# File: src/handlers/database_handler.py
# Author: Gabriel Moraes
# Date: 2026-08-30

"""
Database & Analytics Storage Command Handler (SOLID: SRP & DIP).

Translates IPC actions related to Parquet schema inspection, asynchronous Parquet imports,
and PostgreSQL database connection testing/initialization.
All external workers, importers, and managers are injected via factories.
"""

import os
import threading
from typing import Any, Callable, Optional

from src.ipc.ipc_protocol import IpcMessage
from src.ipc.command_router import Responder
from src.services.data_inspection_service import DataInspectionService


class DatabaseCommandHandler:
    """Handles parquet inspection, database imports, and PostgreSQL operations."""

    def __init__(
        self,
        controller: Any,
        event_emitter: Callable[[str, Any], None],
        data_inspection_service: Optional[DataInspectionService] = None,
        importer_factory: Optional[Callable[[Any], Any]] = None,
        postgres_worker_factory: Optional[Callable[[], Any]] = None,
        postgres_manager_factory: Optional[Callable[[], Any]] = None,
    ):
        self.controller = controller
        self.event_emitter = event_emitter
        self.data_inspection_service = data_inspection_service or DataInspectionService()
        self._importer_factory = importer_factory or self._default_importer_factory
        self._worker_factory = postgres_worker_factory or self._default_worker_factory
        self._manager_factory = postgres_manager_factory or self._default_manager_factory

    @staticmethod
    def _default_importer_factory(storage: Any) -> Any:
        from src.services.database_importer import DatabaseImporter
        return DatabaseImporter(storage)

    @staticmethod
    def _default_worker_factory() -> Any:
        from src.infrastructure.postgres_manager import PostgresWorker
        return PostgresWorker()

    @staticmethod
    def _default_manager_factory() -> Any:
        from src.infrastructure.postgres_manager import PostgresManager
        return PostgresManager()

    def handle_inspect_parquet(self, msg: IpcMessage, responder: Responder) -> None:
        path = msg.payload.get("path", "")
        try:
            info = self.data_inspection_service.inspect_parquet(path)
            responder(True, info)
        except Exception as err:
            responder(False, error=str(err))

    def handle_import_parquet(self, msg: IpcMessage, responder: Responder) -> None:
        raw_path = msg.payload.get("path", "")
        path = os.path.expanduser(raw_path.strip().strip('"\'')) if raw_path else ""

        if not path or not os.path.exists(path):
            responder(False, error=f"Arquivo Parquet não encontrado: {path}")
            return

        storage = getattr(self.controller, "storage", None)
        importer = self._importer_factory(storage)

        def _on_progress(p: int):
            self.event_emitter("import_progress", {"progress": p})

        def _on_log(m: str):
            self.event_emitter("log_message", {"message": m, "level": "INFO"})

        def _on_finished(ok: bool, m: str):
            if ok:
                try:
                    app_state = getattr(self.controller, "app_state", None)
                    if app_state is not None:
                        from src.domain.entities import DataSource, SourceType, SourceStatus
                        from src.managers.storage_manager import StorageManager
                        sm = storage or StorageManager()
                        target_file = os.path.join(sm.get_datalake_base_path(), "base_v1.parquet")
                        final_path = target_file if os.path.exists(target_file) else path
                        
                        src = DataSource(
                            id="historical_base",
                            name="Base Histórica Parquet",
                            source_type=SourceType.PARQUET,
                            connection_string=final_path,
                            is_local=False,
                            status=SourceStatus.ACTIVE,
                        )
                        app_state.add_data_source(src)
                except Exception:
                    pass
            self.event_emitter("import_finished", {"success": ok, "message": m})

        importer.on_progress = _on_progress
        importer.on_log = _on_log
        importer.on_finished = _on_finished

        if hasattr(importer, "progress_update"):
            try:
                importer.progress_update.connect(_on_progress)
            except Exception:
                pass
        if hasattr(importer, "log_message"):
            try:
                importer.log_message.connect(_on_log)
            except Exception:
                pass
        if hasattr(importer, "import_finished"):
            try:
                importer.import_finished.connect(lambda ok, m: _on_finished(ok, m))
            except Exception:
                pass

        if hasattr(importer, "execute_import"):
            threading.Thread(target=importer.execute_import, args=(path,), daemon=True).start()

        responder(True, {"status": "import_started", "path": path})

    def handle_test_db_connection(self, msg: IpcMessage, responder: Responder) -> None:
        config = msg.payload.get("config", {})

        def _run():
            try:
                worker = self._worker_factory()
                # Run synchronously — do_check_connection emits a signal,
                # but we catch the result directly here instead.
                import psycopg2
                schema = config.get("schema", "schema_synapse")
                conn = psycopg2.connect(
                    host=config.get("host", "localhost"),
                    port=config.get("port", 5432),
                    database=config.get("dbname", "banco_de_dados_noxfort"),
                    user=config.get("user", "user_synapse"),
                    password=config.get("password", "synapse123"),
                    options=f"-c search_path={schema},public",
                    connect_timeout=3
                )
                conn.close()

                # Persist settings
                try:
                    from src.database.db_engine import DatabaseEngine
                    pg_cfg = dict(config)
                    pg_cfg["db_type"] = "postgres"
                    pg_cfg["schema"] = schema
                    pg_cfg["connected"] = "true"
                    engine = DatabaseEngine(custom_config=pg_cfg)
                    engine.save_settings_to_ini(pg_cfg)
                except Exception:
                    pass

                responder(True, {"message": f"Conexão bem-sucedida ao schema '{schema}'."})
            except Exception as e:
                msg_err = str(e).split('\n')[0]
                responder(False, error=f"Falha na conexão: {msg_err}")

        threading.Thread(target=_run, daemon=True).start()

    def handle_initialize_db(self, msg: IpcMessage, responder: Responder) -> None:
        root_pass = msg.payload.get("root_password", "")
        config = msg.payload.get("config", {})

        def _run():
            try:
                import psycopg2
                from psycopg2 import sql as pg_sql
                from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT as AUTOCOMMIT

                host = config.get("host", "localhost")
                port = config.get("port", 5432)
                target_user = config.get("user", "user_synapse")
                target_pass = config.get("password", "synapse123")
                target_db = config.get("dbname", "banco_de_dados_noxfort")
                target_schema = config.get("schema", "schema_synapse")

                # 1. Connect as postgres root
                conn = psycopg2.connect(
                    host=host, port=port, database="postgres",
                    user="postgres", password=root_pass, connect_timeout=5
                )
                conn.set_isolation_level(AUTOCOMMIT)
                cursor = conn.cursor()

                # 2. Create user if not exists
                cursor.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (target_user,))
                if not cursor.fetchone():
                    cursor.execute(
                        pg_sql.SQL("CREATE USER {} WITH ENCRYPTED PASSWORD %s").format(
                            pg_sql.Identifier(target_user)
                        ), (target_pass,)
                    )

                # 3. Create database if not exists
                cursor.execute("SELECT 1 FROM pg_database WHERE datname=%s", (target_db,))
                if not cursor.fetchone():
                    cursor.execute(
                        pg_sql.SQL("CREATE DATABASE {} OWNER {}").format(
                            pg_sql.Identifier(target_db),
                            pg_sql.Identifier(target_user)
                        )
                    )

                cursor.close()
                conn.close()

                # 4. Connect to target DB as root to provision schema
                conn2 = psycopg2.connect(
                    host=host, port=port, database=target_db,
                    user="postgres", password=root_pass, connect_timeout=5
                )
                conn2.set_isolation_level(AUTOCOMMIT)
                cur2 = conn2.cursor()

                cur2.execute(
                    pg_sql.SQL("GRANT ALL PRIVILEGES ON DATABASE {} TO {}").format(
                        pg_sql.Identifier(target_db), pg_sql.Identifier(target_user)
                    )
                )
                cur2.execute(
                    pg_sql.SQL("CREATE SCHEMA IF NOT EXISTS {} AUTHORIZATION {}").format(
                        pg_sql.Identifier(target_schema), pg_sql.Identifier(target_user)
                    )
                )
                cur2.execute(
                    pg_sql.SQL("GRANT ALL ON SCHEMA {} TO {}").format(
                        pg_sql.Identifier(target_schema), pg_sql.Identifier(target_user)
                    )
                )
                cur2.close()
                conn2.close()

                # 5. Initialize tables via DatabaseEngine
                try:
                    from src.database.db_engine import DatabaseEngine
                    pg_cfg = dict(config)
                    pg_cfg["db_type"] = "postgres"
                    pg_cfg["user"] = target_user
                    pg_cfg["password"] = target_pass
                    pg_cfg["dbname"] = target_db
                    pg_cfg["schema"] = target_schema
                    pg_cfg["connected"] = "true"
                    pg_cfg["setup_done"] = "true"
                    engine = DatabaseEngine(custom_config=pg_cfg)
                    engine.save_settings_to_ini(pg_cfg)
                except Exception:
                    pass

                responder(True, {
                    "message": f"Usuário '{target_user}', schema '{target_schema}' e tabelas criados com sucesso!"
                })
            except Exception as e:
                msg_err = str(e).split('\n')[0]
                responder(False, error=f"Falha na inicialização: {msg_err}")

        threading.Thread(target=_run, daemon=True).start()

    def handle_get_database_config(self, msg: IpcMessage, responder: Responder) -> None:
        try:
            from src.database.db_engine import DatabaseEngine
            engine = DatabaseEngine()
            cfg = engine.load_database_settings()
            responder(True, cfg)
        except Exception as e:
            responder(False, error=str(e))

    def handle_disconnect_db(self, msg: IpcMessage, responder: Responder) -> None:
        try:
            from src.database.db_engine import DatabaseEngine
            engine = DatabaseEngine()
            engine.save_settings_to_ini({"connected": "false"})
            responder(True, {"message": "Desconectado com sucesso."})
        except Exception as e:
            responder(False, error=str(e))

    def handle_get_telemetry_config(self, msg: IpcMessage, responder: Responder) -> None:
        try:
            from src.database.db_engine import DatabaseEngine
            engine = DatabaseEngine()
            cfg = engine.load_telemetry_settings()
            responder(True, cfg)
        except Exception as e:
            responder(False, error=str(e))

    def handle_save_telemetry_config(self, msg: IpcMessage, responder: Responder) -> None:
        try:
            from src.database.db_engine import DatabaseEngine
            engine = DatabaseEngine()
            payload = msg.payload or {}
            ip = payload.get("ip", "localhost")
            host = payload.get("host", "localhost")
            port = int(payload.get("port", 1883))
            connected = bool(payload.get("connected", False))
            engine.save_telemetry_settings(ip, host, port, connected)
            responder(True, {"message": "Configurações de telemetria salvas com sucesso."})
        except Exception as e:
            responder(False, error=str(e))
