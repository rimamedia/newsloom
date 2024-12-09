import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import TestCase
from streams.models import Stream, StreamLog


class StreamExecutionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a test stream with valid configuration
        cls.stream = Stream.objects.create(
            name="Test Stream",
            stream_type="telegram_test",
            frequency="5min",
            status="active",
            configuration={
                "channel_id": "-1001234567890",
                "bot_token": "test_bot_token",
            },
        )

    def setUp(self):
        # Clear cache before each test
        cache.clear()

    def tearDown(self):
        cache.clear()

    @patch("streams.tasks.get_task_function")
    def test_successful_task_execution(self, mock_get_task_function):
        # Mock the task function
        mock_task = Mock(return_value={"status": "success"})
        mock_get_task_function.return_value = mock_task

        # Execute the task
        self.stream.execute_task()

        # Check that task was called with correct parameters
        mock_task.assert_called_once_with(
            stream_id=self.stream.id,
            channel_id="-1001234567890",
            bot_token="test_bot_token",
        )

        # Verify stream log was created
        log = StreamLog.objects.get(stream=self.stream)
        self.assertEqual(log.status, "success")
        self.assertIsNotNone(log.completed_at)

        # Verify next_run was updated correctly
        expected_next_run = self.stream.last_run + timedelta(minutes=5)
        self.assertEqual(self.stream.next_run, expected_next_run)

    def test_locked_stream_execution(self):
        # Set lock in cache
        cache.add(f"stream_lock_{self.stream.id}", "1", timeout=300)

        # Try to execute the task
        self.stream.execute_task()

        # Verify stream log indicates locked status
        log = StreamLog.objects.get(stream=self.stream)
        self.assertEqual(log.status, "failed")
        self.assertEqual(log.error_message, "Stream is locked")

    @patch("streams.tasks.get_task_function")
    def test_task_function_not_found(self, mock_get_task_function):
        # Mock task function not found
        mock_get_task_function.return_value = None

        # Execute the task
        self.stream.execute_task()

        # Verify stream log indicates error
        log = StreamLog.objects.get(stream=self.stream)
        self.assertEqual(log.status, "failed")
        self.assertIn("No task function found", log.error_message)

    @patch("streams.tasks.get_task_function")
    def test_task_execution_failure(self, mock_get_task_function):
        # Mock task function that raises an exception
        mock_task = Mock(side_effect=Exception("Task failed"))
        mock_get_task_function.return_value = mock_task

        # Execute the task and expect exception
        with self.assertRaisesRegex(Exception, "Task failed"):
            self.stream.execute_task()

        # Verify stream log indicates failure
        log = StreamLog.objects.get(stream=self.stream)
        self.assertEqual(log.status, "failed")
        self.assertEqual(log.error_message, "Task failed")

        # Verify stream status was updated
        self.stream.refresh_from_db()
        self.assertEqual(self.stream.status, "failed")

    @patch("streams.tasks.get_task_function")
    @patch("streams.models.StreamLog.objects.create")
    @patch("streams.models.Stream.save")
    def test_concurrent_execution_prevention(
        self, mock_save, mock_create_log, mock_get_task_function
    ):
        execution_count = 0
        lock = threading.Lock()

        def count_execution(*args, **kwargs):
            nonlocal execution_count
            with lock:
                execution_count += 1
                return {"status": "success"}

        mock_task = Mock(side_effect=count_execution)
        mock_get_task_function.return_value = mock_task
        mock_create_log.return_value = Mock()
        mock_save.return_value = None

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(self.stream.execute_task) for _ in range(3)]
            for future in futures:
                future.result()

        self.assertEqual(execution_count, 1)
