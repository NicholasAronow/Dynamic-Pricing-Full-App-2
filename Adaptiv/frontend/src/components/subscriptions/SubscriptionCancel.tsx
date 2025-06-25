import React from 'react';
import { Result, Button } from 'antd';
import { CloseCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const SubscriptionCancel: React.FC = () => {
  const navigate = useNavigate();
  
  return (
    <div style={{ padding: '40px', maxWidth: '800px', margin: '0 auto' }}>
      <Result
        icon={<CloseCircleOutlined style={{ color: '#ff4d4f' }} />}
        title="Subscription Process Cancelled"
        subTitle="You've cancelled the subscription process. You can still subscribe at any time to access premium features."
        extra={[
          <Button 
            type="primary" 
            key="try-again" 
            onClick={() => navigate('/subscription-plans')}
          >
            View Plans Again
          </Button>,
          <Button 
            key="dashboard" 
            onClick={() => navigate('/dashboard')}
          >
            Go to Dashboard
          </Button>,
        ]}
      />
    </div>
  );
};

export default SubscriptionCancel;
