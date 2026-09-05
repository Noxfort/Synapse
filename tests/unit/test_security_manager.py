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
# File: tests/unit/test_security_manager.py
# Author: Gabriel Moraes
# Date: 2026-09-03

"""
Unit Tests for SecurityManager, AuditLogger, and SecurityCommandHandler.
Verifies built-in master superuser authentication (admin/admin fallback and custom environment override),
lockdown failsafe, user CRUD, audit logs, and database synchronization.
"""

import os
import shutil
import tempfile
import pytest
from unittest.mock import MagicMock

from src.security.security_manager import SecurityManager
from src.security.audit_logger import AuditLogger
from src.handlers.security_handler import SecurityCommandHandler
from src.handlers.system_handler import SystemCommandHandler
from src.handlers.source_handler import SourceCommandHandler
from src.ipc.ipc_protocol import IpcMessage


@pytest.fixture
def temp_sec_dir():
    temp_dir = tempfile.mkdtemp(prefix="synapse_sec_test_")
    yield temp_dir
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


def test_security_manager_initialization_no_default_user(temp_sec_dir):
    """Ensures no custom user accounts are written by default. Clean state."""
    sec = SecurityManager(config_dir=temp_sec_dir)
    assert os.path.isfile(sec.security_file)
    users = sec.list_users()
    assert len(users) == 0  # No custom users! Master user works as built-in fallback


def test_security_manager_master_user_authentication(temp_sec_dir):
    """Verifies that the default master superuser (admin/admin) authenticates with role MASTER."""
    sec = SecurityManager(config_dir=temp_sec_dir)

    # Master user valid credentials
    success, role = sec.authenticate("admin", "admin")
    assert success is True
    assert role == "MASTER"

    # Master user wrong password
    fail, err = sec.authenticate("admin", "wrong_pass")
    assert fail is False
    assert "Credenciais inválidas" in err


def test_security_manager_custom_env_credentials(temp_sec_dir, monkeypatch):
    """Verifies that master superuser can be customized via environment variables (.env)."""
    monkeypatch.setenv("SYNAPSE_SUPERUSER", "custom_operator")
    monkeypatch.setenv("SYNAPSE_SUPERUSER_PASSWORD", "CustomSafePass@123")
    sec = SecurityManager(config_dir=temp_sec_dir)
    assert sec.master_user == "custom_operator"

    ok_custom, role_custom = sec.authenticate("custom_operator", "CustomSafePass@123")
    assert ok_custom is True
    assert role_custom == "MASTER"

    # Default admin also still authenticates as master fallback
    ok_admin, role_admin = sec.authenticate("admin", "admin")
    assert ok_admin is True
    assert role_admin == "MASTER"


def test_security_manager_lockdown_failsafe(temp_sec_dir):
    """Verifies that 3 failed attempts trigger lockdown, and only master superuser can unlock."""
    sec = SecurityManager(config_dir=temp_sec_dir)
    assert sec.is_lockdown() is False

    # Attempt 1
    sec.authenticate("unknown_user", "bad1")
    assert sec.is_lockdown() is False

    # Attempt 2
    sec.authenticate("unknown_user", "bad2")
    assert sec.is_lockdown() is False

    # Attempt 3 -> Triggers lockdown!
    sec.authenticate("unknown_user", "bad3")
    assert sec.is_lockdown() is True
    assert os.path.isfile(sec.lockdown_file)

    # During lockdown, bad credentials or operator cannot unlock
    sec.add_user("operator1", "pass123", "OPERATOR")
    ok, msg = sec.authenticate("operator1", "pass123")
    assert ok is False
    assert "SISTEMA BLOQUEADO" in msg

    # Master superuser CAN unlock
    ok_unlock, role = sec.authenticate("admin", "admin")
    assert ok_unlock is True
    assert role == "MASTER"
    assert sec.is_lockdown() is False
    assert not os.path.isfile(sec.lockdown_file)


