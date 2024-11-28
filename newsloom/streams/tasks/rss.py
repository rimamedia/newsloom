import luigi

class RSSFeedParsingTask(luigi.Task):
    stream_id = luigi.IntParameter()
    scheduled_time = luigi.DateTimeParameter()
    
    def run(self):
        # TODO: Implement RSS feed parsing
        pass
    
    def output(self):
        return luigi.LocalTarget(f'/tmp/rss_task_{self.stream_id}') 