import tempfile
from datetime import datetime

import luigi


class WebArticleScrapingTask(luigi.Task):
    stream_id = luigi.IntParameter()
    scheduled_time = luigi.DateTimeParameter()

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
