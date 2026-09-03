# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# File: src/database/db_engine.py
# Author: Gabriel Moraes
# Date: 2026-09-02

import os
import json
import sqlite3
import logging
import configparser
from typing import Any, Optional, Dict
from pathlib import Path

logger = logging.getLogger("Synapse.DatabaseEngine")


class DatabaseEngine:
    """
    Central engine for managing database connections (PostgreSQL or SQLite).
    Responsible for connecting, initializing the schema dynamically from 
    config/synapse_schema_queries.json, handling automated migrations, and 
    providing active database connections with fatal error circuit breaking.
    """

    def __init__(self, db_name: str = "synapse_data.db", custom_config: Optional[Dict[str, Any]] = None):
        self._fatal_db_error = False
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    def _get_ini_val(self, section: str, key1: str, key2: Optional[str] = None, fallback: str = "") -> str:
        if self.config_parser.has_section(section):
            if self.config_parser.has_option(section, key1):
                return self.config_parser.get(section, key1)
            if key2 and self.config_parser.has_option(section, key2):
                return self.config_parser.get(section, key2)
        return fallback

    def __init__(self, db_name: str = "synapse_data.db", custom_config: Optional[Dict[str, Any]] = None):
        self._fatal_db_error = False
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.settings_path = os.path.join(self.project_root, "config", "settings.ini")
        
        # 1. Parse settings from INI, Environment Variables, or Defaults
        self.config_parser = configparser.ConfigParser()
        if os.path.exists(self.settings_path):
            self.config_parser.read(self.settings_path)
            
        custom = custom_config or {}
        self.db_type = custom.get("db_type") or os.getenv("SYNAPSE_DB_TYPE") or self._get_ini_val("DATABASE", "db_type", fallback="postgres")
        self.db_host = custom.get("host") or custom.get("db_host") or os.getenv("SYNAPSE_DB_HOST") or self._get_ini_val("DATABASE", "host", "db_host", fallback="localhost")
        self.db_port = str(custom.get("port") or custom.get("db_port") or os.getenv("SYNAPSE_DB_PORT") or self._get_ini_val("DATABASE", "port", "db_port", fallback="5432"))
        self.db_user = custom.get("user") or custom.get("db_user") or os.getenv("SYNAPSE_DB_USER") or self._get_ini_val("DATABASE", "user", "db_user", fallback="user_synapse")
        self.db_password = custom.get("password") or custom.get("db_password") or os.getenv("SYNAPSE_DB_PASSWORD") or self._get_ini_val("DATABASE", "password", "db_password", fallback="synapse123")
        self.db_name_pg = custom.get("dbname") or custom.get("db_name") or os.getenv("SYNAPSE_DB_NAME") or self._get_ini_val("DATABASE", "dbname", "db_name", fallback="banco_de_dados_noxfort")
        self.db_schema = custom.get("schema") or custom.get("db_schema") or os.getenv("SYNAPSE_DB_SCHEMA") or self._get_ini_val("DATABASE", "schema", "db_schema", fallback="schema_synapse")

        # 2. SQLite local path
        home = Path.home()
        docs = home / "Documentos" if (home / "Documentos").exists() else home / "Documents"
        db_dir = docs / "Synapse" / "data" / "db"
        try:
            os.makedirs(db_dir, exist_ok=True)
            self.db_path = str(db_dir / db_name)
        except Exception:
            local_fallback = Path(self.project_root) / "data" / "db"
            local_fallback.mkdir(parents=True, exist_ok=True)
            self.db_path = str(local_fallback / db_name)

        self._initialize_db()
        logger.info(f"[DB_ENGINE] Central Engine Initialized. DB: {self.db_type}")

    def load_database_settings(self) -> Dict[str, Any]:
        """Loads normalized database settings from config/settings.ini."""
        if os.path.exists(self.settings_path):
            self.config_parser.read(self.settings_path)
        return {
            "db_type": self._get_ini_val("DATABASE", "db_type", fallback="postgres"),
            "host": self._get_ini_val("DATABASE", "host", "db_host", fallback="localhost"),
            "port": int(self._get_ini_val("DATABASE", "port", "db_port", fallback="5432")),
            "user": self._get_ini_val("DATABASE", "user", "db_user", fallback="user_synapse"),
            "password": self._get_ini_val("DATABASE", "password", "db_password", fallback="synapse123"),
            "dbname": self._get_ini_val("DATABASE", "dbname", "db_name", fallback="banco_de_dados_noxfort"),
            "schema": self._get_ini_val("DATABASE", "schema", "db_schema", fallback="schema_synapse"),
            "connected": self._get_ini_val("DATABASE", "connected", fallback="false").lower() in ("true", "1", "yes"),
            "setup_done": self._get_ini_val("DATABASE", "setup_done", fallback="false").lower() in ("true", "1", "yes"),
        }

    def load_telemetry_settings(self) -> Dict[str, Any]:
        """Loads telemetry settings from config/settings.ini."""
        if os.path.exists(self.settings_path):
            self.config_parser.read(self.settings_path)
        ip = self._get_ini_val("TELEMETRY", "ip", fallback="localhost")
        host = self._get_ini_val("TELEMETRY", "host", fallback="localhost")
        port = int(self._get_ini_val("TELEMETRY", "port", fallback="1883"))
        connected = self._get_ini_val("TELEMETRY", "connected", fallback="false").lower() in ("true", "1", "yes")
        return {
            "ip": ip,
            "host": host,
            "port": port,
            "connected": connected,
        }

    def save_telemetry_settings(self, ip: str, host: str, port: int, connected: bool):
        """Saves telemetry settings to config/settings.ini."""
        try:
            if not self.config_parser.has_section("TELEMETRY"):
                self.config_parser.add_section("TELEMETRY")
            self.config_parser.set("TELEMETRY", "ip", str(ip))
            self.config_parser.set("TELEMETRY", "host", str(host))
            self.config_parser.set("TELEMETRY", "port", str(port))
            self.config_parser.set("TELEMETRY", "connected", "true" if connected else "false")
            os.makedirs(os.path.dirname(self.settings_path), exist_ok=True)
            with open(self.settings_path, "w", encoding="utf-8") as f:
                self.config_parser.write(f)
            logger.info(f"[DB_ENGINE] Telemetry settings saved to {self.settings_path}")
        except Exception as e:
            logger.error(f"[DB_ENGINE] Failed to save telemetry settings: {e}")

    def get_connection(self) -> Any:
        """Returns a connection (psycopg2 or sqlite3) depending on the configuration."""
        if getattr(self, '_fatal_db_error', False):
            return None
            
        try:
            if self.db_type == "postgres":
                import psycopg2
                return psycopg2.connect(
                    host=self.db_host,
                    port=int(self.db_port),
                    user=self.db_user,
                    password=self.db_password,
                    dbname=self.db_name_pg,
                    options=f"-c search_path={self.db_schema},public",
                    connect_timeout=5
                )
            else:
                return sqlite3.connect(self.db_path)
        except Exception as e:
            error_msg = str(e).lower()
            if "password authentication failed" in error_msg or "fatal:" in error_msg or "fe_sendauth" in error_msg:
                self._fatal_db_error = True
                logger.critical(f"[DB_ENGINE] Fatal PostgreSQL connection error for user '{self.db_user}' / db '{self.db_name_pg}': {e}")
            else:
                logger.error(f"[DB_ENGINE] Failed to connect to the database ({self.db_type}): {e}")
            return None

    def reset_circuit_breaker(self):
        """Resets the fatal error circuit breaker to permit retry attempts."""
        self._fatal_db_error = False

    def save_settings_to_ini(self, config_dict: Dict[str, Any]):
        """Persists updated connection settings to config/settings.ini."""
        try:
            if not self.config_parser.has_section("DATABASE"):
                self.config_parser.add_section("DATABASE")
            for k, v in config_dict.items():
                self.config_parser.set("DATABASE", str(k), str(v))
            
            # Map canonical keys so both host/db_host, user/db_user, etc. are written
            canonical_map = {
                "host": "db_host",
                "port": "db_port",
                "user": "db_user",
                "password": "db_password",
                "dbname": "db_name",
                "schema": "db_schema",
            }
            for k, alias in canonical_map.items():
                if k in config_dict:
                    self.config_parser.set("DATABASE", alias, str(config_dict[k]))
                elif alias in config_dict:
                    self.config_parser.set("DATABASE", k, str(config_dict[alias]))

            os.makedirs(os.path.dirname(self.settings_path), exist_ok=True)
            with open(self.settings_path, "w", encoding="utf-8") as f:
                self.config_parser.write(f)
            logger.info(f"[DB_ENGINE] Settings saved to {self.settings_path}")
        except Exception as e:
            logger.error(f"[DB_ENGINE] Failed to save settings to {self.settings_path}: {e}")

    def _load_schema_config(self) -> dict:
        try:
            json_path = os.path.join(self.project_root, "config", "synapse_schema_queries.json")
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"[DB_ENGINE] Failed to load synapse_schema_queries.json: {e}")
        return {}

    def _initialize_db(self):
        """
        Creates the necessary tables, migrations, and indexes in the database dynamically from JSON.
        """
        conn = self.get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            schema_config = self._load_schema_config()
            dialect_config = schema_config.get(self.db_type, schema_config.get("sqlite", {}))

            # 1. Create Tables
            for table_sql in dialect_config.get("tables", []):
                cursor.execute(table_sql)
                conn.commit()

            # 2. Migrations
            migrations = dialect_config.get("migrations", [])
            if self.db_type == "postgres":
                cursor.execute("""
                    SELECT table_name, column_name FROM information_schema.columns 
                    WHERE table_schema = %s OR table_schema = 'public';
                """, (self.db_schema,))
                existing_cols = {(row[0], row[1]) for row in cursor.fetchall()}
                for m in migrations:
                    if isinstance(m, dict):
                        t_name = m.get("table", "synapse_sensor_telemetry_raw")
                        col_name = m.get("column")
                        if (t_name, col_name) not in existing_cols:
                            try:
                                cursor.execute(m["sql"])
                                conn.commit()
                            except Exception:
                                pass
            else:
                for migration_sql in migrations:
                    sql_stmt = migration_sql if isinstance(migration_sql, str) else migration_sql.get("sql")
                    try:
                        cursor.execute(sql_stmt)
                        conn.commit()
                    except Exception:
                        pass

            # 3. Create Indexes
            for index_sql in dialect_config.get("indexes", []):
                try:
                    cursor.execute(index_sql)
                    conn.commit()
                except Exception as ie:
                    logger.debug(f"[DB_ENGINE] Index creation notice: {ie}")

        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            logger.error(f"[DB_ENGINE] Error during _initialize_db: {e}")
        finally:
            if conn:
                conn.close()
