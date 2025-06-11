import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Typography, Card, Button, Row, Col, Space, Statistic, Table, Tag, Divider, Spin, Alert } from 'antd';
import { 
  ArrowLeftOutlined, 
  ArrowUpOutlined, 
  ArrowDownOutlined, 
  ShopOutlined, 
  DollarOutlined,
  LeftOutlined 
} from '@ant-design/icons';
import { 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip as RechartsTooltip, 
  Legend 
} from 'recharts';
import competitorService, { CompetitorItem } from '../../services/competitorService';
import itemService, { Item } from '../../services/itemService';
import axios from 'axios';

const { Title, Text } = Typography;

// Utility function to format numbers with commas
const formatNumberWithCommas = (num: any): string => {
  if (Array.isArray(num)) {
    return formatNumberWithCommas(num[0]);
  }
  if (typeof num === 'string') {
    return Number(num).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }
  if (typeof num === 'number') {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }
  return String(num);
};

// Sample data generator function for common items
const generateCommonItems = (competitorId: string) => {
  const items = [
    {
      key: '1',
      itemName: 'Signature Latte',
      ourPrice: 4.50,
      theirPrice: 4.95,
      category: 'Beverages'
    },
    {
      key: '2',
      itemName: 'Cappuccino',
      ourPrice: 4.25,
      theirPrice: 3.99,
      category: 'Beverages'
    },
    {
      key: '3',
      itemName: 'Croissant',
      ourPrice: 3.50,
      theirPrice: 3.99,
      category: 'Bakery'
    },
    {
      key: '4',
      itemName: 'Avocado Toast',
      ourPrice: 8.99,
      theirPrice: 9.49,
      category: 'Food'
    },
    {
      key: '5',
      itemName: 'Blueberry Muffin',
      ourPrice: 3.25,
      theirPrice: 2.99,
      category: 'Bakery'
    },
    {
      key: '6',
      itemName: 'Cold Brew',
      ourPrice: 4.75,
      theirPrice: 5.25,
      category: 'Beverages'
    },
    {
      key: '7',
      itemName: 'Breakfast Sandwich',
      ourPrice: 6.99,
      theirPrice: 7.49,
      category: 'Food'
    },
  ];

  // Calculate the price difference and status
  const itemsWithDifference = items.map(item => {
    // Calculate how our price compares to theirs
    // Negative percentage means our price is lower (good)
    // Positive percentage means our price is higher (bad)
    const priceDiff = ((item.ourPrice - item.theirPrice) / item.theirPrice) * 100;
    const status = priceDiff < 0 ? 'lower' : priceDiff > 0 ? 'higher' : 'same';
    const formattedDiff = `${priceDiff > 0 ? '+' : ''}${priceDiff.toFixed(1)}%`;
    
    return {
      ...item,
      difference: formattedDiff,
      diffValue: priceDiff, // Store the actual numeric value for sorting
      status: status
    };
  });

  // Filter items randomly based on competitorId to simulate different competitors having different items
  return itemsWithDifference.filter((_, index: number) => {
    const competitorIdNum = parseInt(competitorId || '1', 10);
    return (index % competitorIdNum !== 0);
  });
};

