Creating Stream Schemas
====================

Schema Development Guide
---------------------

NewLoom uses Pydantic v2 for schema validation. All stream configuration schemas inherit from a base configuration class that provides common functionality.

Base Configuration
---------------

All stream schemas inherit from BaseConfig:

.. code-block:: python

    from pydantic import BaseModel

    class BaseConfig(BaseModel):
        """Base configuration class for all stream configurations."""
        
        model_config = {
            "extra": "ignore"  # Allow but ignore any extra fields
        }

Basic Schema Structure
-------------------

Create new schemas by inheriting from BaseConfig:

.. code-block:: python

    from pydantic import HttpUrl, Field
    from typing import Optional, Dict, List
    from .base_model import BaseConfig

    class MyNewSchema(BaseConfig):
        """Schema description"""
        
        # Required fields
        url: HttpUrl
        max_items: int = Field(gt=0, le=1000)
        
        # Optional fields
        custom_field: Optional[str] = None

Schema Components
--------------

1. Field Types
~~~~~~~~~~~~

Common field types:

- ``HttpUrl``: For URL validation
- ``int``: With Field constraints
- ``str``: For text fields
- ``Dict``: For nested configurations
- ``List``: For arrays
- ``bool``: For flags
- ``Optional``: For optional fields

2. Validation
~~~~~~~~~~~

Add field validators using Pydantic v2 syntax:

.. code-block:: python

    from pydantic import field_validator
    
    class MySchema(BaseConfig):
        field_name: str
        
        @field_validator('field_name')
        def validate_field(cls, v: str) -> str:
            if not v.startswith('valid_'):
                raise ValueError("Field must start with 'valid_'")
            return v

3. Configuration
~~~~~~~~~~~~~

Schema configuration is handled through model_config:

.. code-block:: python

    class MySchema(BaseConfig):
        model_config = {
            "json_schema_extra": {
                "examples": [
                    {
                        "url": "https://example.com",
                        "max_items": 100
                    }
                ]
            }
        }

Registering Schemas
----------------

Register your schema in the schema mapping:

.. code-block:: python

    # streams/schemas.py
    STREAM_CONFIG_SCHEMAS = {
        'my_new_stream': MyNewSchema,
        # ... other schemas
    }

Schema Validation
--------------

The Stream model automatically validates configurations:

.. code-block:: python

    def clean(self):
        try:
            config_schema = STREAM_CONFIG_SCHEMAS.get(self.stream_type)
            if config_schema:
                validated_config = config_schema(**self.configuration)
                self.configuration = json.loads(validated_config.model_dump_json())
        except ValidationError as e:
            raise ValidationError(f"Configuration validation failed: {e}")

Best Practices
------------

1. Documentation
   - Document all fields
   - Provide examples
   - Explain validation rules

2. Validation
   - Use appropriate field types
   - Add custom validators
   - Set reasonable limits

3. Testing
   - Test valid configurations
   - Test invalid configurations
   - Test edge cases
