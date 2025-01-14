from pydantic import BaseModel


class ArticleanConfiguration(BaseModel):
    """Configuration for the Articlean task.

    Note:
        This task requires the following environment variables to be set:
        - ARTICLEAN_API_KEY: API key for authentication
        - ARTICLEAN_API_URL: Endpoint URL for the Articlean service
    """

    pass