def test_security_manager_user_crud(temp_sec_dir):
    """Verifies adding and removing users, and ensuring master_user cannot be removed."""
    sec = SecurityManager(config_dir=temp_sec_dir)

    # Add operator
    assert sec.add_user("op_john", "pass_john", "OPERATOR") is True
    # Duplicate fails
    assert sec.add_user("op_john", "pass_john2", "OPERATOR") is False
    # Invalid role fails
    assert sec.add_user("guest", "pass", "INVALID_ROLE") is False

    users = sec.list_users()
    assert len(users) == 1
    assert users[0]["username"] == "op_john"
    assert users[0]["role"] == "OPERATOR"

    # Auth operator
    ok, role = sec.authenticate("op_john", "pass_john")
    assert ok is True
    assert role == "OPERATOR"

    # Cannot delete master user
    assert sec.remove_user("admin") is False

    # Delete operator
    assert sec.remove_user("op_john") is True
    assert len(sec.list_users()) == 0


def test_audit_logger(temp_sec_dir):
    aud = AuditLogger(config_dir=temp_sec_dir)
    aud.log_action("admin", "SYSTEM_ACCESS", "Testing audit logger")
    logs = aud.get_logs(limit=10)
    assert len(logs) == 1
    assert logs[0]["username"] == "admin"
    assert logs[0]["action"] == "SYSTEM_ACCESS"


def test_security_command_handler(temp_sec_dir):
    sec = SecurityManager(config_dir=temp_sec_dir)
    aud = AuditLogger(config_dir=temp_sec_dir)
    emitter_events = []
    emitter = lambda ev, data=None: emitter_events.append((ev, data))

    handler = SecurityCommandHandler(
        security_manager=sec, audit_logger=aud, event_emitter=emitter
    )

    responses = []
    responder = lambda ok, res=None, err=None: responses.append((ok, res, err))

    # Test authenticate master
    msg_auth = IpcMessage(
        action="authenticate",
        payload={"username": "admin", "password": "admin"}
    )
    handler.handle_authenticate(msg_auth, responder)
    assert len(responses) == 1
    assert responses[0][0] is True
    assert responses[0][1]["role"] == "MASTER"

    # Test check_lockdown
    handler.handle_check_lockdown(IpcMessage(action="check_lockdown"), responder)
    assert responses[-1][0] is True
    assert responses[-1][1]["active"] is False

    # Test add_user and list_users
    msg_add = IpcMessage(action="add_user", payload={"username": "alice", "password": "pwd", "role": "OPERATOR"})
    handler.handle_add_user(msg_add, responder)
    assert responses[-1][0] is True

    handler.handle_list_users(IpcMessage(action="list_users"), responder)
    users = responses[-1][1]["users"]
    assert any(u["username"] == "alice" for u in users)

    # Test remove_user
    msg_rm = IpcMessage(action="remove_user", payload={"username": "alice"})
    handler.handle_remove_user(msg_rm, responder)
    assert responses[-1][0] is True


def test_system_handler_lockdown_rejection(temp_sec_dir):
    sec = SecurityManager(config_dir=temp_sec_dir)
    controller = MagicMock()
    sys_handler = SystemCommandHandler(controller, security_manager=sec)

    # Normal mode -> works
    controller.start_optimization_flow.return_value = True
    res = sys_handler.handle_start_optimization(IpcMessage(action="start_optimization"))
    assert res["started"] is True

    # Trigger lockdown
    sec.trigger_lockdown()

    with pytest.raises(RuntimeError, match="LOCKDOWN"):
        sys_handler.handle_start_optimization(IpcMessage(action="start_optimization"))

    with pytest.raises(RuntimeError, match="LOCKDOWN"):
        sys_handler.handle_start_offline_bootstrap(IpcMessage(action="start_offline_bootstrap"))

    with pytest.raises(RuntimeError, match="LOCKDOWN"):
        sys_handler.handle_start_online_operation(IpcMessage(action="start_online_operation"))


