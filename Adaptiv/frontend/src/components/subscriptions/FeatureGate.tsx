import React, { ReactNode } from 'react';
import { Alert, Button } from 'antd';
import { useSubscription } from '../../contexts/SubscriptionContext';
import { useNavigate } from 'react-router-dom';

interface FeatureGateProps {
  feature: keyof typeof import('../../contexts/SubscriptionContext').SUBSCRIPTION_FEATURES;
  children: ReactNode;
  fallback?: ReactNode;
}

/**
 * FeatureGate component restricts access to features based on subscription tier
 * Usage: Wrap premium features with this component
 */
const FeatureGate: React.FC<FeatureGateProps> = ({ 
  feature, 
  children, 
  fallback 
}) => {
  const { hasAccess } = useSubscription();
  const navigate = useNavigate();
  
  // If the user has access to this feature, render the children
  if (hasAccess(feature)) {
    return <>{children}</>;
  }
  
  // If a fallback is provided, render that instead
  if (fallback) {
    return <>{fallback}</>;
  }
  
  // Default fallback: upgrade prompt
  return (
    <Alert
      message="Premium Feature"
      description={
        <div>
          <p>This feature requires a premium subscription.</p>
          <Button 
            type="primary" 
            size="small" 
            onClick={() => navigate('/subscription-plans')}
          >
            Upgrade Now
          </Button>
        </div>
      }
      type="info"
      showIcon
    />
  );
};

export default FeatureGate;
