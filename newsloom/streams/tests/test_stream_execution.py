from datetime import timedelta
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import TestCase
from streams.models import Stream, StreamLog


class StreamExecutionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from django.utils import timezone

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
            next_run=timezone.now(),  # Set initial next_run time
        )

    def setUp(self):
        # Clear cache before each test
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_next_run_update_behavior(self):
        """Test that next_run is only set automatically when creating a new stream."""

        # Create a new stream and verify next_run is set
        stream = Stream.objects.create(
            name="Test Next Run",
            stream_type="telegram_test",
            frequency="5min",
            status="active",
            configuration={
                "channel_id": "-1001234567890",
                "bot_token": "test_bot_token",
            },
        )
        self.assertIsNotNone(stream.next_run)
        initial_next_run = stream.next_run

        # Update the stream and verify next_run doesn't change
        stream.name = "Updated Name"
        stream.save()
        stream.refresh_from_db()
        self.assertEqual(stream.next_run, initial_next_run)

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
