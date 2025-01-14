from pydantic import BaseModel


class BaseConfig(BaseModel):
    """Base configuration class for all stream configurations.

    This class sets up common configuration for all stream schemas,
    including allowing extra fields to be provided without validation errors.
    """

    model_config = {"extra": "ignore"}  # Allow but ignore any extra fields
