import React from 'react';
import { Card, Statistic, Progress, Row, Col } from 'antd';
import { RiseOutlined, FallOutlined, DollarOutlined } from '@ant-design/icons';

interface PremiumAnalyticsWidgetProps {
  // You would add any props needed for real analytics data
}

/**
 * This component represents a premium analytics widget that should only be 
 * displayed to users with basic or premium subscriptions
 */
const PremiumAnalyticsWidget: React.FC<PremiumAnalyticsWidgetProps> = () => {
  return (
    <Card title="Advanced Analytics" bordered={false} className="premium-widget">
      <Row gutter={16}>
        <Col span={8}>
          <Statistic
            title="Pricing Efficiency Score"
            value={82}
            suffix="%"
            valueStyle={{ color: '#3f8600' }}
            prefix={<RiseOutlined />}
          />
          <Progress percent={82} status="active" strokeColor="#3f8600" />
        </Col>
        <Col span={8}>
          <Statistic
            title="Revenue Potential"
            value={24.8}
            precision={1}
            valueStyle={{ color: '#cf1322' }}
            prefix={<DollarOutlined />}
            suffix="%"
          />
          <Progress percent={24.8} status="active" strokeColor="#cf1322" />
        </Col>
        <Col span={8}>
          <Statistic
            title="Market Position"
            value={76}
            suffix="%"
            valueStyle={{ color: '#1890ff' }}
            prefix={<RiseOutlined />}
          />
          <Progress percent={76} status="active" />
        </Col>
      </Row>

      <div style={{ marginTop: '16px' }}>
        <p>
          <strong>Pricing Intelligence:</strong> Your prices are competitive in 78% of product categories.
        </p>
        <p>
          <strong>Revenue Opportunity:</strong> Optimizing your remaining product prices could increase revenue by up to 24.8%.
        </p>
      </div>
    </Card>
  );
};

export default PremiumAnalyticsWidget;
