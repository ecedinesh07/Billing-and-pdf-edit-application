from app.services.render_service import AppliedEdit, RenderService


def _edit(old: str, new: str, block_id: str = "b1") -> AppliedEdit:
    return AppliedEdit(
        operation_type="replace_text",
        page_number=1,
        old_value=old,
        new_value=new,
        bbox={"x0": 10, "y0": 10, "x1": 200, "y1": 30},
        block_id=block_id,
    )


def test_coalesce_reverts_to_original_are_skipped():
    edits = [
        _edit("STATEMENT", "STATEMENTS DINESH"),
        _edit("STATEMENTS DINESH", "STATEMENT"),
    ]
    assert RenderService.coalesce_edits(edits) == []


def test_coalesce_chain_keeps_final_text_only():
    edits = [
        _edit("STATEMENT", "STATEMENTS DINESH"),
        _edit("STATEMENTS DINESH", "STATEMENT FINAL"),
    ]
    result = RenderService.coalesce_edits(edits)
    assert len(result) == 1
    assert result[0].old_value == "STATEMENT"
    assert result[0].new_value == "STATEMENT FINAL"


def test_coalesce_separate_blocks_remain_separate():
    edits = [
        _edit("A", "B", block_id="b1"),
        _edit("X", "Y", block_id="b2"),
    ]
    result = RenderService.coalesce_edits(edits)
    assert len(result) == 2
