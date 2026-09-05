# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# File: src/repositories/cloud_vault_repo.py
# Author: Gabriel Moraes
# Date: 2026-09-02

import os
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Optional, List, Dict, Any

if TYPE_CHECKING:
    from src.database.db_engine import DatabaseEngine

logger = logging.getLogger("Synapse.CloudVaultRepo")


class CloudVaultRepository:
    """
    Repository for managing neural model checkpoints (.pth, .safetensors, .json)
    synchronization and disaster-recovery backup in PostgreSQL (BYTEA).
    Ported from CARINA CloudVaultRepository.
    """

    MAX_FILE_SIZE_MB = 100.0

    def __init__(self, engine: 'DatabaseEngine'):
        self.engine = engine

    def sync_file_to_vault(self, filepath: str, base_dir: str) -> bool:
        """
        Reads a local file and upserts it into cloud_file_vault if it's <= MAX_FILE_SIZE_MB.
        Returns True if successful, False otherwise.
        """
        try:
            if not os.path.exists(filepath):
                return False

            file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
            if file_size_mb > self.MAX_FILE_SIZE_MB:
                logger.debug(f"[CloudVaultRepo] Skipped {filepath} - Exceeds {self.MAX_FILE_SIZE_MB}MB limit ({file_size_mb:.1f}MB)")
                return False

            with open(filepath, 'rb') as f:
                content = f.read()

            rel_path = os.path.relpath(filepath, base_dir)
            filename = os.path.basename(filepath)
            now = datetime.now()

            conn = self.engine.get_connection()
            if not conn:
                return False

            try:
                cursor = conn.cursor()
                import psycopg2
                cursor.execute("""
                    INSERT INTO cloud_file_vault (filename, relative_path, file_content, last_updated)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (relative_path) 
                    DO UPDATE SET file_content = EXCLUDED.file_content, last_updated = EXCLUDED.last_updated;
                """, (filename, rel_path, psycopg2.Binary(content), now))

                conn.commit()
                logger.debug(f"[CloudVaultRepo] Synced {rel_path} ({file_size_mb:.2f}MB) into vault.")
                return True
            except Exception as e:
                logger.error(f"[CloudVaultRepo] Failed to insert file {filename} in vault: {e}")
                return False
            finally:
                conn.close()

        except Exception as general_err:
            logger.error(f"[CloudVaultRepo] Vault File Read Error for {filepath}: {general_err}")
            return False

    def sync_all_files_to_vault(self, base_dir: str):
        """Recursively scans base_dir and syncs all checkpoints/configs to vault."""
        if not os.path.exists(base_dir):
            return

        synced = 0
        skipped = 0
        errors = 0

        for root, dirs, files in os.walk(base_dir):
            for file in files:
                if (file.endswith('.db') or file.endswith('.db-journal') 
                        or file.endswith('.log') or file.endswith('.jsonl') or file.endswith('.tmp')):
                    continue

                filepath = os.path.join(root, file)
                success = self.sync_file_to_vault(filepath, base_dir)
                if success:
                    synced += 1
                else:
                    if os.path.exists(filepath) and os.path.getsize(filepath) > self.MAX_FILE_SIZE_MB * 1024 * 1024:
                        skipped += 1
                    else:
                        errors += 1

        if synced > 0 or errors > 0:
            logger.info(f"[CloudVaultRepo] Sync completed: {synced} synced, {skipped} skipped (>{self.MAX_FILE_SIZE_MB}MB), {errors} errors.")

    def fetch_file_from_vault(self, relative_path: str) -> Optional[bytes]:
        """Reads raw binary content of a file from cloud_file_vault by relative_path."""
        conn = self.engine.get_connection()
        if not conn:
            return None
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT file_content FROM cloud_file_vault WHERE relative_path = %s;", (relative_path,))
            row = cursor.fetchone()
            if row and row[0] is not None:
                val = row[0]
                return bytes(val) if not isinstance(val, bytes) else val
            return None
        except Exception as e:
            logger.error(f"[CloudVaultRepo] Failed to fetch file {relative_path} from vault: {e}")
            return None
        finally:
            conn.close()

    def restore_file_from_vault(self, relative_path: str, target_filepath: str) -> bool:
        """Fetches content from cloud_file_vault and writes it to target_filepath on local disk."""
        content = self.fetch_file_from_vault(relative_path)
        if content is None:
            return False
        try:
            os.makedirs(os.path.dirname(target_filepath), exist_ok=True)
            with open(target_filepath, "wb") as f:
                f.write(content)
            logger.info(f"[CloudVaultRepo] Restored {relative_path} from database vault to {target_filepath}")
            return True
        except Exception as e:
            logger.error(f"[CloudVaultRepo] Failed to write restored file {target_filepath}: {e}")
            return False

    def restore_all_files_from_vault(self, base_dir: str) -> int:
        """Fetches all files stored in cloud_file_vault and restores them into base_dir."""
        conn = self.engine.get_connection()
        if not conn:
            return 0
        restored = 0
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT relative_path, file_content FROM cloud_file_vault;")
            rows = cursor.fetchall()
            for rel_path, content in rows:
                if not rel_path or content is None:
                    continue
                full_path = os.path.join(base_dir, rel_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "wb") as f:
                    f.write(bytes(content) if not isinstance(content, bytes) else content)
                restored += 1
            logger.info(f"[CloudVaultRepo] Restored {restored} files from database vault into {base_dir}")
            return restored
        except Exception as e:
            logger.error(f"[CloudVaultRepo] Error restoring all files from vault: {e}")
            return restored
        finally:
            conn.close()

    def has_file(self, relative_path: str) -> bool:
        """Checks if a file exists in cloud_file_vault without loading content."""
        conn = self.engine.get_connection()
        if not conn:
            return False
        try:
            cursor = conn.cursor()
            param = "%s" if self.engine.db_type == "postgres" else "?"
            cursor.execute(f"SELECT 1 FROM cloud_file_vault WHERE relative_path = {param};", (relative_path,))
            return cursor.fetchone() is not None
        except Exception as e:
            logger.debug(f"[CloudVaultRepo] Error checking existence for {relative_path}: {e}")
            return False
        finally:
            conn.close()

    def list_vault_files(self) -> List[Dict[str, Any]]:
        """Lists all files stored in the vault along with metadata."""
        conn = self.engine.get_connection()
        if not conn:
            return []
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT filename, relative_path, last_updated FROM cloud_file_vault ORDER BY relative_path;")
            rows = cursor.fetchall()
            return [
                {"filename": row[0], "relative_path": row[1], "last_updated": row[2]}
                for row in rows
            ]
        except Exception as e:
            logger.debug(f"[CloudVaultRepo] Error listing vault files: {e}")
            return []
        finally:
            conn.close()