// Generate market position data with normalized 1-10 scale
const generateMarketPositionData = (competitorId: string) => {
  // This would come from API in a real implementation
  const competitorIdNum = parseInt(competitorId || '1', 10);
  
  // Original price points (for reference)
  const originalMarketLow = 3.99;
  const originalMarketHigh = 6.99;
  const originalOurPrice = 4.50;
  
  // Define the normalized scale
  const scaleMin = 1;
  const scaleMax = 10;
  
  // Set original competitor price based on ID
  let originalCompetitorPrice;
  if (competitorIdNum === 1) {
    originalCompetitorPrice = 4.29; // Lower than our price
  } else if (competitorIdNum === 2) {
    originalCompetitorPrice = 4.99; // Same as market average
  } else {
    originalCompetitorPrice = 5.49; // Higher than our price
  }
  
  // Normalize prices to 1-10 scale
  const normalize = (price: number) => {
    // Linear transformation from the original price range to 1-10 scale
    return (
      ((price - originalMarketLow) / (originalMarketHigh - originalMarketLow)) * 
      (scaleMax - scaleMin) + 
      scaleMin
    );
  };
  
  const normalizedMarketLow = scaleMin;
  const normalizedMarketHigh = scaleMax;
  const normalizedOurPrice = normalize(originalOurPrice);
  const normalizedCompetitorPrice = normalize(originalCompetitorPrice);
  const normalizedMarketAverage = normalize(4.99); // Original market average
  
  // Calculate percentage position for visualization
  const ourPricePosition = ((normalizedOurPrice - scaleMin) / (scaleMax - scaleMin)) * 100;
  const competitorPricePosition = ((normalizedCompetitorPrice - scaleMin) / (scaleMax - scaleMin)) * 100;
  
  return {
    // Original price data (for reference and display in table)
    originalMarketLow,
    originalMarketHigh,
    originalOurPrice,
    originalCompetitorPrice,
    originalMarketAverage: 4.99,
    
    // Normalized scale data (for visualization)
    marketLow: normalizedMarketLow,
    marketHigh: normalizedMarketHigh,
    ourPrice: normalizedOurPrice,
    competitorPrice: normalizedCompetitorPrice,
    marketAverage: normalizedMarketAverage,
    
    // Positioning for visualization
    ourPricePosition,
    competitorPricePosition
  };
};

// Interface for our processed competitor data
interface CompetitorData {
  id: string;
  name: string;
  similarityScore: number;
  priceDifference: string;
  status: 'higher' | 'lower' | 'same';
  categories: string[];
}

// Interface for competitor API response
interface CompetitorMenuResponse {
  success: boolean;
  competitor: {
    name: string;
    address: string;
    category: string;
    report_id: number;
  };
  menu_items: any[];
  batch?: {
    batch_id: string;
    sync_timestamp: string;
  };
}

// Interface for competitor menu items
interface CompetitorMenuItem {
  item_name: string;
  category: string;
  price: number;
  description?: string;
  similarity_score?: number;
}

// Interface for common items between our menu and competitor menu
interface CommonItem {
  key: string;
  itemName: string;
  ourPrice: number;
  theirPrice: number;
  category: string;
  difference: string;
  diffValue: number;
  status: 'higher' | 'lower' | 'same';
  productId: string;
  ourItemName: string;
  similarity_score?: number;
}

// Interface for market position visualization
interface MarketPosition {
  marketLow: number;
  marketHigh: number;
  ourPrice: number;
  competitorPrice: number;
  marketAverage: number;
  ourPricePosition: number;
  competitorPricePosition: number;
  originalMarketLow: number;
  originalMarketHigh: number;
  originalOurPrice: number;
  originalCompetitorPrice: number;
  originalMarketAverage: number;
}

