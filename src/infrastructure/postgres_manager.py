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
# File: src/infrastructure/postgres_manager.py
# Author: Gabriel Moraes
# Date: 2025-11-26

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QThread
from src.utils.logging_setup import get_logger

logger = get_logger("PostgresManager")

class PostgresWorker(QObject):
    """
    Worker responsible for executing blocking SQL operations in a background thread.
    """
    
    # Signals
    connection_checked = pyqtSignal(bool, str)  # (Success, Message)
    setup_finished = pyqtSignal(bool, str)      # (Success, Message)
    
    def __init__(self):
        super().__init__()

    @pyqtSlot(dict)
    def do_check_connection(self, config: dict):
        """
        Attempts to connect to the specific application database.
        """
        try:
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
            
            # Save validated settings to config/settings.ini
            try:
                from src.database.db_settings_manager import DatabaseSettingsManager
                pg_cfg = dict(config)
                pg_cfg["db_type"] = "postgres"
                pg_cfg["schema"] = schema
                settings_mgr = DatabaseSettingsManager()
                settings_mgr.save_database_settings(pg_cfg)
            except Exception as se:
                logger.warning(f"Could not persist settings.ini: {se}")

            self.connection_checked.emit(True, f"Conexão bem-sucedida ao schema '{schema}'.")
        except Exception as e:
            # Clean up error message
            msg = str(e).split('\n')[0]
            self.connection_checked.emit(False, f"Connection failed: {msg}")

    @pyqtSlot(str, dict)
    def do_setup_database(self, root_password: str, target_config: dict):
        """
        Connects as 'postgres' (root) to create the application User and Database.
        This automates the "Step 3" of installation.
        """
        conn = None
        try:
            # 1. Connect to maintenance DB 'postgres' as root
            conn = psycopg2.connect(
                host=target_config.get("host", "localhost"),
                port=target_config.get("port", 5432),
                database="postgres",
                user="postgres",
                password=root_password,
                connect_timeout=5
            )
            
            # Necessary for CREATE DATABASE
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            target_user = target_config.get("user", "user_synapse")
            target_pass = target_config.get("password", "synapse123")
            target_db = target_config.get("dbname", "banco_de_dados_noxfort")
            target_schema = target_config.get("schema", "schema_synapse")

            # 2. Check if User exists, create if not
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (target_user,))
            if not cursor.fetchone():
                cmd_user = sql.SQL("CREATE USER {} WITH ENCRYPTED PASSWORD %s").format(
                    sql.Identifier(target_user)
                )
                cursor.execute(cmd_user, (target_pass,))
                logger.info(f"User '{target_user}' created.")
            else:
                logger.info(f"User '{target_user}' already exists.")

            # 3. Check if Database exists, create if not
            cursor.execute("SELECT 1 FROM pg_database WHERE datname=%s", (target_db,))
            if not cursor.fetchone():
                cmd_db = sql.SQL("CREATE DATABASE {} OWNER {}").format(
                    sql.Identifier(target_db),
                    sql.Identifier(target_user)
                )
                cursor.execute(cmd_db)
                logger.info(f"Database '{target_db}' created.")
            else:
                logger.info(f"Database '{target_db}' already exists.")

            cursor.close()
            conn.close()
            conn = None

            # 4. Connect to target database as root to configure schema and permissions
            conn_target = psycopg2.connect(
                host=target_config.get("host", "localhost"),
                port=target_config.get("port", 5432),
                database=target_db,
                user="postgres",
                password=root_password,
                connect_timeout=5
            )
            conn_target.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cur_target = conn_target.cursor()

            # Grant DB permissions
            cur_target.execute(
                sql.SQL("GRANT ALL PRIVILEGES ON DATABASE {} TO {}").format(
                    sql.Identifier(target_db),
                    sql.Identifier(target_user)
                )
            )

            # Create dedicated schema and grant authorization
            cmd_schema = sql.SQL("CREATE SCHEMA IF NOT EXISTS {} AUTHORIZATION {}").format(
                sql.Identifier(target_schema),
                sql.Identifier(target_user)
            )
            cur_target.execute(cmd_schema)

            cur_target.execute(
                sql.SQL("GRANT ALL ON SCHEMA {} TO {}").format(
                    sql.Identifier(target_schema),
                    sql.Identifier(target_user)
                )
            )
            logger.info(f"Schema '{target_schema}' provisioned for user '{target_user}'.")

            cur_target.close()
            conn_target.close()

            # 5. Initialize Tables & Indexes inside target_schema via DatabaseEngine
            try:
                from src.database.db_engine import DatabaseEngine
                pg_cfg = dict(target_config)
                pg_cfg["db_type"] = "postgres"
                pg_cfg["user"] = target_user
                pg_cfg["password"] = target_pass
                pg_cfg["dbname"] = target_db
                pg_cfg["schema"] = target_schema
                engine = DatabaseEngine(custom_config=pg_cfg)
                engine.save_settings_to_ini(pg_cfg)
                logger.info(f"Tables and indexes initialized in schema '{target_schema}'.")
            except Exception as se:
                logger.warning(f"Schema tables initialization notice: {se}")

            self.setup_finished.emit(
                True,
                f"Usuário '{target_user}', schema '{target_schema}' e tabelas criados com sucesso!"
            )

        except Exception as e:
            if conn: conn.close()
            self.setup_finished.emit(False, f"Setup failed: {str(e)}")


class PostgresManager(QObject):
    """
    Controller interface for PostgreSQL operations.
    Manages the worker thread lifecycle.
    """
    
    # Proxy signals for UI
    status_received = pyqtSignal(bool, str)
    setup_complete = pyqtSignal(bool, str)
    
    # Internal signals to talk to worker
    _cmd_check = pyqtSignal(dict)
    _cmd_setup = pyqtSignal(str, dict)

    def __init__(self):
        super().__init__()
        self.thread = QThread()
        self.worker = PostgresWorker()
        self.worker.moveToThread(self.thread)
        
        # Wiring
        self._cmd_check.connect(self.worker.do_check_connection)
        self._cmd_setup.connect(self.worker.do_setup_database)
        
        self.worker.connection_checked.connect(self.status_received)
        self.worker.setup_finished.connect(self.setup_complete)
        
        self.thread.start()

    def check_connection(self, config: dict):
        """Non-blocking check."""
        self._cmd_check.emit(config)

    def initialize_database(self, root_pass: str, target_config: dict):
        """Non-blocking setup (Create Role/DB)."""
        self._cmd_setup.emit(root_pass, target_config)

    def stop(self):
        self.thread.quit()
        self.thread.wait()
