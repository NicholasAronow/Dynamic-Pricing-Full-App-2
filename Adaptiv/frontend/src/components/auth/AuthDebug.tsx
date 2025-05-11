import React, { useState, useEffect } from 'react';
import { Card, Button, Typography, Divider, Input, message, Alert, Space } from 'antd';
import axios from 'axios';

const { Title, Text, Paragraph } = Typography;

const AuthDebug: React.FC = () => {
  const [backendUrl, setBackendUrl] = useState<string>('');
  const [email, setEmail] = useState<string>('test@example.com');
  const [password, setPassword] = useState<string>('password123');
  const [response, setResponse] = useState<any>(null);
  const [error, setError] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [configLoading, setConfigLoading] = useState<boolean>(true);
  
  useEffect(() => {
    // Get the current API URL from the environment
    const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    console.log('Current API URL:', apiUrl);
    setBackendUrl(apiUrl);
    setConfigLoading(false);
  }, []);

  const testBackendConnection = async () => {
    setLoading(true);
    setError(null);
    setResponse(null);
    
    try {
      // Test if we can reach the backend at all
      const response = await axios.get(`${backendUrl}/api/auth/debug`);
      setResponse(response.data);
      message.success('Successfully connected to backend!');
    } catch (err: any) {
      console.error('Backend connection test error:', err);
      setError({
        message: err.message,
        status: err.response?.status,
        data: err.response?.data,
        config: {
          url: err.config?.url,
          method: err.config?.method
        }
      });
      message.error('Failed to connect to backend');
    } finally {
      setLoading(false);
    }
  };

  const testDebugRegister = async () => {
    setLoading(true);
    setError(null);
    setResponse(null);
    
    try {
      // Try to register using the debug endpoint
      const response = await axios.post(`${backendUrl}/api/auth/debug-register`, {
        email,
        password
      });
      setResponse(response.data);
      message.success('Debug registration successful!');
    } catch (err: any) {
      console.error('Debug registration error:', err);
      setError({
        message: err.message,
        status: err.response?.status,
        data: err.response?.data,
        config: {
          url: err.config?.url,
          method: err.config?.method
        }
      });
      message.error('Debug registration failed');
    } finally {
      setLoading(false);
    }
  };

  const testDebugLogin = async () => {
    setLoading(true);
    setError(null);
    setResponse(null);
    
    try {
      // Try to login using the debug endpoint
      const response = await axios.post(`${backendUrl}/api/auth/debug-login`, {
        email,
        password
      });
      setResponse(response.data);
      message.success('Debug login successful!');
    } catch (err: any) {
      console.error('Debug login error:', err);
      setError({
        message: err.message,
        status: err.response?.status,
        data: err.response?.data,
        config: {
          url: err.config?.url,
          method: err.config?.method
        }
      });
      message.error('Debug login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '20px' }}>
      <Card>
        <Title level={2}>Authentication Debugging Tool</Title>
        <Paragraph>
          This tool helps diagnose problems with your authentication system by testing direct connections to your backend API.
        </Paragraph>

        <Divider />
        
        <Title level={4}>Backend Configuration</Title>
        {configLoading ? (
          <Text>Loading configuration...</Text>
        ) : (
          <div>
            <Text>Current backend URL from environment: </Text>
            <Text keyboard>{process.env.REACT_APP_API_URL || 'http://localhost:8000'}</Text>
            
            <div style={{ marginTop: '16px' }}>
              <Text>Test with URL:</Text>
              <Input 
                value={backendUrl} 
                onChange={(e) => setBackendUrl(e.target.value)}
                style={{ width: '100%', marginTop: '8px' }}
                placeholder="e.g. https://your-backend.render.com"
              />
            </div>
          </div>
        )}
        
        <Divider />
        
        <Title level={4}>Test Credentials</Title>
        <div style={{ marginBottom: '16px' }}>
          <Text>Email:</Text>
          <Input 
            value={email} 
            onChange={(e) => setEmail(e.target.value)}
            style={{ width: '100%', marginTop: '8px' }}
          />
        </div>
        
        <div style={{ marginBottom: '16px' }}>
          <Text>Password:</Text>
          <Input.Password 
            value={password} 
            onChange={(e) => setPassword(e.target.value)}
            style={{ width: '100%', marginTop: '8px' }}
          />
        </div>
        
        <Divider />
        
        <Title level={4}>Test Actions</Title>
        <Space style={{ marginBottom: '16px' }}>
          <Button type="primary" onClick={testBackendConnection} loading={loading}>
            Test Backend Connection
          </Button>
          
          <Button type="primary" onClick={testDebugRegister} loading={loading}>
            Test Debug Registration
          </Button>
          
          <Button type="primary" onClick={testDebugLogin} loading={loading}>
            Test Debug Login
          </Button>
        </Space>
        
        <Divider />
        
        <Title level={4}>Results</Title>
        
        {error && (
          <Alert
            message="Error"
            description={
              <div>
                <p><strong>Message:</strong> {error.message}</p>
                <p><strong>Status:</strong> {error.status}</p>
                <p><strong>URL:</strong> {error.config?.url}</p>
                <p><strong>Method:</strong> {error.config?.method}</p>
                {error.data && (
                  <div>
                    <p><strong>Response Data:</strong></p>
                    <pre>{JSON.stringify(error.data, null, 2)}</pre>
                  </div>
                )}
              </div>
            }
            type="error"
            showIcon
            style={{ marginBottom: '16px' }}
          />
        )}
        
        {response && (
          <Alert
            message="Success"
            description={
              <div>
                <p><strong>Response Data:</strong></p>
                <pre>{JSON.stringify(response, null, 2)}</pre>
              </div>
            }
            type="success"
            showIcon
          />
        )}
      </Card>
    </div>
  );
};

export default AuthDebug;
