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
# File: tests/unit/test_cloud_vault_repo.py
# Author: Gabriel Moraes
# Date: 2026-09-04

"""
Unit tests for CloudVaultRepository syncing, fetching, and restoring BLOB checkpoints.
"""

from src.repositories.cloud_vault_repo import CloudVaultRepository


def test_cloud_vault_repository(temp_db_engine, tmp_path):
    """Verifies syncing and restoring neural checkpoints from PostgreSQL/SQLite BLOB."""
    vault = CloudVaultRepository(temp_db_engine)

    # Create a mock checkpoint file
    mock_ckpt = tmp_path / "models" / "best_hparams.pth"
    mock_ckpt.parent.mkdir(parents=True, exist_ok=True)
    dummy_content = b"SYNAPSE_NEURAL_WEIGHTS_VERSION_2_PAYLOAD_TEST_12345"
    mock_ckpt.write_bytes(dummy_content)

    # Sync to vault
    synced = vault.sync_file_to_vault(str(mock_ckpt), str(tmp_path))
    assert synced is True

    # Fetch bytes directly
    content = vault.fetch_file_from_vault("models/best_hparams.pth")
    assert content == dummy_content

    # Restore into another location
    restore_path = tmp_path / "restored" / "best_hparams.pth"
    restored = vault.restore_file_from_vault("models/best_hparams.pth", str(restore_path))
    assert restored is True
    assert restore_path.exists()
    assert restore_path.read_bytes() == dummy_content
