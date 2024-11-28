import tempfile
from datetime import datetime

import luigi


class TelegramChannelMonitorTask(luigi.Task):
    stream_id = luigi.IntParameter()
    scheduled_time = luigi.DateTimeParameter()

    def run(self):
        # TODO: Implement Telegram channel monitoring
        pass

    def output(self):
        temp_file = tempfile.NamedTemporaryFile(
            prefix=f"telegram_task_{self.stream_id}_",
            suffix=f'_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            delete=False,
        )
        return luigi.LocalTarget(temp_file.name)
