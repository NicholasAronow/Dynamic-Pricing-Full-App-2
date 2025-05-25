import React, { useState, useEffect } from 'react';
import { Modal, Progress, Timeline, Typography, Card, Badge, Space } from 'antd';
import { 
  CheckCircleOutlined, 
  SyncOutlined, 
  ClockCircleOutlined, 
  RobotOutlined,
  ExperimentOutlined,
  ShopOutlined,
  UserOutlined,
  BarChartOutlined
} from '@ant-design/icons';
import agentService, { AgentProgressData } from '../../services/agentService';

const { Title, Text, Paragraph } = Typography;

interface AgentProgressMonitorProps {
  visible: boolean;
  processId: string;
  onClose: () => void;
}

const AgentProgressMonitor: React.FC<AgentProgressMonitorProps> = ({ 
  visible, 
  processId,
  onClose 
}) => {
  const [progress, setProgress] = useState<AgentProgressData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [intervalId, setIntervalId] = useState<NodeJS.Timeout | null>(null);

  // Function to fetch process status
  const fetchProcessStatus = async () => {
    try {
      const data = await agentService.getProcessStatus(processId);
      setProgress(data);
      setLoading(false);
      
      // If process is complete or has error, stop polling
      if (data.status === 'completed' || data.status === 'error') {
        if (intervalId) {
          clearInterval(intervalId);
          setIntervalId(null);
        }
      }
    } catch (err) {
      console.error('Error fetching process status:', err);
      setError('Failed to get process status');
      setLoading(false);
      
      // Stop polling on error
      if (intervalId) {
        clearInterval(intervalId);
        setIntervalId(null);
      }
    }
  };

  // Set up polling when the component mounts
  useEffect(() => {
    if (visible && processId) {
      // Fetch initial status
      fetchProcessStatus();
      
      // Set up polling every 2 seconds
      const id = setInterval(fetchProcessStatus, 2000);
      setIntervalId(id);
    }
    
    // Clean up on unmount
    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [visible, processId]);

  // Get agent icon based on type
  const getAgentIcon = (agentType: string) => {
    switch (agentType) {
      case 'competitor_agent':
        return <ShopOutlined />;
      case 'customer_agent':
        return <UserOutlined />;
      case 'market_agent':
        return <BarChartOutlined />;
      case 'pricing_agent':
        return <RobotOutlined />;
      case 'experiment_agent':
        return <ExperimentOutlined />;
      default:
        return <RobotOutlined />;
    }
  };

  // Get step status icon
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'running':
        return <SyncOutlined spin style={{ color: '#1890ff' }} />;
      case 'pending':
        return <ClockCircleOutlined style={{ color: '#d9d9d9' }} />;
      default:
        return <ClockCircleOutlined style={{ color: '#d9d9d9' }} />;
    }
  };

  // Modal title based on process status
  const getModalTitle = () => {
    if (!progress) return 'Agent Process';
    
    switch (progress.status) {
      case 'completed':
        return 'Agent Process Completed';
      case 'error':
        return 'Agent Process Failed';
      case 'running':
        return `Agent Process Running - ${progress.current_step.replace('_', ' ')}`;
      default:
        return 'Agent Process';
    }
  };

  // If not visible, don't render anything
  if (!visible) return null;

  return (
    <Modal
      title={<Title level={4}>{getModalTitle()}</Title>}
      open={visible}
      onCancel={onClose}
      width={600}
      footer={null}
      maskClosable={progress?.status === 'completed' || progress?.status === 'error'}
      closable={progress?.status === 'completed' || progress?.status === 'error'}
    >
      {loading && !progress ? (
        <div style={{ textAlign: 'center', padding: '20px' }}>
          <SyncOutlined spin style={{ fontSize: 24 }} />
          <Paragraph style={{ marginTop: 10 }}>Loading process status...</Paragraph>
        </div>
      ) : error ? (
        <div style={{ textAlign: 'center', padding: '20px' }}>
          <Paragraph type="danger">{error}</Paragraph>
        </div>
      ) : progress ? (
        <div>
          <Card style={{ marginBottom: 16 }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text strong>Progress:</Text>
              <Progress 
                percent={progress.progress_percent} 
                status={progress.status === 'error' ? 'exception' : progress.status === 'completed' ? 'success' : 'active'} 
              />
              <Text>{progress.message}</Text>
              {progress.error && <Text type="danger">Error: {progress.error}</Text>}
            </Space>
          </Card>
          
          <Timeline mode="left">
            {Object.entries(progress.steps).map(([agentType, stepData]) => {
              const status = (stepData as any).status;
              return (
                <Timeline.Item 
                  key={agentType}
                  dot={getAgentIcon(agentType)}
                  color={status === 'completed' ? 'green' : status === 'running' ? 'blue' : 'gray'}
                >
                  <Space>
                    <Text strong style={{ textTransform: 'capitalize' }}>
                      {agentType.replace('_', ' ')}
                    </Text>
                    <Badge 
                      status={status === 'completed' ? 'success' : status === 'running' ? 'processing' : 'default'} 
                      text={status} 
                    />
                    {getStatusIcon(status)}
                  </Space>
                  {(stepData as any).report_id && (
                    <div>
                      <Text type="secondary">Report ID: {(stepData as any).report_id}</Text>
                    </div>
                  )}
                </Timeline.Item>
              );
            })}
          </Timeline>
        </div>
      ) : (
        <div style={{ textAlign: 'center', padding: '20px' }}>
          <Paragraph>No process information available</Paragraph>
        </div>
      )}
    </Modal>
  );
};

export default AgentProgressMonitor;
