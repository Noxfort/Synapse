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
# File: src/security/security_manager.py
# Author: Gabriel Moraes
# Date: 2026-09-03

"""
Security Manager Subsystem.
Manages user accounts, PBKDF2 authentication, audit logging, and global Lockdown failsafe logic.
Roles available: OPERATOR, SUPERUSER, MASTER.
"""

import os
import sys
import json
import logging
import hashlib
import binascii
from typing import Dict, Any, List, Tuple, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from src.utils.logging_setup import get_logger


def get_user_config_dir() -> str:
    """
    Returns the persistent user configuration directory following OS standards.
    Supports SYNAPSE_CONFIG_DIR environment override.
    """
    env_dir = os.environ.get("SYNAPSE_CONFIG_DIR")
    if env_dir:
        os.makedirs(env_dir, exist_ok=True)
        return env_dir

    if sys.platform.startswith("win"):
        base_dir = os.environ.get("APPDATA") or os.path.expanduser("~/AppData/Roaming")
    elif sys.platform.startswith("darwin"):
        base_dir = os.path.expanduser("~/Library/Application Support")
    else:
        # Linux / Unix XDG standard
        base_dir = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")

    config_dir = os.path.join(base_dir, "synapse")
    os.makedirs(config_dir, exist_ok=True)
    return config_dir


