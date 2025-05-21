import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Result, Spin } from 'antd';
import { integrationService } from '../../services/integrationService';

/**
 * Component to handle the OAuth callback from Square
 * This is the component that will be rendered when Square redirects back to our app
 */
const SquareCallback: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
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
        
        // Process the callback by sending the code to backend
        await integrationService.processSquareCallback(code, state || '');
        
        // Navigate to the dashboard on success with a success parameter
        // The dashboard can then show a success message
        navigate('/square-test?success=true');
      } catch (err) {
        console.error('Error processing Square callback:', err);
        setError('Failed to process Square authorization. Please try again.');
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
