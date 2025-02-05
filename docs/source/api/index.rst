API Documentation
===============

This section covers the API endpoints available in the Newsloom project. NewLoom provides both RESTful HTTP endpoints and WebSocket connections for real-time updates.

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   authentication
   rest_endpoints
   websockets

Quick Start
----------

1. Authentication
   - See :doc:`authentication` for obtaining API tokens
   - Required for both REST and WebSocket endpoints

2. REST API
   - RESTful endpoints using Django REST Framework
   - JSON request/response format
   - Token or session authentication
   - See :doc:`rest_endpoints` for detailed documentation

3. WebSocket API
   - Real-time updates using Django Channels
   - JSON message format
   - Supports chat and stream status updates
   - See :doc:`websockets` for detailed documentation

API Versioning
------------

The current API version is v1. All endpoints are prefixed with ``/api/v1/``.

Rate Limiting
-----------

- REST API: 1000 requests per hour for authenticated users
- WebSocket: No strict message limit, but implement reasonable client-side throttling
