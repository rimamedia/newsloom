import logging

from django.utils import timezone
from streams.models import Stream


def scrape_web_article(stream_id, base_url, selectors, headers):
    logger = logging.getLogger(__name__)
    result = {
        "scraped_count": 0,
        "errors": [],
        "timestamp": timezone.now().isoformat(),
        "stream_id": stream_id,
    }

    try:
        # TODO: Implement web article scraping logic
        # Use base_url, selectors, and headers to scrape the web article
        # Update result["scraped_count"] and handle any errors

        # Example:
        # response = requests.get(base_url, headers=headers)
        # soup = BeautifulSoup(response.content, 'html.parser')
        # title = soup.select_one(selectors['title']).get_text()
        # content = soup.select_one(selectors['content']).get_text()
        # date = soup.select_one(selectors['date']).get_text()

        # Save scraped data to the database

        stream = Stream.objects.get(id=stream_id)
        stream.last_run = timezone.now()
        stream.save(update_fields=["last_run"])

    except Exception as e:
        logger.error(f"Error scraping web article: {str(e)}", exc_info=True)
        result["errors"].append(str(e))
        Stream.update_status(stream_id, status="failed")
        raise e

    return result
