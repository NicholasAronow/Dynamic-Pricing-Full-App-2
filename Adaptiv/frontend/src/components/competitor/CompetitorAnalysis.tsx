import React from 'react';
import { Typography, Card, Alert, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Title } = Typography;

const CompetitorAnalysis: React.FC = () => {
  const navigate = useNavigate();

  // Sample competitor data
  const unsortedCompetitors = [
    {
      key: '1',
      name: 'PriceWise',
      similarityScore: 85,
      priceDifference: '+15%',
      status: 'higher',
      categories: ['Dynamic Pricing', 'Analytics', 'Integrations']
    },
    {
      key: '2',
      name: 'MarketMaster',
      similarityScore: 72,
      priceDifference: '-3%',
      status: 'lower',
      categories: ['Analytics', 'AI Recommendations']
    },
    {
      key: '3',
      name: 'PricePoint',
      similarityScore: 91,
      priceDifference: '+5%',
      status: 'higher',
      categories: ['Analytics', 'Integrations', 'Multi-platform']
    }
  ];
  
  // Define competitor type for better type safety
  interface Competitor {
    key: string;
    name: string;
    similarityScore: number;
    priceDifference: string;
    status: string;
    categories: string[];
  }

  // Sort competitors by similarity score (descending)
  const competitors = [...unsortedCompetitors].sort((a, b) => b.similarityScore - a.similarityScore);

  const columns: ColumnsType<Competitor> = [
    {
      title: 'Competitor Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Similarity Score',
      dataIndex: 'similarityScore',
      key: 'similarityScore',
      defaultSortOrder: 'descend' as const,
      sorter: (a: Competitor, b: Competitor) => a.similarityScore - b.similarityScore,
      render: (score: number) => (
        <span>{score}%</span>
      ),
    },
    {
      title: 'Avg. Price Difference',
      dataIndex: 'priceDifference',
      key: 'priceDifference',
      render: (text: string, record: any) => (
        <span>
          {record.status === 'higher' ? 
            <span style={{ color: '#cf1322' }}><ArrowUpOutlined /> {text}</span> : 
            <span style={{ color: '#3f8600' }}><ArrowDownOutlined /> {text}</span>}
        </span>
      ),
    },
    {
      title: 'Categories',
      key: 'categories',
      dataIndex: 'categories',
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
        <Title level={4} style={{ marginTop: 0, marginBottom: 16 }}>Competitor Data</Title>
        <Table 
          dataSource={competitors} 
          columns={columns} 
          pagination={false} 
          onRow={(record) => ({
            onClick: () => navigate(`/competitor/${record.key}`),
            style: { cursor: 'pointer' }
          })}
        />
      </Card>
    </div>
  );
};

export default CompetitorAnalysis;