class SecurityManager:
    """
    Manages authentication, user accounts, and the Lockdown failsafe mechanism.
    Roles:
      - OPERATOR: Standard access.
      - SUPERUSER: Full access (settings, play, account management).
      - MASTER: God mode fallback with hardcoded SHA-256 hash.
    Persists user credentials in both local security.json and central PostgreSQL (synapse_users table).
    """

    def __init__(self, config_dir: Optional[str] = None, db_engine: Optional[Any] = None):
        self.logger = get_logger("SecurityManager")
        self.max_failed_attempts = 3

        target_dir = config_dir or get_user_config_dir()
        self.config_dir = target_dir
        self.security_file = os.path.join(target_dir, "security.json")
        self.lockdown_file = os.path.join(target_dir, "lockdown.flag")

        # Database Engine integration for PostgreSQL / persistent centralized storage
        if db_engine is not None:
            self.db_engine = db_engine
        elif config_dir is None:
            try:
                from src.database.db_engine import DatabaseEngine
                self.db_engine = DatabaseEngine()
            except Exception as e:
                self.logger.debug(f"Could not auto-initialize DatabaseEngine in SecurityManager: {e}")
                self.db_engine = None
        else:
            self.db_engine = None

        # Master Super User configuration (fallback god mode)
        # Default public fallback: User 'admin' / Pass 'admin'
        self.default_user = "admin"
        self.default_hash = "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918"  # sha256("admin")

        self.master_user = os.environ.get("SYNAPSE_SUPERUSER", self.default_user)
        custom_password = os.environ.get("SYNAPSE_SUPERUSER_PASSWORD")
        if custom_password:
            self.master_hash = hashlib.sha256(custom_password.encode("utf-8")).hexdigest()
        else:
            self.master_hash = os.environ.get("SYNAPSE_SUPERUSER_HASH", self.default_hash)

        self.last_auth_user = "SYSTEM"

        self._ensure_files()

    def _ensure_db_table(self) -> None:
        """Ensures the synapse_users table exists in the PostgreSQL database."""
        if not self.db_engine:
            return
        try:
            conn = self.db_engine.get_connection()
            if not conn:
                return
            try:
                cur = conn.cursor()
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS synapse_users (
                        username VARCHAR(128) PRIMARY KEY,
                        password_hash TEXT NOT NULL,
                        role VARCHAR(32) NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    );
                """)
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            self.logger.debug(f"[DB USER] Table check notice in SecurityManager: {e}")

    def _db_fetch_users(self) -> Dict[str, Dict[str, str]]:
        """Loads all registered users and their password hashes from the central database."""
        if not self.db_engine:
            return {}
        try:
            conn = self.db_engine.get_connection()
            if not conn:
                return {}
            try:
                cur = conn.cursor()
                cur.execute("SELECT username, password_hash, role FROM synapse_users;")
                rows = cur.fetchall()
                result = {}
                for row in rows:
                    uname = row[0]
                    pwd_hash = row[1]
                    role = row[2]
                    result[uname] = {"hash": pwd_hash, "role": role}
                return result
            finally:
                conn.close()
        except Exception as e:
            self.logger.debug(f"[DB USER] Failed to fetch users from database: {e}")
            return {}

    def _db_save_user(self, username: str, password_hash: str, role: str) -> bool:
        """Persists or updates a user credential record in the PostgreSQL database."""
        if not self.db_engine:
            return False
        try:
            conn = self.db_engine.get_connection()
            if not conn:
                return False
            try:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO synapse_users (username, password_hash, role, updated_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (username) DO UPDATE
                    SET password_hash = EXCLUDED.password_hash,
                        role = EXCLUDED.role,
                        updated_at = NOW();
                """, (username, password_hash, role))
                conn.commit()
                return True
            finally:
                conn.close()
        except Exception as e:
            self.logger.debug(f"[DB USER] Failed to save user '{username}' to database: {e}")
            return False

    def _db_delete_user(self, username: str) -> bool:
        """Deletes a user record from the PostgreSQL database."""
        if not self.db_engine:
            return False
        try:
            conn = self.db_engine.get_connection()
            if not conn:
                return False
            try:
                cur = conn.cursor()
                cur.execute("DELETE FROM synapse_users WHERE username = %s;", (username,))
                conn.commit()
                return True
            finally:
                conn.close()
        except Exception as e:
            self.logger.debug(f"[DB USER] Failed to delete user '{username}' from database: {e}")
            return False

    def _sync_with_db(self) -> None:
        """
        Synchronizes user credentials between the local security.json and the database.
        If security.json was deleted (e.g. synapse config folder removed), all users
        are automatically restored from the database into the local file.
        Conversely, any local users not yet present in the database are synced up.
        """
        if not self.db_engine:
            return

        self._ensure_db_table()
        db_users = self._db_fetch_users()
        local_db = self._load_db()
        local_users = local_db.get("users", {})

        modified_local = False

        # 1. Restore from Database to Local if missing locally
        for uname, udata in db_users.items():
            if uname not in local_users:
                local_users[uname] = {
                    "hash": udata["hash"],
                    "role": udata["role"],
                }
                modified_local = True

        # 2. Push any local users not present in Database
        for uname, udata in local_users.items():
            if uname not in db_users:
                self._db_save_user(uname, udata.get("hash", ""), udata.get("role", "OPERATOR"))

        if modified_local:
            local_db["users"] = local_users
            self._save_db(local_db)
            self.logger.info(
                f"Restored {len(db_users)} user(s) from central database to local security file."
            )

    def _ensure_files(self) -> None:
        """Initializes security.json if not present and synchronizes with the database."""
        os.makedirs(self.config_dir, exist_ok=True)
        if not os.path.exists(self.security_file):
            default_db = {
                "users": {},
                "failed_attempts": 0,
            }
            self._save_db(default_db)
            self.logger.info("Security file created with clean user table (master user active).")
        self._sync_with_db()

    def _load_db(self) -> Dict[str, Any]:
        """Loads the security database from JSON."""
        if not os.path.exists(self.security_file):
            os.makedirs(self.config_dir, exist_ok=True)
            default_db = {"users": {}, "failed_attempts": 0}
            self._save_db(default_db)

        try:
            with open(self.security_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error reading security database: {e}")
            return {"users": {}, "failed_attempts": 0}

    def _save_db(self, db: Dict[str, Any]) -> None:
        """Saves the security database to JSON."""
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.security_file, "w", encoding="utf-8") as f:
                json.dump(db, f, indent=4)
        except Exception as e:
            self.logger.error(f"Error saving security database: {e}")

    def _hash_password(self, password: str, salt: Optional[bytes] = None) -> str:
        """Hashes a password using PBKDF2 HMAC SHA-256 with 100,000 iterations."""
        if salt is None:
            salt = os.urandom(16)
        pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        return f"{binascii.hexlify(salt).decode('utf-8')}:{binascii.hexlify(pwd_hash).decode('utf-8')}"

    def _verify_password(self, password: str, stored_hash_str: str) -> bool:
        """Verifies a password against a stored PBKDF2 hash string."""
        try:
            salt_hex, hash_hex = stored_hash_str.split(":")
            salt = binascii.unhexlify(salt_hex)
            stored_hash = binascii.unhexlify(hash_hex)
            new_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
            return new_hash == stored_hash
        except Exception:
            return False

    def is_lockdown(self) -> bool:
        """Returns True if the system is currently under persistent lockdown."""
        return os.path.exists(self.lockdown_file)

    def trigger_lockdown(self) -> None:
        """Creates the persistent lockdown flag file."""
        try:
            with open(self.lockdown_file, "w", encoding="utf-8") as f:
                f.write("LOCKDOWN_ACTIVE")
            self.logger.critical("🚨 SISTEMA ENTROU EM LOCKDOWN (Múltiplas tentativas de acesso inválidas).")
        except Exception as e:
            self.logger.error(f"Failed to create lockdown flag: {e}")

    def clear_lockdown(self) -> None:
        """Removes the persistent lockdown flag and resets failed attempts."""
        if os.path.exists(self.lockdown_file):
            try:
                os.remove(self.lockdown_file)
            except Exception as e:
                self.logger.error(f"Failed to remove lockdown flag: {e}")

        db = self._load_db()
        db["failed_attempts"] = 0
        self._save_db(db)
        self.logger.info("Lockdown removed and failed attempts counter reset.")

    def record_failed_attempt(self) -> bool:
        """
        Increments the failed attempts counter. Triggers lockdown if >= 3.
        Returns True if lockdown is active or was triggered during this call.
        """
        if self.is_lockdown():
            return True

        db = self._load_db()
        db["failed_attempts"] = db.get("failed_attempts", 0) + 1
        current = db["failed_attempts"]
        self.logger.warning(
            f"Failed login attempt recorded. Total: {current}/{self.max_failed_attempts}"
        )

        if current >= self.max_failed_attempts:
            self.trigger_lockdown()
            self._save_db(db)
            return True

        self._save_db(db)
        return False

    def authenticate(self, username: str, password: str) -> Tuple[bool, str]:
        """
        Attempts to authenticate a user.
        Returns: (success_bool, role_string_or_error_msg)
        """
        invalid_msg = "Credenciais inválidas."
        system_locked_msg = "SISTEMA BLOQUEADO. Apenas Super Usuários podem desbloquear."

        # 1. Master Fallback Check (God mode)
        # Supports master_user (from .env/environment) or default fallback 'admin'
        is_master_match = False
        if username == self.master_user:
            raw_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
            if raw_hash == self.master_hash:
                is_master_match = True
        elif username == self.default_user:
            raw_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
            if raw_hash == self.default_hash:
                is_master_match = True

        if is_master_match:
            self.last_auth_user = username
            if self.is_lockdown():
                self.clear_lockdown()
            return True, "MASTER"
        elif username in (self.master_user, self.default_user):
            self.record_failed_attempt()
            return False, invalid_msg

        db = self._load_db()

        # 2. Lockdown handling: only SUPERUSER or MASTER can unlock
        if self.is_lockdown():
            if username not in db.get("users", {}) and self.db_engine:
                self._sync_with_db()
                db = self._load_db()

            if username in db.get("users", {}):
                user_data = db["users"][username]
                if user_data.get("role") == "SUPERUSER":
                    if self._verify_password(password, user_data.get("hash", "")):
                        self.last_auth_user = username
                        self.clear_lockdown()
                        return True, "SUPERUSER"

            return False, system_locked_msg

        # 3. Standard authentication
        if username not in db.get("users", {}) and self.db_engine:
            self._sync_with_db()
            db = self._load_db()

        if username not in db.get("users", {}):
            self.record_failed_attempt()
            return False, invalid_msg

        user_data = db["users"][username]
        if self._verify_password(password, user_data.get("hash", "")):
            self.last_auth_user = username
            if db.get("failed_attempts", 0) > 0:
                db["failed_attempts"] = 0
                self._save_db(db)
            return True, user_data.get("role", "OPERATOR")
        else:
            self.record_failed_attempt()
            return False, invalid_msg

    def add_user(self, username: str, password: str, role: str) -> bool:
        """Creates a new user with the specified role."""
        if role not in ["OPERATOR", "SUPERUSER"]:
            return False
        if not username or not password:
            return False
        if username in (self.master_user, self.default_user):
            return False

        if self.db_engine:
            self._sync_with_db()

        db = self._load_db()
        if username in db.get("users", {}):
            return False  # User already exists

        pwd_hash = self._hash_password(password)
        db["users"][username] = {
            "hash": pwd_hash,
            "role": role,
        }
        self._save_db(db)

        # Persist to database
        self._db_save_user(username, pwd_hash, role)

        self.logger.info(f"New user registered: {username} ({role})")
        return True

    def remove_user(self, username: str) -> bool:
        """Removes an existing user. Blocked for master users."""
        if username in (self.master_user, self.default_user):
            self.logger.warning(f"Blocked attempt to remove protected master user '{username}'.")
            return False

        db = self._load_db()
        user_existed = username in db.get("users", {})
        if user_existed:
            del db["users"][username]
            self._save_db(db)

        db_removed = self._db_delete_user(username)

        if user_existed or db_removed:
            self.logger.info(f"User removed: {username}")
            return True
        return False

    def list_users(self) -> List[Dict[str, str]]:
        """Returns the list of registered users and their roles (excluding passwords)."""
        if self.db_engine:
            if not os.path.exists(self.security_file):
                self._ensure_files()
            else:
                self._sync_with_db()
        db = self._load_db()
        users = []
        for uname, data in db.get("users", {}).items():
            users.append({"username": uname, "role": data.get("role", "OPERATOR")})
        return users
