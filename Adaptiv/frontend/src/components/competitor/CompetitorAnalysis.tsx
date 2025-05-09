import React from 'react';
import { Typography, Card, Alert, Table, Tag } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';

const { Title } = Typography;

const CompetitorAnalysis: React.FC = () => {
  // Sample competitor data
  const competitors = [
    {
      key: '1',
      name: 'PriceWise',
      price: '$149.99',
      difference: '+15%',
      status: 'higher',
      features: ['Dynamic Pricing', 'Analytics', 'Integrations']
    },
    {
      key: '2',
      name: 'MarketMaster',
      price: '$129.99',
      difference: '-3%',
      status: 'lower',
      features: ['Analytics', 'AI Recommendations']
    },
    {
      key: '3',
      name: 'PricePoint',
      price: '$139.99',
      difference: '+5%',
      status: 'higher',
      features: ['Analytics', 'Integrations', 'Multi-platform']
    }
  ];

  const columns = [
    {
      title: 'Competitor Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Price',
      dataIndex: 'price',
      key: 'price',
    },
    {
      title: 'Difference',
      dataIndex: 'difference',
      key: 'difference',
      render: (text: string, record: any) => (
        <span>
          {record.status === 'higher' ? 
            <span style={{ color: '#cf1322' }}><ArrowUpOutlined /> {text}</span> : 
            <span style={{ color: '#3f8600' }}><ArrowDownOutlined /> {text}</span>}
        </span>
      ),
    },
    {
      title: 'Features',
      key: 'features',
      dataIndex: 'features',
      render: (tags: string[]) => (
        <>
          {tags.map(tag => (
            <Tag color="blue" key={tag}>
              {tag}
            </Tag>
          ))}
        </>
      ),
    }
  ];

  return (
    <div>
      <Title level={2}>Competitor Analysis</Title>
      <Title level={5} type="secondary" style={{ marginTop: 0 }}>
        Monitor competitor pricing and features
      </Title>
      
      <Card style={{ marginTop: 24 }}>
        <Alert
          message="Feature in Development"
          description="The competitor analysis feature is currently in development. Check back soon for detailed comparisons of your products against competitors."
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
        />
        
        <Title level={4}>Sample Competitor Data (Placeholder)</Title>
        <Table dataSource={competitors} columns={columns} pagination={false} />
      </Card>
    </div>
  );
};

export default CompetitorAnalysis;
