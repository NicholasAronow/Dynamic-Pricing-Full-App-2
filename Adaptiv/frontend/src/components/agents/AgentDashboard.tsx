import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Typography, Tabs, Button, Space, Tooltip, Modal, message, Spin, Empty } from 'antd';
import { RobotOutlined, PlusOutlined, SettingOutlined, ApiOutlined, PlayCircleOutlined, FileTextOutlined } from '@ant-design/icons';
import agentService, { AgentReport } from '../../services/agentService';
import AgentReports from './AgentReports';
import AgentProgressMonitor from './AgentProgressMonitor';

const { Title, Paragraph } = Typography;
const { TabPane } = Tabs;

interface AgentCard {
  id: string;
  name: string;
  description: string;
  type: string;
  status: 'active' | 'inactive' | 'training';
}

const AgentDashboard: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(false);
  const [runningProcess, setRunningProcess] = useState<boolean>(false);
  const [reports, setReports] = useState<AgentReport | null>(null);
  const [reportModalVisible, setReportModalVisible] = useState<boolean>(false);
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null);
  
  // Progress monitoring state
  const [progressModalVisible, setProgressModalVisible] = useState<boolean>(false);
  const [currentProcessId, setCurrentProcessId] = useState<string>('');

  // Define default agent configurations but we'll update their status based on reports
  const [agents, setAgents] = useState<AgentCard[]>([
    {
      id: '1',
      name: 'Pricing Agent',
      description: 'Analyzes sales data and market trends to recommend optimal pricing strategies.',
      type: 'pricing',
      status: 'inactive'
    },
    {
      id: '2',
      name: 'Competitor Agent',
      description: 'Monitors competitor prices and product offerings to provide competitive insights.',
      type: 'competitor',
      status: 'inactive'
    },
    {
      id: '3', 
      name: 'Customer Agent',
      description: 'Analyzes customer behavior and preferences to predict demand and price sensitivity.',
      type: 'customer',
      status: 'inactive'
    },
    {
      id: '4',
      name: 'Market Agent',
      description: 'Analyzes market trends and external factors affecting pricing decisions.',
      type: 'market',
      status: 'inactive'
    },
    {
      id: '5',
      name: 'Experiment Agent',
      description: 'Designs and evaluates pricing experiments to test price elasticity and customer responses.',
      type: 'experiment',
      status: 'inactive'
    }
  ]);

  useEffect(() => {
    fetchLatestReports();
    
    return () => {
      // Clean up polling interval when component unmounts
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, []);

  const fetchLatestReports = async () => {
    try {
      setLoading(true);
      const data = await agentService.getLatestReports();
      setReports(data);

      // Update agent statuses based on available reports
      // This ensures we only show agents as active if they have reports for this user
      const updatedAgents = [...agents];
      
      // Check each agent type and update status based on report availability
      updatedAgents.forEach(agent => {
        switch(agent.type) {
          case 'competitor':
            agent.status = data?.competitor_report?.id ? 'active' : 'inactive';
            break;
          case 'customer':
            agent.status = data?.customer_report?.id ? 'active' : 'inactive';
            break;
          case 'market':
            agent.status = data?.market_report?.id ? 'active' : 'inactive';
            break;
          case 'pricing':
            agent.status = data?.pricing_report?.id ? 'active' : 'inactive';
            break;
          case 'experiment':
            agent.status = data?.experiment_recommendation?.id ? 'active' : 'inactive';
            break;
        }
      });
      
      setAgents(updatedAgents);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching reports:', error);
      setLoading(false);
      message.error('Failed to fetch agent reports');
    }
  };

  const runFullAgentProcess = async () => {
    try {
      setRunningProcess(true);
      const response = await agentService.runFullAgentProcess();
      message.success(response.message);
      
      // Get the process ID from the response
      if (response.data && response.data.process_id) {
        const processId = response.data.process_id;
        setCurrentProcessId(processId);
        setProgressModalVisible(true);
      }
      
      // Set up polling for updates
      const interval = setInterval(async () => {
        try {
          const data = await agentService.getLatestReports();
          setReports(data);
          
          // Check if all reports are generated
          if (data.experiment_recommendation && data.experiment_recommendation.id) {
            clearInterval(interval);
            setRunningProcess(false);
            message.success('All agent reports generated successfully!');
            // Fetch reports one more time to ensure we have the latest data
            fetchLatestReports();
          }
        } catch (error) {
          console.error('Error polling for reports:', error);
        }
      }, 5000); // Poll every 5 seconds
      
      setPollingInterval(interval);
      
      // Stop polling after 10 minutes to prevent endless polling
      setTimeout(() => {
        if (interval) {
          clearInterval(interval);
          setPollingInterval(null);
          setRunningProcess(false);
        }
      }, 600000);
      
    } catch (error) {
      console.error('Error running agent process:', error);
      setRunningProcess(false);
      message.error('Failed to start agent process');
    }
  };

  const getStatusColor = (status: string) => {
    switch(status) {
      case 'active': return '#52c41a';
      case 'inactive': return '#d9d9d9';
      case 'training': return '#faad14';
      default: return '#d9d9d9';
    }
  };

  return (
    <div>
      <Row gutter={[16, 16]} align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={2} style={{ margin: 0 }}>
            <RobotOutlined /> Agent Dashboard
          </Title>
        </Col>
        <Col flex="auto"></Col>
        <Col>
          <Space>
            <Button 
              type="primary" 
              icon={<PlayCircleOutlined />} 
              onClick={runFullAgentProcess} 
              loading={runningProcess}
              disabled={runningProcess}
            >
              Run Full Agent Process
            </Button>
            <Button 
              icon={<FileTextOutlined />} 
              onClick={() => setReportModalVisible(true)}
              disabled={!reports}
            >
              View Reports
            </Button>
          </Space>
        </Col>
      </Row>

      <Paragraph style={{ marginBottom: 24 }}>
        Manage your intelligent agents that help optimize your pricing strategy. Each agent specializes in different aspects of your business. Run the full agent process to generate comprehensive pricing recommendations based on competitor, customer, and market analysis.
      </Paragraph>

      <Tabs defaultActiveKey="all">
        <TabPane tab="All Agents" key="all">
          <Row gutter={[16, 16]}>
            {agents.map(agent => (
              <Col xs={24} sm={12} lg={8} xl={6} key={agent.id}>
                <Card
                  hoverable
                  style={{ height: '100%' }}
                  actions={[
                    <Tooltip title="Configure Agent">
                      <SettingOutlined key="setting" />
                    </Tooltip>,
                    <Tooltip title="API Access">
                      <ApiOutlined key="api" />
                    </Tooltip>
                  ]}
                >
                  <div style={{ marginBottom: 12 }}>
                    <Space>
                      <RobotOutlined style={{ fontSize: 24 }} />
                      <span style={{ fontSize: 18, fontWeight: 500 }}>{agent.name}</span>
                    </Space>
                    <div 
                      style={{ 
                        float: 'right', 
                        width: 10, 
                        height: 10, 
                        borderRadius: 5, 
                        backgroundColor: getStatusColor(agent.status),
                        marginTop: 8
                      }} 
                    />
                  </div>
                  <Paragraph 
                    style={{ 
                      height: 60, 
                      overflow: 'hidden', 
                      textOverflow: 'ellipsis', 
                      display: '-webkit-box',
                      WebkitLineClamp: 3,
                      WebkitBoxOrient: 'vertical'
                    }}
                  >
                    {agent.description}
                  </Paragraph>
                  <div style={{ marginTop: 12 }}>
                    <span style={{ 
                      textTransform: 'capitalize', 
                      color: getStatusColor(agent.status),
                      fontWeight: 500
                    }}>
                      {agent.status}
                    </span>
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
        </TabPane>
        <TabPane tab="Active" key="active">
          <Row gutter={[16, 16]}>
            {agents.filter(agent => agent.status === 'active').map(agent => (
              <Col xs={24} sm={12} lg={8} xl={6} key={agent.id}>
                <Card
                  hoverable
                  style={{ height: '100%' }}
                  actions={[
                    <Tooltip title="Configure Agent">
                      <SettingOutlined key="setting" />
                    </Tooltip>,
                    <Tooltip title="API Access">
                      <ApiOutlined key="api" />
                    </Tooltip>
                  ]}
                >
                  <div style={{ marginBottom: 12 }}>
                    <Space>
                      <RobotOutlined style={{ fontSize: 24 }} />
                      <span style={{ fontSize: 18, fontWeight: 500 }}>{agent.name}</span>
                    </Space>
                    <div 
                      style={{ 
                        float: 'right', 
                        width: 10, 
                        height: 10, 
                        borderRadius: 5, 
                        backgroundColor: getStatusColor(agent.status),
                        marginTop: 8
                      }} 
                    />
                  </div>
                  <Paragraph 
                    style={{ 
                      height: 60, 
                      overflow: 'hidden', 
                      textOverflow: 'ellipsis', 
                      display: '-webkit-box',
                      WebkitLineClamp: 3,
                      WebkitBoxOrient: 'vertical'
                    }}
                  >
                    {agent.description}
                  </Paragraph>
                  <div style={{ marginTop: 12 }}>
                    <span style={{ 
                      textTransform: 'capitalize', 
                      color: getStatusColor(agent.status),
                      fontWeight: 500
                    }}>
                      {agent.status}
                    </span>
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
        </TabPane>
      </Tabs>
      <Modal
        title="Agent Reports"
        open={reportModalVisible}
        onCancel={() => setReportModalVisible(false)}
        width={800}
        footer={null}
      >
        <AgentReports reports={reports} loading={loading} />
      </Modal>
      
      <AgentProgressMonitor
        visible={progressModalVisible}
        processId={currentProcessId}
        onClose={() => setProgressModalVisible(false)}
      />
    </div>
  );
};

export default AgentDashboard;
