import React, { useState, useEffect } from 'react';
import { Card, Button, message, Spin, Alert, Tabs, Badge, Progress, Statistic, Row, Col, Timeline, Tag, Tooltip, Space, Divider } from 'antd';
import { RobotOutlined, PlayCircleOutlined, CheckCircleOutlined, ClockCircleOutlined, ExperimentOutlined, LineChartOutlined, SearchOutlined, ThunderboltOutlined, WarningOutlined } from '@ant-design/icons';
import axios from 'axios';
import { API_BASE_URL } from 'config';

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

const DynamicPricingAgents: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [analysisStatus, setAnalysisStatus] = useState<'idle' | 'running' | 'completed' | 'error'>('idle');
  const [results, setResults] = useState<AnalysisResults | null>(null);
  const [agentStatuses, setAgentStatuses] = useState<AgentStatus[]>([
    { name: 'Data Collection', status: 'idle', icon: <SearchOutlined /> },
    { name: 'Market Analysis', status: 'idle', icon: <LineChartOutlined /> },
    { name: 'Pricing Strategy', status: 'idle', icon: <ThunderboltOutlined /> },
    { name: 'Performance Monitor', status: 'idle', icon: <CheckCircleOutlined /> },
    { name: 'Experimentation', status: 'idle', icon: <ExperimentOutlined /> }
  ]);

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
    const maxAttempts = 120; // 2 minutes max
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
    </div>
  );
};

export default DynamicPricingAgents;
