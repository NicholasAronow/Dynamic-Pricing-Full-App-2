import React, { useState, useEffect } from 'react';
import { Typography, Card, Alert, Table, Tag, Spin, Tooltip } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { ArrowUpOutlined, ArrowDownOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import competitorService, { CompetitorItem } from '../../services/competitorService';
import itemService, { Item } from '../../services/itemService';

const { Title } = Typography;

// Define competitor type for better type safety
interface Competitor {
  key: string;
  name: string;
  similarityScore: number;
  priceSimScore: number;
  menuSimScore: number;
  distanceScore: number;
  priceDifference: string;
  status: string;
  categories: string[];
  distance: number;
}

const CompetitorAnalysis: React.FC = () => {
  const navigate = useNavigate();
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        
        // Get all unique competitor names from the API
        const competitorNames = await competitorService.getCompetitors();
        
        // Get all competitor items for categories
        const allCompetitorItems = await competitorService.getCompetitorItems();
        
        // Process each competitor using the new similarity score calculator
        const competitorData: Competitor[] = [];
        
        for (let i = 0; i < competitorNames.length; i++) {
          const name = competitorNames[i];
          
          // Filter items for this competitor to get categories
          const competitorItems = allCompetitorItems.filter(
            item => item.competitor_name.toLowerCase() === name.toLowerCase()
          );
          
          // Skip if no items found
          if (competitorItems.length === 0) {
            continue;
          }
          
          // Get categories
          const categoriesSet = new Set<string>();
          competitorItems.forEach(item => {
            if (item.category) categoriesSet.add(item.category);
          });
          
          try {
            // Use the new similarity score calculator
            const similarityData = await competitorService.calculateSimilarityScore(name);
            
            // Get our items for price calculations
            const ourItems = await itemService.getItems();
            
            // Calculate average prices directly (same approach as CompetitorDetail.tsx)
            const ourAvgPrice = ourItems.reduce((acc, item) => acc + item.current_price, 0) / ourItems.length;
            
            // Get competitor items for this specific competitor
            const competitorItems = allCompetitorItems.filter(
              item => item.competitor_name.toLowerCase() === name.toLowerCase()
            );
            
            // Calculate competitor average price
            const competitorAvgPrice = competitorItems.reduce((acc, item) => acc + item.price, 0) / competitorItems.length;
            
            // Calculate price difference using the same formula as CompetitorDetail.tsx
            const priceDiff = ((competitorAvgPrice - ourAvgPrice) / competitorAvgPrice) * 100;
            const formattedDiff = `${priceDiff > 0 ? '+' : ''}${priceDiff.toFixed(1)}%`;
            const status = priceDiff > 0 ? 'higher' : priceDiff < 0 ? 'lower' : 'same';
            
            competitorData.push({
              key: String(i + 1),
              name: name,
              similarityScore: similarityData.similarityScore,
              priceSimScore: similarityData.priceSimScore,
              menuSimScore: similarityData.menuSimScore,
              distanceScore: similarityData.distanceScore,
              priceDifference: formattedDiff,
              status: status,
              categories: Array.from(categoriesSet),
              distance: similarityData.distance
            });
          } catch (err) {
            console.error(`Error calculating similarity for ${name}:`, err);
            // Use fallback data if the calculation fails
            competitorData.push({
              key: String(i + 1),
              name: name,
              similarityScore: 75,
              priceSimScore: 75,
              menuSimScore: 75,
              distanceScore: 75,
              priceDifference: '0.0%',
              status: 'same',
              categories: Array.from(categoriesSet),
              distance: 1.0
            });
          }
        }
        
        // Sort competitors by overall similarity score (descending)
        const sortedCompetitors = [...competitorData].sort((a, b) => b.similarityScore - a.similarityScore);
        
        setCompetitors(sortedCompetitors);
        setLoading(false);
      } catch (err) {
        console.error('Error fetching competitor data:', err);
        setError('Failed to load competitor data. Please try again later.');
        setLoading(false);
      }
    };
    
    fetchData();
  }, []);

  const columns: ColumnsType<Competitor> = [
    {
      title: 'Competitor Name',
      dataIndex: 'name',
      key: 'name',
      width: 180,
    },
    {
      title: 'Similarity Score',
      dataIndex: 'similarityScore',
      key: 'similarityScore',
      width: 220,
      defaultSortOrder: 'descend' as const,
      sorter: (a: Competitor, b: Competitor) => a.similarityScore - b.similarityScore,
      render: (score: number, record: Competitor) => {
        const tooltipContent = (
          <div style={{ padding: '4px 0' }}>
            <div><b>Similarity Score Breakdown:</b></div>
            <div style={{ marginTop: '8px' }}>
              <div>Menu Similarity: {record.menuSimScore}%</div>
              <div>Price Similarity: {record.priceSimScore}%</div>
              <div>Distance Score: {record.distanceScore}%</div>
            </div>
            <div style={{ marginTop: '8px', fontSize: '11px', color: '#999' }}>
              Overall score is weighted: 60% menu, 20% price, 20% distance
            </div>
          </div>
        );
        
        return (
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <Tooltip title={tooltipContent} placement="right">
              <InfoCircleOutlined style={{ marginRight: '8px', color: 'gray', cursor: 'pointer' }} />
            </Tooltip>
            <div style={{ fontWeight: 'bold', fontSize: '16px' }}>{score}%</div>
          </div>
        );
      },
    },
    {
      title: 'Avg. Price Difference',
      dataIndex: 'priceDifference',
      key: 'priceDifference',
      render: (text: string, record: Competitor) => {
        if (record.status === 'higher') {
          return <span style={{ color: '#cf1322' }}><ArrowUpOutlined /> {text}</span>;
        } else if (record.status === 'lower') {
          return <span style={{ color: '#3f8600' }}><ArrowDownOutlined /> {text}</span>;
        } else {
          // Handle 'same' price status
          return <span style={{ color: '#888888' }}>{text}</span>;
        }
      },
      sorter: (a: Competitor, b: Competitor) => {
        const aValue = parseFloat(a.priceDifference);
        const bValue = parseFloat(b.priceDifference);
        return isNaN(aValue) || isNaN(bValue) ? 0 : aValue - bValue;
      },
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
    },
    {
      title: 'Distance',
      dataIndex: 'distance',
      key: 'distance',
      width: 100,
      sorter: (a: Competitor, b: Competitor) => a.distance - b.distance,
      render: (distance: number) => (
        <span>{distance.toFixed(1)} mi</span>
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
        
        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <Spin size="large" />
            <div style={{ marginTop: 16 }}>Loading competitor data...</div>
          </div>
        ) : error ? (
          <Alert message={error} type="error" showIcon />
        ) : competitors.length === 0 ? (
          <Alert 
            message="No competitors found" 
            description="Add competitor data through the API to see competitive analysis."
            type="info" 
            showIcon 
          />
        ) : (
          <Table 
            dataSource={competitors} 
            columns={columns} 
            pagination={false} 
            onRow={(record) => ({
              onClick: () => navigate(`/competitor/${encodeURIComponent(record.name)}`),
              style: { cursor: 'pointer' }
            })}
          />
        )}
      </Card>
    </div>
  );
};

export default CompetitorAnalysis;
