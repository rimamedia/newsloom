import logging
import os
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
    logger.info(
        f"Initializing Google services using credentials from: {service_account_path}"
    )
    try:
        logger.debug("Loading service account credentials")
        credentials = service_account.Credentials.from_service_account_file(
            service_account_path, scopes=SCOPES
        )
        logger.debug("Building Drive service")
        drive_service = build("drive", "v3", credentials=credentials)
        logger.debug("Building Docs service")
        docs_service = build("docs", "v1", credentials=credentials)
        logger.info("Successfully initialized Google services")
        return drive_service, docs_service
    except Exception as e:
        logger.error(f"Failed to initialize Google services: {e}", exc_info=True)
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
    logger.info(f"Creating new Google Doc: '{title}' in folder: {folder_id}")
    try:
        if template_id:
            logger.debug(f"Using template ID: {template_id}")
            # Copy template
            file = (
                drive_service.files()
                .copy(fileId=template_id, body={"name": title, "parents": [folder_id]})
                .execute()
            )
            logger.debug("Successfully copied template to new doc")
        else:
            logger.debug("Creating new empty document")
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
        logger.debug(f"Created document with ID: {doc_id}")

        # Update document content
        content_length = len(content)
        logger.debug(f"Updating document content (length: {content_length} characters)")
        requests = [{"insertText": {"location": {"index": 1}, "text": content}}]

        docs_service.documents().batchUpdate(
            documentId=doc_id, body={"requests": requests}
        ).execute()
        logger.info(f"Successfully created and populated Google Doc with ID: {doc_id}")

        doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
        logger.debug(f"Document URL: {doc_url}")
        return doc_url

    except Exception as e:
        logger.error(f"Failed to create Google Doc '{title}': {e}", exc_info=True)
        raise


def google_doc_creator(
    stream_id: int,
    folder_id: str,
    template_id: str | None = None,
    service_account_path: str | None = None,
) -> Dict:
    """Process docs and create Google Docs for them.

    The credentials file path is resolved in the following order:
    1. Explicitly provided service_account_path parameter
    2. GOOGLE_APPLICATION_CREDENTIALS environment variable
    3. Default path relative to project root (newsloom/credentials.json)
    """
    # Get credentials path from environment variable or use provided path or default
    credentials_path = (
        service_account_path
        or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "credentials.json",
        )
    )
    from streams.models import Stream

    logger.info(f"Starting Google Doc creator for stream ID: {stream_id}")
    logger.debug(f"Using folder ID: {folder_id}, template ID: {template_id}")

    stream = Stream.objects.get(id=stream_id)
    logger.debug(f"Found stream: {stream.name} (media: {stream.media})")

    # Get docs that need processing (status='new')
    docs = Doc.objects.filter(
        status="new", media=stream.media, google_doc_link__isnull=True
    ).order_by("created_at")

    doc_count = docs.count()
    logger.info(f"Found {doc_count} new docs to process")

    if not docs.exists():
        logger.info("No new docs to process")
        return {"message": "No new docs to process"}

    logger.debug(
        f"Initializing Google services with credentials path: {credentials_path}"
    )
    drive_service, docs_service = get_google_services(credentials_path)
    processed = 0
    failed = 0

    for doc in docs:
        logger.info(f"Processing doc ID: {doc.id} - '{doc.title or 'Untitled'}'")
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
            logger.debug(f"Updating doc {doc.id} with Google Doc link and status")
            doc.google_doc_link = google_doc_link
            doc.status = "edit"
            doc.published_at = timezone.now()
            doc.save()
            logger.info(
                f"Successfully processed doc {doc.id}, Google Doc created at: {google_doc_link}"
            )

            processed += 1

            # Add a small delay to avoid rate limiting
            logger.debug("Adding delay to avoid rate limiting")
            time.sleep(1)

        except Exception as e:
            logger.error(f"Failed to process doc {doc.id}: {e}", exc_info=True)
            doc.status = "failed"
            doc.save()
            failed += 1

    result = {"processed": processed, "failed": failed, "total": len(docs)}
    logger.info(f"Google Doc creator completed. Results: {result}")
    return result
