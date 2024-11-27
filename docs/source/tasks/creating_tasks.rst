Creating New Tasks
================

Task Development Guide
--------------------

To create a new task in NewLoom, you'll need to:

1. Create a new task class
2. Define the task schema
3. Register the task
4. Implement the task logic

Basic Task Structure
------------------

All NewLoom tasks should inherit from ``luigi.Task`` and follow this basic structure:

.. code-block:: python

    import luigi
    from django.utils import timezone
    
    class MyNewTask(luigi.Task):
        """Task description"""
        
        # Required parameters
        stream_id = luigi.IntParameter(description="ID of the Stream model instance")
        scheduled_time = luigi.Parameter(description="Scheduled execution time")
        
        # Custom parameters
        my_param = luigi.Parameter(description="Custom parameter")
        
        def run(self):
            try:
                # Task implementation
                pass
            except Exception as e:
                # Error handling
                raise e
        
        def output(self):
            return luigi.LocalTarget(
                f'/tmp/my_task_{self.stream_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
            )

Required Components
-----------------

1. Parameters
~~~~~~~~~~~~

Every task must include these base parameters:

- ``stream_id``: Links the task to a Stream model instance
- ``scheduled_time``: Defines when the task should run

2. Run Method
~~~~~~~~~~~~

The ``run()`` method should:

- Implement the task's core logic
- Handle exceptions appropriately
- Update stream status
- Log task progress

3. Output Method
~~~~~~~~~~~~~~

The ``output()`` method should:

- Return a ``luigi.Target`` instance
- Include unique identifiers (stream_id, timestamp)
- Use appropriate target type (LocalTarget, S3Target, etc.)

Registering Tasks
---------------

After creating your task, register it in the task mapping:

.. code-block:: python

    # streams/tasks/__init__.py
    TASK_MAPPING = {
        'my_new_task': MyNewTask,
        # ... other tasks
    }

Error Handling
------------

Implement proper error handling in your tasks:

.. code-block:: python

    def run(self):
        from streams.models import Stream
        logger = logging.getLogger(__name__)
        
        try:
            # Task implementation
            stream = Stream.objects.get(id=self.stream_id)
            # ... task logic ...
            
            # Update success status
            stream.last_run = timezone.now()
            stream.save(update_fields=['last_run'])
            
        except Exception as e:
            logger.error(f"Task error: {str(e)}", exc_info=True)
            Stream.objects.filter(id=self.stream_id).update(
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