def test_system_and_source_handler_audit_logging(temp_sec_dir):
    sec = SecurityManager(config_dir=temp_sec_dir)
    aud = AuditLogger(config_dir=temp_sec_dir)
    controller = MagicMock()
    app_state = MagicMock()

    # Authenticate as admin
    sec.authenticate("admin", "admin")
    assert sec.last_auth_user == "admin"

    sys_handler = SystemCommandHandler(
        controller, security_manager=sec, audit_logger=aud
    )
    controller.start_optimization_flow.return_value = True
    sys_handler.handle_start_optimization(IpcMessage(action="start_optimization"))

    logs = aud.get_logs(limit=10)
    assert any(
        l["action"] == "START_OPTIMIZATION" and l["username"] == "admin"
        for l in logs
    )

    # Source handler audit log
    source_handler = SourceCommandHandler(
        app_state, security_manager=sec, audit_logger=aud
    )
    source_handler.handle_add_source(
        IpcMessage(action="add_source", payload={"name": "Radar_A1", "is_local": True})
    )

    logs_after_source = aud.get_logs(limit=10)
    assert any(
        l["action"] == "ADD_SENSOR" and "Radar_A1" in l["details"]
        for l in logs_after_source
    )


def test_audit_logger_database_and_telemetry_reporting(temp_sec_dir):
    from src.database.db_engine import DatabaseEngine

    db_engine = DatabaseEngine(custom_config={"db_type": "postgres", "schema": "schema_synapse_test"}, auto_init=True)
    
    # Clean audit logs in test schema
    conn = db_engine.get_connection()
    assert conn is not None
    cur = conn.cursor()
    cur.execute("TRUNCATE TABLE schema_synapse_test.security_audit_logs RESTART IDENTITY;")
    conn.commit()
    conn.close()

    aud = AuditLogger(config_dir=temp_sec_dir, db_engine=db_engine)
    aud.log_action("test_user", "TEST_DB_ACTION", "Testing database persistence")

    # Verify log is in DB
    db_logs = aud.get_logs(limit=5)
    assert any(l["action"] == "TEST_DB_ACTION" and l["username"] == "test_user" for l in db_logs)

    # Telemetry incident reporting verification
    sec = SecurityManager(config_dir=temp_sec_dir)
    telemetry = MagicMock()
    handler = SecurityCommandHandler(
        security_manager=sec, audit_logger=aud, telemetry_service=telemetry
    )

    responses = []
    responder = lambda ok, res=None, err=None: responses.append((ok, res, err))

    # 1. Failed login -> reports incident WARNING
    handler.handle_authenticate(
        IpcMessage(action="authenticate", payload={"username": "hacker", "password": "wrong"}),
        responder
    )
    assert telemetry.report_incident.called
    pos_args = telemetry.report_incident.call_args[0]
    assert pos_args[0] == "SOFTWARE"
    assert pos_args[1] == "WARNING"
    assert "hacker" in pos_args[2]

    # 2. Trigger lockdown -> reports incident CRITICAL
    handler.handle_authenticate(
        IpcMessage(action="authenticate", payload={"username": "hacker", "password": "wrong"}),
        responder
    )
    handler.handle_authenticate(
        IpcMessage(action="authenticate", payload={"username": "hacker", "password": "wrong"}),
        responder
    )
    assert sec.is_lockdown() is True
    pos_args_lock = telemetry.report_incident.call_args[0]
    assert pos_args_lock[1] == "CRITICAL"
    assert "LOCKDOWN" in pos_args_lock[2]

    # 3. Unlock -> reports incident INFO
    handler.handle_authenticate(
        IpcMessage(action="authenticate", payload={"username": "admin", "password": "admin"}),
        responder
    )
    pos_args_unlock = telemetry.report_incident.call_args[0]
    assert pos_args_unlock[1] == "INFO"

    # 4. Remove sensor -> reports incident WARNING
    app_state = MagicMock()
    src_handler = SourceCommandHandler(
        app_state, security_manager=sec, audit_logger=aud, telemetry_service=telemetry
    )
    src_handler.handle_remove_source(IpcMessage(action="remove_source", payload={"source_id": "cam_01"}))
    pos_args_sensor = telemetry.report_incident.call_args[0]
    assert pos_args_sensor[1] == "WARNING"
    assert "cam_01" in pos_args_sensor[2]


