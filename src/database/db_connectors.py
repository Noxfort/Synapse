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
# File: src/database/db_connectors.py
# Author: Gabriel Moraes
# Date: 2026-09-04
# Description: Concrete database connector (PostgreSQL) implementing IConnectionProvider (Strategy Pattern).

import os
import logging
import threading
from pathlib import Path
from typing import Any, Optional, Dict
from src.database.db_interfaces import IConnectionProvider, ISettingsManager

logger = logging.getLogger("Synapse.DatabaseConnectors")


class PooledConnectionProxy:
    """
    Transparent proxy for a pooled psycopg2 connection.
    Intercepts .close() to return the connection to ThreadedConnectionPool
    instead of terminating the underlying TCP socket.
    """

    def __init__(self, pool: Any, conn: Any):
        self._pool = pool
        self._conn = conn
        self._returned = False

    @property
    def closed(self) -> int:
        if self._returned:
            return 1
        return getattr(self._conn, "closed", 0)

    @property
    def raw_connection(self) -> Any:
        return self._conn

    def close(self) -> None:
        """Returns connection back to pool cleanly with transaction rollback reset."""
        if not self._returned:
            self._returned = True
            if self._pool and self._conn:
                try:
                    is_broken = getattr(self._conn, "closed", 1) != 0
                    if not is_broken:
                        try:
                            # Roll back any dirty transaction before returning to pool
                            if not getattr(self._conn, "autocommit", False):
                                self._conn.rollback()
                        except Exception:
                            is_broken = True
                    self._pool.putconn(self._conn, close=is_broken)
                except Exception as e:
                    logger.debug(f"[PooledConnectionProxy] Error returning connection to pool: {e}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            try:
                self._conn.rollback()
            except Exception:
                pass
        self.close()

    @property
    def autocommit(self) -> bool:
        return getattr(self._conn, "autocommit", False)

    @autocommit.setter
    def autocommit(self, val: bool) -> None:
        setattr(self._conn, "autocommit", val)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._conn, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in ("_pool", "_conn", "_returned"):
            super().__setattr__(name, value)
        else:
            setattr(self._conn, name, value)


class PostgresConnector(IConnectionProvider):
    """
    Dedicated connection provider for PostgreSQL with built-in ThreadedConnectionPool.
    Encapsulates connection parameters, connection pooling, psycopg2 driver execution,
    search_path schema binding, and fatal error circuit breaking.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        user: str = "user_synapse",
        password: str = "synapse123",
        dbname: str = "banco_de_dados_noxfort",
        schema: str = "schema_synapse",
        connect_timeout: int = 5,
        min_connections: int = 1,
        max_connections: int = 20,
        enable_pool: bool = True
    ):
        self.host = host
        self.port = int(port)
        self.user = user
        self.password = password
        self.dbname = dbname
        self.schema = schema
        self.connect_timeout = connect_timeout
        self.min_connections = int(min_connections)
        self.max_connections = int(max_connections)
        self.enable_pool = enable_pool
        self._fatal_db_error = False
        self._pool: Optional[Any] = None
        self._pool_lock = threading.Lock()

    @property
    def db_type(self) -> str:
        return "postgres"

    def _get_or_create_pool(self) -> Optional[Any]:
        if not self.enable_pool or self._fatal_db_error:
            return None

        if self._pool is not None:
            return self._pool

        with self._pool_lock:
            if self._pool is not None:
                return self._pool
            try:
                from psycopg2.pool import ThreadedConnectionPool
                self._pool = ThreadedConnectionPool(
                    minconn=self.min_connections,
                    maxconn=self.max_connections,
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    dbname=self.dbname,
                    options=f"-c search_path={self.schema},public",
                    connect_timeout=self.connect_timeout
                )
                logger.info(
                    f"[POSTGRES_CONNECTOR] ThreadedConnectionPool initialized "
                    f"(min={self.min_connections}, max={self.max_connections}) schema='{self.schema}'."
                )
                return self._pool
            except Exception as e:
                error_msg = str(e).lower()
                if "password authentication failed" in error_msg or "fatal:" in error_msg or "fe_sendauth" in error_msg:
                    self._fatal_db_error = True
                    logger.critical(f"[POSTGRES_CONNECTOR] Fatal PostgreSQL connection error for user '{self.user}' / db '{self.dbname}': {e}")
                else:
                    logger.warning(f"[POSTGRES_CONNECTOR] Could not create connection pool: {e} (will fallback to direct connect)")
                return None

    def get_connection(self) -> Optional[Any]:
        if self._fatal_db_error:
            return None

        # 1. Attempt connection via pool
        pool = self._get_or_create_pool()
        if pool:
            try:
                raw_conn = pool.getconn()
                if getattr(raw_conn, "closed", 0) == 0:
                    return PooledConnectionProxy(pool, raw_conn)
                else:
                    pool.putconn(raw_conn, close=True)
            except Exception as pe:
                logger.debug(f"[POSTGRES_CONNECTOR] Pool getconn notice: {pe}, attempting direct connection.")

        # 2. Fallback to direct connection if pool is disabled, exhausted, or failed
        try:
            import psycopg2
            return psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                dbname=self.dbname,
                options=f"-c search_path={self.schema},public",
                connect_timeout=self.connect_timeout
            )
        except Exception as e:
            error_msg = str(e).lower()
            if "password authentication failed" in error_msg or "fatal:" in error_msg or "fe_sendauth" in error_msg:
                self._fatal_db_error = True
                logger.critical(f"[POSTGRES_CONNECTOR] Fatal PostgreSQL connection error for user '{self.user}' / db '{self.dbname}': {e}")
            else:
                logger.error(f"[POSTGRES_CONNECTOR] Failed to connect to PostgreSQL: {e}")
            return None

    def reset_circuit_breaker(self) -> None:
        self._fatal_db_error = False
        self.close()

    def close(self) -> None:
        """Closes all connections in the pool."""
        with self._pool_lock:
            if self._pool is not None:
                try:
                    self._pool.closeall()
                    logger.info("[POSTGRES_CONNECTOR] ThreadedConnectionPool closed successfully.")
                except Exception as e:
                    logger.warning(f"[POSTGRES_CONNECTOR] Error closing connection pool: {e}")
                finally:
                    self._pool = None


def create_connector(
    custom_config: Optional[Dict[str, Any]] = None,
    settings_mgr: Optional[ISettingsManager] = None,
    db_name: str = "banco_de_dados_noxfort"
) -> IConnectionProvider:
    """
    Factory function producing the appropriate IConnectionProvider implementation.
    Synapse strictly uses PostgreSQL; SQLite is not supported.
    """
    custom = custom_config or {}
    ini_db = settings_mgr.load_database_settings() if settings_mgr else {}

    db_type = (
        custom.get("db_type")
        or os.getenv("SYNAPSE_DB_TYPE")
        or ini_db.get("db_type")
        or "postgres"
    ).lower()

    if db_type == "sqlite":
        raise ValueError("Synapse opera estritamente com PostgreSQL. Suporte ao SQLite foi descontinuado.")

    host = custom.get("host") or custom.get("db_host") or os.getenv("SYNAPSE_DB_HOST") or ini_db.get("host", "localhost")
    port = int(custom.get("port") or custom.get("db_port") or os.getenv("SYNAPSE_DB_PORT") or ini_db.get("port", 5432))
    user = custom.get("user") or custom.get("db_user") or os.getenv("SYNAPSE_DB_USER") or ini_db.get("user", "user_synapse")
    password = custom.get("password") or custom.get("db_password") or os.getenv("SYNAPSE_DB_PASSWORD") or ini_db.get("password", "synapse123")
    dbname = custom.get("dbname") or custom.get("db_name") or os.getenv("SYNAPSE_DB_NAME") or ini_db.get("dbname", "banco_de_dados_noxfort")
    schema = custom.get("schema") or custom.get("db_schema") or os.getenv("SYNAPSE_DB_SCHEMA") or ini_db.get("schema", "schema_synapse")

    min_conn = int(custom.get("min_connections") or os.getenv("SYNAPSE_DB_POOL_MIN") or 1)
    max_conn = int(custom.get("max_connections") or os.getenv("SYNAPSE_DB_POOL_MAX") or 20)
    enable_pool = custom.get("enable_pool", True)
    if isinstance(enable_pool, str):
        enable_pool = enable_pool.lower() not in ("false", "0", "no")

    return PostgresConnector(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=dbname,
        schema=schema,
        min_connections=min_conn,
        max_connections=max_conn,
        enable_pool=enable_pool
    )

