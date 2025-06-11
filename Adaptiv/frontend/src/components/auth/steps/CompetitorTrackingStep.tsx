import React, { useState } from 'react';
import { Form, Radio, Typography, Card, Space, Button, Input, Spin, List, Checkbox } from 'antd';
import { CompassOutlined, RightOutlined, ClockCircleOutlined, SearchOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Title, Paragraph, Text } = Typography;

interface CompetitorTrackingStepProps {
  formData: any;
  updateFormData: (data: any) => void;
}

interface CompetitorType {
  name: string;
  address?: string;
  distance_km?: number;
  selected?: boolean;
}

const CompetitorTrackingStep: React.FC<CompetitorTrackingStepProps> = ({ formData, updateFormData }) => {
  const [form] = Form.useForm();
  const [showSearch, setShowSearch] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<CompetitorType[]>([]);
  const [searching, setSearching] = useState(false);
  const [selectedCompetitors, setSelectedCompetitors] = useState<CompetitorType[]>(formData.selectedCompetitors || []);
  
  const handleValuesChange = (_: any, allValues: any) => {
    // Only update the setupCompetitorsNow value directly
    updateFormData({ setupCompetitorsNow: allValues.setupCompetitorsNow });
    
    // If user selects "Set up later", hide the search section
    if (allValues.setupCompetitorsNow === false) {
      setShowSearch(false);
    }
  };
  
  const handleSetupNowClick = () => {
    form.setFieldsValue({ setupCompetitorsNow: true });
    updateFormData({ setupCompetitorsNow: true });
    setShowSearch(true);
  };
  
  const searchCompetitors = async () => {
    if (!searchQuery.trim()) return;
    
    try {
      setSearching(true);
      // In a real implementation, this would call the backend API
      // For demo purposes, we'll simulate a search response with mock data
      
      // Simulate network delay
      await new Promise(resolve => setTimeout(resolve, 800));
      
      // Mock data based on the search query
      const mockResults = [
        { name: `${searchQuery} Coffee`, address: '123 Main St, New York, NY', distance_km: 0.5 },
        { name: `Bean's ${searchQuery} Cafe`, address: '456 Park Ave, New York, NY', distance_km: 1.2 },
        { name: `The ${searchQuery} Bistro`, address: '789 Broadway, New York, NY', distance_km: 0.8 },
        { name: `${searchQuery}'s Deli`, address: '321 Madison Ave, New York, NY', distance_km: 1.6 }
      ];
      
      setSearchResults(mockResults);
    } catch (error) {
      console.error('Error searching for competitors:', error);
    } finally {
      setSearching(false);
    }
  };
  
  const toggleCompetitorSelection = (competitor: CompetitorType) => {
    // Check if this competitor is already in the selected list
    const isSelected = selectedCompetitors.some(c => c.name === competitor.name);
    
    if (isSelected) {
      // Remove from selection
      const newSelectedCompetitors = selectedCompetitors.filter(c => c.name !== competitor.name);
      setSelectedCompetitors(newSelectedCompetitors);
      updateFormData({ selectedCompetitors: newSelectedCompetitors });
    } else {
      // Add to selection
      const newSelectedCompetitors = [...selectedCompetitors, competitor];
      setSelectedCompetitors(newSelectedCompetitors);
      updateFormData({ selectedCompetitors: newSelectedCompetitors });
    }
  };

  return (
    <div className="registration-step">
      <Title level={4}>Competitor Tracking</Title>
      <Paragraph>
        Set up competitor tracking to monitor pricing changes and stay competitive in your market.
      </Paragraph>
      
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          setupCompetitorsNow: formData.setupCompetitorsNow
        }}
        onValuesChange={handleValuesChange}
      >
        <Form.Item name="setupCompetitorsNow">
          <Radio.Group>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Card 
                hoverable 
                className={`selection-card ${formData.setupCompetitorsNow ? 'selected' : ''}`}
                onClick={handleSetupNowClick}
              >
                <Space>
                  <CompassOutlined style={{ fontSize: '24px', color: '#1890ff' }} />
                  <div>
                    <Text strong>Set up now</Text>
                    <Paragraph style={{ marginBottom: 0 }}>
                      Find and track competitors in your area right away
                    </Paragraph>
                  </div>
                  <RightOutlined style={{ marginLeft: 'auto' }} />
                </Space>
              </Card>
              
              <Card 
                hoverable 
                className={`selection-card ${formData.setupCompetitorsNow === false ? 'selected' : ''}`}
                onClick={() => {
                  form.setFieldsValue({ setupCompetitorsNow: false });
                  updateFormData({ setupCompetitorsNow: false, selectedCompetitors: [] });
                  setShowSearch(false);
                }}
              >
                <Space>
                  <ClockCircleOutlined style={{ fontSize: '24px', color: '#52c41a' }} />
                  <div>
                    <Text strong>Set up later</Text>
                    <Paragraph style={{ marginBottom: 0 }}>
                      Skip for now and set up competitor tracking anytime from your dashboard
                    </Paragraph>
                  </div>
                  <RightOutlined style={{ marginLeft: 'auto' }} />
                </Space>
              </Card>
            </Space>
          </Radio.Group>
        </Form.Item>

        {showSearch && (
          <Card bordered={false} style={{ backgroundColor: '#f5f5f5', marginTop: 20 }}>
            <Title level={5}>Find Local Competitors</Title>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Input.Search
                placeholder="Search for competitors by name or cuisine"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onSearch={searchCompetitors}
                enterButton={<SearchOutlined />}
                loading={searching}
              />
              
              {searching && (
                <div style={{ textAlign: 'center', padding: '20px 0' }}>
                  <Spin />
                  <div style={{ marginTop: 8 }}>Searching for competitors...</div>
                </div>
              )}
              
              {!searching && searchResults.length > 0 && (
                <List
                  itemLayout="horizontal"
                  dataSource={searchResults}
                  renderItem={item => {
                    const isSelected = selectedCompetitors.some(c => c.name === item.name);
                    return (
                      <List.Item 
                        actions={[
                          <Button 
                            type={isSelected ? "primary" : "default"}
                            onClick={() => toggleCompetitorSelection(item)}
                          >
                            {isSelected ? "Selected" : "Select"}
                          </Button>
                        ]}
                      >
                        <List.Item.Meta
                          title={item.name}
                          description={
                            <>
                              {item.address}
                              {item.distance_km !== undefined && (
                                <div>{item.distance_km} km away</div>
                              )}
                            </>
                          }
                        />
                      </List.Item>
                    );
                  }}
                />
              )}
              
              {!searching && searchResults.length === 0 && searchQuery && (
                <div style={{ textAlign: 'center', padding: '20px 0' }}>
                  <div>No competitors found. Please try a different search term.</div>
                </div>
              )}
              
              {selectedCompetitors.length > 0 && (
                <div style={{ marginTop: 20 }}>
                  <Title level={5}>Selected Competitors ({selectedCompetitors.length})</Title>
                  <List
                    size="small"
                    bordered
                    dataSource={selectedCompetitors}
                    renderItem={item => (
                      <List.Item
                        actions={[
                          <Button 
                            type="text" 
                            danger
                            onClick={() => toggleCompetitorSelection(item)}
                          >
                            Remove
                          </Button>
                        ]}
                      >
                        {item.name}
                      </List.Item>
                    )}
                  />
                </div>
              )}
            </Space>
          </Card>
        )}
      </Form>
    </div>
  );
};

export default CompetitorTrackingStep;
