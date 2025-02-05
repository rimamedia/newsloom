from unittest import TestCase
from unittest.mock import patch

from streams.tasks.news_stream import validate_aws_credentials


class TestNewsStream(TestCase):
    @patch.dict(
        "os.environ",
        {
            "BEDROCK_AWS_ACCESS_KEY_ID": "test-key",
            "BEDROCK_AWS_SECRET_ACCESS_KEY": "test-secret",
            "BEDROCK_AWS_REGION": "us-east-1",
        },
        clear=True,
    )  # Clear ensures no other env vars exist
    def test_validate_aws_credentials_success(self):
        """Test AWS credentials validation with all required variables."""
        is_valid, error_msg = validate_aws_credentials()
        self.assertTrue(is_valid)
        self.assertIsNone(error_msg)

    @patch.dict(
        "os.environ",
        {
            "BEDROCK_AWS_ACCESS_KEY_ID": "test-key",
            # Missing SECRET_ACCESS_KEY and REGION
        },
        clear=True,
    )  # Clear ensures no other env vars exist
    def test_validate_aws_credentials_missing_vars(self):
        """Test AWS credentials validation with missing variables."""
        is_valid, error_msg = validate_aws_credentials()
        self.assertFalse(is_valid)
        self.assertIn("BEDROCK_AWS_SECRET_ACCESS_KEY", error_msg)
        self.assertIn("BEDROCK_AWS_REGION", error_msg)
