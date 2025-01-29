// Example of how to authenticate with the backend from a frontend application

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

// Example of how to make authenticated requests
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

// Usage example:
/*
// Login
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
*/
