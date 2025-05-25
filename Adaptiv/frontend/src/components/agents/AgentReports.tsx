import React, { useState } from 'react';
import { Card, Row, Col, Typography, Tabs, Button, Divider, List, Collapse, Timeline, Tag, Statistic, Empty, Space, message as antMessage } from 'antd';
import { CalendarOutlined, AuditOutlined, ThunderboltOutlined, InfoCircleOutlined, BarChartOutlined, LineChartOutlined, TeamOutlined, ShopOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import agentService, { AgentReport } from '../../services/agentService';

const { Title, Paragraph, Text } = Typography;
const { TabPane } = Tabs;
const { Panel } = Collapse;

interface AgentReportsProps {
  reports: AgentReport | null;
  loading: boolean;
}

// Helper function to check if a report has valid content
const hasValidContent = (text: string | undefined | null): boolean => {
  if (!text) return false;
  if (text === "No summary provided") return false;
  if (text.startsWith("Error generating")) return false;
  return true;
};

const hasValidArray = (arr: any[] | undefined | null): boolean => {
  return Array.isArray(arr) && arr.length > 0;
};

const AgentReports: React.FC<AgentReportsProps> = ({ reports, loading }) => {
  // State for tracking price change actions - must be before any conditional returns
  const [actionLoading, setActionLoading] = useState<Record<number, boolean>>({});
  
  if (loading) {
    return <div>Loading reports...</div>;
  }

  if (!reports) {
    return <Empty description="No reports available" />;
  }
  
  // Function to handle price change approval/denial
  const handlePriceChangeAction = (productId: number, approved: boolean) => {
    // Find the product name for better user feedback
    const productName = reports.pricing_report?.recommended_changes?.find(item => item.product_id === productId)?.product_name || 'Product';
    
    // Set loading state for this specific product
    setActionLoading(prev => ({ ...prev, [productId]: true }));
    
    agentService.handlePriceRecommendation(productId, approved)
      .then((response) => {
        // Display success notification
        if (approved) {
          antMessage.success(`Price change for ${productName} approved`);
        } else {
          antMessage.info(`Price change for ${productName} declined`);
        }
        
        // Refresh reports data after 1 second to get updated status
        setTimeout(() => {
          // Note: You may want to add a prop to this component to refresh reports data
          console.log('Reports data should refresh here');
          // Reset loading state
          setActionLoading(prev => ({ ...prev, [productId]: false }));
        }, 1000);
      })
      .catch((error: Error) => {
        // Handle error
        antMessage.error(`Failed to process price change: ${error.message}`);
        setActionLoading(prev => ({ ...prev, [productId]: false }));
      });
  }
  
  return (
    <Tabs defaultActiveKey="summary">
      <TabPane tab="Summary" key="summary">
        <Row gutter={[16, 16]}>
          
          {/* Price Change Recommendations Section */}
          <Col span={24}>
            <Card 
              title={
                <Space>
                  <BarChartOutlined /> 
                  <span>Recommended Price Changes</span>
                </Space>
              } 
              bordered={false}
              extra={<Text type="secondary">Review and take action on these recommendations</Text>}
            >
              {reports.pricing_report && reports.pricing_report.id && hasValidArray(reports.pricing_report.recommended_changes) ? (
                <List
                  dataSource={reports.pricing_report.recommended_changes}
                  renderItem={(item: any) => (
                    <List.Item
                      actions={[
                        <Button 
                          type="primary" 
                          loading={actionLoading[item.product_id] === true}
                          onClick={() => handlePriceChangeAction(item.product_id, true)}
                        >
                          Approve
                        </Button>,
                        <Button 
                          danger 
                          loading={actionLoading[item.product_id] === true}
                          onClick={() => handlePriceChangeAction(item.product_id, false)}
                        >
                          Deny
                        </Button>
                      ]}
                    >
                      <List.Item.Meta
                        avatar={<BarChartOutlined style={{ fontSize: 24, color: '#1890ff' }} />}
                        title={
                          <Space>
                            <span>{`${item.product_name}`}</span>
                            <Tag color={item.change_percentage > 0 ? 'green' : 'red'}>
                              {item.change_percentage > 0 ? '+' : ''}{item.change_percentage.toFixed(2)}%
                            </Tag>
                          </Space>
                        }
                        description={
                          <>
                            <Row gutter={[0, 8]}>
                              <Col span={8}>
                                <Text type="secondary">Current:</Text>{' '}
                                <Text strong>${item.current_price.toFixed(2)}</Text>
                              </Col>
                              <Col span={8}>
                                <Text type="secondary">Recommended:</Text>{' '}
                                <Text strong type={item.change_percentage > 0 ? 'success' : 'danger'}>
                                  ${item.recommended_price.toFixed(2)}
                                </Text>
                              </Col>
                              <Col span={8}>
                                <Text type="secondary">Change:</Text>{' '}
                                <Text strong type={item.change_percentage > 0 ? 'success' : 'danger'}>
                                  {item.change_percentage > 0 ? '+' : ''}{item.change_percentage.toFixed(2)}%
                                </Text>
                              </Col>
                            </Row>
                            <Row>
                              <Col span={24}>
                                <Text type="secondary">Rationale:</Text>
                                <Paragraph style={{ marginTop: 4, marginBottom: 0 }}>
                                  {item.rationale}
                                </Paragraph>
                              </Col>
                            </Row>
                          </>
                        }
                      />
                    </List.Item>
                  )}
                />
              ) : (
                <Empty description="No pricing recommendations available" />
              )}
            </Card>
          </Col>
          
          {/* Action Summary Section */}
          <Col span={24}>
            <Card 
              title={<Space><AuditOutlined /> <span>Implementation Summary</span></Space>} 
              bordered={false}
              actions={[
                <Button size="large" type="primary" style={{ width: '95%' }} 
                  onClick={() => alert('All recommendations approved for implementation!')}>
                  Approve All Recommendations
                </Button>,
                <Button size="large" style={{ width: '95%' }} 
                  onClick={() => alert('Implementation deferred for review')}>
                  Defer for Review
                </Button>
              ]}
            >
              <Paragraph>
                These recommendations are based on analysis of market trends, competitor pricing, and customer behavior patterns. 
                Implementing these changes should optimize your pricing strategy for increased profitability while maintaining competitiveness.
              </Paragraph>
              
              <Row gutter={16}>
                <Col span={8}>
                  <Statistic 
                    title="Total Recommendations" 
                    value={reports.pricing_report?.recommended_changes?.length || 0} 
                    prefix={<BarChartOutlined />} 
                  />
                </Col>
                <Col span={8}>
                  {reports.pricing_report?.recommended_changes && reports.pricing_report.recommended_changes.length > 0 && (
                    <Statistic 
                      title="Price Decreases / Increases" 
                      value={`${reports.pricing_report.recommended_changes.filter(item => item.change_percentage < 0).length} / ${reports.pricing_report.recommended_changes.filter(item => item.change_percentage > 0).length}`}
                      prefix={<LineChartOutlined />} 
                    />
                  )}
                </Col>
                <Col span={8}>
                  {reports.pricing_report?.recommended_changes && reports.pricing_report.recommended_changes.length > 0 && (
                    <Statistic 
                      title="Avg. Price Change" 
                      value={(() => {
                        const changes = reports.pricing_report.recommended_changes;
                        const total = changes.reduce((sum, item) => sum + item.change_percentage, 0);
                        const avg = total / changes.length;
                        return `${avg.toFixed(2)}%`;
                      })()}
                      valueStyle={(() => {
                        const changes = reports.pricing_report.recommended_changes;
                        const total = changes.reduce((sum, item) => sum + item.change_percentage, 0);
                        return { color: total >= 0 ? '#3f8600' : '#cf1322' };
                      })()}
                      prefix={<LineChartOutlined />} 
                    />
                  )}
                </Col>
              </Row>
            </Card>
          </Col>
          
          {/* Experiment Recommendation */}
          <Col span={24}>
            <Card title={<Space><ThunderboltOutlined /> <span>Experiment Plan</span></Space>} bordered={false}>
              {reports.experiment_recommendation && reports.experiment_recommendation.id ? (
                <>
                  <Paragraph>{reports.experiment_recommendation.summary}</Paragraph>
                  <div>
                    <Divider>Implementation Timeline</Divider>
                    <Row gutter={16}>
                      <Col span={12}>
                        <Statistic 
                          title="Start Date" 
                          value={dayjs(reports.experiment_recommendation.start_date).format('MMMM D, YYYY')} 
                          prefix={<CalendarOutlined />} 
                        />
                      </Col>
                      <Col span={12}>
                        <Statistic 
                          title="Evaluation Date" 
                          value={dayjs(reports.experiment_recommendation.evaluation_date).format('MMMM D, YYYY')} 
                          prefix={<AuditOutlined />} 
                        />
                      </Col>
                    </Row>
                    
                    <Divider>Price Change Recommendations</Divider>
                    {reports.experiment_recommendation.recommendations?.implementation && 
                     hasValidArray(reports.experiment_recommendation.recommendations.implementation) ? (
                      <List
                        dataSource={reports.experiment_recommendation.recommendations.implementation}
                        renderItem={(item: any) => (
                          <List.Item>
                            <List.Item.Meta
                              avatar={<ThunderboltOutlined style={{ fontSize: 24, color: '#1890ff' }} />}
                              title={`${item.product_name} (ID: ${item.product_id})`}
                              description={
                                <>
                                  <Tag color={item.new_price > item.current_price ? 'green' : 'red'}>
                                    {item.new_price > item.current_price ? 'Price Increase' : 'Price Decrease'}
                                  </Tag>
                                  <div>Current Price: ${item.current_price.toFixed(2)}</div>
                                  <div>New Price: ${item.new_price.toFixed(2)}</div>
                                  <div>Change: {((item.new_price - item.current_price) / item.current_price * 100).toFixed(2)}%</div>
                                </>
                              }
                            />
                          </List.Item>
                        )}
                      />
                    ) : (
                      <Empty description="No implementation recommendations available" />
                    )}
                  </div>
                </>
              ) : (
                <Empty description="No experiment recommendation available" />
              )}
            </Card>
          </Col>
        </Row>
      </TabPane>
      
      <TabPane tab="Competitor Report" key="competitor">
        <Card title="Competitor Analysis" bordered={false}>
          {/* Direct debug output of competitor report data */}

          {reports.competitor_report && reports.competitor_report.id ? (
            <>
              <Paragraph>{reports.competitor_report.summary}</Paragraph>
              
              {/* Render key insights based on report structure */}
              <Collapse defaultActiveKey={['insights']}>
                <Panel header="Key Insights" key="insights">
                  {/* Try to access insights at different potential nesting levels */}
                  {(() => {
                    // Get the insights array, checking all possible paths
                    let insightsArray = null;
                    let positioningText = null;
                    
                    const insights = reports.competitor_report.insights;
                    
                    // Path 1: insights.insights.insights (deeply nested)
                    if (insights?.insights?.insights && Array.isArray(insights.insights.insights)) {
                      insightsArray = insights.insights.insights;
                      positioningText = insights.insights.positioning || '';
                    }
                    // Path 2: insights.insights (medium nested)
                    else if (insights?.insights && Array.isArray(insights.insights)) {
                      insightsArray = insights.insights; 
                      positioningText = insights.positioning || '';
                    }
                    
                    return (
                      <>
                        {insightsArray && insightsArray.length > 0 ? (
                          <List
                            dataSource={insightsArray}
                            renderItem={(item: any) => (
                              <List.Item>
                                <List.Item.Meta
                                  title={item.title}
                                  description={item.description}
                                />
                              </List.Item>
                            )}
                          />
                        ) : (
                          <Empty description="No insights available" />
                        )}
                        
                        {positioningText && (
                          <div style={{ marginTop: 16 }}>
                            <Divider>Market Positioning</Divider>
                            <Paragraph>{positioningText}</Paragraph>
                          </div>
                        )}
                      </>
                    );
                  })()}
                </Panel>
              </Collapse>
            </>
          ) : (
            <Empty description="No competitor report available" />
          )}
        </Card>
      </TabPane>
      
      <TabPane tab="Customer Report" key="customer">
        <Card title="Customer Analysis" bordered={false}>
          {reports.customer_report && reports.customer_report.id ? (
            <>
              <Paragraph>{reports.customer_report.summary}</Paragraph>
              
              <Row gutter={[16, 16]}>
                <Col span={12}>
                  <Card title="Demographics" size="small">
                    {reports.customer_report.demographics ? (
                      <List
                        dataSource={reports.customer_report.demographics}
                        renderItem={(item: any) => (
                          <List.Item>
                            <List.Item.Meta
                              title={item.name}
                              description={
                                <>
                                  <div>Characteristics: {item.characteristics.join(', ')}</div>
                                  <div>Price Sensitivity: {(item.price_sensitivity * 100).toFixed(0)}%</div>
                                </>
                              }
                            />
                          </List.Item>
                        )}
                      />
                    ) : (
                      <Empty description="No demographic data available" />
                    )}
                  </Card>
                </Col>
                
                <Col span={12}>
                  <Card title="Upcoming Events" size="small">
                    {reports.customer_report.events ? (
                      <List
                        dataSource={reports.customer_report.events}
                        renderItem={(item: any) => (
                          <List.Item>
                            <List.Item.Meta
                              title={item.name}
                              description={
                                <>
                                  <div>Date: {item.date}</div>
                                  <div>Impact: {item.projected_impact}</div>
                                  <div>
                                    <Tag color={item.impact_level > 0.7 ? 'red' : item.impact_level > 0.3 ? 'orange' : 'green'}>
                                      Impact Level: {(item.impact_level * 100).toFixed(0)}%
                                    </Tag>
                                  </div>
                                </>
                              }
                            />
                          </List.Item>
                        )}
                      />
                    ) : (
                      <Empty description="No event data available" />
                    )}
                  </Card>
                </Col>
              </Row>
            </>
          ) : (
            <Empty description="No customer report available" />
          )}
        </Card>
      </TabPane>
      
      <TabPane tab="Market Report" key="market">
        <Card title="Market Analysis" bordered={false}>
          {reports.market_report && reports.market_report.id ? (
            <>
              <Paragraph>{reports.market_report.summary}</Paragraph>
              
              <Collapse defaultActiveKey={['supply']}>
                <Panel header="Supply Chain Factors" key="supply">
                  {reports.market_report.supply_chain && hasValidArray(reports.market_report.supply_chain) ? (
                    <List
                      dataSource={reports.market_report.supply_chain}
                      renderItem={(item: any) => (
                        <List.Item>
                          <List.Item.Meta
                            title={item.factor}
                            description={
                              <>
                                <div>Impact: {item.impact}</div>
                                <div>
                                  <Tag color={item.trend === 'increasing' ? 'red' : item.trend === 'decreasing' ? 'green' : 'blue'}>
                                    Trend: {item.trend.charAt(0).toUpperCase() + item.trend.slice(1)}
                                  </Tag>
                                </div>
                              </>
                            }
                          />
                        </List.Item>
                      )}
                    />
                  ) : (
                    <Empty description="No supply chain data available" />
                  )}
                </Panel>
                
                <Panel header="Cost Trends" key="costs">
                  {reports.market_report.market_trends && reports.market_report.market_trends.cost_trends && 
                   hasValidArray(reports.market_report.market_trends.cost_trends) ? (
                    <List
                      dataSource={reports.market_report.market_trends.cost_trends}
                      renderItem={(item: any) => (
                        <List.Item>
                          <List.Item.Meta
                            title={item.input_category}
                            description={
                              <>
                                <div>Trend: {item.trend}</div>
                                <div>Forecast: {item.forecast}</div>
                              </>
                            }
                          />
                        </List.Item>
                      )}
                    />
                  ) : (
                    <Empty description="No cost trend data available" />
                  )}
                </Panel>
              </Collapse>
            </>
          ) : (
            <Empty description="No market report available" />
          )}
        </Card>
      </TabPane>
      
      <TabPane tab="Pricing Report" key="pricing">
        <Card title="Pricing Analysis" bordered={false}>
          {reports.pricing_report && reports.pricing_report.id ? (
            <>
              <Paragraph>{reports.pricing_report.summary}</Paragraph>
              
              {reports.pricing_report.recommended_changes && (
                <div>
                  <Divider>Product Recommendations</Divider>
                  {hasValidArray(reports.pricing_report.recommended_changes) ? (
                    <List
                      dataSource={reports.pricing_report.recommended_changes}
                      renderItem={(item: any) => (
                        <List.Item>
                          <List.Item.Meta
                            avatar={<BarChartOutlined style={{ fontSize: 24, color: '#1890ff' }} />}
                            title={`${item.product_name} (ID: ${item.product_id})`}
                            description={
                              <>
                                <Tag color={item.change_percentage > 0 ? 'green' : 'red'}>
                                  {item.change_percentage > 0 ? 'Price Increase' : 'Price Decrease'}: {item.change_percentage.toFixed(2)}%
                                </Tag>
                                <div>Current Price: ${item.current_price.toFixed(2)}</div>
                                <div>Recommended Price: ${item.recommended_price.toFixed(2)}</div>
                                <div>Rationale: {item.rationale}</div>
                              </>
                            }
                          />
                        </List.Item>
                      )}
                    />
                  ) : (
                    <Empty description="No specific pricing recommendations provided" />
                  )}
                  
                  {reports.pricing_report.rationale && (
                    <div style={{ marginTop: 16 }}>
                      <Divider>Implementation Advice</Divider>
                      {reports.pricing_report.rationale.implementation && 
                       Object.keys(reports.pricing_report.rationale.implementation).length > 0 ? (
                        <Card size="small">
                          <Row gutter={16}>
                            <Col span={8}>
                              <Title level={5}>Timing</Title>
                              <Paragraph>{reports.pricing_report.rationale.implementation.timing || 'Not specified'}</Paragraph>
                            </Col>
                            <Col span={8}>
                              <Title level={5}>Sequencing</Title>
                              <Paragraph>{reports.pricing_report.rationale.implementation.sequencing || 'Not specified'}</Paragraph>
                            </Col>
                            <Col span={8}>
                              <Title level={5}>Monitoring</Title>
                              <Paragraph>{reports.pricing_report.rationale.implementation.monitoring || 'Not specified'}</Paragraph>
                            </Col>
                          </Row>
                        </Card>
                      ) : (
                        <Empty description="No implementation advice provided" />
                      )}
                    </div>
                  )}
                </div>
              )}
            </>
          ) : (
            <Empty description="No pricing report available" />
          )}
        </Card>
      </TabPane>
    </Tabs>
  );
};

export default AgentReports;
