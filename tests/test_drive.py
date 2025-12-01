import io
from pathlib import Path

from src import drive


class _FakeMediaRequest:
    def __init__(self, file_id: str, content: bytes):
        self.fileId = file_id
        self._content = content

    def read(self):  # pragma: no cover - compatibility
        return self._content


class _FakeFilesResource:
    def __init__(self, files):
        self._files = files
        self._list_calls = 0

    def list(self, q=None, spaces=None, pageToken=None, fields=None):  # noqa: N803
        self._list_calls += 1
        return _FakeListRequest(self._files, pageToken)

    def get_media(self, fileId):  # noqa: N803
        file_data = next(f for f in self._files if f["id"] == fileId)
        return _FakeMediaRequest(fileId, file_data["content"])


class _FakeDriveService:
    def __init__(self, files):
        self._files_resource = _FakeFilesResource(files)

    def files(self):  # noqa: D401
        """Return fake files resource."""
        return self._files_resource


class _FakeListRequest:
    def __init__(self, files, page_token):
        self._files = files
        self._page_token = page_token

    def execute(self):
        if self._page_token:
            return {"files": [], "nextPageToken": None}
        return {"files": self._files, "nextPageToken": None}


class _FakeStatus:
    def __init__(self, progress):
        self._progress = progress

    def progress(self):
        return self._progress


class _FakeDownloader:
    def __init__(self, file_handle: io.FileIO, request: _FakeMediaRequest):
        self._file_handle = file_handle
        self._request = request
        self._done = False

    def next_chunk(self):
        if self._done:
            return None, True
        self._file_handle.write(self._request._content)
        self._done = True
        return _FakeStatus(1.0), True


def test_download_resumes_from_drive_downloads_new_files(monkeypatch, tmp_path: Path):
    files = [
        {"id": "1", "name": "candidate1.pdf", "content": b"pdf-bytes"},
        {"id": "2", "name": "candidate2.docx", "content": b"docx-bytes"},
    ]
    service = _FakeDriveService(files)

    monkeypatch.setattr(drive, "MediaIoBaseDownload", _FakeDownloader)

    drive.download_resumes_from_drive("folder-id", dest_dir=tmp_path, drive_service=service)

    assert (tmp_path / "candidate1.pdf").read_bytes() == b"pdf-bytes"
    assert (tmp_path / "candidate2.docx").read_bytes() == b"docx-bytes"


def test_download_resumes_from_drive_skips_existing(monkeypatch, tmp_path: Path, capsys):
    existing_file = tmp_path / "candidate1.pdf"
    existing_file.write_bytes(b"existing")

    files = [
        {"id": "1", "name": "candidate1.pdf", "content": b"new-bytes"},
    ]
    service = _FakeDriveService(files)

    monkeypatch.setattr(drive, "MediaIoBaseDownload", _FakeDownloader)

    drive.download_resumes_from_drive("folder-id", dest_dir=tmp_path, drive_service=service)

    captured = capsys.readouterr().out
    assert "Skipping download" in captured
    assert existing_file.read_bytes() == b"existing"