const CompetitorDetail: React.FC = () => {
  // Get competitor ID from URL params (could be either a name or report_id)
  const { competitorId } = useParams<{ competitorId: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [commonItems, setCommonItems] = useState<CommonItem[]>([]);
  const [marketPositionData, setMarketPositionData] = useState<MarketPosition | null>(null);
  const [competitorData, setCompetitorData] = useState<CompetitorData | null>(null);
  const [isReportId, setIsReportId] = useState<boolean>(false);
  
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        
        if (!competitorId) {
          setError('Competitor identifier is required');
          setLoading(false);
          return;
        }

        // Check if competitorId is a report_id (numeric) or a competitor name
        const isNumericId = !isNaN(Number(competitorId));
        setIsReportId(isNumericId);
        
        let competitorItems: CompetitorMenuItem[] = [];
        let competitorName = '';
        
        if (isNumericId) {
          // This is a report_id from the new Competitors.tsx
          const token = localStorage.getItem('token');
          if (!token) {
            throw new Error('Authentication required');
          }
          
          try {
            // Get menu URL from API
            const menuResponse = await axios.get(`/api/gemini-competitors/get-stored-menu/${competitorId}`, {
              headers: {
                Authorization: `Bearer ${token}`
              }
            });
            
            const responseData = menuResponse.data as CompetitorMenuResponse;
            
            if (responseData.success && responseData.menu_items) {
              competitorItems = responseData.menu_items.map((item: any): CompetitorMenuItem => ({
                item_name: item.item_name,
                category: item.category,
                price: item.price,
                description: item.description || '',
                similarity_score: 75 // Default similarity score since real API might not provide this
              }));
              competitorName = responseData.competitor?.name || 'Unknown Competitor';
            } else {
              setError('No menu items found for this competitor');
              setLoading(false);
              return;
            }
          } catch (err: any) {
            console.error('Error fetching competitor data from API:', err);
            setError(err.response?.data?.detail || 'Failed to load competitor data');
            setLoading(false);
            return;
          }
        } else {
          // This is a competitor name from the old CompetitorAnalysis.tsx
          // Get all competitor names to find the right one
          const competitorNames = await competitorService.getCompetitors();
          
          // Decode the URI component to match with the actual competitor name
          const decodedName = decodeURIComponent(competitorId);
          competitorName = decodedName;
          
          // Check if the name exists in our competitor list
          if (!competitorNames.includes(decodedName)) {
            setError(`Competitor '${decodedName}' not found`);
            setLoading(false);
            return;
          }
          
          // Get competitor items using the old service
          competitorItems = await competitorService.getCompetitorItems(decodedName);
        }
        
        // Note: competitorItems are already fetched above based on whether we're using the old or new system
        
        // Get our items
        const ourItems = await itemService.getItems();
        
        // Create common items array by matching categories
        const processedCommonItems: CommonItem[] = [];
        
        // Helper function to find string similarity
        const findStringSimilarity = (str1: string, str2: string): number => {
          // Convert both strings to lowercase for case-insensitive comparison
          const s1 = str1.toLowerCase();
          const s2 = str2.toLowerCase();
          
          // Count common words
          const words1 = s1.split(/\s+/);
          const words2 = s2.split(/\s+/);
          
          let commonWords = 0;
          words1.forEach(w1 => {
            if (words2.some(w2 => w2.includes(w1) || w1.includes(w2))) {
              commonWords++;
            }
          });
          
          // Return similarity score (0 to 1)
          return commonWords / Math.max(words1.length, words2.length);
        };
        
                // Helper functions for robust menu item matching
        const normalizeItemName = (name: string): string => {
          return name
            .toLowerCase()
            .replace(/\s+/g, ' ')                // Normalize whitespace
            .replace(/[^a-z0-9\s]/g, '')         // Remove special characters
            .trim();                            // Remove leading/trailing whitespace
        };
        
        const getKeywords = (name: string): string[] => {
          const normalized = normalizeItemName(name);
          // Split by spaces and filter out common words and short words
          const commonWords = ['with', 'and', 'or', 'the', 'a', 'an', 'in', 'on', 'at', 'of', 'to', 'for'];
          return normalized
            .split(' ')
            .filter(word => word.length > 2 && !commonWords.includes(word));
        };
        
        const calculateStringSimilarity = (str1: string, str2: string): number => {
          // Levenshtein distance implementation
          const track = Array(str2.length + 1).fill(null).map(() => 
            Array(str1.length + 1).fill(null));
          
          for (let i = 0; i <= str1.length; i += 1) {
            track[0][i] = i;
          }
          
          for (let j = 0; j <= str2.length; j += 1) {
            track[j][0] = j;
          }
          
          for (let j = 1; j <= str2.length; j += 1) {
            for (let i = 1; i <= str1.length; i += 1) {
              const indicator = str1[i - 1] === str2[j - 1] ? 0 : 1;
              track[j][i] = Math.min(
                track[j][i - 1] + 1,                  // deletion
                track[j - 1][i] + 1,                  // insertion
                track[j - 1][i - 1] + indicator,      // substitution
              );
            }
          }
          
          const distance = track[str2.length][str1.length];
          const maxLength = Math.max(str1.length, str2.length);
          if (maxLength === 0) return 1; // Both strings are empty, consider them identical
          
          // Return similarity score between 0 and 1, where 1 is perfect match
          return 1 - distance / maxLength;
        };
        
        const keywordMatch = (keywords1: string[], keywords2: string[]): number => {
          // Count how many keywords from keywords1 appear in keywords2
          const matches = keywords1.filter(kw1 => keywords2.some(kw2 => kw2.includes(kw1) || kw1.includes(kw2)));
          const maxKeywords = Math.max(keywords1.length, keywords2.length);
          if (maxKeywords === 0) return 0;
          
          return matches.length / maxKeywords;
        };

        // Find common items by category and name similarity
        competitorItems.forEach((compItem: CompetitorMenuItem, index: number) => {
          // Prepare competitor item data for matching
          const normalizedCompName = normalizeItemName(compItem.item_name);
          const compKeywords = getKeywords(compItem.item_name);
          
          // First try matching by category if available
          const categoryItems = compItem.category ? 
            ourItems.filter(item => item.category?.toLowerCase() === compItem.category?.toLowerCase()) : 
            ourItems;
          
          // If no category match, fall back to all items
          const itemsToSearch = categoryItems.length > 0 ? categoryItems : ourItems;
          
          let bestMatch: any = null;
          let bestScore = 0;
          
          // Find the best matching item using multiple matching techniques
          for (const ourItem of itemsToSearch) {
            // Skip items with missing names
            if (!ourItem.name || !compItem.item_name) continue;
            
            const normalizedOurName = normalizeItemName(ourItem.name);
            const ourKeywords = getKeywords(ourItem.name);
            
            // Calculate string similarity
            const nameSimilarity = calculateStringSimilarity(normalizedOurName, normalizedCompName);
            
            // Calculate keyword match percentage
            const keywordSimilarity = keywordMatch(ourKeywords, compKeywords);
            
            // Combine scores with different weights
            const combinedScore = (nameSimilarity * 0.6) + (keywordSimilarity * 0.4);
            
            // Update best match if score is high enough and better than previous
            if (combinedScore > 0.5 && combinedScore > bestScore) {
              bestMatch = ourItem;
              bestScore = combinedScore;
            }
          }
          
          // If a match was found, add it to common items
          if (bestMatch) {
            // Handle zero price edge case
            if (compItem.price === 0) {
              // Don't calculate price difference for items without price data
              processedCommonItems.push({
                key: `${index}`,
                itemName: compItem.item_name,
                ourPrice: bestMatch.current_price,
                theirPrice: 0, // Will be displayed as N/A in the UI
                category: compItem.category || 'Uncategorized',
                difference: 'N/A',
                diffValue: 0, // Will be excluded from market position calculations
                status: 'same', // Neutral status for zero-price items
                productId: String(bestMatch.id),
                ourItemName: bestMatch.name,
                similarity_score: Math.round(bestScore * 100)
              });
            } else {
              // Calculate price difference for normal items
              const priceDiff = ((compItem.price - bestMatch.current_price) / compItem.price) * 100;
              const formattedDiff = priceDiff > 0 
                ? `+${priceDiff.toFixed(1)}%` 
                : `${priceDiff.toFixed(1)}%`;
              const status = priceDiff > 0 ? 'higher' : priceDiff < 0 ? 'lower' : 'same';
            
              // Add to common items list
              processedCommonItems.push({
                key: `${index}`,
                itemName: compItem.item_name,
                ourPrice: bestMatch.current_price,
                theirPrice: compItem.price,
                category: compItem.category || 'Uncategorized',
                difference: formattedDiff,
                diffValue: priceDiff,
                status: status,
                productId: String(bestMatch.id), // Store the actual product ID for navigation
                ourItemName: bestMatch.name, // Store our item name for reference
                similarity_score: Math.round(bestScore * 100)
              });
            }
          }
        });
        
        // Sort by category
        processedCommonItems.sort((a, b) => a.category.localeCompare(b.category));
        
        // Filter out zero-price items for market position calculation and display
        const validPriceItems = processedCommonItems.filter(item => item.theirPrice !== 0);
        
        // Only display items with price data
        setCommonItems(validPriceItems);
        
        // Create market position data
        const generateMarketData = (): MarketPosition => {
          // Only use common items with valid prices for visualization (same as table items)
          if (validPriceItems.length === 0) {
            // Default values if no valid common items
            return {
              marketLow: 1,
              marketHigh: 10,
              ourPrice: 5,
              competitorPrice: 5,
              marketAverage: 5,
              ourPricePosition: 50,
              competitorPricePosition: 50,
              originalMarketLow: 0,
              originalMarketHigh: 0,
              originalOurPrice: 0,
              originalCompetitorPrice: 0,
              originalMarketAverage: 0
            };
          }

          // Get price points only for items in the table (validPriceItems)
          const ourMatchedPrices = validPriceItems.map(item => item.ourPrice);
          const competitorMatchedPrices = validPriceItems.map(item => item.theirPrice);
          const allMatchedPrices = [...ourMatchedPrices, ...competitorMatchedPrices];
          
          const marketLow = Math.min(...allMatchedPrices);
          const marketHigh = Math.max(...allMatchedPrices);
          
          // Calculate average prices using ONLY matched items with valid prices
          const ourAvgPrice = ourMatchedPrices.reduce((acc, price) => acc + price, 0) / ourMatchedPrices.length;
          const competitorAvgPrice = competitorMatchedPrices.reduce((acc, price) => acc + price, 0) / competitorMatchedPrices.length;
          const marketAvgPrice = allMatchedPrices.reduce((a, b) => a + b, 0) / allMatchedPrices.length;
          
          // Normalize prices to 1-10 scale
          const normalize = (price: number) => {
            return ((price - marketLow) / (marketHigh - marketLow)) * 9 + 1;
          };
          
          // Calculate percentage position for visualization
          const ourPricePosition = ((ourAvgPrice - marketLow) / (marketHigh - marketLow)) * 100;
          const competitorPricePosition = ((competitorAvgPrice - marketLow) / (marketHigh - marketLow)) * 100;
          
          return {
            marketLow: 1,
            marketHigh: 10,
            ourPrice: normalize(ourAvgPrice),
            competitorPrice: normalize(competitorAvgPrice),
            marketAverage: normalize(marketAvgPrice),
            ourPricePosition,
            competitorPricePosition,
            originalMarketLow: marketLow,
            originalMarketHigh: marketHigh,
            originalOurPrice: ourAvgPrice,
            originalCompetitorPrice: competitorAvgPrice,
            originalMarketAverage: marketAvgPrice
          };
        };
        
        setMarketPositionData(generateMarketData());
        
        // Calculate overall competitor data using only the items displayed in the table
        const categoriesSet = new Set<string>();
        validPriceItems.forEach(item => item.category && categoriesSet.add(item.category));
        
        // Use the same valid price items for summary calculations
        let avgPriceDiff = 0;
        let status: 'higher' | 'lower' | 'same' = 'same';
        let formattedDiff = '0.0%';
        
        if (validPriceItems.length > 0) {
          // Get average prices from the matched valid items
          const ourAvgPrice = validPriceItems.reduce((acc, item) => acc + item.ourPrice, 0) / validPriceItems.length;
          const competitorAvgPrice = validPriceItems.reduce((acc, item) => acc + item.theirPrice, 0) / validPriceItems.length;
          
          // Calculate price difference
          avgPriceDiff = ((competitorAvgPrice - ourAvgPrice) / competitorAvgPrice) * 100;
          formattedDiff = `${avgPriceDiff > 0 ? '+' : ''}${avgPriceDiff.toFixed(1)}%`;
          status = avgPriceDiff > 0 ? 'higher' : avgPriceDiff < 0 ? 'lower' : 'same';
        }
        
        // Calculate average similarity score for displayed items only
        const avgSimilarityScore = validPriceItems.length > 0 ?
          validPriceItems.reduce((acc, item) => acc + (item.similarity_score || 75), 0) / validPriceItems.length :
          75; // Default value if no valid items
        
        setCompetitorData({
          id: '0', // Using a placeholder ID since we're now using names
          name: competitorName,
          similarityScore: Math.round(avgSimilarityScore),
          priceDifference: formattedDiff,
          status: status,
          categories: Array.from(categoriesSet)
        });
        
        setLoading(false);
      } catch (err: any) {
        console.error('Error fetching competitor data:', err);
        setError('Failed to load competitor data. Please try again later.');
        setLoading(false);
      }
    };
    
    // Always fetch data regardless of how we're identifying the competitor
    fetchData();
  }, [competitorId]);

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '40px 0' }}>
        <Spin size="large" />
      </div>
    );
  }
  
  if (error || !competitorData) {
    return (
      <div>
        <Button 
          icon={<ArrowLeftOutlined />} 
          onClick={() => {
            // Navigate back to either the new or old component based on where we came from
            navigate(isReportId ? '/competitors' : '/competitor-analysis');
          }} 
          style={{ marginBottom: 16 }}
        >
          Back to {isReportId ? 'Competitors' : 'Competitor Analysis'}
        </Button>
        
        <Alert
          message="Error"
          description={error || 'Failed to load competitor data'}
          type="error"
          showIcon
        />
      </div>
    );
  }

  return (
    <div>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Button 
          type="link" 
          icon={<LeftOutlined />} 
          onClick={() => navigate('/competitor-analysis')}
          style={{ padding: 0, fontSize: 20, color: 'gray' }}
        >
          Competitor Analysis
        </Button>
        
        {/* Header Section */}
        <Card>
          <Row gutter={[24, 24]} align="middle">
            <Col xs={24} md={8}>
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <div style={{ 
                  width: 64, 
                  height: 64, 
                  backgroundColor: '#f0f0f0', 
                  borderRadius: '50%', 
                  display: 'flex', 
                  justifyContent: 'center', 
                  alignItems: 'center',
                  marginRight: 16,
                  fontSize: 28
                }}>
                  <ShopOutlined />
                </div>
                <div>
                  <Title level={5} type="secondary">In-Depth Analysis of {competitorData?.name}</Title>
                  <div style={{ marginTop: 8 }}>
                    {competitorData?.categories.map((category, index) => (
                      <Tag color="blue" key={index} style={{ marginBottom: 4 }}>{category}</Tag>
                    ))}
                  </div>
                </div>
              </div>
            </Col>
            <Col xs={24} md={8} style={{ textAlign: 'center' }}>
              <Statistic
                title="Relative Price"
                value={competitorData?.priceDifference}
                valueStyle={{
                  color: competitorData?.status === 'higher' ? '#cf1322' : '#3f8600'
                }}
                prefix={competitorData?.status === 'higher' ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
              />
              <Text type="secondary">compared to your prices</Text>
            </Col>
            <Col xs={24} md={8} style={{ textAlign: 'center' }}>
              <Statistic
                title="Similarity Score"
                value={competitorData?.similarityScore}
                suffix="%"
                valueStyle={{ color: '#1890ff' }}
              />
              <Text type="secondary">based on menu overlap</Text>
            </Col>
          </Row>
        </Card>
        
        {/* Market Overview Card */}
        <Card>
          <Divider>Relative Market Position</Divider>
          <div style={{ padding: '80px 0 80px' }}>
            <div style={{ position: 'relative', height: 10, background: 'linear-gradient(to right, #f0f0f0, #d9d9d9, #bfbfbf)', borderRadius: 4 }}>
              {/* Our price dot */}
              <div
                style={{
                  position: 'absolute',
                  left: `${marketPositionData?.ourPricePosition}%`,
                  top: '50%',
                  width: 12,
                  height: 12,
                  backgroundColor: '#1890ff',
                  borderRadius: '50%',
                  transform: 'translate(-50%, -50%)',
                  border: '2px solid white',
                  zIndex: 2
                }}
              />
              
              {/* Competitor price dot */}
              <div
                style={{
                  position: 'absolute',
                  left: `${marketPositionData?.competitorPricePosition}%`,
                  top: '50%',
                  width: 12,
                  height: 12,
                  backgroundColor: '#cf1322',
                  borderRadius: '50%',
                  transform: 'translate(-50%, -50%)',
                  border: '2px solid white',
                  zIndex: 2
                }}
              />
              
              {/* Market average dot with hover effect */}
              <div style={{ position: 'relative' }}>
                <div
                  style={{
                    position: 'absolute',
                    left: `${(marketPositionData?.marketAverage ? (marketPositionData.marketAverage - 1) / 9 * 100 : 50)}%`,
                    top: 5,
                    width: 12,
                    height: 12,
                    backgroundColor: '#faad14',
                    borderRadius: '50%',
                    transform: 'translate(-50%, -50%)',
                    border: '2px solid white',
                    zIndex: 2,
                    cursor: 'pointer'
                  }}
                  onMouseOver={(e) => {
                    // Find the tooltip element
                    const tooltip = e.currentTarget.nextElementSibling as HTMLElement;
                    if (tooltip) {
                      tooltip.style.display = 'block';
                    }
                  }}
                  onMouseOut={(e) => {
                    // Find the tooltip element
                    const tooltip = e.currentTarget.nextElementSibling as HTMLElement;
                    if (tooltip) {
                      tooltip.style.display = 'none';
                    }
                  }}
                />
                <div
                  style={{
                    position: 'absolute',
                    left: `${(marketPositionData?.marketAverage ? (marketPositionData.marketAverage - 1) / 9 * 100 : 50)}%`,
                    top: -50,
                    transform: 'translateX(-50%)',
                    backgroundColor: '#fff8e6',
                    border: '1px solid #ffe58f',
                    borderRadius: '4px',
                    padding: '4px 8px',
                    zIndex: 3,
                    display: 'none',
                    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
                    whiteSpace: 'nowrap',
                    textAlign: 'center',
                    color: '#5c3c00',
                    fontSize: '14px',
                    fontWeight: 'bold'
                  }}
                >
                  Market Average: {marketPositionData?.marketAverage ? marketPositionData.marketAverage.toFixed(1) : '0.0'}
                </div>
              </div>
              {/* Scale markings */}
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(mark => {
                // Calculate position - distributing marks from 0% to 100%
                const position = (mark - 1) / 9 * 100; // This ensures mark 1 is at 0% and mark 10 is at 100%
                
                return (
                  <div 
                    key={mark}
                    style={{
                      position: 'absolute',
                      left: `${position}%`,
                      bottom: -20,
                      color: '#666',
                      fontSize: '12px',
                      transform: 'translateX(-50%)'
                    }}
                  >
                    {mark}
                  </div>
                );
              })}
              
              {/* Our price marker */}
              <div 
                style={{ 
                  position: 'absolute', 
                  left: `${marketPositionData?.ourPricePosition}%`, 
                  bottom: -50, 
                  transform: 'translateX(-50%)',
                  color: '#1890ff',
                  textAlign: 'center',
                  backgroundColor: '#f0f9ff',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  border: '1px solid #d6e4ff',
                  minWidth: '80px'
                }}
              >
                <ArrowUpOutlined style={{ fontSize: 20, position: 'absolute', top: -20, left: '50%', transform: 'translateX(-50%)', color: '#1890ff' }} />
                <div style={{ fontWeight: 'bold' }}>Your Price: {marketPositionData?.ourPrice ? marketPositionData.ourPrice.toFixed(1) : '0.0'}</div>
              </div>
              
              {/* Competitor price marker */}
              <div 
                style={{ 
                  position: 'absolute', 
                  left: `${marketPositionData?.competitorPricePosition}%`, 
                  top: -50, 
                  transform: 'translateX(-50%)',
                  color: '#cf1322',
                  textAlign: 'center',
                  backgroundColor: '#fff1f0',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  border: '1px solid #ffccc7',
                  minWidth: '80px'
                }}
              >
                <div style={{ fontWeight: 'bold' }}>{competitorData.name}: {marketPositionData?.competitorPrice ? marketPositionData.competitorPrice.toFixed(1) : '0.0'}</div>
                <ArrowDownOutlined style={{ fontSize: 20, position: 'absolute', bottom: -20, left: '50%', transform: 'translateX(-50%)', color: '#cf1322' }} />
              </div>
            </div>
          </div>
          
          <Text type="secondary" style={{ display: 'block' }}>
            This chart shows the relative price positioning on a normalized scale of 1-10, where 1 represents the lowest market price and 10 represents the highest market price. 
            Original dollar prices are shown below each score.
          </Text>
        </Card>
        
        {/* Common Items Table */}
        <Card 
          title={<span><ShopOutlined /> Similar Menu Items</span>}
          style={{ marginTop: 24 }}
        >
          <Divider orientation="left">Menu Items Comparison</Divider>
          
          {commonItems.length === 0 ? (
            <Alert
              message="No Common Items Found"
              description="No menu items were found that match between your business and this competitor."
              type="info"
              showIcon
            />
          ) : (
            <Table 
              dataSource={commonItems}
              style={{ marginTop: 20 }}
              onRow={(record) => ({
                onClick: () => navigate(`/product/${record.productId}`),
                style: { cursor: 'pointer' }
              })}
              columns={[
                {
                  title: 'Competitor Item',
                  dataIndex: 'itemName',
                  key: 'itemName',
                },
                {
                  title: 'Your Item',
                  dataIndex: 'ourItemName',
                  key: 'ourItemName',
                },
                {
                  title: 'Category',
                  dataIndex: 'category',
                  key: 'category',
                  filters: Array.from(new Set(commonItems.map(item => item.category)))
                    .map(category => ({ text: category, value: category })),
                  onFilter: (value, record) => record.category === value,
                  render: (category) => (
                    <Tag color="blue">{category}</Tag>
                  )
                },
                {
                  title: 'Our Price',
                  dataIndex: 'ourPrice',
                  key: 'ourPrice',
                  render: (price) => `$${price.toFixed(2)}`,
                  sorter: (a, b) => a.ourPrice - b.ourPrice,
                },
                {
                  title: 'Their Price',
                  dataIndex: 'theirPrice',
                  key: 'theirPrice',
                  render: (price) => price === 0 ? 'N/A' : `$${price.toFixed(2)}`,
                  sorter: (a, b) => a.theirPrice - b.theirPrice,
                },
                {
                  title: 'Difference',
                  dataIndex: 'difference',
                  sorter: (a, b) => a.diffValue - b.diffValue,
                  render: (diff, record) => {
                    if (diff === 'N/A') return <Tag color='gray'>N/A</Tag>;
                    
                    const status = record.status;
                    return (
                      <Tag color={status === 'higher' ? 'green' : status === 'lower' ? 'red' : 'gray'}>
                        {diff}
                      </Tag>
                    );
                  },
                },
              ]}
            />
          )}
          
          <Text type="secondary" style={{ display: 'block', marginTop: 16 }}>
            Click on any item to view detailed product information and metrics.
          </Text>
        </Card>
      </Space>
    </div>
  );
};

export default CompetitorDetail;
