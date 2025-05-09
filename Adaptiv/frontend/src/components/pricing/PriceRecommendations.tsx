import React from 'react';
import { Typography, Card, Alert } from 'antd';

const { Title } = Typography;

const PriceRecommendations: React.FC = () => {
  return (
    <div>
      <Title level={2}>Price Recommendations</Title>
      <Title level={5} type="secondary" style={{ marginTop: 0 }}>
        Optimize your product pricing strategy
      </Title>
      
      <Card style={{ marginTop: 24 }}>
        <Alert
          message="Feature in Development"
          description="The price recommendations feature is currently in development. Check back soon for dynamic pricing insights based on your market position and customer behavior."
          type="info"
          showIcon
        />
      </Card>
    </div>
  );
};

export default PriceRecommendations;
