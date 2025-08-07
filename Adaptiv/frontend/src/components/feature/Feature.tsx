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
  Modal,
  Upload
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
  LeftOutlined,
  CloseCircleOutlined,
  FileTextOutlined,
  UploadOutlined,
  ExclamationCircleOutlined
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
  // Add these new fields
  uploadedFile?: File;
  isProcessingFile?: boolean;
  pendingConfirmation?: {
    message: string;
    action: string;
    data: any;
  };
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
      // Replace the entire switch statement in the streaming loop (lines ~380-430) with:

      let currentContent = '';
      let currentAgentThinking = '';
      let lastAgentName = 'Ada';
      let allAgentsContent: { [agent: string]: string } = {}; // Track content from all agents
      let lastCompleteAgent: string | null = null;
      let allContent = ''; // Track ALL content in order
      let agentContents: { [agent: string]: string } = {};
      let agentOrder: string[] = [];
      // Stream the response
      for await (const chunk of langgraphService.streamTask(request)) {
        switch (chunk.type) {
          case 'agent_start':
            // Track which agent is active
            lastAgentName = chunk.agent === 'pricing_orchestrator' ? 'Ada' : chunk.agent;
            
            // Initialize content tracking for this agent if needed
            if (!agentContents[chunk.agent]) {
              agentContents[chunk.agent] = '';
              agentOrder.push(chunk.agent);
            }
            
            // Clear tools for this agent when it starts
            setChatState(prev => ({
              ...prev,
              activeTools: {
                ...(prev.activeTools || {}),
                [chunk.agent]: []
              }
            }));
            
            // Show agent thinking status
            currentAgentThinking = `${chunk.agent === 'pricing_orchestrator' ? 'Ada' : chunk.agent} is analyzing...`;
            
            // Update message to show current status
            setChatState(prev => ({
              ...prev,
              messages: prev.messages.map(m => 
                m.id === assistantMessage.id 
                  ? { 
                      ...m, 
                      content: allContent || currentAgentThinking, 
                      agentName: lastAgentName 
                    }
                  : m
              )
            }));
            break;
          
          case 'message_start':
            // A new message is starting from an agent
            lastAgentName = chunk.agent === 'pricing_orchestrator' ? 'Ada' : chunk.agent;
            
            // Add a separator if this is not the first agent and we have content
            if (allContent && chunk.agent !== 'pricing_orchestrator' && !allContent.endsWith('\n\n')) {
              allContent += '\n\n---\n\n';
            }
            break;
          
          case 'database_confirmation':
            // Store the pending confirmation
            setChatState(prev => ({
              ...prev,
              pendingConfirmation: {
                message: chunk.message,
                action: chunk.action,
                data: chunk.data
              }
            }));
            
            // Show confirmation dialog
            handleDatabaseConfirmation(chunk.action, chunk.data);
            break;
        
          case 'message_chunk':
            if (chunk.content) {
              // Check if this message is asking for confirmation
              const confirmationPhrases = [
                'confirm this change',
                'proceed with this update',
                'make this change',
                'update the database',
                'add this to your database'
              ];
              
              const lowerContent = chunk.content.toLowerCase();
              const isAskingConfirmation = confirmationPhrases.some(phrase => 
                lowerContent.includes(phrase)
              );
              
              if (isAskingConfirmation && chunk.agent === 'database_agent') {
                // Auto-show confirmation dialog for database changes
                setTimeout(() => {
                  Modal.confirm({
                    title: 'Database Update Requested',
                    content: 'The assistant wants to make changes to your database. Please review the conversation above and confirm if you want to proceed.',
                    okText: 'Proceed with Changes',
                    cancelText: 'Cancel',
                    onOk: () => {
                      const confirmMessage = "Yes, please proceed with the database changes.";
                      setChatState(prev => ({ ...prev, currentInput: confirmMessage }));
                      setTimeout(() => handleSendMessage(), 100);
                    },
                    onCancel: () => {
                      const cancelMessage = "No, don't make any changes.";
                      setChatState(prev => ({ ...prev, currentInput: cancelMessage }));
                      setTimeout(() => handleSendMessage(), 100);
                    }
                  });
                }, 1000); // Small delay to let the message render first
              }
              
              // Accumulate content for the specific agent AND in the combined view
              agentContents[chunk.agent] = (agentContents[chunk.agent] || '') + chunk.content;
              
              // Add to combined content stream
              allContent += chunk.content;
              
              // Update the display with ALL accumulated content
              setChatState(prev => ({
                ...prev,
                messages: prev.messages.map(m => 
                  m.id === assistantMessage.id 
                    ? { 
                        ...m, 
                        content: allContent, 
                        agentName: lastAgentName 
                      }
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
        
          case 'message_complete':
            // Message from an agent is complete
            lastCompleteAgent = chunk.agent;
            
            // Add a visual separator after sub-agent responses (optional)
            if (chunk.agent !== 'pricing_orchestrator' && allContent && !allContent.endsWith('\n\n')) {
              // Add subtle spacing after sub-agent responses
              allContent += '\n\n';
            }
            break;
        
          case 'complete':
            // Don't replace with final_result - keep the accumulated content!
            // The final_result is often just the orchestrator's summary
            
            // Optionally append the final summary if it's different from what we have
            if (chunk.final_result && !allContent.includes(chunk.final_result)) {
              // Only add if it's not already in the content
              if (allContent && !allContent.endsWith(chunk.final_result)) {
                // Check if the final result is substantially different
                const finalResultWords = chunk.final_result.split(' ').slice(0, 10).join(' ');
                if (!allContent.includes(finalResultWords)) {
                  allContent += '\n\n---\n\n**Final Summary:**\n' + chunk.final_result;
                }
              } else if (!allContent) {
                // If we have no content at all, use the final result
                allContent = chunk.final_result;
              }
            }
            
            // Ensure we have some content
            const displayContent = allContent || chunk.final_result || 'No response generated';
            
            setChatState(prev => ({
              ...prev,
              isLoading: false,
              streamingMessageId: undefined,
              messages: prev.messages.map(m => 
                m.id === assistantMessage.id 
                  ? { 
                      ...m, 
                      content: displayContent,
                      isStreaming: false,
                      toolsUsed: { ...prev.activeTools },
                      agentName: 'Ada'  // Always show as Ada for the final response
                    }
                  : m
              ),
              activeTools: {}
            }));
            
            // Save the complete response including all agent content
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
              
              // Save the FULL accumulated content, not just the final_result
              if (displayContent && displayContent.trim().length > 0) {
                await conversationService.addMessage(conversationId!, {
                  role: 'assistant',
                  content: displayContent, // Save all the accumulated content
                  agent_name: 'Ada',
                  tools_used: toolsUsed.length > 0 ? toolsUsed : undefined
                });
                
                console.log('Saved complete assistant message with all agent responses');
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

  const handleFileUpload = async (file: File) => {
    // Set processing state
    setChatState(prev => ({ 
      ...prev, 
      uploadedFile: file, 
      isProcessingFile: true 
    }));
    
    try {
      // Read file content based on type
      let content = '';
      let fileType = file.name.split('.').pop()?.toLowerCase() || 'txt';
      
      if (fileType === 'csv' || fileType === 'txt' || fileType === 'json') {
        content = await file.text();
      } else if (fileType === 'xlsx' || fileType === 'xls') {
        // For Excel files, we'd need to use a library like SheetJS
        message.warning('Excel file detected. Processing as text for now.');
        content = await file.text();
      } else {
        message.error('Unsupported file type. Please upload CSV, JSON, or Excel files.');
        return;
      }
      
      // Create message about the file
      const fileMessage = `I've uploaded a ${fileType} file named "${file.name}". Please process it and tell me what you found. If it contains menu items or competitor data, please help me import it.`;
      
      // Create user message with file indicator
      const userMessage: ChatMessage = {
        id: Date.now().toString(),
        role: 'user',
        content: fileMessage,
        timestamp: new Date()
      };
      
      // Create or get current conversation
      let conversationId = chatState.currentConversationId;
      if (!conversationId) {
        const newConversation = await createNewConversation();
        if (!newConversation) return;
        conversationId = newConversation.id;
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
        isLoading: true,
        error: null,
        streamingMessageId: assistantMessage.id,
        isProcessingFile: false
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
      
      // Prepare request with file content as context
      const request: MultiAgentRequest = {
        task: fileMessage,
        architecture: 'supervisor',
        context: `File content (first 5000 characters):\n\`\`\`${fileType}\n${content.substring(0, 5000)}\n\`\`\`${content.length > 5000 ? '\n... (truncated)' : ''}`,
        previous_messages: chatState.messages
          .filter(msg => msg.role === 'user' || msg.role === 'assistant')
          .slice(-6) // Last 3 exchanges
          .map(msg => ({
            role: msg.role,
            content: msg.content
          }))
      };
      
      // Process through the normal streaming flow
      let currentContent = '';
      let allAgentsContent: { [agent: string]: string } = {};
      let lastAgentName = 'Ada';
      
      for await (const chunk of langgraphService.streamTask(request)) {
        // ... (use the same streaming logic from handleSendMessage)
        // Copy the entire switch statement from handleSendMessage here
        // Just make sure to reference the correct assistantMessage.id
      }
      
    } catch (error: any) {
      console.error('File processing error:', error);
      message.error(`Failed to process file: ${error.message}`);
      setChatState(prev => ({ 
        ...prev, 
        isProcessingFile: false,
        isLoading: false
      }));
    }
  };

  const handleDatabaseConfirmation = (action: string, data: any) => {
    Modal.confirm({
      title: 'Confirm Database Change',
      icon: <ExclamationCircleOutlined />,
      content: (
        <div>
          <p>{action}</p>
          {data && (
            <div style={{ 
              marginTop: '12px', 
              padding: '8px', 
              backgroundColor: '#f5f5f5',
              borderRadius: '4px',
              fontFamily: 'monospace',
              fontSize: '12px'
            }}>
              <pre style={{ margin: 0 }}>{JSON.stringify(data, null, 2)}</pre>
            </div>
          )}
        </div>
      ),
      okText: 'Confirm Change',
      cancelText: 'Cancel',
      onOk: async () => {
        // Send confirmation message
        const confirmMessage = `Confirmed: ${action}`;
        setChatState(prev => ({ 
          ...prev, 
          currentInput: confirmMessage,
          pendingConfirmation: undefined
        }));
        // Trigger send
        await handleSendMessage();
      },
      onCancel: () => {
        // Send cancellation message
        const cancelMessage = "Cancel the database change.";
        setChatState(prev => ({ 
          ...prev, 
          currentInput: cancelMessage,
          pendingConfirmation: undefined
        }));
        // Trigger send
        handleSendMessage();
      }
    });
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
                          
                          // Update the agentDisplay mapping to include database_agent
                          const agentDisplay = {
                            'database_agent': { name: '🗄️ Database Specialist', color: '#1890ff' },
                            'web_researcher': { name: '🔍 Market Researcher', color: '#722ed1' },
                            'algorithm_selector': { name: '⚙️ Algorithm Specialist', color: '#fa8c16' },
                            'pricing_orchestrator': { name: '💼 Ada', color: '#52c41a' }  // Changed to show as Ada
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
                              hr: () => (
                                <div style={{
                                  margin: '20px 0',
                                  padding: '0 20px',
                                  display: 'flex',
                                  alignItems: 'center',
                                  opacity: 0.3
                                }}>
                                  <div style={{
                                    flex: 1,
                                    height: '1px',
                                    background: 'linear-gradient(90deg, transparent, #d9d9d9, transparent)'
                                  }} />
                                </div>
                              ),
                              
                              // Style agent names if they appear in the content
                              strong: ({children}) => {
                                const text = String(children);
                                // Check if this is an agent identifier
                                if (text.includes('Database Specialist:') || 
                                    text.includes('Market Researcher:') || 
                                    text.includes('Algorithm Specialist:') ||
                                    text.includes('Summary:')) {
                                  return (
                                    <strong style={{
                                      display: 'block',
                                      marginTop: '16px',
                                      marginBottom: '8px',
                                      color: '#1890ff',
                                      fontSize: '14px',
                                      fontWeight: 600,
                                      textTransform: 'uppercase',
                                      letterSpacing: '0.5px'
                                    }}>
                                      {children}
                                    </strong>
                                  );
                                }
                                // Regular bold text
                                return <strong style={{fontWeight: '600', color: '#24292f'}}>{children}</strong>;
                              },
                              
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
                              width: '2px',
                              height: '16px',
                              backgroundColor: '#000',
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
          {/* Replace the existing input area div with this enhanced version */}
          <div style={{ 
            backgroundColor: '#f9f9f9',
            padding: '20px 0 32px 0',
            flexShrink: 0
          }}>
            <div style={{ maxWidth: '768px', margin: '0 auto', padding: '0 20px' }}>
              {/* File upload indicator */}
              {chatState.uploadedFile && (
                <div style={{
                  marginBottom: '8px',
                  padding: '8px 12px',
                  backgroundColor: '#e6f7ff',
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <FileTextOutlined style={{ color: '#1890ff' }} />
                    <Text style={{ fontSize: '14px' }}>
                      {chatState.uploadedFile.name}
                    </Text>
                    {chatState.isProcessingFile && (
                      <Spin size="small" />
                    )}
                  </div>
                  <Button
                    type="text"
                    size="small"
                    icon={<CloseCircleOutlined />}
                    onClick={() => setChatState(prev => ({ 
                      ...prev, 
                      uploadedFile: undefined,
                      isProcessingFile: false
                    }))}
                  />
                </div>
              )}
              
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
                {/* File upload button */}
                <Upload
                  beforeUpload={(file) => {
                    // Validate file size (max 10MB)
                    const isLt10M = file.size / 1024 / 1024 < 10;
                    if (!isLt10M) {
                      message.error('File must be smaller than 10MB!');
                      return false;
                    }
                    
                    // Validate file type
                    const validTypes = ['csv', 'json', 'txt', 'xlsx', 'xls'];
                    const fileType = file.name.split('.').pop()?.toLowerCase();
                    if (!fileType || !validTypes.includes(fileType)) {
                      message.error('Please upload CSV, JSON, TXT, or Excel files only!');
                      return false;
                    }
                    
                    handleFileUpload(file);
                    return false; // Prevent default upload
                  }}
                  showUploadList={false}
                  accept=".csv,.json,.txt,.xlsx,.xls"
                  disabled={chatState.isLoading || chatState.isProcessingFile}
                >
                  <Tooltip title="Upload file (CSV, JSON, Excel)">
                    <Button
                      type="text"
                      icon={<UploadOutlined />}
                      disabled={chatState.isLoading || chatState.isProcessingFile}
                      style={{
                        width: '32px',
                        height: '32px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: chatState.isLoading ? '#d9d9d9' : '#595959'
                      }}
                    />
                  </Tooltip>
                </Upload>
                
                <TextArea
                  ref={inputRef}
                  value={chatState.currentInput}
                  onChange={(e) => setChatState(prev => ({ ...prev, currentInput: e.target.value }))}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask anything or upload a file"
                  autoSize={{ minRows: 1, maxRows: 6 }}
                  disabled={chatState.isLoading || chatState.isProcessingFile}
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
                  icon={chatState.isLoading || chatState.isProcessingFile ? 
                    <LoadingOutlined /> : 
                    <ArrowUpOutlined style={{ fontSize: '18px' }} />
                  }
                  onClick={handleSendMessage}
                  disabled={(!chatState.currentInput.trim() && !chatState.uploadedFile) || 
                            chatState.isLoading || 
                            chatState.isProcessingFile}
                  style={{ 
                    width: '32px',
                    height: '32px',
                    borderRadius: '16px',
                    backgroundColor: (chatState.currentInput.trim() || chatState.uploadedFile) && 
                                    !chatState.isLoading && 
                                    !chatState.isProcessingFile ? '#000' : '#e5e5e5',
                    color: (chatState.currentInput.trim() || chatState.uploadedFile) && 
                          !chatState.isLoading && 
                          !chatState.isProcessingFile ? '#fff' : '#999',
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