def test_security_manager_database_synchronization_and_folder_deletion_recovery(temp_sec_dir):
    """
    Verifies that users and password hashes saved in SecurityManager are also
    persisted to the database, and if the synapse config folder is completely
    deleted, a new SecurityManager instance automatically restores all users
    and password hashes from the database.
    """
    from src.database.db_engine import DatabaseEngine

    db_engine = DatabaseEngine(custom_config={"db_type": "postgres", "schema": "schema_synapse_test"}, auto_init=True)
    conn = db_engine.get_connection()
    assert conn is not None
    cur = conn.cursor()
    cur.execute("TRUNCATE TABLE schema_synapse_test.synapse_users RESTART IDENTITY;")
    conn.commit()
    conn.close()

    # 1. Initialize SecurityManager with DB
    sec1 = SecurityManager(config_dir=temp_sec_dir, db_engine=db_engine)
    assert len(sec1.list_users()) == 0

    # 2. Add user "operador1"
    ok = sec1.add_user("operador1", "SenhaForte@2026", "OPERATOR")
    assert ok is True

    # Verify present locally and authenticates
    assert len(sec1.list_users()) == 1
    assert sec1.list_users()[0]["username"] == "operador1"
    auth_ok, role = sec1.authenticate("operador1", "SenhaForte@2026")
    assert auth_ok is True
    assert role == "OPERATOR"

    # Verify present in PostgreSQL synapse_users table
    conn = db_engine.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT username, password_hash, role FROM synapse_users WHERE username = %s;", ("operador1",))
    row = cur.fetchone()
    assert row is not None
    assert row[0] == "operador1"
    assert row[2] == "OPERATOR"
    db_hash = row[1]
    assert sec1._verify_password("SenhaForte@2026", db_hash) is True
    conn.close()

    # 3. SIMULATE DELETING THE ENTIRE SYNAPSE CONFIG DIRECTORY
    shutil.rmtree(temp_sec_dir)
    assert not os.path.exists(temp_sec_dir)
    assert not os.path.exists(sec1.security_file)

    # 4. Instantiate a NEW SecurityManager pointing to the recreated/new synapse directory
    sec2 = SecurityManager(config_dir=temp_sec_dir, db_engine=db_engine)

    # 5. Verify the folder and security.json were recreated, and users RESTORED from DB!
    assert os.path.exists(sec2.security_file)
    restored_users = sec2.list_users()
    assert len(restored_users) == 1
    assert restored_users[0]["username"] == "operador1"
    assert restored_users[0]["role"] == "OPERATOR"

    # 6. Verify authentication works with the restored password hash!
    auth_ok2, role2 = sec2.authenticate("operador1", "SenhaForte@2026")
    assert auth_ok2 is True
    assert role2 == "OPERATOR"

    # Wrong password must still be rejected
    auth_fail, err = sec2.authenticate("operador1", "wrong_password")
    assert auth_fail is False
    assert "Credenciais inválidas" in err

    # 7. Add second user "super_gestor"
    ok_super = sec2.add_user("super_gestor", "GestorMaster#2026", "SUPERUSER")
    assert ok_super is True
    assert len(sec2.list_users()) == 2

    # 8. Remove user "operador1"
    assert sec2.remove_user("operador1") is True
    assert len(sec2.list_users()) == 1

    # Check removed from database as well
    conn = db_engine.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM synapse_users WHERE username = %s;", ("operador1",))
    assert cur.fetchone()[0] == 0
    cur.execute("SELECT count(*) FROM synapse_users WHERE username = %s;", ("super_gestor",))
    assert cur.fetchone()[0] == 1
    conn.close()


def test_security_manager_resilience_when_database_offline(temp_sec_dir):
    """
    Verifies that if the central database is offline or unreachable,
    SecurityManager continues to work with local files without crashing.
    """
    mock_engine = MagicMock()
    mock_engine.get_connection.return_value = None  # DB offline
    mock_engine.db_type = "postgres"

    sec = SecurityManager(config_dir=temp_sec_dir, db_engine=mock_engine)

    # Adding user locally still works
    assert sec.add_user("local_user", "local_pass", "OPERATOR") is True
    assert len(sec.list_users()) == 1

    # Authentication works locally
    ok, role = sec.authenticate("local_user", "local_pass")
    assert ok is True
    assert role == "OPERATOR"

    # Removing user works locally
    assert sec.remove_user("local_user") is True
    assert len(sec.list_users()) == 0



