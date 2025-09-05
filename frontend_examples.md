# Frontend Integration Examples

This document provides examples for integrating OAuth2/OIDC authentication with your frontend application.

## JavaScript/React Example

### 1. Login with OAuth2 Providers

```javascript
// OAuth2 Login Component
import React, { useEffect, useState } from 'react';

const OAuth2Login = () => {
  const handleOAuth2Login = (provider) => {
    // Redirect to OAuth2 login endpoint
    window.location.href = `${process.env.REACT_APP_API_URL}/api/v1/auth/${provider}/login`;
  };

  return (
    <div className="oauth-login">
      <button onClick={() => handleOAuth2Login('google')}>
        Login with Google
      </button>
      <button onClick={() => handleOAuth2Login('github')}>
        Login with GitHub
      </button>
    </div>
  );
};

export default OAuth2Login;
```

### 2. Handle OAuth2 Callback

```javascript
// OAuth2 Callback Handler
import React, { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

const OAuth2Callback = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  useEffect(() => {
    const token = searchParams.get('token');
    
    if (token) {
      // Store token in localStorage or secure storage
      localStorage.setItem('access_token', token);
      
      // Redirect to dashboard or home page
      navigate('/dashboard');
    } else {
      // Handle error case
      navigate('/login?error=oauth_failed');
    }
  }, [searchParams, navigate]);

  return (
    <div className="oauth-callback">
      <p>Processing authentication...</p>
    </div>
  );
};

export default OAuth2Callback;
```

### 3. API Service with Authentication

```javascript
// api.js - API service with authentication
class ApiService {
  constructor() {
    this.baseURL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
  }

  getAuthHeaders() {
    const token = localStorage.getItem('access_token');
    return {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` })
    };
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      headers: this.getAuthHeaders(),
      credentials: 'include', // Include cookies for session-based auth
      ...options
    };

    try {
      const response = await fetch(url, config);
      
      if (response.status === 401) {
        // Redirect to login if unauthorized
        localStorage.removeItem('access_token');
        window.location.href = '/login';
        throw new Error('Unauthorized');
      }

      return await response.json();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // Authentication methods
  async getCurrentUser() {
    return this.request('/api/v1/auth/me');
  }

  async getSessionInfo() {
    return this.request('/api/v1/auth/session');
  }

  async logout() {
    await this.request('/api/v1/auth/logout', { method: 'POST' });
    localStorage.removeItem('access_token');
  }
}

export const apiService = new ApiService();
```

### 4. Authentication Context

```javascript
// AuthContext.js - React context for authentication
import React, { createContext, useContext, useEffect, useState } from 'react';
import { apiService } from './api';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const userData = await apiService.getCurrentUser();
      setUser(userData);
    } catch (error) {
      // User not authenticated
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = (provider) => {
    window.location.href = `${apiService.baseURL}/api/v1/auth/${provider}/login`;
  };

  const logout = async () => {
    try {
      await apiService.logout();
      setUser(null);
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  const value = {
    user,
    loading,
    login,
    logout,
    isAuthenticated: !!user
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
```

### 5. Protected Route Component

```javascript
// ProtectedRoute.js
import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from './AuthContext';

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return <div>Loading...</div>;
  }

  return isAuthenticated ? children : <Navigate to="/login" replace />;
};

export default ProtectedRoute;
```

## Vue.js Example

### 1. OAuth2 Login Component

```vue
<template>
  <div class="oauth-login">
    <button @click="loginWith('google')" class="google-btn">
      Login with Google
    </button>
    <button @click="loginWith('github')" class="github-btn">
      Login with GitHub
    </button>
  </div>
</template>

<script>
export default {
  name: 'OAuth2Login',
  methods: {
    loginWith(provider) {
      const apiUrl = process.env.VUE_APP_API_URL || 'http://localhost:8000';
      window.location.href = `${apiUrl}/api/v1/auth/${provider}/login`;
    }
  }
};
</script>
```

### 2. Authentication Store (Vuex/Pinia)

```javascript
// auth.store.js (Pinia)
import { defineStore } from 'pinia';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    token: localStorage.getItem('access_token'),
    loading: false
  }),

  getters: {
    isAuthenticated: (state) => !!state.user,
    authHeaders: (state) => ({
      'Content-Type': 'application/json',
      ...(state.token && { Authorization: `Bearer ${state.token}` })
    })
  },

  actions: {
    async fetchUser() {
      if (!this.token) return;
      
      try {
        this.loading = true;
        const response = await fetch('/api/v1/auth/me', {
          headers: this.authHeaders,
          credentials: 'include'
        });
        
        if (response.ok) {
          this.user = await response.json();
        } else {
          this.logout();
        }
      } catch (error) {
        console.error('Failed to fetch user:', error);
        this.logout();
      } finally {
        this.loading = false;
      }
    },

    async logout() {
      try {
        await fetch('/api/v1/auth/logout', {
          method: 'POST',
          headers: this.authHeaders,
          credentials: 'include'
        });
      } catch (error) {
        console.error('Logout failed:', error);
      } finally {
        this.user = null;
        this.token = null;
        localStorage.removeItem('access_token');
      }
    },

    setToken(token) {
      this.token = token;
      localStorage.setItem('access_token', token);
      this.fetchUser();
    }
  }
});
```

## Environment Variables

Create a `.env` file in your frontend project:

```bash
# React
REACT_APP_API_URL=http://localhost:8000

# Vue.js
VUE_APP_API_URL=http://localhost:8000

# Next.js
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Security Best Practices

1. **Token Storage**: Store JWT tokens securely (httpOnly cookies preferred over localStorage)
2. **HTTPS**: Always use HTTPS in production
3. **CSRF Protection**: Include CSRF tokens when necessary
4. **Token Refresh**: Implement token refresh logic for long-lived sessions
5. **Logout**: Properly clear tokens and redirect on logout
6. **Error Handling**: Handle authentication errors gracefully

## CORS Configuration

Ensure your backend CORS settings match your frontend domain:

```python
# In your FastAPI app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```