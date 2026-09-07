"""Tests for scraper audit log helper (TD-04, Sprint 6).

Verifies that _audit_log() correctly inserts admin_audit_log entries
attributed to the well-known system user UUID.
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import MagicMock, patch

from scraper.tasks import _SYSTEM_USER_ID, _audit_log


class TestAuditLogHelper:
    """Unit tests for the _audit_log function."""

    def test_system_user_id_is_well_known_uuid(self):
        """The system user UUID must match the migration-seeded value."""
        assert _SYSTEM_USER_ID == "00000000-0000-0000-0000-000000000001"
        # Ensure it's a valid UUID
        parsed = uuid.UUID(_SYSTEM_USER_ID)
        assert str(parsed) == _SYSTEM_USER_ID

    @patch("scraper.tasks.get_db_session")
    def test_audit_log_inserts_row(self, mock_get_db):
        """_audit_log should execute an INSERT with the system user actor_id."""
        mock_db = MagicMock()
        mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)

        _audit_log(
            action="test_action",
            target_table="scraper_runs",
            target_id="run-123",
            new_value={"documents_enqueued": 5},
        )

        # Verify execute was called
        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args

        # Verify the SQL params
        params = call_args[0][1]
        assert params["actor_id"] == _SYSTEM_USER_ID
        assert params["action"] == "test_action"
        assert params["target_table"] == "scraper_runs"
        assert params["target_id"] == "run-123"
        assert json.loads(params["new_value"]) == {"documents_enqueued": 5}

        # Verify commit was called
        mock_db.commit.assert_called_once()

    @patch("scraper.tasks.get_db_session")
    def test_audit_log_without_optional_fields(self, mock_get_db):
        """_audit_log should work with only the action parameter."""
        mock_db = MagicMock()
        mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)

        _audit_log(action="heartbeat")

        params = mock_db.execute.call_args[0][1]
        assert params["actor_id"] == _SYSTEM_USER_ID
        assert params["action"] == "heartbeat"
        assert params["target_table"] is None
        assert params["target_id"] is None
        assert params["new_value"] is None

    @patch("scraper.tasks.get_db_session")
    def test_audit_log_generates_unique_ids(self, mock_get_db):
        """Each _audit_log call should generate a unique row ID."""
        mock_db = MagicMock()
        mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)

        _audit_log(action="action_1")
        _audit_log(action="action_2")

        id_1 = mock_db.execute.call_args_list[0][0][1]["id"]
        id_2 = mock_db.execute.call_args_list[1][0][1]["id"]

        # Both should be valid UUIDs
        uuid.UUID(id_1)
        uuid.UUID(id_2)
        # And distinct
        assert id_1 != id_2
