import tempfile
from datetime import datetime

import luigi


class WebArticleScrapingTask(luigi.Task):
    stream_id = luigi.IntParameter()
    scheduled_time = luigi.DateTimeParameter()

    @classmethod
    def get_config_example(cls):
        return {
            "base_url": "https://example.com",
            "selectors": {
                "title": "h1.article-title",
                "content": "div.article-content",
                "date": "time.published-date",
            },
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"  # noqa: E501
            },
        }

    def run(self):
        # TODO: Implement web article scraping
        pass

    def output(self):
        temp_file = tempfile.NamedTemporaryFile(
            prefix=f"web_task_{self.stream_id}_",
            suffix=f'_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            delete=False,
        )
        return luigi.LocalTarget(temp_file.name)
