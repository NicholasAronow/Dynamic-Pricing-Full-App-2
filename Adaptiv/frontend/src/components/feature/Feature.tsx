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
  Tooltip,
  Layout,
  Menu,
  Dropdown,
  Modal
} from 'antd';
import {
  ArrowUpOutlined,
  RobotOutlined,
  UserOutlined,
  BulbOutlined,
  SearchOutlined,
  SettingOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  LoadingOutlined,
  PlusOutlined,
  MessageOutlined,
  DeleteOutlined,
  EditOutlined,
  MoreOutlined,
  RightOutlined,
  LeftOutlined
} from '@ant-design/icons';
import { ReactComponent as AiSparkleIcon } from '../../assets/icons/ai_sparkle.svg';

import langgraphService, {
  MultiAgentResponse,
  ArchitectureInfo,
  MultiAgentRequest
} from '../../services/langgraphService';
import conversationService, {
  Conversation,
  ConversationMessage,
} from '../../services/conversationService';

const { Title, Paragraph, Text } = Typography;
const { TextArea } = Input;
const { Sider, Content } = Layout;

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  agentName?: string;
  isStreaming?: boolean;
  toolsUsed?: { [agent: string]: string[] };
}

interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  currentInput: string;
  error: string | null;
  streamingMessageId?: string;
  activeTools?: { [agent: string]: string[] };
  currentConversationId?: number;
  conversations: Conversation[];
  conversationsLoading: boolean;
  siderCollapsed: boolean;
}

