import React, { useState, useEffect } from 'react';
import { Card, Button, message, Spin, Alert, Tabs, Badge, Progress, Statistic, Row, Col, Timeline, Tag, Tooltip, Space, Divider, Modal, Input, Empty } from 'antd';
import { RobotOutlined, PlayCircleOutlined, CheckCircleOutlined, ClockCircleOutlined, ExperimentOutlined, LineChartOutlined, SearchOutlined, ThunderboltOutlined, WarningOutlined, CheckOutlined, CloseOutlined } from '@ant-design/icons';
import axios from 'axios';
import { API_BASE_URL } from 'config';
import pricingService, { AgentPricingRecommendation } from '../../services/pricingService';

const { TabPane } = Tabs;

interface AgentStatus {
  name: string;
  status: 'idle' | 'running' | 'completed' | 'error';
  lastRun?: string;
  icon: React.ReactNode;
}

interface AnalysisResults {
  executive_summary?: {
    overall_status: string;
    revenue_trend: string;
    key_opportunities: string[];
    immediate_actions: string[];
    risk_factors: string[];
  };
  consolidated_recommendations?: Array<{
    priority: string;
    recommendation: string;
    expected_impact: string;
    category: string;
  }>;
  next_steps?: Array<{
    step: number;
    action: string;
    expected_impact: string;
    timeline: string;
  }>;
}

const { TextArea } = Input;

interface FeedbackModalProps {
  visible: boolean;
  recommendation: AgentPricingRecommendation | null;
  action: 'accept' | 'reject';
  onSubmit: (action: 'accept' | 'reject', feedback: string) => void;
  onCancel: () => void;
}

const FeedbackModal: React.FC<FeedbackModalProps> = ({ 
  visible, 
  recommendation, 
  action, 
  onSubmit, 
  onCancel 
}) => {
  const [feedback, setFeedback] = useState('');

  useEffect(() => {
    if (visible) {
      setFeedback(''); // Reset feedback when modal opens
    }
  }, [visible]);

  return (
    <Modal
      title={action === 'accept' ? 'Accept Price Recommendation' : 'Reject Price Recommendation'}
      open={visible}
      onCancel={onCancel}
      footer={[
        <Button key="back" onClick={onCancel}>
          Cancel
        </Button>,
        <Button 
          key="submit" 
          type="primary" 
          onClick={() => onSubmit(action, feedback)}
        >
          {action === 'accept' ? 'Accept' : 'Reject'}
        </Button>,
      ]}
    >
      {recommendation && (
        <>
          <p>
            <strong>Item:</strong> {recommendation.item_name}<br />
            <strong>Current Price:</strong> ${Number(recommendation.current_price).toFixed(2)}<br />
            <strong>Recommended Price:</strong> ${Number(recommendation.recommended_price).toFixed(2)}<br />
            <strong>Change:</strong> ${Number(recommendation.price_change_amount).toFixed(2)} ({(Number(recommendation.price_change_percent) * 100).toFixed(1)}%)
          </p>
          <div style={{ marginBottom: 16 }}>
            <div style={{ color: '#888', marginBottom: 8 }}>Please provide any feedback or reasoning (optional):</div>
            <TextArea
              rows={4}
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="Add your feedback here..."
            />
          </div>
        </>
      )}
    </Modal>
  );
};

