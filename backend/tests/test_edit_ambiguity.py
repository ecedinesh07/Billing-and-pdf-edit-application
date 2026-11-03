"""Unit-level policy checks for ambiguous edits (no DB)."""

from app.models.document import OperationType


def test_replace_text_operation_type_exists():
    assert OperationType.REPLACE_TEXT.value == "replace_text"


def test_operation_types_cover_mvp():
    values = {op.value for op in OperationType}
    assert {"replace_text", "insert_text", "delete_text"} <= values