const Feature: React.FC = () => {
  const [chatState, setChatState] = useState<ChatState>({
    messages: [], // Start with empty messages to show welcome screen
    isLoading: false,
    currentInput: '',
    error: null,
    activeTools: {},
    currentConversationId: undefined,
    conversations: [],
    conversationsLoading: false,
    siderCollapsed: false
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
    loadConversations();
  }, []);

  const loadArchitectures = async () => {
    try {
      const architectures = await langgraphService.getArchitectures();
      setArchitectures(architectures);
    } catch (error) {
      console.error('Failed to load architectures:', error);
    }
  };

  const loadConversations = async () => {
    try {
      setChatState(prev => ({ ...prev, conversationsLoading: true }));
      const conversations = await conversationService.getConversations();
      setChatState(prev => ({ 
        ...prev, 
        conversations,
        conversationsLoading: false 
      }));
    } catch (error) {
      console.error('Failed to load conversations:', error);
      setChatState(prev => ({ ...prev, conversationsLoading: false }));
    }
  };

  const createNewConversation = async () => {
    try {
      // Create conversation without title - will be generated after first message
      const conversation = await conversationService.createConversation({});
      setChatState(prev => ({
        ...prev,
        conversations: [conversation, ...prev.conversations],
        currentConversationId: conversation.id,
        messages: []
      }));
      return conversation;
    } catch (error) {
      console.error('Failed to create conversation:', error);
      message.error('Failed to create new conversation');
      return null;
    }
  };

  const loadConversation = async (conversationId: number) => {
    try {
      setChatState(prev => ({ ...prev, isLoading: true }));
      const conversationData = await conversationService.getConversation(conversationId);
      
      // Convert ConversationMessage to ChatMessage format
      const messages: ChatMessage[] = conversationData.messages.map(msg => ({
        id: msg.id.toString(),
        role: msg.role,
        content: msg.content,
        timestamp: new Date(msg.created_at),
        agentName: msg.agent_name || undefined,
        toolsUsed: msg.tools_used ? { [msg.agent_name || 'unknown']: msg.tools_used } : undefined
      }));
      
      setChatState(prev => ({
        ...prev,
        currentConversationId: conversationId,
        messages,
        isLoading: false
      }));
    } catch (error) {
      console.error('Failed to load conversation:', error);
      message.error('Failed to load conversation');
      setChatState(prev => ({ ...prev, isLoading: false }));
    }
  };

  const generateConversationTitle = async (firstMessage: string): Promise<string> => {
    try {
      // Simple LLM call to generate a title
      const response = await fetch('/api/langgraph/generate-title', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ message: firstMessage })
      });
      
      if (response.ok) {
        const data = await response.json();
        return data.title || conversationService.generateConversationTitle(firstMessage);
      }
    } catch (error) {
      console.error('Failed to generate title with LLM:', error);
    }
    
    // Fallback to simple title generation
    return conversationService.generateConversationTitle(firstMessage);
  };

  const deleteConversation = async (conversationId: number) => {
    try {
      await conversationService.deleteConversation(conversationId);
      setChatState(prev => ({
        ...prev,
        conversations: prev.conversations.filter(c => c.id !== conversationId),
        currentConversationId: prev.currentConversationId === conversationId ? undefined : prev.currentConversationId,
        messages: prev.currentConversationId === conversationId ? [] : prev.messages
      }));
      message.success('Conversation deleted');
    } catch (error) {
      console.error('Failed to delete conversation:', error);
      message.error('Failed to delete conversation');
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
  
    // Create or get current conversation
    let conversationId = chatState.currentConversationId;
    let shouldGenerateTitle = false;
    
    console.log('Current conversation ID:', conversationId);
    
    if (!conversationId) {
      console.log('Creating new conversation');
      const newConversation = await createNewConversation();
      if (!newConversation) return;
      conversationId = newConversation.id;
      shouldGenerateTitle = true;
      console.log('Created new conversation:', conversationId, 'shouldGenerateTitle:', shouldGenerateTitle);
    } else {
      // Check if existing conversation has no title
      const currentConversation = chatState.conversations.find(c => c.id === conversationId);
      shouldGenerateTitle = !currentConversation?.title;
      console.log('Existing conversation:', conversationId, 'title:', currentConversation?.title, 'shouldGenerateTitle:', shouldGenerateTitle);
    }
  
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

    // Save user message to database
    try {
      await conversationService.addMessage(conversationId, {
        role: 'user',
        content: userMessage.content
      });
    } catch (error) {
      console.error('Failed to save user message:', error);
    }

    // Focus the input after clearing it
    setTimeout(() => {
      if (inputRef.current) {
        inputRef.current.focus();
      }
    }, 100);
  
    try {
      // Prepare conversation history
      const previousMessages = chatState.messages
      .filter(msg => msg.role === 'user' || msg.role === 'assistant')
      .slice(0, -1)  // Exclude the current assistant message placeholder
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
      let lastAgentName = 'Ada'; // Track the last agent that provided content
  
      // Stream the response
      for await (const chunk of langgraphService.streamTask(request)) {
        switch (chunk.type) {
          case 'agent_start':
            // Track which agent is active
            lastAgentName = chunk.agent === 'pricing_orchestrator' ? 'Ada' : chunk.agent;
            // Clear tools for this agent when it starts
            setChatState(prev => ({
              ...prev,
              activeTools: {
                ...(prev.activeTools || {}),
                [chunk.agent]: []
              }
            }));
            // Show agent thinking in a subtle way
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
          
          case 'message_start':
            // A new message is starting from an agent
            lastAgentName = chunk.agent === 'pricing_orchestrator' ? 'Ada' : chunk.agent;
            break;

          case 'message_chunk':
            // Accumulate all content, regardless of which agent it comes from
            if (chunk.content) {
              currentContent += chunk.content;
              setChatState(prev => ({
                ...prev,
                messages: prev.messages.map(m => 
                  m.id === assistantMessage.id 
                    ? { ...m, content: currentContent, agentName: lastAgentName }
                    : m
                )
              }));
            }
            break;
        
          case 'tool_call':
            // Add tool to active tools list
            setChatState(prev => ({
              ...prev,
              activeTools: {
                ...(prev.activeTools || {}),
                [chunk.agent]: [
                  ...(prev.activeTools?.[chunk.agent] || []),
                  chunk.tool_name
                ].filter((v, i, a) => a.indexOf(v) === i) // Remove duplicates
              }
            }));
            break;
        
          case 'tool_response':
            // Tool completed, keep them to show what was used
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
        
            // Around line 419, when saving the assistant message, update to:

          case 'complete':
            // Use the accumulated content, not just final_result
            const finalContent = currentContent || chunk.final_result || '';
            
            setChatState(prev => ({
              ...prev,
              isLoading: false,
              streamingMessageId: undefined,
              messages: prev.messages.map(m => 
                m.id === assistantMessage.id 
                  ? { 
                      ...m, 
                      content: finalContent,
                      isStreaming: false,
                      toolsUsed: { ...prev.activeTools },
                      agentName: lastAgentName
                    }
                  : m
              ),
              activeTools: {}
            }));
            
            // Save the complete response including tool results
            try {
              const toolsUsed = Object.values(chatState.activeTools || {}).flat();
              if (shouldGenerateTitle) {
                console.log('Generating title for conversation:', conversationId, 'with message:', userMessage.content);
                const title = await generateConversationTitle(userMessage.content);
                console.log('Generated title:', title);
                await conversationService.updateConversation(conversationId!, { title });
                console.log('Updated conversation with title');
                
                setChatState(prev => ({
                  ...prev,
                  conversations: prev.conversations.map(c => 
                    c.id === conversationId ? { ...c, title } : c
                  )
                }));
              }
              if (finalContent && finalContent.trim().length > 0) {
                await conversationService.addMessage(conversationId!, {
                  role: 'assistant',
                  content: finalContent,
                  agent_name: lastAgentName,
                  tools_used: toolsUsed.length > 0 ? toolsUsed : undefined
                });
                
                console.log('Saved assistant message with content:', finalContent);
              }
                
                
              
            } catch (error) {
              console.error('Failed to save assistant message:', error);
            }
              
              setTimeout(() => {
                if (inputRef.current) {
                  inputRef.current.focus();
                }
              }, 100);
              break;
        
          case 'error':
            setChatState(prev => ({
              ...prev,
              isLoading: false,
              error: chunk.message,
              streamingMessageId: undefined,
              activeTools: {},
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

  // Check if this is the initial state (no messages)
  const isInitialState = chatState.messages.length === 0;

  const renderConversationItem = (conversation: Conversation) => {
    const isActive = conversation.id === chatState.currentConversationId;
    const isRecent = conversationService.isRecentConversation(conversation);
    
    return (
      <div
        key={conversation.id}
        className={`conversation-item ${
          isActive ? 'active' : ''
        } ${isRecent ? 'recent' : ''}`}
        onClick={() => loadConversation(conversation.id)}
        style={{
          padding: '12px 16px',
          cursor: 'pointer',
          borderRadius: '8px',
          margin: '4px 0',
          backgroundColor: isActive ? '#e6f7ff' : 'transparent',
          border: isActive ? '1px solid #1890ff' : '1px solid transparent',
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          position: 'relative',
          transform: 'translateX(0)',
        }}
        onMouseEnter={(e) => {
          if (!isActive) {
            e.currentTarget.style.backgroundColor = '#f5f5f5';
            e.currentTarget.style.transform = 'translateX(4px)';
          }
        }}
        onMouseLeave={(e) => {
          if (!isActive) {
            e.currentTarget.style.backgroundColor = 'transparent';
            e.currentTarget.style.transform = 'translateX(0)';
          }
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{
              fontSize: '14px',
              fontWeight: isActive ? 600 : 400,
              color: isActive ? '#1890ff' : '#262626',
              marginBottom: '4px',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap'
            }}>
              {conversation.title || 'Untitled Conversation'}
            </div>
            <div style={{
              fontSize: '12px',
              color: '#8c8c8c',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap'
            }}>
              {conversationService.formatRelativeTime(conversation.updated_at)}
            </div>
          </div>
          <Dropdown
            menu={{
              items: [
                {
                  key: 'delete',
                  label: 'Delete',
                  icon: <DeleteOutlined />,
                  danger: true,
                  onClick: () => {
                    Modal.confirm({
                      title: 'Delete Conversation',
                      content: 'Are you sure you want to delete this conversation?',
                      onOk: () => deleteConversation(conversation.id)
                    });
                  }
                }
              ]
            }}
            trigger={['click']}
            placement="bottomRight"
          >
            <Button
              type="text"
              size="small"
              icon={<MoreOutlined />}
              onClick={(e) => e.stopPropagation()}
              style={{ opacity: 0.6 }}
            />
          </Dropdown>
        </div>
        {/*{isRecent && (
          <div style={{
            position: 'absolute',
            top: '8px',
            right: '32px',
            width: '6px',
            height: '6px',
            backgroundColor: '#52c41a',
            borderRadius: '50%'
          }} />
        )}*/}
      </div>
    );
  };

  const groupedConversations = conversationService.groupConversationsByDate(chatState.conversations);

  return (
    <Layout style={{ height: '90vh', backgroundColor: '#fafafa'}}>
      <Sider
        width={300}
        collapsedWidth={60}
        collapsible
        collapsed={chatState.siderCollapsed}
        onCollapse={(collapsed) => setChatState(prev => ({ ...prev, siderCollapsed: collapsed }))}
        trigger={null}
        style={{
          backgroundColor: '#fafafa',
          borderRight: '1px solid #e0e0e0',
          overflow: 'hidden',
        }}
      >
        <div style={{
          padding: '16px',
          borderBottom: '1px solid #fafafa',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Button
              type="text"
              icon={chatState.siderCollapsed ? <RightOutlined /> : <LeftOutlined />}
              size="small"
              onClick={() => setChatState(prev => ({ ...prev, siderCollapsed: !prev.siderCollapsed }))}
              style={{ 
                padding: '4px',
                minWidth: 'auto',
                height: '24px',
                width: '24px'
              }}
            />
            {!chatState.siderCollapsed && (
              <Title level={4} style={{ margin: 0, fontSize: '16px' }}>
                Conversations
              </Title>
            )}
          </div>
          {!chatState.siderCollapsed && (
            <Button
              type="text"
              size="small"
              onClick={createNewConversation}
              style={{
                borderRadius: '8px',
                background: 'transparent',
                border: '1px solid rgba(24, 144, 255, 0.2)',
                boxShadow: '0 2px 8px rgba(24, 144, 255, 0.15)',
                height: '32px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontWeight: 500,
                transition: 'all 0.2s ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-1px)';
                e.currentTarget.style.boxShadow = '0 4px 12px rgba(24, 144, 255, 0.3)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = '0 2px 8px rgba(24, 144, 255, 0.2)';
              }}
            >
              <AiSparkleIcon style={{
                width: '14px',
                height: '14px',
                fill: 'url(#newButtonGradient)',
                filter: 'drop-shadow(0 0 2px rgba(24, 144, 255, 0.4))'
              }} />
              <svg width="0" height="0" style={{ position: 'absolute' }}>
                <defs>
                  <linearGradient id="newButtonGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#1890ff" />
                    <stop offset="100%" stopColor="#722ed1" />
                  </linearGradient>
                </defs>
              </svg>
              <span style={{
                background: 'linear-gradient(135deg, #1890ff 0%, #722ed1 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text'
              }}>New</span>
            </Button>
          )}
        </div>
        
        <div style={{
          height: 'calc(100% - 73px)',
          overflow: 'auto',
          padding: chatState.siderCollapsed ? '8px 4px' : '8px 16px'
        }}>
          {chatState.siderCollapsed ? (
            // Collapsed view - show only conversation icons
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <Tooltip title="New Conversation" placement="right">
                <Button
                  type="text"
                  onClick={createNewConversation}
                  style={{
                    width: '40px',
                    height: '40px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    borderRadius: '10px',
                    background: 'transparent',
                    border: '1px solid rgba(24, 144, 255, 0.3)',
                    boxShadow: '0 3px 10px rgba(24, 144, 255, 0.2)',
                    transition: 'all 0.2s ease'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'translateY(-2px) scale(1.05)';
                    e.currentTarget.style.boxShadow = '0 6px 16px rgba(24, 144, 255, 0.3)';
                    e.currentTarget.style.borderColor = 'rgba(24, 144, 255, 0.5)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'translateY(0) scale(1)';
                    e.currentTarget.style.boxShadow = '0 3px 10px rgba(24, 144, 255, 0.2)';
                    e.currentTarget.style.borderColor = 'rgba(24, 144, 255, 0.3)';
                  }}
                >
                  <AiSparkleIcon style={{
                    width: '24px',
                    height: '24px',
                    fill: 'url(#collapsedButtonGradient)',
                    filter: 'drop-shadow(0 0 3px rgba(24, 144, 255, 0.5))'
                  }} />
                  <svg width="0" height="0" style={{ position: 'absolute' }}>
                    <defs>
                      <linearGradient id="collapsedButtonGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#1890ff" />
                        <stop offset="100%" stopColor="#722ed1" />
                      </linearGradient>
                    </defs>
                  </svg>
                </Button>
              </Tooltip>
              {chatState.conversations.slice(0, 8).map((conversation) => (
                <Tooltip key={conversation.id} title={conversation.title || 'Untitled Conversation'} placement="right">
                  <div
                    onClick={() => loadConversation(conversation.id)}
                    style={{
                      width: '40px',
                      height: '40px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      borderRadius: '8px',
                      backgroundColor: conversation.id === chatState.currentConversationId ? '#e6f7ff' : '#f5f5f5',
                      border: conversation.id === chatState.currentConversationId ? '2px solid #1890ff' : '2px solid transparent',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease'
                    }}
                  >
                    <MessageOutlined style={{ 
                      color: conversation.id === chatState.currentConversationId ? '#1890ff' : '#666',
                      fontSize: '16px'
                    }} />
                  </div>
                </Tooltip>
              ))}
            </div>
          ) : (
            // Expanded view - show full conversation list
            <>
              {chatState.conversationsLoading ? (
                <div style={{ textAlign: 'center', padding: '20px' }}>
                  <Spin size="small" />
                  <div style={{ marginTop: '8px', fontSize: '12px', color: '#8c8c8c' }}>
                    Loading conversations...
                  </div>
                </div>
              ) : chatState.conversations.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '20px', color: '#8c8c8c' }}>
                  <MessageOutlined style={{ fontSize: '24px', marginBottom: '8px' }} />
                  <div style={{ fontSize: '14px' }}>No conversations yet</div>
                  <div style={{ fontSize: '12px', marginTop: '4px' }}>Start a new conversation to begin</div>
                </div>
              ) : (
                Object.entries(groupedConversations).map(([dateGroup, conversations]) => (
                  <div key={dateGroup} style={{ marginBottom: '16px' }}>
                    <div style={{
                      fontSize: '12px',
                      fontWeight: 600,
                      color: '#8c8c8c',
                      marginBottom: '8px',
                      textTransform: 'uppercase',
                      letterSpacing: '0.5px'
                    }}>
                      {dateGroup}
                    </div>
                    {conversations.map(renderConversationItem)}
                  </div>
                ))
              )}
            </>
          )}
        </div>
      </Sider>
      
      <Content style={{ display: 'flex', flexDirection: 'column' }}>
      {isInitialState ? (
        /* Welcome Screen - Centered */
        <div style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '40px 20px'
        }}>
          <div style={{ textAlign: 'center', marginBottom: '40px' }}>
            <Title level={1} style={{ 
              fontSize: '48px', 
              fontWeight: '700',
              margin: '0 0 16px 0',
              background: 'linear-gradient(135deg, #1890ff 0%, #722ed1 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
              filter: 'drop-shadow(0 0 2px rgba(114, 46, 209, 0.3))'
            }}>
              Ada
            </Title>
            <Text style={{ 
              fontSize: '20px', 
              color: '#666',
              display: 'block',
              maxWidth: '600px',
              lineHeight: '1.5'
            }}>
              Ask Ada about your menu, pricing, competitors, and more!
            </Text>
          </div>
          
          {/* Centered Input Box */}
          <div style={{ 
            width: '100%',
            maxWidth: '600px',
            position: 'relative',
            backgroundColor: '#fff',
            borderRadius: '36px',
            border: '1px solid #e5e5e5',
            boxShadow: '0 4px 20px rgba(0, 0, 0, 0.1)',
            padding: '16px 20px',
            display: 'flex',
            alignItems: 'flex-end',
            gap: '12px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', flex: 1, gap: '8px' }}>
              <div style={{ position: 'relative', flexShrink: 0 }}>
                <svg width="0" height="0">
                  <defs>
                    <linearGradient id="sparkleGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#1890ff" />
                      <stop offset="100%" stopColor="#722ed1" />
                    </linearGradient>
                  </defs>
                </svg>
                <AiSparkleIcon style={{ 
                  width: '24px', 
                  height: '24px', 
                  fill: 'url(#sparkleGradient)', 
                  opacity: 0.7,
                  filter: 'drop-shadow(0 0 2px rgba(114, 46, 209, 0.3))',
                  flexShrink: 0
                }} />
              </div>
              <TextArea
                ref={inputRef}
                value={chatState.currentInput}
                onChange={(e) => setChatState(prev => ({ ...prev, currentInput: e.target.value }))}
                onKeyPress={handleKeyPress}
                placeholder="What would you like to know about your business?"
                autoSize={{ minRows: 1, maxRows: 6 }}
                disabled={chatState.isLoading}
                style={{ 
                  resize: 'none',
                  fontSize: '16px',
                  border: 'none',
                  outline: 'none',
                  boxShadow: 'none',
                  backgroundColor: 'transparent',
                  padding: '8px 0',
                  flex: 1,
                }}
              />
            </div>
            <Button
              type="text"
              icon={chatState.isLoading ? <LoadingOutlined /> : <ArrowUpOutlined style={{ fontSize: '18px' }} />}
              onClick={handleSendMessage}
              disabled={!chatState.currentInput.trim() || chatState.isLoading}
              style={{ 
                width: '40px',
                height: '40px',
                borderRadius: '20px',
                background: chatState.currentInput.trim() && !chatState.isLoading ? 'linear-gradient(135deg, #1890ff 0%, #722ed1 100%)' : '#e5e5e5',
                color: chatState.currentInput.trim() && !chatState.isLoading ? '#fff' : '#999',
                border: 'none',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: 0,
                minWidth: '40px',
                flexShrink: 0
              }}
            />
          </div>
        </div>
      ) : (
        /* Normal Chat Layout */
        <>
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
                  alignItems: 'flex-start',
                  flexDirection: msg.role === 'user' ? 'row-reverse' : 'row'
                 }}>
                  {/* Avatar 
                  <div style={{ flexShrink: 0 }}>
                    {msg.role === 'assistant' ? (
                      <div style={{
                        width: '36px',
                        height: '36px',
                        borderRadius: '50%',
                        background: 'linear-gradient(135deg, #1890ff 0%, #722ed1 100%)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        boxShadow: '0 2px 8px rgba(24, 144, 255, 0.2)'
                      }}>
                        <AiSparkleIcon 
                          style={{ 
                            width: '18px', 
                            height: '18px',
                            fill: 'white'
                          }} 
                        />
                      </div>
                    ) : (
                      <Avatar 
                        icon={<UserOutlined />} 
                        style={{ 
                          backgroundColor: '#f0f0f0',
                          color: '#666'
                        }} 
                      />
                    )}
                  </div>
                  */}

                  {/* Message Content */}
                  <div style={{ 
                    flex: msg.role === 'user' ? 'none' : 1, 
                    minWidth: 0,
                    maxWidth: msg.role === 'user' ? '70%' : '100%',
                    width: msg.role === 'user' ? '70%' : 'auto',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start'
                  }}>
                    <div style={{ 
                      fontWeight: 600, 
                      marginBottom: '4px',
                      color: '#030303',
                      textAlign: msg.role === 'user' ? 'right' : 'left'
                    }}>
                      {msg.role === 'user' ? 'You' : 'Ada'}
                    </div>

                    {((msg.id === chatState.streamingMessageId && Object.keys(chatState.activeTools || {}).length > 0) ||
                      (msg.toolsUsed && Object.keys(msg.toolsUsed).length > 0)) && (
                      <div style={{ marginBottom: '12px' }}>
                        {Object.entries(
                          msg.id === chatState.streamingMessageId 
                            ? (chatState.activeTools || {})
                            : (msg.toolsUsed || {})
                        ).map(([agent, tools]) => {
                          if (!tools || tools.length === 0) return null;
                          
                          const agentDisplay = {
                            'database_agent': { name: '🗄️ Database Specialist', color: '#1890ff' },
                            'web_researcher': { name: '🔍 Market Researcher', color: '#722ed1' },
                            'algorithm_selector': { name: '⚙️ Algorithm Specialist', color: '#fa8c16' },
                            'pricing_orchestrator': { name: '💼 Pricing Expert', color: '#52c41a' }
                          }[agent] || { name: agent, color: '#666' };
                          
                          return (
                            <Card
                              key={agent}
                              size="small"
                              style={{
                                borderColor: '#cacaca',
                                backgroundColor: '#e8e9ea',
                                position: 'relative',
                                overflow: 'hidden',
                                paddingTop: '4px',
                                marginBottom: '8px',
                              }}
                            >
                              <div style={{ fontSize: '13px', position: 'relative' }}>
                                <ul style={{ margin: '0 0 0 0', paddingLeft: '2px', listStyle: 'none' }}>
                                  {tools.map((tool, idx) => (
                                    <li key={idx} style={{ marginBottom: '4px', display: 'flex', alignItems: 'center' }}>
                                      {msg.id === chatState.streamingMessageId ? (
                                        <LoadingOutlined 
                                          style={{ 
                                            marginRight: '8px', 
                                            color: '#000',
                                            fontSize: '18px'
                                          }} 
                                        />
                                      ) : (
                                        <span style={{ 
                                          marginRight: '8px', 
                                          color: '#52c41a',
                                          fontSize: '24px'
                                        }}>•</span>
                                      )}
                                      <Text>{tool.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</Text>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            </Card>
                          );
                        })}
                      </div>
                    )}
                    
                    <div style={{ 
                      color: '#030303',
                      lineHeight: '1.5',
                      fontSize: '15px'
                    }}>
                      {msg.role === 'user' ? (
                        <div style={{ 
                          whiteSpace: 'pre-wrap',
                          backgroundColor: '#e5e5ea',
                          padding: '12px 16px',
                          borderRadius: '18px',
                          display: 'inline-block',
                          maxWidth: '100%',
                          wordWrap: 'break-word'
                        }}>
                          {msg.content}
                        </div>
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
                              ul: ({children}) => <ul style={{margin: '16px 0', paddingLeft: '28px', lineHeight: '1.6'}}>{children}</ul>,
                              ol: ({children}) => <ol style={{margin: '16px 0', paddingLeft: '28px', lineHeight: '1.6'}}>{children}</ol>,
                              li: ({children}) => <li style={{margin: '6px 0', paddingLeft: '4px'}}>{children}</li>,
                              
                              
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
                            {(msg.content || '').replace(/\\n/g, '\n')}
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
            backgroundColor: '#f9f9f9',
            padding: '20px 0 32px 0',
            flexShrink: 0
          }}>
            <div style={{ maxWidth: '768px', margin: '0 auto', padding: '0 20px' }}>
              <div style={{ 
                position: 'relative',
                backgroundColor: '#fff',
                borderRadius: '24px',
                border: '1px solid #e5e5e5',
                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
                padding: '12px 16px',
                display: 'flex',
                alignItems: 'flex-end',
                gap: '8px'
              }}>
                <TextArea
                  ref={inputRef}
                  value={chatState.currentInput}
                  onChange={(e) => setChatState(prev => ({ ...prev, currentInput: e.target.value }))}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask anything"
                  autoSize={{ minRows: 1, maxRows: 6 }}
                  disabled={chatState.isLoading}
                  style={{ 
                    resize: 'none',
                    fontSize: '16px',
                    border: 'none',
                    outline: 'none',
                    boxShadow: 'none',
                    backgroundColor: 'transparent',
                    padding: '4px 0',
                    flex: 1
                  }}
                />
                <Button
                  type="text"
                  icon={chatState.isLoading ? <LoadingOutlined /> : <ArrowUpOutlined style={{ fontSize: '18px' }} />}
                  onClick={handleSendMessage}
                  disabled={!chatState.currentInput.trim() || chatState.isLoading}
                  style={{ 
                    width: '32px',
                    height: '32px',
                    borderRadius: '16px',
                    backgroundColor: chatState.currentInput.trim() && !chatState.isLoading ? '#000' : '#e5e5e5',
                    color: chatState.currentInput.trim() && !chatState.isLoading ? '#fff' : '#999',
                    border: 'none',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: 0,
                    minWidth: '32px',
                    flexShrink: 0
                  }}
                />
              </div>
            </div>
          </div>
        </>
      )}
  
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
      </Content>
    </Layout>
  );
};

export default Feature;
