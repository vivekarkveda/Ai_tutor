# tests/test_exception_handler.py

import uuid
from unittest.mock import MagicMock, patch
from Transaction.exception import ExceptionHandler, exception


# --------------------------
# Test connect_db()
# --------------------------
@patch("Transaction.excepetion.psycopg2.connect")
@patch("Transaction.excepetion.Settings")
def test_connect_db(mock_settings, mock_connect):
    # Mock Settings.POSTGRES
    mock_settings.POSTGRES = {
        "host": "localhost",
        "port": 5432,
        "user": "test",
        "password": "pass",
        "dbname": "test_db",
    }

    # Mock DB connection + cursor
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value = mock_cursor
    mock_connect.return_value = mock_conn

    handler = ExceptionHandler()
    handler.connect_db()

    # Assertions
    mock_connect.assert_called_once_with(
        host="localhost",
        port=5432,
        user="test",
        password="pass",
        dbname="test_db",
    )
    assert handler.conn == mock_conn
    assert handler.cursor == mock_cursor


# --------------------------
# Test upsert_exception()
# --------------------------
@patch("Transaction.excepetion.psycopg2.connect")
@patch("Transaction.excepetion.Settings")
def test_upsert_exception(mock_settings, mock_connect):
    # Mock config
    mock_settings.POSTGRES = {
        "host": "localhost",
        "port": 5432,
        "user": "test",
        "password": "pass",
        "dbname": "test_db",
    }

    # Mock DB connection + cursor
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_connect.return_value = mock_conn

    handler = ExceptionHandler()
    handler.connect_db()

    handler.upsert_exception(
        transaction_id="T123",
        type="RuntimeError",
        description="Something broke",
        module="video_pipeline",
    )

    # Verify INSERT was called once
    assert mock_cursor.execute.call_count == 1

    # Extract the executed SQL & args
    sql, args = mock_cursor.execute.call_args[0]

    assert "INSERT INTO exception_store" in sql
    assert args[1] == "T123"  # transaction_id
    assert args[2] == "RuntimeError"
    assert args[3] == "Something broke"
    assert args[4] == "video_pipeline"

    mock_conn.commit.assert_called_once()


# --------------------------
# Test wrapper function: exception()
# --------------------------
@patch("Transaction.excepetion.ExceptionHandler")
def test_wrapper_function(mock_handler_cls):
    mock_handler = MagicMock()
    mock_handler_cls.return_value = mock_handler

    exception("T999", type="ValueError", description="Oops", module="core")

    # Ensures internal methods were called
    mock_handler.connect_db.assert_called_once()
    mock_handler.create_table_if_not_exists.assert_called_once()
    mock_handler.upsert_exception.assert_called_once_with(
        "T999", "ValueError", "Oops", "core"
    )
    mock_handler.close_db.assert_called_once()
