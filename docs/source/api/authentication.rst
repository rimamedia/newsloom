Authentication
=============

The Newsloom API uses token-based authentication. To access protected endpoints, you need to obtain an authentication token by logging in with your credentials.

Login
-----

.. http:post:: /api/login/

   Authenticate a user and retrieve a token.

   **Example request**:

   .. sourcecode:: http

      POST /api/login/ HTTP/1.1
      Host: example.com
      Content-Type: application/json

      {
          "username": "your_username",
          "password": "your_password"
      }

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
          "user_id": 1,
          "username": "your_username"
      }

   :reqheader Content-Type: application/json
   :resheader Content-Type: application/json
   :statuscode 200: Login successful
   :statuscode 400: Invalid credentials

Using the Token
--------------

Once you have obtained a token, include it in the ``Authorization`` header of all subsequent requests:

.. sourcecode:: http

   GET /api/users/ HTTP/1.1
   Host: example.com
   Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b

JavaScript Example
----------------

Here's a complete example of how to authenticate and make API requests using JavaScript:

.. code-block:: javascript

   // Login function
   async function login(username, password) {
     try {
       const response = await fetch('http://your-backend-url/api/login/', {
         method: 'POST',
         headers: {
           'Content-Type': 'application/json',
         },
         body: JSON.stringify({
           username: username,
           password: password
         })
       });

       if (!response.ok) {
         throw new Error('Login failed');
       }

       const data = await response.json();
       // Store the token
       localStorage.setItem('authToken', data.token);
       return data;
     } catch (error) {
       console.error('Login error:', error);
       throw error;
     }
   }

   // Making authenticated requests
   async function makeAuthenticatedRequest(url, method = 'GET', body = null) {
     const token = localStorage.getItem('authToken');
     
     try {
       const response = await fetch(url, {
         method: method,
         headers: {
           'Authorization': `Token ${token}`,
           'Content-Type': 'application/json',
         },
         body: body ? JSON.stringify(body) : null
       });

       if (!response.ok) {
         throw new Error('Request failed');
       }

       return await response.json();
     } catch (error) {
       console.error('Request error:', error);
       throw error;
     }
   }

   // Usage example
   login('username', 'password')
     .then(data => {
       console.log('Logged in successfully', data);
       
       // Make authenticated requests
       return makeAuthenticatedRequest('http://your-backend-url/api/users/');
     })
     .then(userData => {
       console.log('User data:', userData);
     })
     .catch(error => {
       console.error('Error:', error);
     });

CORS Support
-----------

The API supports Cross-Origin Resource Sharing (CORS), allowing you to make requests from different domains. This is particularly useful for frontend applications running on different domains or local development servers.

Error Handling
-------------

The API uses standard HTTP status codes:

- 200: Success
- 400: Bad Request (e.g., invalid credentials)
- 401: Unauthorized (missing or invalid token)
- 403: Forbidden (valid token but insufficient permissions)
- 404: Not Found
- 500: Internal Server Error

Security Considerations
---------------------

1. Always use HTTPS in production
2. Store tokens securely (e.g., in localStorage or secure cookie)
3. Implement token refresh mechanism for long-running applications
4. Clear tokens on logout
5. Set appropriate CORS policies in production
