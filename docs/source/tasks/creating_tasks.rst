Creating New Tasks
================

Complete Task Implementation Guide
------------------------------

To create a new task in NewLoom, you need to implement and integrate several components:

1. Create a Configuration Schema
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a new file in ``streams/schemas/`` to define your task's configuration:

.. code-block:: python

    # streams/schemas/my_task.py
    from pydantic import BaseModel, Field
    
    class MyTaskConfig(BaseModel):
        """Configuration schema for my task."""
        
        parameter1: str = Field(
            ...,  # ... means required
            description="Description of parameter1",
            example="example value"
        )
        parameter2: int = Field(
            default=10,  # default value if not provided
            description="Description of parameter2",
            ge=1,  # greater than or equal to 1
            le=100  # less than or equal to 100
        )

2. Register the Schema
~~~~~~~~~~~~~~~~~~~

Add your schema to ``streams/schemas/__init__.py``:

.. code-block:: python

    from .my_task import MyTaskConfig
    
    STREAM_CONFIG_SCHEMAS = {
        "my_task": MyTaskConfig,
        # ... other schemas
    }

3. Create Task Implementation
~~~~~~~~~~~~~~~~~~~~~~~~~

Create a new file in ``streams/tasks/`` for your task implementation:

Basic Task Structure
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    def my_task(stream_id: int, **kwargs) -> Dict:
        """
        Task description and purpose.

        Args:
            stream_id: ID of the stream
            **kwargs: Configuration parameters defined in MyTaskConfig
        """
        result = {
            "extracted_count": 0,
            "saved_count": 0,
            "timestamp": timezone.now().isoformat(),
            "stream_id": stream_id,
        }
        
        try:
            # Get stream
            stream = Stream.objects.get(id=stream_id)
            
            # Task implementation
            # ...
            
            return result
            
        except Exception as e:
            logger.error(f"Task error: {str(e)}", exc_info=True)
            Stream.objects.filter(id=stream_id).update(
                status='failed',
                last_run=timezone.now()
            )
            raise e

4. Register the Task
~~~~~~~~~~~~~~~~~

Add your task to ``streams/tasks/__init__.py``:

.. code-block:: python

    from .my_task import my_task
    
    TASK_MAPPING = {
        "my_task": my_task,
        # ... other tasks
    }
    
    # Add configuration example
    TASK_CONFIG_EXAMPLES = {
        "my_task": {
            "parameter1": "example value",
            "parameter2": 50
        },
        # ... other examples
    }

5. Add to Stream Model
~~~~~~~~~~~~~~~~~~~

Add your task type to ``streams/models.py``:

.. code-block:: python

    class Stream(models.Model):
        TYPE_CHOICES = [
            ("my_task", "My Task Name"),
            # ... other tasks
        ]

6. Document the Task
~~~~~~~~~~~~~~~~~

Add your task to ``docs/source/tasks/available_tasks.rst``:

.. code-block:: rst

    My Task
    ~~~~~~~
    - Type: ``my_task``
    - Description: What your task does
    - Key Features:
        * Feature 1
        * Feature 2
        * Feature 3

Error Handling and Best Practices
-----------------------------

1. Error Handling
~~~~~~~~~~~~~~

Always implement proper error handling:

.. code-block:: python

    try:
        # Task logic
        pass
    except Exception as e:
        logger.error(f"Task error: {str(e)}", exc_info=True)
        Stream.objects.filter(id=stream_id).update(
            status='failed',
            last_run=timezone.now()
        )
        raise e

2. Best Practices
~~~~~~~~~~~~~~

1. Documentation
   - Include detailed docstrings with type hints
   - Document all parameters and return values
   - Provide configuration examples
   - Update available_tasks.rst with features list

2. Configuration Schema
   - Use pydantic Field for parameter validation
   - Include descriptions and examples
   - Set appropriate value constraints
   - Make parameters required or optional as needed

3. Resource Management
   - Use context managers for resources (with statements)
   - Close connections and files properly
   - Clean up temporary resources
   - Handle browser/API sessions appropriately

4. Testing
   - Write unit tests for your task
   - Test configuration validation
   - Test error cases
   - Mock external services and APIs

5. Logging
   - Use appropriate log levels (debug, info, warning, error)
   - Include context in log messages
   - Log start/end of operations
   - Log important state changes

6. Performance
   - Use connection pooling where appropriate
   - Implement proper timeouts
   - Consider batch operations
   - Handle pagination for large datasets

Example Implementation
-------------------

The following example demonstrates how to implement a task that performs Google searches with time-based filtering:

1. Configuration Schema:

.. code-block:: python

    # streams/schemas/google_search.py
    class GoogleSearchConfig(BaseModel):
        keywords: List[str] = Field(
            ...,
            description="List of keywords to search for",
            example=["climate change", "renewable energy"],
        )
        days_ago: Optional[int] = Field(
            default=None,
            description="Filter results from the last X days",
            ge=1,
            le=365,
        )

2. Task Implementation:

.. code-block:: python

    # streams/tasks/google_search.py
    @cancellable_task
    def search_google(
        stream_id: int,
        keywords: List[str],
        days_ago: Optional[int] = None,
        **kwargs
    ) -> Dict:
        result = {
            "extracted_count": 0,
            "saved_count": 0,
            "links": [],
        }
        try:
            # Implementation...
            pass
        except Exception as e:
            logger.error(f"Error in Google search: {str(e)}")
            raise e

3. Integration:

.. code-block:: python

    # streams/tasks/__init__.py
    TASK_MAPPING = {
        "google_search": search_google,
    }
    
    TASK_CONFIG_EXAMPLES = {
        "google_search": {
            "keywords": ["example search"],
            "days_ago": 7,
        }
    }

    # streams/schemas/__init__.py
    STREAM_CONFIG_SCHEMAS = {
        "google_search": GoogleSearchConfig,
    }

    # streams/models.py
    TYPE_CHOICES = [
        ("google_search", "Google Search"),
    ]

For a complete example of a task implementation, see the following files:

- Schema: ``streams/schemas/google_search.py``
- Task: ``streams/tasks/google_search.py``
- Integration: Updates to ``__init__.py``, ``models.py``, and documentation

This example demonstrates proper configuration validation, error handling, resource management, and integration with the NewLoom system.
