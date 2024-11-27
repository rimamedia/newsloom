Creating Stream Schemas
====================

Schema Development Guide
---------------------

NewLoom uses Pydantic for schema validation. Here's how to create and implement new schemas:

Basic Schema Structure
-------------------

.. code-block:: python

    from pydantic import BaseModel, HttpUrl, Field
    from typing import Optional, Dict, List

    class MyNewSchema(BaseModel):
        """Schema description"""
        
        # Required fields
        url: HttpUrl
        max_items: int = Field(gt=0, le=1000)
        
        # Optional fields
        custom_field: Optional[str] = None
        
        class Config:
            extra = 'forbid'  # Prevent additional fields

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

2. Validation
~~~~~~~~~~~

Add field validators:

.. code-block:: python

    from pydantic import field_validator
    
    class MySchema(BaseModel):
        field_name: str
        
        @field_validator('field_name')
        def validate_field(cls, v):
            if not v.startswith('valid_'):
                raise ValueError("Field must start with 'valid_'")
            return v

3. Configuration
~~~~~~~~~~~~~

Set schema configuration:

.. code-block:: python

    class Config:
        extra = 'forbid'  # Prevent additional fields
        arbitrary_types_allowed = True  # Allow custom types
        json_schema_extra = {
            "examples": [
                {
                    "url": "https://example.com",
                    "max_items": 100
                }
            ]
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