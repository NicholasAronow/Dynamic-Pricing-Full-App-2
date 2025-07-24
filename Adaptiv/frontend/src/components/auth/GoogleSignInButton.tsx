import React, { useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Button } from 'antd';
import { GoogleOutlined } from '@ant-design/icons';

interface GoogleSignInButtonProps {
  onSuccess?: () => void;
  onError?: (error: any) => void;
}

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: any) => void;
          prompt: () => void;
        };
      };
    };
  }
}

const GoogleSignInButton: React.FC<GoogleSignInButtonProps> = ({ onSuccess, onError }) => {
  const { googleLogin } = useAuth();
  const [isGoogleLoaded, setIsGoogleLoaded] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  
  useEffect(() => {
    // Load the Google Sign-In script
    const loadGoogleScript = () => {
      const script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.defer = true;
      script.onload = initializeGoogleSignIn;
      document.body.appendChild(script);
    };

    // Initialize Google Sign-In
    const initializeGoogleSignIn = () => {
      if (window.google) {
        // Get client ID from environment or use the one we know works for localhost
        const clientId = process.env.REACT_APP_GOOGLE_CLIENT_ID || '';
        console.log('Initializing Google Sign-In with client ID:', clientId);
        
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: handleCredentialResponse,
          auto_select: false,
        });
        
        setIsGoogleLoaded(true);
      }
    };

    // Handle the sign in response
    const handleCredentialResponse = async (response: any) => {
      console.log("Google sign-in response:", response);
      setIsLoading(true);
      try {
        await googleLogin(response.credential);
        if (onSuccess) onSuccess();
      } catch (error) {
        console.error("Error with Google sign-in:", error);
        if (onError) onError(error);
      } finally {
        setIsLoading(false);
      }
    };

    loadGoogleScript();
  }, [googleLogin, onSuccess, onError]);

  // Handle static button click
  const handleStaticButtonClick = () => {
    if (window.google && isGoogleLoaded) {
      setIsLoading(true);
      window.google.accounts.id.prompt();
      // Reset loading state after a delay in case prompt is cancelled
      setTimeout(() => setIsLoading(false), 3000);
    } else {
      console.error("Google sign-in script not loaded");
    }
  };

  return (
    <div style={{ marginBottom: '16px' }}>
      <Button 
        icon={<GoogleOutlined />} 
        onClick={handleStaticButtonClick}
        loading={isLoading}
        disabled={!isGoogleLoaded}
        block 
        size="large"
        style={{
          height: '48px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '16px',
          fontWeight: 500,
          border: '1px solid #dadce0',
          borderRadius: '4px',
          backgroundColor: '#fff',
          color: '#3c4043',
          transition: 'all 0.2s ease'
        }}
      >
        Sign in with Google
      </Button>
    </div>
  );
};

export default GoogleSignInButton;
