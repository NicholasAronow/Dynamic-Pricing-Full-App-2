import React, { useState, useEffect, useMemo } from 'react';
import { Typography, Card, Alert, Table, Tag, Spin, Tooltip, Button, Empty } from 'antd';
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
  const [hasData, setHasData] = useState<boolean>(false);

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
        
        // Filter out invalid entries with 0% similarity or NaN values
        const validCompetitors = competitorData.filter(comp => {
          // Check if similarity score is valid (not zero, not NaN)
          const hasValidSimilarity = comp.similarityScore > 0 && !isNaN(comp.similarityScore);
          // Check if price scores are valid
          const hasValidPriceScores = comp.priceSimScore > 0 && !isNaN(comp.priceSimScore);
          // Check if menu scores are valid
          const hasValidMenuScores = comp.menuSimScore > 0 && !isNaN(comp.menuSimScore);
          
          return hasValidSimilarity && hasValidPriceScores && hasValidMenuScores;
        });

        // Sort competitors by overall similarity score (descending)
        const sortedCompetitors = [...validCompetitors].sort((a, b) => b.similarityScore - a.similarityScore);
        
        setCompetitors(sortedCompetitors);
        // Only set hasData true if we have valid competitors with meaningful data
        setHasData(sortedCompetitors.length > 0);
        setLoading(false);
      } catch (err) {
        console.error('Error fetching competitor data:', err);
        setError('Failed to load competitor data. Please try again later.');
        setHasData(false);
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

  // Generate sample competitor data for the blurred background
  const sampleCompetitors = useMemo(() => {
    return Array(5).fill(null).map((_, index) => ({
      key: String(index + 1),
      name: `Sample Competitor ${index + 1}`,
      similarityScore: 85 - (index * 5),
      priceSimScore: 80 - (index * 3),
      menuSimScore: 85 - (index * 4),
      distanceScore: 90 - (index * 5),
      priceDifference: index % 2 === 0 ? '+5.2%' : '-3.8%',
      status: index % 2 === 0 ? 'higher' : 'lower',
      categories: ['Coffee', 'Pastry'].slice(0, index % 2 + 1),
      distance: 0.5 + (index * 0.3)
    }));
  }, []);

  return (
    <div>
      <Title level={2}>Competitor Analysis</Title>
      <Title level={5} type="secondary" style={{ marginTop: 0 }}>
        Monitor competitor pricing and features
      </Title>
      
      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Spin size="large" />
          <div style={{ marginTop: 16 }}>Loading competitor data...</div>
        </div>
      ) : error ? (
        <Alert message={error} type="error" showIcon />
      ) : !hasData ? (
        <div style={{ position: 'relative' }}>
          {/* Blurred sample data in background */}
          <div style={{ filter: 'blur(5px)', opacity: 0.5 }}>
            <Card style={{ marginTop: 24 }}> 
              <Title level={4} style={{ marginTop: 0, marginBottom: 16 }}>Competitor Data</Title>
              <Table 
                dataSource={sampleCompetitors} 
                columns={columns} 
                pagination={false} 
              />
            </Card>
          </div>
          
          {/* Overlay with message */}
          <div style={{ 
            position: 'absolute', 
            top: 0, 
            left: 0, 
            width: '100%', 
            height: '100%', 
            display: 'flex', 
            flexDirection: 'column', 
            justifyContent: 'center', 
            alignItems: 'center',
            backgroundColor: 'rgba(255, 255, 255, 0.85)',
            padding: '100px 0'
          }}>
            <div style={{ 
              padding: '30px', 
              borderRadius: '8px', 
              textAlign: 'center',
              maxWidth: '80%' 
            }}>
              <p style={{ fontSize: '22px', fontWeight: 500, marginBottom: '16px' }}>No competitor data available</p>
              <p style={{ color: '#666', marginBottom: '24px', fontSize: '16px' }}>To view competitor analysis, please connect your POS provider</p>
              <Button type="primary" size="large">
                Connect POS Provider
              </Button>
            </div>
          </div>
        </div>
      ) : (
        <Card style={{ marginTop: 24 }}> 
          <Title level={4} style={{ marginTop: 0, marginBottom: 16 }}>Competitor Data</Title>
          
          <Table 
            dataSource={competitors} 
            columns={columns} 
            pagination={false} 
            onRow={(record) => ({
              onClick: () => navigate(`/competitor/${encodeURIComponent(record.name)}`),
              style: { cursor: 'pointer' }
            })}
          />
        </Card>
      )}
    </div>
  );
};

export default CompetitorAnalysis;
