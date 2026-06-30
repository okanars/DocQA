import os
import tempfile
from app.upload import parse_file, save_upload


def test_parse_txt():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Hello, this is a test document.\nWith multiple lines.")
        f.flush()
        path = f.name

    try:
        pages = parse_file(path)
        assert len(pages) == 1
        assert "Hello" in pages[0]["text"]
        assert pages[0]["page"] == 1
    finally:
        os.unlink(path)


def test_parse_empty_txt():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("")
        f.flush()
        path = f.name

    try:
        pages = parse_file(path)
        assert pages == []
    finally:
        os.unlink(path)


def test_unsupported_format():
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        f.write(b"a,b,c")
        path = f.name

    try:
        try:
            parse_file(path)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Unsupported" in str(e)
    finally:
        os.unlink(path)


def test_save_upload(tmp_path):
    content = b"file content here"
    filepath = save_upload(content, "test.txt", str(tmp_path))
    assert os.path.exists(filepath)
    with open(filepath, "rb") as f:
        assert f.read() == content


def test_save_upload_duplicate(tmp_path):
    content = b"content"
    path1 = save_upload(content, "doc.txt", str(tmp_path))
    path2 = save_upload(content, "doc.txt", str(tmp_path))
    assert path1 != path2
    assert os.path.exists(path1)
    assert os.path.exists(path2)
