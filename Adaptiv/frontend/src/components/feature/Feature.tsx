import React, { useState, useEffect, useRef } from 'react';
import {
  Card,
  Typography,
  Button,
  Input,
  Space,
  Spin,
  Alert,
  Tag,
  Divider,
  Row,
  Col,
  Avatar,
  List,
  message,
  Tooltip
} from 'antd';
import {
  SendOutlined,
  RobotOutlined,
  UserOutlined,
  BulbOutlined,
  SearchOutlined,
  SettingOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined
} from '@ant-design/icons';

import langgraphService, {
  MultiAgentResponse,
  ArchitectureInfo,
  MultiAgentRequest
} from '../../services/langgraphService';

const { Title, Paragraph, Text } = Typography;
const { TextArea } = Input;

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'agent';
  content: string;
  timestamp: Date;
  agentName?: string;
  executionPath?: string[];
  isThinking?: boolean;
  isStreaming?: boolean;
}

interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  currentInput: string;
  error: string | null;
}

const Feature: React.FC = () => {
  const [chatState, setChatState] = useState<ChatState>({
    messages: [
      {
        id: '1',
        role: 'assistant',
        content: 'Hello! I\'m your pricing expert assistant. I can help you with pricing strategies, market analysis, and algorithm selection. What pricing challenge can I help you with today?',
        timestamp: new Date(),
        agentName: 'pricing_orchestrator'
      }
    ],
    isLoading: false,
    currentInput: '',
    error: null
  });
  
  const [architectures, setArchitectures] = useState<ArchitectureInfo[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<any>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatState.messages]);

  useEffect(() => {
    loadArchitectures();
  }, []);

  const loadArchitectures = async () => {
    try {
      const architectures = await langgraphService.getArchitectures();
      setArchitectures(architectures);
    } catch (error) {
      console.error('Failed to load architectures:', error);
    }
  };

  const handleSendMessage = async () => {
    if (!chatState.currentInput.trim() || chatState.isLoading) return;
  
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: chatState.currentInput.trim(),
      timestamp: new Date()
    };
  
    setChatState(prev => ({
      ...prev,
      messages: [...prev.messages, userMessage],
      currentInput: '',
      isLoading: true,
      error: null
    }));
  
    try {
      // Prepare conversation history (exclude system messages and thinking states)
      const previousMessages = chatState.messages
        .filter(msg => !msg.isThinking && (msg.role === 'user' || msg.role === 'assistant'))
        .map(msg => ({
          role: msg.role,
          content: msg.content
        }));
  
      const request: MultiAgentRequest = {
        task: userMessage.content,
        architecture: 'supervisor',
        context: '',
        previous_messages: previousMessages
      };
  
      // Rest of the function remains the same...

      let currentAgentMessage: ChatMessage | null = null;
      let currentContent = '';

      // Stream the response
      for await (const chunk of langgraphService.streamTask(request)) {
        switch (chunk.type) {
          case 'status':
            // Show initial status
            const statusMessage: ChatMessage = {
              id: `status-${Date.now()}`,
              role: 'assistant',
              content: chunk.message,
              timestamp: new Date(),
              isThinking: true,
              agentName: 'system'
            };
            setChatState(prev => ({
              ...prev,
              messages: [...prev.messages, statusMessage]
            }));
            break;

          case 'agent_start':
            // Agent starts thinking
            const thinkingMessage: ChatMessage = {
              id: `thinking-${chunk.agent}-${Date.now()}`,
              role: 'assistant',
              content: chunk.message,
              timestamp: new Date(),
              isThinking: true,
              agentName: chunk.agent
            };
            setChatState(prev => ({
              ...prev,
              messages: [...prev.messages.filter(m => !m.isThinking || m.agentName !== chunk.agent), thinkingMessage]
            }));
            break;

          case 'message_start':
            // Start of a new message from an agent
            currentContent = '';
            const newAgentMessage: ChatMessage = {
              id: `message-${chunk.agent}-${Date.now()}`,
              role: 'assistant',
              content: '',
              timestamp: new Date(),
              agentName: chunk.agent,
              isStreaming: true
            };
            currentAgentMessage = newAgentMessage;
            setChatState(prev => ({
              ...prev,
              messages: [...prev.messages.filter(m => m && !m.isThinking), newAgentMessage]
            }));
            break;

          // Replace the case 'message_chunk' section:
          case 'message_chunk':
            // Streaming content chunk
            if (currentAgentMessage && chunk.content) {
              currentContent += chunk.content;
              const updatedMessage = {
                ...currentAgentMessage,
                content: currentContent
              };
              setChatState(prev => ({
                ...prev,
                messages: prev.messages.map(m => 
                  m && currentAgentMessage && m.id === currentAgentMessage.id ? updatedMessage : m
                )
              }));
            }
            break;

            case 'message_complete':
              // Message streaming complete
              if (currentAgentMessage) {
                const finalMessage = {
                  ...currentAgentMessage,
                  isStreaming: false
                };
                setChatState(prev => ({
                  ...prev,
                  messages: prev.messages.map(m => 
                    m && currentAgentMessage && m.id === currentAgentMessage.id ? finalMessage : m
                  )
                }));
                currentAgentMessage = null;
                currentContent = ''; // Reset content buffer
              }
              break;

          // Replace the case 'complete' section:
          case 'complete':
            // Final completion
            setChatState(prev => ({
              ...prev,
              isLoading: false,
              messages: prev.messages.filter(m => m && !m.isThinking)
            }));
            // Log execution info
            console.log('Execution complete:', {
              path: chunk.execution_path,
              time: chunk.total_execution_time,
              messageCount: chunk.messages?.length
            });
            break;

          case 'complete':
            // Final completion
            setChatState(prev => ({
              ...prev,
              isLoading: false,
              messages: prev.messages.filter(m => !m.isThinking)
            }));
            break;

          case 'error':
            setChatState(prev => ({
              ...prev,
              isLoading: false,
              error: chunk.message,
              messages: prev.messages.filter(m => !m.isThinking)
            }));
            break;
        }
      }

    } catch (error: any) {
      setChatState(prev => ({
        ...prev,
        messages: prev.messages.filter(m => !m.isThinking),
        isLoading: false,
        error: error.message || 'Failed to get response'
      }));
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const getMessageIcon = (msg: ChatMessage) => {
    if (msg.role === 'user') {
      return <Avatar icon={<UserOutlined />} style={{ backgroundColor: '#1890ff' }} />;
    }
    
    if (msg.isThinking) {
      return <Avatar icon={<Spin size="small" />} style={{ backgroundColor: '#52c41a' }} />;
    }
    
    switch (msg.agentName) {
      case 'web_researcher':
        return <Avatar icon={<SearchOutlined />} style={{ backgroundColor: '#722ed1' }} />;
      case 'algorithm_selector':
        return <Avatar icon={<SettingOutlined />} style={{ backgroundColor: '#fa8c16' }} />;
      default:
        return <Avatar icon={<RobotOutlined />} style={{ backgroundColor: '#52c41a' }} />;
    }
  };

  const getAgentName = (msg: ChatMessage) => {
    if (msg.role === 'user') return 'You';
    if (msg.isThinking) return 'Pricing Expert (thinking...)';
    
    switch (msg.agentName) {
      case 'web_researcher':
        return 'Market Researcher';
      case 'algorithm_selector':
        return 'Algorithm Specialist';
      case 'pricing_orchestrator':
      default:
        return 'Pricing Expert';
    }
  };

  return (
    <>
      <style>
        {`
          @keyframes blink {
            0%, 50% { opacity: 1; }
            51%, 100% { opacity: 0; }
          }
        `}
      </style>
      <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Card 
        title={
          <Space>
            <RobotOutlined style={{ color: '#52c41a' }} />
            <Title level={4} style={{ margin: 0 }}>Pricing Expert Chat</Title>
          </Space>
        }
        style={{ flex: 1, display: 'flex', flexDirection: 'column' }}
        bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column', padding: 0 }}
      >
        {/* Chat Messages Area */}
        <div 
          style={{ 
            flex: 1, 
            overflowY: 'auto', 
            padding: '16px',
            backgroundColor: '#fafafa'
          }}
        >
          <List
            dataSource={chatState.messages.filter(msg => msg && msg.id)}
            renderItem={(msg) => (
              <List.Item
                style={{
                  border: 'none',
                  padding: '8px 0',
                  justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start'
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
                    alignItems: 'flex-start',
                    maxWidth: '80%',
                    gap: '8px'
                  }}
                >
                  {getMessageIcon(msg)}
                  <div
                    style={{
                      backgroundColor: msg.role === 'user' ? '#1890ff' : '#ffffff',
                      color: msg.role === 'user' ? '#ffffff' : '#000000',
                      padding: '12px 16px',
                      borderRadius: '12px',
                      boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                      maxWidth: '100%'
                    }}
                  >
                    <div style={{ fontSize: '12px', opacity: 0.8, marginBottom: '4px' }}>
                      {getAgentName(msg)}
                    </div>
                    <div style={{ whiteSpace: 'pre-wrap' }}>
                      {msg.content}
                      {msg.isStreaming && !msg.isThinking && (
                        <span style={{ 
                          animation: 'blink 1s infinite',
                          marginLeft: '2px',
                          fontSize: '16px'
                        }}>
                          |
                        </span>
                      )}
                    </div>
                    {msg.executionPath && msg.executionPath.length > 1 && (
                      <div style={{ marginTop: '8px', fontSize: '12px', opacity: 0.7 }}>
                        <Space size={4}>
                          <BulbOutlined />
                          <Text>Consulted: {msg.executionPath.join(' → ')}</Text>
                        </Space>
                      </div>
                    )}
                  </div>
                </div>
              </List.Item>
            )}
          />
          <div ref={messagesEndRef} />
        </div>

        {/* Error Display */}
        {chatState.error && (
          <Alert
            message={chatState.error}
            type="error"
            closable
            onClose={() => setChatState(prev => ({ ...prev, error: null }))}
            style={{ margin: '16px' }}
          />
        )}

        {/* Input Area */}
        <div style={{ padding: '16px', backgroundColor: '#ffffff', borderTop: '1px solid #f0f0f0' }}>
          <Space.Compact style={{ width: '100%' }}>
            <TextArea
              ref={inputRef}
              value={chatState.currentInput}
              onChange={(e) => setChatState(prev => ({ ...prev, currentInput: e.target.value }))}
              onKeyPress={handleKeyPress}
              placeholder="Ask me about pricing strategies, market analysis, or algorithm selection..."
              autoSize={{ minRows: 1, maxRows: 4 }}
              disabled={chatState.isLoading}
              style={{ resize: 'none' }}
            />
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSendMessage}
              loading={chatState.isLoading}
              disabled={!chatState.currentInput.trim()}
              style={{ height: 'auto' }}
            >
              Send
            </Button>
          </Space.Compact>
          
          <div style={{ marginTop: '8px', fontSize: '12px', color: '#666' }}>
            <Space>
              <CheckCircleOutlined style={{ color: '#52c41a' }} />
              <Text>Connected to Pricing Expert System</Text>
              {architectures.length > 0 && (
                <>
                  <Divider type="vertical" />
                  <Text>Architecture: {architectures[0]?.title}</Text>
                </>
              )}
            </Space>
          </div>
        </div>
      </Card>
      </div>
    </>
  );
};

export default Feature;
