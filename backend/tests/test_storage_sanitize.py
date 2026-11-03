from app.services.storage_service import sanitize_filename


def test_sanitize_strips_path_traversal():
    assert ".." not in sanitize_filename("../../etc/passwd.pdf")
    assert sanitize_filename("../../etc/passwd.pdf").endswith(".pdf")


def test_sanitize_keeps_simple_name():
    assert sanitize_filename("invoice-01.PDF") == "invoice-01.PDF"
