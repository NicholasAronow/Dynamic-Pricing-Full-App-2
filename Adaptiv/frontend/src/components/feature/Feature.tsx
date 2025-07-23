import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
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
  ClockCircleOutlined,
  LoadingOutlined
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
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  agentName?: string;
  isStreaming?: boolean;
}

interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  currentInput: string;
  error: string | null;
  streamingMessageId?: string; // Track which message is currently streaming
}

const Feature: React.FC = () => {
  const [chatState, setChatState] = useState<ChatState>({
    messages: [
      {
        id: '1',
        role: 'assistant',
        content: 'Hello! I\'m Ada, your pricing expert assistant. I can help you with pricing strategies, market analysis, and algorithm selection. What pricing challenge can I help you with today?',
        timestamp: new Date()
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
  
    // Create placeholder for assistant message
    const assistantMessage: ChatMessage = {
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isStreaming: true
    };
  
    setChatState(prev => ({
      ...prev,
      messages: [...prev.messages, userMessage, assistantMessage],
      currentInput: '',
      isLoading: true,
      error: null,
      streamingMessageId: assistantMessage.id
    }));
  
    try {
      // Prepare conversation history
      const previousMessages = chatState.messages
        .filter(msg => msg.role === 'user' || msg.role === 'assistant')
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
  
      let currentContent = '';
      let currentAgentThinking = '';
  
      // Stream the response
      for await (const chunk of langgraphService.streamTask(request)) {
        switch (chunk.type) {
          case 'status':
          case 'agent_start':
            // Show agent thinking in a subtle way (like ChatGPT's "Analyzing...")
            currentAgentThinking = chunk.message || 'Thinking...';
            setChatState(prev => ({
              ...prev,
              messages: prev.messages.map(m => 
                m.id === assistantMessage.id 
                  ? { ...m, content: currentContent || currentAgentThinking, agentName: chunk.agent }
                  : m
              )
            }));
            break;
  
          case 'message_chunk':
            // Accumulate content
            if (chunk.content) {
              currentContent += chunk.content;
              setChatState(prev => ({
                ...prev,
                messages: prev.messages.map(m => 
                  m.id === assistantMessage.id 
                    ? { ...m, content: currentContent }
                    : m
                )
              }));
            }
            break;
  
          case 'message_complete':
            // Message from an agent is complete, but keep streaming
            break;
  
          case 'complete':
            // All done
            setChatState(prev => ({
              ...prev,
              isLoading: false,
              streamingMessageId: undefined,
              messages: prev.messages.map(m => 
                m.id === assistantMessage.id 
                  ? { ...m, isStreaming: false }
                  : m
              )
            }));
            break;
  
          case 'error':
            setChatState(prev => ({
              ...prev,
              isLoading: false,
              error: chunk.message,
              streamingMessageId: undefined,
              messages: prev.messages.filter(m => m.id !== assistantMessage.id)
            }));
            break;
        }
      }
  
    } catch (error: any) {
      setChatState(prev => ({
        ...prev,
        messages: prev.messages.filter(m => m.id !== assistantMessage.id),
        isLoading: false,
        streamingMessageId: undefined,
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
      return ;
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
    else return "Ada"
  };

  return (
    <div style={{ 
      height: '100vh', 
      display: 'flex', 
      flexDirection: 'column',
      backgroundColor: '#f7f7f8'
    }}>
      {/* Header */}
      <div style={{
        backgroundColor: '#fff',
        borderBottom: '1px solid #e5e5e5',
        padding: '16px 24px',
        flexShrink: 0
      }}>
        <div style={{ maxWidth: '768px', margin: '0 auto', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <RobotOutlined style={{ color: '#1890ff', fontSize: '24px' }} />
          <Title level={4} style={{ margin: 0 }}>Ada - Pricing Expert</Title>
        </div>
      </div>
  
      {/* Chat Messages Area */}
      <div style={{ 
        flex: 1, 
        overflowY: 'auto',
        paddingBottom: '20px'
      }}>
        <div style={{ maxWidth: '768px', margin: '0 auto', padding: '20px' }}>
          <List
            dataSource={chatState.messages}
            renderItem={(msg) => (
              <List.Item
                style={{
                  border: 'none',
                  padding: '16px 0',
                  display: 'block'
                }}
              >
                <div style={{
                  display: 'flex',
                  gap: '16px',
                  alignItems: 'flex-start'
                }}>
                  {/* Avatar */}
                  <div style={{ flexShrink: 0 }}>
                    {msg.role === 'user' ? (
                      <Avatar 
                        icon={<UserOutlined />} 
                        style={{ backgroundColor: '#f0f0f0', color: '#666' }}
                        size={36}
                      />
                    ) : (
                      <Avatar 
                        icon={<RobotOutlined />} 
                        style={{ backgroundColor: '#1890ff' }}
                        size={36}
                      />
                    )}
                  </div>
  
                  {/* Message Content */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ 
                      fontWeight: 600, 
                      marginBottom: '4px',
                      color: '#030303'
                    }}>
                      {msg.role === 'user' ? 'You' : 'Ada'}
                    </div>
                    
                    <div style={{ 
                      color: '#030303',
                      lineHeight: '1.5',
                      fontSize: '15px'
                    }}>
                      {msg.role === 'user' ? (
                        <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                      ) : (
                        <>
                          <ReactMarkdown
                            components={{
                              // Paragraphs
                              p: ({children}) => <p style={{margin: '0 0 16px 0', lineHeight: '1.6'}}>{children}</p>,
                              
                              // Headers
                              h1: ({children}) => <h1 style={{fontSize: '28px', fontWeight: '600', margin: '24px 0 16px 0', lineHeight: '1.3'}}>{children}</h1>,
                              h2: ({children}) => <h2 style={{fontSize: '22px', fontWeight: '600', margin: '20px 0 12px 0', lineHeight: '1.3'}}>{children}</h2>,
                              h3: ({children}) => <h3 style={{fontSize: '18px', fontWeight: '600', margin: '16px 0 8px 0', lineHeight: '1.4'}}>{children}</h3>,
                              h4: ({children}) => <h4 style={{fontSize: '16px', fontWeight: '600', margin: '12px 0 8px 0', lineHeight: '1.4'}}>{children}</h4>,
                              h5: ({children}) => <h5 style={{fontSize: '14px', fontWeight: '600', margin: '12px 0 8px 0', lineHeight: '1.4'}}>{children}</h5>,
                              h6: ({children}) => <h6 style={{fontSize: '13px', fontWeight: '600', margin: '12px 0 8px 0', lineHeight: '1.4'}}>{children}</h6>,
                              
                              // Lists
                              ul: ({children}) => <ul style={{margin: '12px 0', paddingLeft: '28px', lineHeight: '1.6'}}>{children}</ul>,
                              ol: ({children}) => <ol style={{margin: '12px 0', paddingLeft: '28px', lineHeight: '1.6'}}>{children}</ol>,
                              li: ({children}) => <li style={{margin: '4px 0', paddingLeft: '4px'}}>{children}</li>,
                              
                              // Code
                              code: ({children, ...props}: any) => {
                                const isInline = !props.className || !props.className.includes('language-');
                                return isInline ? (
                                  <code style={{
                                    backgroundColor: '#f0f2f5',
                                    padding: '2px 6px',
                                    borderRadius: '4px',
                                    fontSize: '85%',
                                    fontFamily: 'Consolas, Monaco, "Courier New", monospace',
                                    color: '#c41d7f'
                                  }}>{children}</code>
                                ) : (
                                  <code style={{
                                    display: 'block',
                                    backgroundColor: '#f6f8fa',
                                    padding: '16px',
                                    borderRadius: '6px',
                                    fontSize: '14px',
                                    fontFamily: 'Consolas, Monaco, "Courier New", monospace',
                                    overflowX: 'auto'
                                  }}>{children}</code>
                                );
                              },
                              
                              pre: ({children}) => (
                                <pre style={{
                                  backgroundColor: '#f6f8fa',
                                  border: '1px solid #e1e4e8',
                                  borderRadius: '6px',
                                  padding: '16px',
                                  overflow: 'auto',
                                  fontSize: '14px',
                                  lineHeight: '1.45',
                                  margin: '16px 0',
                                  fontFamily: 'Consolas, Monaco, "Courier New", monospace'
                                }}>{children}</pre>
                              ),
                              
                              // Blockquotes
                              blockquote: ({children}) => (
                                <blockquote style={{
                                  borderLeft: '4px solid #1890ff',
                                  paddingLeft: '16px',
                                  margin: '16px 0',
                                  color: '#57606a',
                                  fontStyle: 'italic'
                                }}>{children}</blockquote>
                              ),
                              
                              // Text formatting
                              strong: ({children}) => <strong style={{fontWeight: '600', color: '#24292f'}}>{children}</strong>,
                              em: ({children}) => <em style={{fontStyle: 'italic'}}>{children}</em>,
                              del: ({children}) => <del style={{textDecoration: 'line-through', opacity: 0.7}}>{children}</del>,
                              
                              // Links
                              a: ({href, children}) => (
                                <a 
                                  href={href} 
                                  target="_blank" 
                                  rel="noopener noreferrer"
                                  style={{
                                    color: '#1890ff',
                                    textDecoration: 'none',
                                    borderBottom: '1px solid transparent',
                                    transition: 'border-color 0.2s'
                                  }}
                                  onMouseEnter={(e) => e.currentTarget.style.borderBottomColor = '#1890ff'}
                                  onMouseLeave={(e) => e.currentTarget.style.borderBottomColor = 'transparent'}
                                >{children}</a>
                              ),
                              
                              // Horizontal rule
                              hr: () => <hr style={{border: 'none', borderTop: '1px solid #e1e4e8', margin: '24px 0'}} />,
                              
                              // Tables
                              table: ({children}) => (
                                <div style={{overflowX: 'auto', margin: '16px 0'}}>
                                  <table style={{
                                    borderCollapse: 'collapse',
                                    width: '100%',
                                    fontSize: '14px'
                                  }}>{children}</table>
                                </div>
                              ),
                              thead: ({children}) => <thead style={{backgroundColor: '#f6f8fa'}}>{children}</thead>,
                              tbody: ({children}) => <tbody>{children}</tbody>,
                              tr: ({children}) => <tr style={{borderTop: '1px solid #e1e4e8'}}>{children}</tr>,
                              th: ({children}) => (
                                <th style={{
                                  padding: '12px 16px',
                                  fontWeight: '600',
                                  textAlign: 'left',
                                  borderTop: '1px solid #e1e4e8'
                                }}>{children}</th>
                              ),
                              td: ({children}) => (
                                <td style={{
                                  padding: '12px 16px',
                                  borderTop: '1px solid #e1e4e8'
                                }}>{children}</td>
                              ),
                              
                              // Images
                              img: ({src, alt}) => (
                                <img 
                                  src={src} 
                                  alt={alt} 
                                  style={{
                                    maxWidth: '100%',
                                    height: 'auto',
                                    borderRadius: '6px',
                                    margin: '16px 0'
                                  }} 
                                />
                              )
                            }}
                          >
                            {msg.content || ''}
                          </ReactMarkdown>
                          
                          {/* Show subtle loading indicator while streaming */}
                          {msg.isStreaming && msg.id === chatState.streamingMessageId && (
                            <span style={{ 
                              display: 'inline-block',
                              width: '8px',
                              height: '16px',
                              backgroundColor: '#1890ff',
                              animation: 'blink 1s infinite',
                              marginLeft: '2px',
                              verticalAlign: 'text-bottom'
                            }} />
                          )}
                        </>
                      )}
                    </div>
                  </div>
                </div>
              </List.Item>
            )}
          />
          <div ref={messagesEndRef} />
        </div>
      </div>
  
      {/* Error Display */}
      {chatState.error && (
        <div style={{ maxWidth: '768px', margin: '0 auto', padding: '0 20px' }}>
          <Alert
            message={chatState.error}
            type="error"
            closable
            onClose={() => setChatState(prev => ({ ...prev, error: null }))}
            style={{ marginBottom: '16px' }}
          />
        </div>
      )}
  
      {/* Input Area */}
      <div style={{ 
        backgroundColor: '#fff',
        borderTop: '1px solid #e5e5e5',
        padding: '16px 0',
        flexShrink: 0
      }}>
        <div style={{ maxWidth: '768px', margin: '0 auto', padding: '0 20px' }}>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end' }}>
            <TextArea
              ref={inputRef}
              value={chatState.currentInput}
              onChange={(e) => setChatState(prev => ({ ...prev, currentInput: e.target.value }))}
              onKeyPress={handleKeyPress}
              placeholder="Ask about pricing strategies, market analysis, or algorithm selection..."
              autoSize={{ minRows: 1, maxRows: 6 }}
              disabled={chatState.isLoading}
              style={{ 
                resize: 'none',
                fontSize: '15px',
                border: '1px solid #d9d9d9',
                borderRadius: '8px',
                padding: '10px 12px'
              }}
            />
            <Button
              type="primary"
              icon={chatState.isLoading ? <LoadingOutlined /> : <SendOutlined />}
              onClick={handleSendMessage}
              disabled={!chatState.currentInput.trim() || chatState.isLoading}
              style={{ 
                height: '40px',
                borderRadius: '8px',
                padding: '0 20px'
              }}
            >
              {chatState.isLoading ? '' : 'Send'}
            </Button>
          </div>
        </div>
      </div>
  
      <style>
        {`
          @keyframes blink {
            0%, 50% { opacity: 1; }
            51%, 100% { opacity: 0; }
          }
          
          /* Custom scrollbar */
          ::-webkit-scrollbar {
            width: 8px;
          }
          
          ::-webkit-scrollbar-track {
            background: transparent;
          }
          
          ::-webkit-scrollbar-thumb {
            background: #d9d9d9;
            border-radius: 4px;
          }
          
          ::-webkit-scrollbar-thumb:hover {
            background: #bfbfbf;
          }
        `}
      </style>
    </div>
  );
};

export default Feature;
