import React, { useState, useEffect } from 'react';
import { Alert, Button, Card, Col, Divider, Row, Select, Spin, Typography, message } from 'antd';
import { RobotOutlined, PlayCircleOutlined, SyncOutlined, BarChartOutlined } from '@ant-design/icons';
import axios from 'axios';
import { API_BASE_URL } from 'config';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

interface AgentDefinition {
  name: string;
  display_name: string;
  description: string;
  capabilities: string[];
}

const AgentTesting: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(false);
  const [agents, setAgents] = useState<AgentDefinition[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string>('');
  const [agentOutput, setAgentOutput] = useState<any>(null);
  const [outputLoading, setOutputLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [llmAnalysisOutput, setLlmAnalysisOutput] = useState<string | null>(null);
  const [llmAnalysisLoading, setLlmAnalysisLoading] = useState<boolean>(false);
  
  // Fetch available agents on component mount
  useEffect(() => {
    fetchAvailableAgents();
  }, []);
  
  // Fetch all available agents and their capabilities
  const fetchAvailableAgents = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.get(`${API_BASE_URL}/api/agents/dynamic-pricing/agent-capabilities`);
      
      if (response.data && response.data.agents) {
        // Transform the data into the format we need
        const agentList: AgentDefinition[] = Object.entries(response.data.agents).map(([key, value]: [string, any]) => ({
          name: key,
          display_name: value.display_name || key.replace(/_/g, ' '),
          description: value.description || 'No description available',
          capabilities: value.capabilities || []
        }));
        
        setAgents(agentList);
        
        // Set default selected agent if available
        if (agentList.length > 0) {
          setSelectedAgent(agentList[0].name);
        }
      }
    } catch (err) {
      console.error('Error fetching agent capabilities:', err);
      setError('Failed to load agent capabilities. Please try again later.');
      message.error('Failed to load agent capabilities');
    } finally {
      setLoading(false);
    }
  };
  
  // Handle agent selection change
  const handleAgentChange = (value: string) => {
    setSelectedAgent(value);
    // Clear previous output when changing agents
    setAgentOutput(null);
  };
  
  // Test the selected agent
  const testSelectedAgent = async () => {
    if (!selectedAgent) {
      message.warning('Please select an agent first');
      return;
    }
    
    setOutputLoading(true);
    setError(null);
    setAgentOutput(null);
    setLlmAnalysisOutput(null);
    
    try {
      // Call the backend endpoint to test the agent
      const response = await axios.post(`${API_BASE_URL}/api/agents/dynamic-pricing/test-agent/${selectedAgent}`, {});
      
      if (response.data) {
        setAgentOutput(response.data);
        
        if (response.data.status === 'error') {
          message.error(`Agent test failed: ${response.data.error}`);
        } else {
          message.success('Agent test completed successfully');
        }
      }
    } catch (err: any) {
      console.error('Error testing agent:', err);
      setError(err.response?.data?.detail || 'Failed to test agent. Please try again later.');
      message.error('Failed to test agent');
    } finally {
      setOutputLoading(false);
    }
  };
  
  // Run LLM analysis on the agent output
  const runLlmAnalysis = async () => {
    if (!agentOutput) {
      message.warning('Please run the agent test first');
      return;
    }
    
    setLlmAnalysisLoading(true);
    setLlmAnalysisOutput(null);
    
    try {
      // Send the agent output data directly to our backend for LLM analysis
      const response = await axios.post(`${API_BASE_URL}/api/agents/dynamic-pricing/llm-analysis`, 
        agentOutput || {}
      );
      
      if (response.data && response.data.content) {
        setLlmAnalysisOutput(response.data.content);
        message.success('LLM analysis completed');
      }
    } catch (err: any) {
      console.error('Error running LLM analysis:', err);
      setError(err.response?.data?.detail || 'Failed to run LLM analysis. Please try again later.');
      message.error('Failed to run LLM analysis');
    } finally {
      setLlmAnalysisLoading(false);
    }
  };
  
  return (
    <div className="agent-testing-container">
      <Card title={
        <div>
          <RobotOutlined style={{ marginRight: '8px' }} />
          Agent Testing Console
        </div>
      }>
        <Row gutter={[16, 16]}>
          <Col span={24}>
            <Paragraph>
              Test individual dynamic pricing agents and view their outputs directly. 
              This tool helps with debugging and understanding agent behavior.
            </Paragraph>
          </Col>
          
          <Col xs={24} sm={18} md={12}>
            <div style={{ marginBottom: '16px' }}>
              <Text strong>Select an agent to test:</Text>
              <Select 
                style={{ width: '100%', marginTop: '8px' }} 
                value={selectedAgent}
                onChange={handleAgentChange}
                loading={loading}
                disabled={loading || outputLoading}
                placeholder="Select an agent"
              >
                {agents.map(agent => (
                  <Option key={agent.name} value={agent.name}>
                    {agent.display_name}
                  </Option>
                ))}
              </Select>
            </div>
            
            {selectedAgent && agents.find(a => a.name === selectedAgent) && (
              <div style={{ marginBottom: '16px' }}>
                <Text type="secondary">
                  {agents.find(a => a.name === selectedAgent)?.description}
                </Text>
                <div style={{ marginTop: '8px' }}>
                  {agents.find(a => a.name === selectedAgent)?.capabilities.map(cap => (
                    <Text key={cap} type="secondary" style={{ display: 'block' }}>
                      • {cap}
                    </Text>
                  ))}
                </div>
              </div>
            )}
            
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={testSelectedAgent}
              loading={outputLoading}
              disabled={!selectedAgent || loading}
              size="large"
              style={{ marginTop: '16px' }}
            >
              Test {selectedAgent && agents.find(a => a.name === selectedAgent)?.display_name}
            </Button>
            
            {error && (
              <Alert
                message="Error"
                description={error}
                type="error"
                showIcon
                style={{ marginTop: '16px' }}
              />
            )}
          </Col>
        </Row>
        
        <Divider />
        
        <Row>
          <Col span={24}>
            <Title level={4}>Agent Output</Title>
            {outputLoading ? (
              <div style={{ textAlign: 'center', padding: '32px' }}>
                <Spin size="large" />
                <div style={{ marginTop: '16px' }}>
                  <Text>Running agent... This may take a minute or two.</Text>
                </div>
              </div>
            ) : agentOutput ? (
              <div className="agent-output" style={{ maxHeight: '600px', overflow: 'auto' }}>
                <Card>
                  <div style={{ marginBottom: '16px' }}>
                    <Text strong>Agent: </Text>
                    <Text>{agentOutput.agent_name}</Text>
                  </div>
                  <div style={{ marginBottom: '16px' }}>
                    <Text strong>Status: </Text>
                    <Text type={agentOutput.status === 'success' ? 'success' : 'danger'}>
                      {agentOutput.status}
                    </Text>
                  </div>
                  
                  {agentOutput.execution_details && (
                    <div style={{ marginBottom: '16px' }}>
                      <Text strong>Execution Time: </Text>
                      <Text>
                        {agentOutput.execution_details.duration_seconds.toFixed(2)} seconds
                      </Text>
                    </div>
                  )}
                  
                  <Divider />
                  
                  <div>
                    <Text strong>Output:</Text>
                    <div style={{ marginTop: '16px', backgroundColor: '#f5f5f5', padding: '16px', borderRadius: '4px' }}>
                      <Paragraph>
                        <pre style={{ maxHeight: '500px', overflow: 'auto', margin: 0 }}>
                          {JSON.stringify(agentOutput.output || agentOutput, null, 2)}
                        </pre>
                        
                        <div style={{ marginTop: '16px' }}>
                          <Button 
                            type="primary"
                            icon={<BarChartOutlined />}
                            onClick={runLlmAnalysis}
                            loading={llmAnalysisLoading}
                            disabled={!agentOutput}
                          >
                            Run LLM Analysis
                          </Button>
                        </div>
                        
                        {llmAnalysisLoading && (
                          <div style={{ marginTop: '16px', textAlign: 'center' }}>
                            <Spin />
                            <div style={{ marginTop: '8px' }}>
                              <Text>Generating analysis with AI...</Text>
                            </div>
                          </div>
                        )}
                        
                        {llmAnalysisOutput && (
                          <div style={{ marginTop: '16px' }}>
                            <Divider>
                              <Text strong>LLM Analysis</Text>
                            </Divider>
                            <div style={{ backgroundColor: '#f0f9ff', padding: '16px', borderRadius: '4px', border: '1px solid #d1e9ff' }}>
                              <pre style={{ whiteSpace: 'pre-wrap', overflow: 'auto', margin: 0 }}>
                                {llmAnalysisOutput}
                              </pre>
                            </div>
                          </div>
                        )}
                      </Paragraph>
                    </div>
                  </div>
                </Card>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '32px', backgroundColor: '#f5f5f5', borderRadius: '4px' }}>
                <Text type="secondary">Select an agent and click "Test" to see output</Text>
              </div>
            )}
          </Col>
        </Row>
      </Card>
    </div>
  );
};

export default AgentTesting;
