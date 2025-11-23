"""Google Drive integration for downloading resumes."""
import io
import json
import os
from typing import Optional

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
except ImportError:  # pragma: no cover - handled gracefully when dependency missing
    service_account = None  # type: ignore
    build = None  # type: ignore
    MediaIoBaseDownload = None  # type: ignore


def _build_drive_service():
    """Create a Google Drive service using service account credentials.

    Credentials can be provided via either of the following environment variables:
    - GOOGLE_DRIVE_CREDENTIALS: a JSON string containing the service account info
    - GOOGLE_DRIVE_CREDENTIALS_PATH: path to a JSON file with service account info
    """

    if service_account is None or build is None:
        print(
            "google-api-python-client is required for Drive sync. "
            "Install the optional dependency to enable downloads."
        )
        return None

    credentials_json = os.environ.get("GOOGLE_DRIVE_CREDENTIALS")
    credentials_path = os.environ.get("GOOGLE_DRIVE_CREDENTIALS_PATH")

    if not credentials_json and credentials_path and os.path.exists(credentials_path):
        with open(credentials_path, "r", encoding="utf-8") as f:
            credentials_json = f.read()

    if not credentials_json:
        print(
            "Google Drive credentials not provided. "
            "Set GOOGLE_DRIVE_CREDENTIALS or GOOGLE_DRIVE_CREDENTIALS_PATH."
        )
        return None

    try:
        info = json.loads(credentials_json)
        scopes = ["https://www.googleapis.com/auth/drive.readonly"]
        credentials = service_account.Credentials.from_service_account_info(
            info, scopes=scopes
        )
        service = build("drive", "v3", credentials=credentials, cache_discovery=False)
        return service
    except Exception as exc:
        print(f"Failed to initialize Google Drive service: {exc}")
        return None


def download_resumes_from_drive(
    folder_id: str, dest_dir: str = "resumes", drive_service: Optional[object] = None
) -> None:
    """Download PDF and DOCX resumes from a Google Drive folder.

    Args:
        folder_id: Google Drive folder ID containing resumes.
        dest_dir: Local directory where the resumes will be saved.
        drive_service: Optional preconfigured Drive service (useful for testing).
    """

    service = drive_service or _build_drive_service()
    if service is None:
        return

    if MediaIoBaseDownload is None:
        print(
            "google-api-python-client is required for Drive downloads. "
            "Install the optional dependency to enable this feature."
        )
        return

    os.makedirs(dest_dir, exist_ok=True)

    query = (
        f"'{folder_id}' in parents and trashed=false and ("
        "mimeType='application/pdf' or "
        "mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document')"
    )

    page_token = None
    while True:
        try:
            response = (
                service.files()
                .list(
                    q=query,
                    spaces="drive",
                    pageToken=page_token,
                    fields="nextPageToken, files(id, name, mimeType)",
                )
                .execute()
            )
        except Exception as exc:
            print(f"Error listing files from Drive: {exc}")
            return

        for file in response.get("files", []):
            filename = file.get("name")
            if not filename:
                continue

            destination = os.path.join(dest_dir, filename)
            if os.path.exists(destination):
                print(f"Skipping download for {filename}; file already exists.")
                continue

            try:
                request = service.files().get_media(fileId=file["id"])
                with io.FileIO(destination, "wb") as fh:
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                        if status:
                            progress = int(status.progress() * 100)
                            print(f"Downloading {filename}: {progress}%")
                print(f"Downloaded {filename} to {destination}")
            except Exception as exc:  # pragma: no cover - external API errors
                print(f"Failed to download {filename}: {exc}")

        page_token = response.get("nextPageToken")
        if not page_token:
            break
