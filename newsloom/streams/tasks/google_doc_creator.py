import logging
import time
from typing import Dict

from django.utils import timezone
from google.oauth2 import service_account
from googleapiclient.discovery import build
from sources.models import Doc

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def get_google_services(service_account_path: str):
    """Initialize Google Drive and Docs API services."""
    try:
        credentials = service_account.Credentials.from_service_account_file(
            service_account_path, scopes=SCOPES
        )
        drive_service = build("drive", "v3", credentials=credentials)
        docs_service = build("docs", "v1", credentials=credentials)
        return drive_service, docs_service
    except Exception as e:
        logger.error(f"Failed to initialize Google services: {e}")
        raise


def create_google_doc(
    title: str,
    content: str,
    folder_id: str,
    drive_service,
    docs_service,
    template_id: str | None = None,
) -> str:
    """Create a new Google Doc and return its URL."""
    try:
        if template_id:
            # Copy template
            file = (
                drive_service.files()
                .copy(fileId=template_id, body={"name": title, "parents": [folder_id]})
                .execute()
            )
        else:
            # Create new empty document
            file = (
                drive_service.files()
                .create(
                    body={
                        "name": title,
                        "mimeType": "application/vnd.google-apps.document",
                        "parents": [folder_id],
                    }
                )
                .execute()
            )

        doc_id = file.get("id")

        # Update document content
        requests = [{"insertText": {"location": {"index": 1}, "text": content}}]

        docs_service.documents().batchUpdate(
            documentId=doc_id, body={"requests": requests}
        ).execute()

        return f"https://docs.google.com/document/d/{doc_id}/edit"

    except Exception as e:
        logger.error(f"Failed to create Google Doc: {e}")
        raise


def google_doc_creator(
    stream_id: int,
    folder_id: str,
    template_id: str | None = None,
    service_account_path: str = "credentials.json",
) -> Dict:
    """Process docs and create Google Docs for them."""
    from streams.models import Stream

    stream = Stream.objects.get(id=stream_id)

    # Get docs that need processing (status='new')
    docs = Doc.objects.filter(
        status="new", media=stream.media, google_doc_link__isnull=True
    ).order_by("created_at")

    if not docs.exists():
        return {"message": "No new docs to process"}

    drive_service, docs_service = get_google_services(service_account_path)
    processed = 0
    failed = 0

    for doc in docs:
        try:
            # Create Google Doc
            google_doc_link = create_google_doc(
                title=doc.title or "Untitled",
                content=doc.text or "",
                folder_id=folder_id,
                drive_service=drive_service,
                docs_service=docs_service,
                template_id=template_id,
            )

            # Update doc with Google Doc link and status
            doc.google_doc_link = google_doc_link
            doc.status = "edit"
            doc.published_at = timezone.now()
            doc.save()

            processed += 1

            # Add a small delay to avoid rate limiting
            time.sleep(1)

        except Exception as e:
            logger.error(f"Failed to process doc {doc.id}: {e}")
            doc.status = "failed"
            doc.save()
            failed += 1

    return {"processed": processed, "failed": failed, "total": len(docs)}
