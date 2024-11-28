import luigi


class WebArticleScrapingTask(luigi.Task):
    stream_id = luigi.IntParameter()
    scheduled_time = luigi.DateTimeParameter()

    def run(self):
        # TODO: Implement web article scraping
        pass

    def output(self):
        return luigi.LocalTarget(f"/tmp/web_task_{self.stream_id}")