const DynamicPricingAgents: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [analysisStatus, setAnalysisStatus] = useState<'idle' | 'running' | 'completed' | 'error'>('idle');
  const [results, setResults] = useState<AnalysisResults | null>(null);
  const [recommendations, setRecommendations] = useState<AgentPricingRecommendation[]>([]);
  const [pendingRecommendations, setPendingRecommendations] = useState<AgentPricingRecommendation[]>([]);
  const [completedRecommendations, setCompletedRecommendations] = useState<AgentPricingRecommendation[]>([]);
  const [loadingRecommendations, setLoadingRecommendations] = useState<boolean>(false);
  const [lastFetchTime, setLastFetchTime] = useState<number>(0);
  const [feedbackModal, setFeedbackModal] = useState<{
    visible: boolean;
    recommendation: AgentPricingRecommendation | null;
    action: 'accept' | 'reject';
  }>({
    visible: false,
    recommendation: null,
    action: 'accept'
  });
  const [agentStatuses, setAgentStatuses] = useState<AgentStatus[]>([
    { name: 'Data Collection', status: 'idle', icon: <SearchOutlined /> },
    { name: 'Market Analysis', status: 'idle', icon: <LineChartOutlined /> },
    { name: 'Pricing Strategy', status: 'idle', icon: <ThunderboltOutlined /> },
    { name: 'Performance Monitor', status: 'idle', icon: <CheckCircleOutlined /> },
    { name: 'Experimentation', status: 'idle', icon: <ExperimentOutlined /> }
  ]);

  // Load recommendations from localStorage on component mount
  useEffect(() => {
    const savedRecommendations = localStorage.getItem('adaptiv_pricing_recommendations');
    const savedTimestamp = localStorage.getItem('adaptiv_recommendations_timestamp');
    
    if (savedRecommendations && savedTimestamp) {
      try {
        const recommendations = JSON.parse(savedRecommendations);
        const timestamp = parseInt(savedTimestamp, 10);
        
        // Only use saved recommendations if they're less than 24 hours old
        const isRecent = (Date.now() - timestamp) < 24 * 60 * 60 * 1000;
        
        if (isRecent && recommendations.length > 0) {
          setRecommendations(recommendations);
          setLastFetchTime(timestamp);
          
          // Organize recommendations by status
          const pending = recommendations.filter((rec: AgentPricingRecommendation) => !rec.user_action);
          const completed = recommendations.filter((rec: AgentPricingRecommendation) => rec.user_action);
          
          setPendingRecommendations(pending);
          setCompletedRecommendations(completed);
          
          console.log(`Loaded ${recommendations.length} saved recommendations from localStorage`);
        } else {
          // Data is too old or empty, fetch fresh data
          fetchAgentRecommendations();
        }
      } catch (e) {
        console.error('Error parsing saved recommendations:', e);
        fetchAgentRecommendations();
      }
    } else {
      // No saved data, fetch fresh data
      fetchAgentRecommendations();
    }
  }, []);

  const fetchAgentRecommendations = async () => {
    try {
      setLoadingRecommendations(true);
      
      // Fetch ALL recommendations, not just pending ones
      const data = await pricingService.getAgentRecommendations();
      
      // Debug log the received data
      console.log('Pricing recommendations received:', data);
      if (data && data.length > 0) {
        data.forEach((rec: AgentPricingRecommendation) => {
          console.log(`${rec.item_name}: Current: $${rec.current_price}, Recommended: $${rec.recommended_price}, Change %: ${rec.price_change_percent}`);
        });
      }
      
      // Save to state and localStorage
      setRecommendations(data);
      setLastFetchTime(Date.now());
      localStorage.setItem('adaptiv_pricing_recommendations', JSON.stringify(data));
      localStorage.setItem('adaptiv_recommendations_timestamp', Date.now().toString());
      
      // Organize recommendations by status
      const pending = data.filter((rec: AgentPricingRecommendation) => !rec.user_action);
      const completed = data.filter((rec: AgentPricingRecommendation) => rec.user_action);
      
      setPendingRecommendations(pending);
      setCompletedRecommendations(completed);
    } catch (error) {
      console.error('Error fetching agent recommendations:', error);
      message.error('Failed to load pricing recommendations');
    } finally {
      setLoadingRecommendations(false);
    }
  };

  const handleActionClick = (recommendation: AgentPricingRecommendation, action: 'accept' | 'reject') => {
    setFeedbackModal({
      visible: true,
      recommendation,
      action
    });
  };

  const handleActionConfirm = async (action: 'accept' | 'reject', feedback: string) => {
    if (!feedbackModal.recommendation) return;

    try {
      const result = await pricingService.updateRecommendationAction(
        feedbackModal.recommendation.id, 
        action, 
        feedback
      );
      
      if (result) {
        message.success(`Successfully ${action}ed the price recommendation`);
        
        // Update the local state without making another API call
        const updatedRecommendations = recommendations.map((rec: AgentPricingRecommendation) => {
          if (rec.id === feedbackModal.recommendation!.id) {
            return {
              ...rec,
              user_action: action,
              user_feedback: feedback
            };
          }
          return rec;
        });
        
        setRecommendations(updatedRecommendations);
        
        // Update localStorage
        localStorage.setItem('adaptiv_pricing_recommendations', JSON.stringify(updatedRecommendations));
        
        // Re-filter pending and completed recommendations
        setPendingRecommendations(updatedRecommendations.filter((rec: AgentPricingRecommendation) => !rec.user_action));
        setCompletedRecommendations(updatedRecommendations.filter((rec: AgentPricingRecommendation) => rec.user_action));
      } else {
        message.error(`Failed to ${action} the recommendation`);
      }
    } catch (error) {
      console.error(`Error ${action}ing recommendation:`, error);
      message.error(`Error ${action}ing recommendation. Please try again.`);
    } finally {
      // Close modal
      setFeedbackModal({
        visible: false,
        recommendation: null,
        action: 'accept'
      });
    }
  };
  
  const runFullAnalysis = async () => {
    try {
      setLoading(true);
      setAnalysisStatus('running');
      
      // Update all agents to running
      setAgentStatuses(prev => prev.map(agent => ({ ...agent, status: 'running' })));
      
      // Debug logging
      console.log('Calling API to start analysis...');
      
      const response = await axios.post(
        `${API_BASE_URL}/api/agents/dynamic-pricing/run-full-analysis`,
        {},
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`
          }
        }
      );
      
      // Debug logging
      console.log('API response:', response.data);

      if (response.data.status === 'started') {
        setTaskId(response.data.task_id);
        message.info('Dynamic pricing analysis started. This may take a few moments...');
        
        // Start polling for results
        pollForResults(response.data.task_id);
      } else {
        // Handle other response statuses
        message.warning(`Unexpected response: ${response.data.status || 'unknown'}`);
        setAnalysisStatus('error');
      }
    } catch (error) {
      console.error('Error starting analysis:', error);
      message.error('Failed to start analysis');
      setAnalysisStatus('error');
      setAgentStatuses(prev => prev.map(agent => ({ ...agent, status: 'error' })));
    } finally {
      setLoading(false);
    }
  };

  const pollForResults = async (taskId: string) => {
    const maxAttempts = 600; // 10 minutes max
    let attempts = 0;
    
    console.log('Starting to poll for results with task ID:', taskId);
    
    const poll = setInterval(async () => {
      try {
        console.log(`Polling attempt ${attempts + 1}...`);
        
        const response = await axios.get(
          `${API_BASE_URL}/api/agents/dynamic-pricing/analysis-status/${taskId}`,
          {
            headers: {
              Authorization: `Bearer ${localStorage.getItem('token')}`
            }
          }
        );
        
        console.log('Poll response:', response.data);

        // Update status message if available
        if (response.data.message) {
          setAnalysisStatus(response.data.message);
          console.log('Updated status message:', response.data.message);
        }

        if (response.data.status === 'completed') {
          clearInterval(poll);
          setAnalysisStatus('completed');
          console.log('Analysis complete! Results:', response.data.results);
          
          // Check if results structure is as expected
          if (response.data.results) {
            setResults(response.data.results);
            console.log('Results set in state');
          } else {
            console.error('Results missing from response');
            message.warning('Analysis completed but results are not available');
          }
          
          setAgentStatuses(prev => prev.map(agent => ({ 
            ...agent, 
            status: 'completed',
            lastRun: new Date().toLocaleTimeString()
          })));
          message.success('Analysis completed successfully!');
        } else if (response.data.status === 'error') {
          clearInterval(poll);
          setAnalysisStatus('error');
          console.error('Analysis failed with error:', response.data.error);
          setAgentStatuses(prev => prev.map(agent => ({ ...agent, status: 'error' })));
          message.error(`Analysis failed: ${response.data.error || 'Unknown error'}`);
        }
        
        attempts++;
        if (attempts >= maxAttempts) {
          clearInterval(poll);
          message.warning('Analysis is taking longer than expected. Please check back later.');
        }
      } catch (error) {
        console.error('Error polling for results:', error);
        clearInterval(poll);
      }
    }, 1000);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return '#52c41a';
      case 'stable': return '#faad14';
      case 'needs_attention': return '#f5222d';
      default: return '#8c8c8c';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'error';
      case 'medium': return 'warning';
      case 'low': return 'default';
      default: return 'default';
    }
  };

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title={
          <Space>
            <RobotOutlined style={{ fontSize: '24px', color: '#1890ff' }} />
            <span>Dynamic Pricing Agent System</span>
          </Space>
        }
        extra={
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            loading={loading}
            onClick={runFullAnalysis}
            disabled={analysisStatus === 'running'}
          >
            {analysisStatus === 'running' ? 'Analysis Running...' : 'Run Full Analysis'}
          </Button>
        }
      >
        {/* Agent Status Grid */}
        <Row gutter={16} style={{ marginBottom: '24px' }}>
          {agentStatuses.map((agent, index) => (
            <Col span={4} key={index}>
              <Card size="small" bordered={false} style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '24px', marginBottom: '8px' }}>
                  {agent.status === 'running' ? (
                    <Spin />
                  ) : (
                    <span style={{ 
                      color: agent.status === 'completed' ? '#52c41a' : 
                             agent.status === 'error' ? '#f5222d' : '#8c8c8c' 
                    }}>
                      {agent.icon}
                    </span>
                  )}
                </div>
                <div style={{ fontWeight: 500 }}>{agent.name}</div>
                {agent.lastRun && (
                  <div style={{ fontSize: '12px', color: '#8c8c8c' }}>
                    Last run: {agent.lastRun}
                  </div>
                )}
              </Card>
            </Col>
          ))}
        </Row>

        {results && (
          <Tabs defaultActiveKey="summary">
            <TabPane 
              tab={
                <span>
                  Executive Summary
                  <Badge 
                    status={results.executive_summary?.overall_status === 'healthy' ? 'success' : 
                            results.executive_summary?.overall_status === 'stable' ? 'warning' : 'error'} 
                    style={{ marginLeft: '8px' }}
                  />
                </span>
              } 
              key="summary"
            >
              {results.executive_summary && (
                <div>
                  <Row gutter={24} style={{ marginBottom: '24px' }}>
                    <Col span={8}>
                      <Card>
                        <Statistic
                          title="Overall Status"
                          value={results.executive_summary.overall_status}
                          valueStyle={{ 
                            color: getStatusColor(results.executive_summary.overall_status),
                            textTransform: 'capitalize'
                          }}
                        />
                      </Card>
                    </Col>
                    <Col span={8}>
                      <Card>
                        <Statistic
                          title="Revenue Trend"
                          value={results.executive_summary.revenue_trend}
                          valueStyle={{ 
                            color: results.executive_summary.revenue_trend === 'improving' ? '#52c41a' : '#f5222d',
                            textTransform: 'capitalize'
                          }}
                          prefix={results.executive_summary.revenue_trend === 'improving' ? '↑' : '↓'}
                        />
                      </Card>
                    </Col>
                    <Col span={8}>
                      <Card>
                        <Statistic
                          title="Active Alerts"
                          value={results.executive_summary.risk_factors?.length || 0}
                          valueStyle={{ color: results.executive_summary.risk_factors?.length > 0 ? '#f5222d' : '#52c41a' }}
                        />
                      </Card>
                    </Col>
                  </Row>

                  {results.executive_summary.immediate_actions?.length > 0 && (
                    <Alert
                      message="Immediate Actions Required"
                      description={
                        <ul style={{ marginBottom: 0 }}>
                          {results.executive_summary.immediate_actions.map((action, index) => (
                            <li key={index}>{action}</li>
                          ))}
                        </ul>
                      }
                      type="warning"
                      icon={<WarningOutlined />}
                      showIcon
                      style={{ marginBottom: '16px' }}
                    />
                  )}

                  <Card title="Key Opportunities" size="small" style={{ marginBottom: '16px' }}>
                    {results.executive_summary.key_opportunities?.map((opportunity, index) => (
                      <Tag key={index} color="blue" style={{ marginBottom: '8px' }}>
                        {opportunity}
                      </Tag>
                    ))}
                  </Card>

                  {results.executive_summary.risk_factors?.length > 0 && (
                    <Card title="Risk Factors" size="small">
                      {results.executive_summary.risk_factors.map((risk, index) => (
                        <Tag key={index} color="red" style={{ marginBottom: '8px' }}>
                          {risk}
                        </Tag>
                      ))}
                    </Card>
                  )}
                </div>
              )}
            </TabPane>

            <TabPane 
              tab={
                <span>
                  Recommendations 
                  <Badge count={results.consolidated_recommendations?.length || 0} style={{ marginLeft: '8px' }} />
                </span>
              } 
              key="recommendations"
            >
              {results.consolidated_recommendations?.map((rec, index) => (
                <Card 
                  key={index} 
                  size="small" 
                  style={{ marginBottom: '12px' }}
                  title={
                    <Space>
                      <Tag color={getPriorityColor(rec.priority)}>
                        {rec.priority.toUpperCase()}
                      </Tag>
                      <span>{rec.category?.replace(/_/g, ' ').toUpperCase()}</span>
                    </Space>
                  }
                >
                  <p style={{ marginBottom: '8px' }}>{rec.recommendation}</p>
                  {rec.expected_impact && (
                    <div style={{ color: '#52c41a', fontWeight: 500 }}>
                      Expected Impact: {rec.expected_impact}
                    </div>
                  )}
                </Card>
              ))}
            </TabPane>

            <TabPane tab="Next Steps" key="next-steps">
              {results.next_steps && (
                <Timeline>
                  {results.next_steps.map((step, index) => (
                    <Timeline.Item 
                      key={index}
                      color={index === 0 ? 'blue' : 'gray'}
                      dot={index === 0 ? <ClockCircleOutlined /> : undefined}
                    >
                      <Card size="small">
                        <h4>Step {step.step}: {step.action}</h4>
                        <p>Expected Impact: {step.expected_impact}</p>
                        <Tag>{step.timeline}</Tag>
                      </Card>
                    </Timeline.Item>
                  ))}
                </Timeline>
              )}
            </TabPane>

            <TabPane 
              tab={
                <span>
                  <Badge count={pendingRecommendations.length} style={{ marginRight: '6px' }} />
                  Actionable Recommendations
                </span>
              } 
              key="agent-recommendations"
            >
              {loadingRecommendations ? (
                <div style={{ textAlign: 'center', padding: '20px' }}>
                  <Spin size="large" />
                  <div style={{ marginTop: '10px' }}>Loading recommendations...</div>
                </div>
              ) : pendingRecommendations.length > 0 ? (
                <div>
                  <Alert
                    message="Pending Price Recommendations"
                    description="Review and accept/reject these AI-generated price recommendations to help improve your pricing strategy. These recommendations require your decision."
                    type="info"
                    showIcon
                    style={{ marginBottom: '16px' }}
                  />
                  {pendingRecommendations.map((rec) => (
                    <Card 
                      key={rec.id} 
                      size="small" 
                      style={{ marginBottom: '16px' }}
                    >
                      <Row gutter={16} align="middle">
                        <Col span={5}>
                          <strong>{rec.item_name}</strong>
                        </Col>
                        <Col span={4}>
                          Current: <span style={{ fontWeight: 500 }}>${Number(rec.current_price).toFixed(2)}</span>
                        </Col>
                        <Col span={4}>
                          Suggested: <span style={{ fontWeight: 500, color: '#1890ff' }}>${Number(rec.recommended_price).toFixed(2)}</span>
                        </Col>
                        <Col span={3}>
                          <Tag color={rec.price_change_amount >= 0 ? 'green' : 'red'}>
                            {rec.price_change_amount >= 0 ? '+' : ''}
                            {/* Check if price_change_percent is already in percentage format */}
                            {Math.abs(rec.price_change_percent) > 1 ? 
                              rec.price_change_percent.toFixed(1) : 
                              (rec.price_change_percent * 100).toFixed(1)
                            }%
                          </Tag>
                        </Col>
                        <Col span={4}>
                          <Tag color="blue">Confidence: {(rec.confidence_score * 100).toFixed(0)}%</Tag>
                        </Col>
                        <Col span={4}>
                          <Space>
                            <Button 
                              type="primary" 
                              size="small" 
                              icon={<CheckOutlined />} 
                              onClick={() => handleActionClick(rec, 'accept')}
                            >
                              Accept
                            </Button>
                            <Button 
                              size="small" 
                              icon={<CloseOutlined />} 
                              onClick={() => handleActionClick(rec, 'reject')}
                            >
                              Reject
                            </Button>
                          </Space>
                        </Col>
                      </Row>
                      <div style={{ marginTop: '10px' }}>
                        <strong>Rationale:</strong> {rec.rationale}
                      </div>
                    </Card>
                  ))}
                </div>
              ) : (
                <Empty description="No pending pricing recommendations" />
              )}
            </TabPane>
            <TabPane 
              tab={
                <span>
                  <Tag color="#108ee9">{completedRecommendations.length}</Tag>
                  Completed Recommendations
                </span>
              } 
              key="completed-recommendations"
            >
              {completedRecommendations.length > 0 ? (
                <div>
                  <Alert
                    message="Completed Price Recommendations"
                    description="These are recommendations that you have already acted upon."
                    type="success"
                    showIcon
                    style={{ marginBottom: '16px' }}
                  />
                  {completedRecommendations.map((rec: AgentPricingRecommendation) => (
                    <Card 
                      key={rec.id} 
                      size="small" 
                      style={{ marginBottom: '16px' }}
                    >
                      <Row gutter={16} align="middle">
                        <Col span={5}>
                          <strong>{rec.item_name}</strong>
                        </Col>
                        <Col span={4}>
                          Current: <span style={{ fontWeight: 500 }}>${Number(rec.current_price).toFixed(2)}</span>
                        </Col>
                        <Col span={4}>
                          Suggested: <span style={{ fontWeight: 500, color: '#1890ff' }}>${Number(rec.recommended_price).toFixed(2)}</span>
                        </Col>
                        <Col span={3}>
                          <Tag color={rec.price_change_amount >= 0 ? 'green' : 'red'}>
                            {rec.price_change_amount >= 0 ? '+' : ''}
                            {Math.abs(rec.price_change_percent) > 1 ? 
                              rec.price_change_percent.toFixed(1) : 
                              (rec.price_change_percent * 100).toFixed(1)
                            }%
                          </Tag>
                        </Col>
                        <Col span={4}>
                          <Tag color="blue">Confidence: {(rec.confidence_score * 100).toFixed(0)}%</Tag>
                        </Col>
                        <Col span={4}>
                          {rec.user_action === 'accept' ? (
                            <Tag color="success" icon={<CheckOutlined />}>Accepted</Tag>
                          ) : (
                            <Tag color="error" icon={<CloseOutlined />}>Rejected</Tag>
                          )}
                        </Col>
                      </Row>
                      <div style={{ marginTop: '10px' }}>
                        <strong>Rationale:</strong> {rec.rationale}
                      </div>
                      {rec.user_feedback && (
                        <div style={{ marginTop: '8px', background: '#f5f5f5', padding: '8px', borderRadius: '4px' }}>
                          <strong>Your feedback:</strong> {rec.user_feedback}
                        </div>
                      )}
                    </Card>
                  ))}
                </div>
              ) : (
                <Empty description="No completed pricing recommendations" />
              )}
            </TabPane>
          </Tabs>
        )}

        {!results && analysisStatus === 'idle' && (
          <Alert
            message="No Analysis Results"
            description="Click 'Run Full Analysis' to start the dynamic pricing agent system and get recommendations."
            type="info"
            showIcon
          />
        )}

        {analysisStatus === 'running' && (
          <div style={{ textAlign: 'center', padding: '48px' }}>
            <Spin size="large" />
            <p style={{ marginTop: '16px', color: '#8c8c8c' }}>
              Agents are analyzing your pricing data...
            </p>
          </div>
        )}
      </Card>

      <FeedbackModal 
        visible={feedbackModal.visible}
        recommendation={feedbackModal.recommendation}
        action={feedbackModal.action}
        onSubmit={handleActionConfirm}
        onCancel={() => setFeedbackModal({ ...feedbackModal, visible: false })}
      />
    </div>
  );
};
export default DynamicPricingAgents;
