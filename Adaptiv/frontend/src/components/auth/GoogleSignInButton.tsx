import React, { useEffect, useRef } from 'react';
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
          renderButton: (element: HTMLElement, options: any) => void;
          prompt: () => void;
        };
      };
    };
  }
}

const GoogleSignInButton: React.FC<GoogleSignInButtonProps> = ({ onSuccess, onError }) => {
  const { googleLogin } = useAuth();
  const googleButtonRef = useRef<HTMLDivElement>(null);
  
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
      if (window.google && googleButtonRef.current) {
        // Get client ID from environment or use the one we know works for localhost
        const clientId = process.env.REACT_APP_GOOGLE_CLIENT_ID || '';
        console.log('Initializing Google Sign-In with client ID:', clientId);
        
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: handleCredentialResponse,
          auto_select: false,
        });

        window.google.accounts.id.renderButton(
          googleButtonRef.current,
          { 
            type: 'standard',
            theme: 'outline', 
            size: 'large',
            text: 'signin_with',
            width: '100%',
          }
        );
      }
    };

    // Handle the sign in response
    const handleCredentialResponse = async (response: any) => {
      console.log("Google sign-in response:", response);
      try {
        await googleLogin(response.credential);
        if (onSuccess) onSuccess();
      } catch (error) {
        console.error("Error with Google sign-in:", error);
        if (onError) onError(error);
      }
    };

    loadGoogleScript();
  }, [googleLogin, onSuccess, onError]);

  // If Google script fails to load, provide a fallback button
  const handleFallbackClick = () => {
    if (window.google) {
      window.google.accounts.id.prompt();
    } else {
      console.error("Google sign-in script not loaded");
    }
  };

  return (
    <div style={{ marginBottom: '16px' }}>
      <div ref={googleButtonRef}></div>
      {/* Fallback button if Google script doesn't load */}
      <div style={{ display: 'none' }}>
        <Button 
          icon={<GoogleOutlined />} 
          onClick={handleFallbackClick} 
          block 
          size="large"
        >
          Sign in with Google
        </Button>
      </div>
    </div>
  );
};

export default GoogleSignInButton;
