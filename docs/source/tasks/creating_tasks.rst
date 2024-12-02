Creating New Tasks
================

Task Development Guide
--------------------

To create a new task in NewLoom, you'll need to:

1. Create a new task function
2. Define the task schema
3. Register the task
4. Implement the task logic

Basic Task Structure
------------------

All NewLoom tasks should be defined as functions and follow this basic structure:

.. code-block:: python

    def my_new_task(stream_id, **kwargs):
        """Task description"""
        
        # Task implementation
        try:
            # Task logic
            pass
        except Exception as e:
            # Error handling
            raise e

Required Components
-----------------

1. Parameters
~~~~~~~~~~~~

Every task must include these base parameters:

- ``stream_id``: Links the task to a Stream model instance

2. Task Logic
~~~~~~~~~~~~

The task function should:

- Implement the task's core logic
- Handle exceptions appropriately
- Update stream status
- Log task progress

Registering Tasks
---------------

After creating your task, register it in the task mapping:

.. code-block:: python

    # streams/tasks/__init__.py
    TASK_MAPPING = {
        'my_new_task': my_new_task,
        # ... other tasks
    }

Error Handling
------------

Implement proper error handling in your tasks:

.. code-block:: python

    def my_new_task(stream_id, **kwargs):
        from streams.models import Stream
        logger = logging.getLogger(__name__)
        
        try:
            # Task implementation
            stream = Stream.objects.get(id=stream_id)
            # ... task logic ...
            
            # Update success status
            stream.last_run = timezone.now()
            stream.save(update_fields=['last_run'])
            
        except Exception as e:
            logger.error(f"Task error: {str(e)}", exc_info=True)
            Stream.objects.filter(id=stream_id).update(
                status='failed',
                last_run=timezone.now()
            )
            raise e

Best Practices
------------

1. Documentation
   - Include detailed docstrings
   - Document parameters
   - Provide usage examples

2. Error Handling
   - Use try-except blocks
   - Log errors with context
   - Update stream status

3. Resource Management
   - Close connections
   - Clean up temporary files
   - Use context managers

4. Testing
   - Write unit tests
   - Test error cases
   - Mock external services 