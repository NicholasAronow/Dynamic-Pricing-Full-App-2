import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Result, Spin } from 'antd';
import { integrationService } from '../../services/integrationService';
import { useAuth } from '../../context/AuthContext';

/**
 * Component to handle the OAuth callback from Square
 * This is the component that will be rendered when Square redirects back to our app
 */
const SquareCallback: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { fetchUserData } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const processCallback = async () => {
      try {
        // Extract code and state from URL params
        const params = new URLSearchParams(location.search);
        const code = params.get('code');
        const state = params.get('state');
        const errorParam = params.get('error');

        if (errorParam) {
          console.error('Square error:', errorParam);
          setError(`Square returned an error: ${errorParam}`);
          setLoading(false);
          return;
        }

        if (!code) {
          console.error('No authorization code found in callback URL');
          setError('No authorization code found in callback URL');
          setLoading(false);
          return;
        }

        console.log('SquareCallback: Processing code', code);
        
        try {
          // Process the callback by sending the code to backend
          const response = await integrationService.processSquareCallback(code, state || '');
          
          // Refresh user data to get updated pos_connected status regardless of the outcome
          await fetchUserData();
          
          // Check if the response indicates the account was already connected
          const alreadyConnected = response.already_connected;
          
          // Navigate to the dashboard with appropriate success parameter
          navigate(`/dashboard?integration=${alreadyConnected ? 'already-connected' : 'success'}`);
        } catch (apiError: any) {
          console.error('Backend error during Square callback:', apiError);
          
          // Try to refresh user data anyway - the integration might have worked at the API level
          // even if our application had an error processing it
          try {
            await fetchUserData();
          } catch (refreshError) {
            console.error('Failed to refresh user data after Square integration attempt:', refreshError);
          }
          
          // If the error message suggests the user is already connected, navigate to dashboard
          const errorDetail = apiError?.response?.data?.detail || '';
          if (errorDetail.includes('already')) {
            navigate('/dashboard?integration=already-connected');
            return;
          }
          
          // For other errors, show the error message
          throw apiError;
        }
      } catch (err: any) {
        console.error('Error processing Square callback:', err);
        
        // Extract the most useful error message
        let errorMessage = 'Failed to process Square authorization. Please try again.';
        
        if (err?.response?.data?.detail) {
          errorMessage = err.response.data.detail;
        } else if (typeof err.message === 'string') {
          errorMessage = err.message;
        }
        
        // Special handling for common error cases
        if (errorMessage.includes('already used')) {
          errorMessage = 'This authorization code has already been used. Please try connecting again.';
        } else if (errorMessage.includes('already connected') || errorMessage.includes('already has')) {
          // If it indicates the account is already connected, redirect to dashboard
          navigate('/dashboard?integration=already-connected');
          return;
        }
        
        setError(errorMessage);
        setLoading(false);
      }
    };

    processCallback();
  }, [location, navigate]);

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <div style={{ textAlign: 'center' }}>
          <Spin size="large" />
          <div style={{ marginTop: 16 }}>
            <h2>Connecting to Square...</h2>
            <p>Please wait while we complete your Square integration.</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 24 }}>
        <Result
          status="error"
          title="Square Integration Failed"
          subTitle={error}
          extra={[
            <button key="retry" onClick={() => navigate('/dashboard')}>
              Return to Dashboard
            </button>
          ]}
        />
      </div>
    );
  }

  // Normally we would never reach here as we redirect on success,
  // but just in case, we show a success message
  return (
    <div style={{ padding: 24 }}>
      <Result
        status="success"
        title="Square Connected Successfully!"
        subTitle="Your Square account has been connected. You will be redirected to the dashboard."
      />
    </div>
  );
};

export default SquareCallback;
