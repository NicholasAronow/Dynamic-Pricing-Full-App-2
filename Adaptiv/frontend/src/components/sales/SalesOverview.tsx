import React from 'react';
import { Typography, Card, Alert, Divider, Row, Col, Statistic } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';

const { Title } = Typography;

const SalesOverview: React.FC = () => {
  return (
    <div>
      <Title level={2}>Sales Overview</Title>
      <Title level={5} type="secondary" style={{ marginTop: 0 }}>
        Track and analyze your sales performance
      </Title>
      
      <Card style={{ marginTop: 24 }}>
        <Alert
          message="Feature in Development"
          description="The sales overview feature is currently in development. Check back soon for detailed analytics on your sales performance."
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
        />
        
        <Divider>Sample Data (Placeholder)</Divider>
        
        <Row gutter={[16, 16]}>
          <Col span={8}>
            <Statistic 
              title="Monthly Revenue" 
              value={82500} 
              precision={0} 
              prefix="$" 
              valueStyle={{ color: '#3f8600' }} 
              suffix={<ArrowUpOutlined />}
            />
          </Col>
          <Col span={8}>
            <Statistic 
              title="Units Sold" 
              value={634} 
              valueStyle={{ color: '#3f8600' }} 
            />
          </Col>
          <Col span={8}>
            <Statistic 
              title="Average Order Value" 
              value={130.12} 
              precision={2} 
              prefix="$" 
            />
          </Col>
        </Row>
      </Card>
    </div>
  );
};

export default SalesOverview;
