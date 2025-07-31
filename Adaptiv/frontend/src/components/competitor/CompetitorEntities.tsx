import React, { useState, useEffect } from 'react';
import {
  Typography,
  Card,
  Button,
  Table,
  Tag,
  message,
  Spin,
  Empty,
  Modal,
  Form,
  Input,
  Switch,
  Space,
  Tooltip,
  Popconfirm,
  Statistic,
  Row,
  Col,
  Alert,
  Tabs
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  BarChartOutlined,
  LinkOutlined,
  SyncOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import competitorEntityService, {
  CompetitorEntity,
  CompetitorEntityCreate,
  CompetitorEntityUpdate,
  CompetitorStats,
  CompetitorScrapeRequest,
  CompetitorScrapeResponse,
  CompetitorScrapeStatusResponse
} from '../../services/competitorEntityService';
import moment from 'moment';
import { useAuth } from 'context/AuthContext';

const { Title, Text, Paragraph } = Typography;
const { TabPane } = Tabs;

const CompetitorEntities: React.FC = () => {
  const navigate = useNavigate();
  const [form] = Form.useForm();

  // State management
  const [competitors, setCompetitors] = useState<CompetitorEntity[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [modalVisible, setModalVisible] = useState<boolean>(false);
  const [editingCompetitor, setEditingCompetitor] = useState<CompetitorEntity | null>(null);
  const [statsModalVisible, setStatsModalVisible] = useState<boolean>(false);
  const [selectedCompetitorStats, setSelectedCompetitorStats] = useState<CompetitorStats | null>(null);
  const [statsLoading, setStatsLoading] = useState<boolean>(false);
  const [migrationLoading, setMigrationLoading] = useState<boolean>(false);
  const [scrapingLoading, setScrapingLoading] = useState<boolean>(false);
  const [scrapingModalVisible, setScrapingModalVisible] = useState<boolean>(false);
  const [scrapeForm] = Form.useForm();
  const { user } = useAuth();
  
  // Loading competitors state - for showing loading rows during scraping
  const [loadingCompetitors, setLoadingCompetitors] = useState<Map<string, {
    taskId: string;
    name: string;
    location?: string;
    startTime: number;
  }>>(new Map());

  // Summary statistics
  const [summary, setSummary] = useState({
    total_competitors: 0,
    selected_competitors: 0,
    total_items: 0
  });

  // Load competitor entities
  const loadCompetitors = async () => {
    try {
      setLoading(true);
      const data = await competitorEntityService.getCompetitorEntities({
        include_items: false
      });
      
      // Ensure data is an array
      if (Array.isArray(data)) {
        setCompetitors(data);
        
        // Update summary
        const selectedCount = data.filter(c => c.is_selected).length;
        setSummary(prev => ({
          ...prev,
          total_competitors: data.length,
          selected_competitors: selectedCount
        }));
      } else {
        console.error('Unexpected response format:', data);
        setCompetitors([]);
      }
    } catch (error: any) {
      console.error('Error loading competitors:', error);
      // Check if it's a 404 or other specific error
      if (error.response?.status === 404) { 
        message.error('Competitors endpoint not found');
      } else {
        message.error('Failed to load competitors');
      }
      setCompetitors([]);
    } finally {
      setLoading(false);
    }
  };

  // Load summary statistics
  const loadSummary = async () => {
    try {
      const summaryData = await competitorEntityService.getCompetitorSummary();
      setSummary(summaryData);
    } catch (error) {
      console.error('Error loading summary:', error);
      // Set default values on error
      setSummary({
        total_competitors: 0,
        selected_competitors: 0,
        total_items: 0
      });
    }
  };

  useEffect(() => {
    loadCompetitors();
    loadSummary();
    // Check for any pending scraping tasks on component mount
    checkPendingScrapingTasks();
  }, []);

  // Check for pending scraping tasks from localStorage
  const checkPendingScrapingTasks = () => {
    try {
      const pendingTasks = localStorage.getItem('pendingScrapingTasks');
      if (pendingTasks) {
        const tasks = JSON.parse(pendingTasks);
        const loadingMap = new Map();
        
        Object.entries(tasks).forEach(([taskId, taskData]: [string, any]) => {
          // Check if task is not too old (max 10 minutes)
          const maxAge = 10 * 60 * 1000; // 10 minutes
          if (Date.now() - taskData.startTime < maxAge) {
            loadingMap.set(taskId, taskData);
            // Resume polling for this task
            pollScrapeStatus(taskId, taskData.name, false);
          }
        });
        
        setLoadingCompetitors(loadingMap);
        
        // Clean up old tasks from localStorage
        if (loadingMap.size === 0) {
          localStorage.removeItem('pendingScrapingTasks');
        } else {
          const activeTasks: any = {};
          loadingMap.forEach((value, key) => {
            activeTasks[key] = value;
          });
          localStorage.setItem('pendingScrapingTasks', JSON.stringify(activeTasks));
        }
      }
    } catch (error) {
      console.error('Error checking pending scraping tasks:', error);
      localStorage.removeItem('pendingScrapingTasks');
    }
  };

  // Save pending task to localStorage
  const savePendingTask = (taskId: string, name: string, location?: string) => {
    try {
      const pendingTasks = JSON.parse(localStorage.getItem('pendingScrapingTasks') || '{}');
      pendingTasks[taskId] = {
        taskId,
        name,
        location,
        startTime: Date.now()
      };
      localStorage.setItem('pendingScrapingTasks', JSON.stringify(pendingTasks));
    } catch (error) {
      console.error('Error saving pending task:', error);
    }
  };

  // Remove completed task from localStorage and state
  const removePendingTask = (taskId: string) => {
    try {
      const pendingTasks = JSON.parse(localStorage.getItem('pendingScrapingTasks') || '{}');
      delete pendingTasks[taskId];
      
      if (Object.keys(pendingTasks).length === 0) {
        localStorage.removeItem('pendingScrapingTasks');
      } else {
        localStorage.setItem('pendingScrapingTasks', JSON.stringify(pendingTasks));
      }
      
      // Remove from state
      setLoadingCompetitors(prev => {
        const newMap = new Map(prev);
        newMap.delete(taskId);
        return newMap;
      });
    } catch (error) {
      console.error('Error removing pending task:', error);
    }
  };

  // Manual cleanup function for stuck loading states
  const clearAllLoadingStates = () => {
    try {
      localStorage.removeItem('pendingScrapingTasks');
      setLoadingCompetitors(new Map());
      message.info('Cleared all loading states');
    } catch (error) {
      console.error('Error clearing loading states:', error);
    }
  };

  // Cancel specific scraping task
  const cancelScrapingTask = (taskId: string, restaurantName: string) => {
    try {
      // Remove from localStorage and state
      removePendingTask(taskId);
      
      // Show cancellation message
      message.warning(`Cancelled scraping for ${restaurantName}`);
      
      // Note: We can't actually cancel the backend task, but we stop tracking it
      // The backend task will continue but we won't show it in the UI anymore
    } catch (error) {
      console.error('Error cancelling scraping task:', error);
      message.error('Failed to cancel scraping task');
    }
  };

  // Handle create/update competitor
  const handleSaveCompetitor = async (values: CompetitorEntityCreate | CompetitorEntityUpdate) => {
    try {
      if (editingCompetitor) {
        await competitorEntityService.updateCompetitorEntity(editingCompetitor.id, values as CompetitorEntityUpdate);
        message.success('Competitor updated successfully');
      } else {
        await competitorEntityService.createCompetitorEntity(values as CompetitorEntityCreate);
        message.success('Competitor created successfully');
      }
      
      setModalVisible(false);
      setEditingCompetitor(null);
      form.resetFields();
      loadCompetitors();
      loadSummary();
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to save competitor';
      message.error(errorMessage);
    }
  };

  // Handle delete competitor
  const handleDeleteCompetitor = async (competitorId: number) => {
    try {
      await competitorEntityService.deleteCompetitorEntity(competitorId);
      message.success('Competitor deleted successfully');
      loadCompetitors();
      loadSummary();
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to delete competitor';
      message.error(errorMessage);
    }
  };

  // Handle toggle selection
  const handleToggleSelection = async (competitor: CompetitorEntity) => {
    try {
      await competitorEntityService.toggleCompetitorSelection(
        competitor.id,
        !competitor.is_selected
      );
      
      const action = !competitor.is_selected ? 'selected' : 'unselected';
      message.success(`Competitor ${action} for tracking`);
      loadCompetitors();
      loadSummary();
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to update competitor selection';
      message.error(errorMessage);
    }
  };

  // Handle view stats
  const handleViewStats = async (competitor: CompetitorEntity) => {
    try {
      setStatsLoading(true);
      setStatsModalVisible(true);
      const stats = await competitorEntityService.getCompetitorStats(competitor.id);
      setSelectedCompetitorStats(stats);
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to load competitor statistics';
      message.error(errorMessage);
      setStatsModalVisible(false);
    } finally {
      setStatsLoading(false);
    }
  };

  // Handle competitor scraping with task polling
  const handleScrapeCompetitor = async (values: CompetitorScrapeRequest) => {
    try {
      setScrapingLoading(true);
      
      // Start the scraping task
      const response = await competitorEntityService.scrapeCompetitor(values);
      
      console.log('Scrape task started:', response);
      
      if (response.task_id) {
        // Immediately add loading competitor to the table
        const taskData = {
          taskId: response.task_id,
          name: values.restaurant_name,
          location: values.location,
          startTime: Date.now()
        };
        
        setLoadingCompetitors(prev => new Map(prev.set(response.task_id, taskData)));
        savePendingTask(response.task_id, values.restaurant_name, values.location);
        
        message.success(`Started scraping ${values.restaurant_name}. A loading row has been added to the table.`);
        
        // Close the modal immediately
        setScrapingModalVisible(false);
        scrapeForm.resetFields();
        setScrapingLoading(false);
        
        // Start polling in the background (non-blocking)
        pollScrapeStatus(response.task_id, values.restaurant_name, true).catch(error => {
          console.error('Polling error:', error);
        });
      } else {
        message.error('Failed to start scraping task');
        setScrapingLoading(false);
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to start scraping task';
      message.error(errorMessage);
      setScrapingLoading(false);
    }
  };

  // Poll for scraping task status
  const pollScrapeStatus = async (taskId: string, restaurantName: string, isNewTask: boolean = false) => {
    const maxAttempts = 60; // 5 minutes with 5-second intervals
    let attempts = 0;
    
    const poll = async () => {
      try {
        attempts++;
        const statusResponse = await competitorEntityService.getScrapeStatus(taskId);
        

        
        const status = statusResponse.status?.toLowerCase();
        
        if (status === 'success' && statusResponse.result) {
          // Task completed successfully
          if (statusResponse.result.success) {
            message.success(
              `Successfully scraped ${restaurantName}! Found ${statusResponse.result.items_added} menu items.`
            );
            
            // Remove from pending tasks
            removePendingTask(taskId);
            
            // Refresh the data to show the new competitor
            setTimeout(async () => {
              await loadCompetitors();
              await loadSummary();
            }, 500);
          } else {
            message.error(statusResponse.result.error || `Scraping failed for ${restaurantName}`);
            removePendingTask(taskId);
          }
        } else if (status === 'failure') {
          // Task failed
          message.error(statusResponse.error || `Scraping task failed for ${restaurantName}`);
          removePendingTask(taskId);
        } else if (status === 'pending' || status === 'progress') {
          // Task still running, continue polling
          if (attempts < maxAttempts) {
            setTimeout(poll, 5000); // Poll every 5 seconds
          } else {
            message.warning(`Scraping ${restaurantName} is taking longer than expected. The task will continue in the background.`);
            // Don't remove the pending task - it might still complete
          }
        } else {
          // Unknown status, continue polling for a bit
          if (attempts < maxAttempts) {
            setTimeout(poll, 5000);
          } else {
            message.error(`Scraping task status unknown for ${restaurantName}. Please check back later.`);
            // Don't remove the pending task - it might still be running
          }
        }
      } catch (error: any) {
        console.error('Error polling scrape status:', error);
        if (attempts < maxAttempts) {
          setTimeout(poll, 5000); // Continue polling on error
        } else {
          message.error(`Failed to check scraping status for ${restaurantName}. Please try again later.`);
          // Don't remove the pending task on network errors
        }
      }
    };
    
    // Start polling after a short delay
    setTimeout(poll, isNewTask ? 2000 : 1000);
  };

  // Open modal for scraping new competitor
  const handleCreateCompetitor = () => {
    scrapeForm.resetFields();
    setScrapingModalVisible(true);
  };

  // Open modal for manually creating competitor (legacy)
  const handleManualCreateCompetitor = () => {
    setEditingCompetitor(null);
    form.resetFields();
    setModalVisible(true);
  };

  // Open modal for editing competitor
  const handleEditCompetitor = (competitor: CompetitorEntity) => {
    setEditingCompetitor(competitor);
    form.setFieldsValue({
      name: competitor.name,
      address: competitor.address,
      category: competitor.category,
      website: competitor.website,
      menu_url: competitor.menu_url,
      is_selected: competitor.is_selected
    });
    setModalVisible(true);
  };

  // Create combined data source with loading competitors
  const getCombinedDataSource = () => {
    const loadingRows = Array.from(loadingCompetitors.entries()).map(([taskId, taskData]) => ({
      id: `loading-${taskId}`,
      name: taskData.name,
      address: taskData.location || 'Scraping location...',
      category: 'Scraping data...',
      website: null,
      is_selected: false,
      created_at: new Date().toISOString(),
      updated_at: null,
      isLoading: true,
      taskId: taskId,
      startTime: taskData.startTime
    }));
    
    return [...loadingRows, ...competitors];
  };

  // Table columns
  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      width: 250,
      render: (text: string, record: any) => (
        <div style={{ 
          minWidth: '200px',
          wordWrap: 'break-word',
          wordBreak: 'break-word',
          whiteSpace: 'normal',
          lineHeight: '1.4'
        }}>
          <Space wrap>
            {record.isLoading ? (
              <Space wrap>
                <div 
                  style={{
                    width: '16px',
                    height: '16px',
                    border: '2px solid #f3f3f3',
                    borderTop: '2px solid #1890ff',
                    borderRadius: '50%',
                    animation: 'spin 1s linear infinite',
                    display: 'inline-block',
                    flexShrink: 0
                  }}
                />
                <Text strong style={{ 
                  color: '#1890ff',
                  wordWrap: 'break-word',
                  wordBreak: 'break-word'
                }}>
                  {text}
                </Text>
              </Space>
            ) : (
              <Space wrap>
                <Text strong style={{
                  wordWrap: 'break-word',
                  wordBreak: 'break-word'
                }}>
                  {text}
                </Text>
                {record.is_selected? (
                  <Tag color="green" icon={<CheckCircleOutlined />}>
                  </Tag>
                ) : (
                  <Tag color="red" icon={<CloseCircleOutlined />}>
                  </Tag>
                )}
              </Space>
            )}
          </Space>
        </div>
      ),
    },
    {
      title: 'Website',
      dataIndex: 'website',
      key: 'website',
      render: (website: string, record: any) => {
        if (record.isLoading) {
          return <Text type="secondary" style={{ fontStyle: 'italic' }}>Extracting website...</Text>;
        }
        return website ? (
          <a href={website} target="_blank" rel="noopener noreferrer">
            <LinkOutlined /> {website}
          </a>
        ) : (
          <Text type="secondary">Not provided</Text>
        );
      },
    },
    {
      title: 'Location',
      dataIndex: 'address',
      key: 'address',
      render: (address: string, record: any) => {
        if (record.isLoading) {
          return <Text type="secondary" style={{ fontStyle: 'italic' }}>{address}</Text>;
        }
        return address || (
          <Text type="secondary">No address</Text>
        );
      },
    },
    {
      title: 'Category',
      dataIndex: 'category',
      key: 'category',
      render: (category: string, record: any) => {
        if (record.isLoading) {
          return <Text type="secondary" style={{ fontStyle: 'italic' }}>{category}</Text>;
        }
        return category || (
          <Text type="secondary">No category</Text>
        );
      },
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string, record: any) => {
        if (record.isLoading) {
          const elapsed = Math.floor((Date.now() - record.startTime) / 1000);
          return (
            <Text type="secondary" style={{ fontStyle: 'italic' }}>
              Scraping for {elapsed}s...
            </Text>
          );
        }
        return moment(date).format('MMM DD, YYYY');
      },
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: any) => {
        if (record.isLoading) {
          return (
            <Space>
              <Tooltip title="Cancel scraping">
                <Button
                  type="text"
                  danger
                  icon={<CloseCircleOutlined />}
                  onClick={() => cancelScrapingTask(record.taskId, record.name)}
                  size="small"
                  style={{ 
                    color: '#ff4d4f',
                    fontSize: '12px'
                  }}
                >
                  Cancel
                </Button>
              </Tooltip>
            </Space>
          );
        }
        
        return (
          <Space>
            <Tooltip title="View Statistics">
              <Button
                type="text"
                icon={<BarChartOutlined />}
                onClick={() => handleViewStats(record)}
              />
            </Tooltip>
            
            <Tooltip title="View Items">
              <Button
                type="text"
                icon={<EyeOutlined />}
                onClick={() => navigate(`/competitor/${record.id}`)}
              />
            </Tooltip>
            
            <Tooltip title={record.is_selected ? "Stop Tracking" : "Start Tracking"}>
              <Button
                type="text"
                icon={record.is_selected ? <CloseCircleOutlined /> : <CheckCircleOutlined />}
                onClick={() => handleToggleSelection(record)}
              />
            </Tooltip>
            
            <Tooltip title="Edit">
              <Button
                type="text"
                icon={<EditOutlined />}
                onClick={() => handleEditCompetitor(record)}
              />
            </Tooltip>
            
            <Popconfirm
              title="Are you sure you want to delete this competitor?"
              description="This will also delete all associated competitor items."
              onConfirm={() => handleDeleteCompetitor(record.id)}
              okText="Yes"
              cancelText="No"
            >
              <Tooltip title="Delete">
                <Button
                  type="text"
                  danger
                  icon={<DeleteOutlined />}
                />
              </Tooltip>
            </Popconfirm>
          </Space>
        );
      },
    },
  ];

  return (
    <>
      <style>
        {`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}
      </style>
      <div style={{ 
        padding: '0px 0px',
        background: '#fafbfc',
        minHeight: '100vh'
      }}>
      <div style={{ 
        maxWidth: '100vw', 
        margin: '0 auto' 
      }}>
        {/* Header Section */}
        <div style={{ 
          marginBottom: '48px',
          animation: 'fadeIn 0.5s ease-out'
        }}>
          <Title level={2} style={{
            fontSize: '32px',
            fontWeight: '600',
            color: '#0a0a0a',
            marginBottom: '8px',
            letterSpacing: '-0.02em'
          }}>
            Competitor Management
          </Title>
          <Paragraph style={{
            fontSize: '16px',
            color: '#666',
            margin: 0,
            fontWeight: '400'
          }}>
            Manage your competitor entities and track their pricing data.
          </Paragraph>
        </div>

        {/* Summary Statistics */}
        <Row gutter={24} style={{ marginBottom: '32px' }}>
          <Col span={8}>
            <Card style={{
              border: 'none',
              borderRadius: '12px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
              transition: 'all 0.3s ease',
              cursor: 'pointer',
              background: '#fff',
              height: '100%'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.08)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.04)';
            }}>
              <Statistic
                title={<span style={{ 
                  color: '#8e8e93', 
                  fontSize: '13px',
                  fontWeight: '500',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em'
                }}>Total Competitors</span>}
                value={summary.total_competitors}
                prefix={<BarChartOutlined style={{ 
                  fontSize: '20px',
                  color: '#007AFF'
                }} />}
                valueStyle={{
                  fontSize: '36px',
                  fontWeight: '600',
                  color: '#0a0a0a',
                  letterSpacing: '-0.02em'
                }}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card style={{
              border: 'none',
              borderRadius: '12px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
              transition: 'all 0.3s ease',
              cursor: 'pointer',
              background: '#fff',
              height: '100%'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.08)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.04)';
            }}>
              <Statistic
                title={<span style={{ 
                  color: '#8e8e93', 
                  fontSize: '13px',
                  fontWeight: '500',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em'
                }}>Tracking</span>}
                value={summary.selected_competitors}
                prefix={<CheckCircleOutlined style={{ 
                  fontSize: '20px',
                  color: '#34C759'
                }} />}
                valueStyle={{ 
                  fontSize: '36px',
                  fontWeight: '600',
                  color: '#34C759',
                  letterSpacing: '-0.02em'
                }}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card style={{
              border: 'none',
              borderRadius: '12px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
              transition: 'all 0.3s ease',
              cursor: 'pointer',
              background: '#fff',
              height: '100%'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.08)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.04)';
            }}>
              <Statistic
                title={<span style={{ 
                  color: '#8e8e93', 
                  fontSize: '13px',
                  fontWeight: '500',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em'
                }}>Total Items</span>}
                value={summary.total_items}
                prefix={<EyeOutlined style={{ 
                  fontSize: '20px',
                  color: '#5856D6'
                }} />}
                valueStyle={{
                  fontSize: '36px',
                  fontWeight: '600',
                  color: '#0a0a0a',
                  letterSpacing: '-0.02em'
                }}
              />
            </Card>
          </Col>
        </Row>

        {/* Action Bar */}
        <Card style={{ 
          marginBottom: '32px',
          border: 'none',
          borderRadius: '12px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
          background: '#fff',
          padding: '20px 24px'
        }}>
          <Space size={16}>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreateCompetitor}
              loading={scrapingLoading}
              style={{
                background: '#007AFF',
                border: 'none',
                height: '40px',
                padding: '0 24px',
                borderRadius: '8px',
                fontSize: '15px',
                fontWeight: '500',
                boxShadow: '0 2px 8px rgba(0,122,255,0.2)',
                transition: 'all 0.3s ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = '#0051D5';
                e.currentTarget.style.transform = 'translateY(-1px)';
                e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,122,255,0.3)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = '#007AFF';
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,122,255,0.2)';
              }}
            >
              Scrape Competitor
            </Button>
            
            <Button
              icon={<PlusOutlined />}
              onClick={handleManualCreateCompetitor}
              style={{
                background: '#fff',
                border: '1px solid #e5e5e7',
                height: '40px',
                padding: '0 24px',
                borderRadius: '8px',
                fontSize: '15px',
                fontWeight: '500',
                color: '#0a0a0a',
                transition: 'all 0.3s ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = '#007AFF';
                e.currentTarget.style.color = '#007AFF';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = '#e5e5e7';
                e.currentTarget.style.color = '#0a0a0a';
              }}
            >
              Manual Entry
            </Button>
            
            <Button
              icon={<SyncOutlined />}
              onClick={loadCompetitors}
              loading={loading}
              style={{
                background: '#fff',
                border: '1px solid #e5e5e7',
                height: '40px',
                padding: '0 20px',
                borderRadius: '8px',
                fontSize: '15px',
                fontWeight: '500',
                color: '#0a0a0a',
                transition: 'all 0.3s ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = '#007AFF';
                e.currentTarget.style.color = '#007AFF';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = '#e5e5e7';
                e.currentTarget.style.color = '#0a0a0a';
              }}
            >
              Refresh
            </Button>
          </Space>
        </Card>

        {/* Competitors Table */}
        <Card style={{
          border: 'none',
          borderRadius: '12px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
          background: '#fff',
          overflow: 'hidden'
        }}>
          <Table
            columns={columns}
            dataSource={getCombinedDataSource()}
            rowKey="id"
            loading={loading}
            style={{
              fontSize: '12px',
              background: '#fff',
              borderBottom: '1px solid #e5e5e7',
              color: '#8e8e93',
              fontWeight: '300',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              padding: '16px',
            }}
            locale={{
              emptyText: (
                <Empty
                  description={
                    <span style={{ color: '#8e8e93', fontSize: '15px' }}>
                      No competitors found
                    </span>
                  }
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  style={{ padding: '60px 0' }}
                />
              ),
            }}
          />
        </Card>

        {/* Create/Edit Modal */}
        <Modal
          title={
            <span style={{
              fontSize: '20px',
              fontWeight: '600',
              color: '#0a0a0a'
            }}>
              {editingCompetitor ? 'Edit Competitor' : 'Add New Competitor'}
            </span>
          }
          open={modalVisible}
          onCancel={() => {
            setModalVisible(false);
            setEditingCompetitor(null);
            form.resetFields();
          }}
          footer={null}
          style={{
            top: 80
          }}
          bodyStyle={{
            padding: '32px'
          }}
        >
          <Form
            form={form}
            layout="vertical"
            onFinish={handleSaveCompetitor}
            style={{
              fontSize: '14px',
              fontWeight: '200',
              color: '#0a0a0a'
            }}
          >
            <Form.Item
              name="name"
              label="Competitor Name"
              rules={[
                { required: true, message: 'Please enter competitor name' },
                { min: 2, message: 'Name must be at least 2 characters' }
              ]}
              style={{ marginBottom: '24px' }}
            >
              <Input 
                placeholder="Enter competitor name" 
                style={{
                  height: '40px',
                  borderRadius: '8px',
                  fontSize: '15px',
                  border: '1px solid #e5e5e7',
                  transition: 'all 0.3s ease'
                }}
              />
            </Form.Item>

            <Form.Item
              name="website"
              label="Website"
              rules={[
                { type: 'url', message: 'Please enter a valid URL' }
              ]}
              style={{ marginBottom: '24px' }}
            >
              <Input 
                placeholder="https://competitor-website.com" 
                style={{
                  height: '40px',
                  borderRadius: '8px',
                  fontSize: '15px',
                  border: '1px solid #e5e5e7',
                  transition: 'all 0.3s ease'
                }}
              />
            </Form.Item>

            <Form.Item
              name="address"
              label="Location"
              style={{ marginBottom: '24px' }}
            >
              <Input 
                placeholder="Enter competitor address" 
                style={{
                  height: '40px',
                  borderRadius: '8px',
                  fontSize: '15px',
                  border: '1px solid #e5e5e7',
                  transition: 'all 0.3s ease'
                }}
              />
            </Form.Item>

            <Form.Item
              name="category"
              label="Category"
              style={{ marginBottom: '24px' }}
            >
              <Input 
                placeholder="e.g., restaurant, cafe, fast food" 
                style={{
                  height: '40px',
                  borderRadius: '8px',
                  fontSize: '15px',
                  border: '1px solid #e5e5e7',
                  transition: 'all 0.3s ease'
                }}
              />
            </Form.Item>

            <Form.Item
              name="menu_url"
              label="Menu URL"
              rules={[
                { type: 'url', message: 'Please enter a valid URL' }
              ]}
              style={{ marginBottom: '24px' }}
            >
              <Input 
                placeholder="https://competitor-menu-url.com" 
                style={{
                  height: '40px',
                  borderRadius: '8px',
                  fontSize: '15px',
                  border: '1px solid #e5e5e7',
                  transition: 'all 0.3s ease'
                }}
              />
            </Form.Item>

            <Form.Item
              name="is_selected"
              label="Track this competitor"
              valuePropName="checked"
              style={{ marginBottom: '32px' }}
            >
              <Switch 
                style={{
                  background: '#e5e5e7'
                }}
              />
            </Form.Item>

            <Form.Item style={{ marginBottom: 0 }}>
              <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                <Button
                  onClick={() => {
                    setModalVisible(false);
                    setEditingCompetitor(null);
                    form.resetFields();
                  }}
                  style={{
                    height: '40px',
                    padding: '0 24px',
                    borderRadius: '8px',
                    fontSize: '15px',
                    fontWeight: '500',
                    border: '1px solid #e5e5e7',
                    background: '#fff',
                    color: '#0a0a0a'
                  }}
                >
                  Cancel
                </Button>
                <Button 
                  type="primary" 
                  htmlType="submit"
                  style={{
                    height: '40px',
                    padding: '0 24px',
                    borderRadius: '8px',
                    fontSize: '15px',
                    fontWeight: '500',
                    background: '#007AFF',
                    border: 'none',
                    boxShadow: '0 2px 8px rgba(0,122,255,0.2)'
                  }}
                >
                  {editingCompetitor ? 'Update' : 'Create'}
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Modal>

        {/* Statistics Modal */}
        <Modal
          title={
            <span style={{
              fontSize: '20px',
              fontWeight: '600',
              color: '#0a0a0a'
            }}>
              Competitor Statistics
            </span>
          }
          open={statsModalVisible}
          onCancel={() => {
            setStatsModalVisible(false);
            setSelectedCompetitorStats(null);
          }}
          footer={[
            <Button 
              key="close" 
              onClick={() => setStatsModalVisible(false)}
              style={{
                height: '40px',
                padding: '0 24px',
                borderRadius: '8px',
                fontSize: '15px',
                fontWeight: '500',
                border: '1px solid #e5e5e7',
                background: '#fff',
                color: '#0a0a0a'
              }}
            >
              Close
            </Button>
          ]}
          width={800}
          style={{ top: 80 }}
          bodyStyle={{ padding: '32px' }}
        >
          {statsLoading ? (
            <div style={{ textAlign: 'center', padding: '60px' }}>
              <Spin size="large" />
            </div>
          ) : selectedCompetitorStats ? (
            <div>
              <Title level={4} style={{
                fontSize: '24px',
                fontWeight: '600',
                color: '#0a0a0a',
                marginBottom: '32px'
              }}>
                {selectedCompetitorStats.competitor_name}
              </Title>
              
              <Row gutter={24} style={{ marginBottom: '40px' }}>
                <Col span={8}>
                  <div style={{
                    background: '#fafbfc',
                    padding: '24px',
                    borderRadius: '12px',
                    textAlign: 'center'
                  }}>
                    <Statistic
                      title={<span style={{ 
                        color: '#8e8e93', 
                        fontSize: '13px',
                        fontWeight: '500',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em'
                      }}>Total Items</span>}
                      value={selectedCompetitorStats.total_items}
                      valueStyle={{
                        fontSize: '32px',
                        fontWeight: '600',
                        color: '#0a0a0a'
                      }}
                    />
                  </div>
                </Col>
                <Col span={8}>
                  <div style={{
                    background: '#fafbfc',
                    padding: '24px',
                    borderRadius: '12px',
                    textAlign: 'center'
                  }}>
                    <Statistic
                      title={<span style={{ 
                        color: '#8e8e93', 
                        fontSize: '13px',
                        fontWeight: '500',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em'
                      }}>Average Price</span>}
                      value={selectedCompetitorStats.price_stats.avg_price}
                      precision={2}
                      prefix="$"
                      valueStyle={{
                        fontSize: '32px',
                        fontWeight: '600',
                        color: '#0a0a0a'
                      }}
                    />
                  </div>
                </Col>
                <Col span={8}>
                  <div style={{
                    background: '#fafbfc',
                    padding: '24px',
                    borderRadius: '12px',
                    textAlign: 'center'
                  }}>
                    <Statistic
                      title={<span style={{ 
                        color: '#8e8e93', 
                        fontSize: '13px',
                        fontWeight: '500',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em'
                      }}>Price Range</span>}
                      value={`$${selectedCompetitorStats.price_stats.min_price.toFixed(2)} - $${selectedCompetitorStats.price_stats.max_price.toFixed(2)}`}
                      valueStyle={{
                        fontSize: '20px',
                        fontWeight: '600',
                        color: '#0a0a0a'
                      }}
                    />
                  </div>
                </Col>
              </Row>

              <Title level={5} style={{
                fontSize: '16px',
                fontWeight: '600',
                color: '#0a0a0a',
                marginBottom: '16px',
                textTransform: 'uppercase',
                letterSpacing: '0.05em'
              }}>
                Category Breakdown
              </Title>
              <Table
                dataSource={selectedCompetitorStats.category_breakdown}
                columns={[
                  {
                    title: 'Category',
                    dataIndex: 'category',
                    key: 'category',
                  },
                  {
                    title: 'Items',
                    dataIndex: 'item_count',
                    key: 'item_count',
                  },
                  {
                    title: 'Avg Price',
                    dataIndex: 'avg_price',
                    key: 'avg_price',
                    render: (price: number) => `$${price.toFixed(2)}`,
                  },
                ]}
                pagination={false}
                size="small"
                style={{
                    background: '#fafbfc',
                    borderBottom: '1px solid #e5e5e7',
                    color: '#8e8e93',
                    fontWeight: '600',
                    fontSize: '12px',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em'
                }}
              />
            </div>
          ) : null}
        </Modal>

        {/* Competitor Scraping Modal */}
        <Modal
          title={
            <span style={{
              fontSize: '20px',
              fontWeight: '600',
              color: '#0a0a0a'
            }}>
              Scrape Competitor Menu
            </span>
          }
          open={scrapingModalVisible}
          onCancel={() => {
            setScrapingModalVisible(false);
            scrapeForm.resetFields();
          }}
          footer={null}
          width={600}
          style={{ top: 80 }}
          bodyStyle={{ padding: '32px' }}
        >
          <Alert
            message={
              <span style={{ fontWeight: '600', fontSize: '15px' }}>
                AI-Powered Menu Scraping
              </span>
            }
            description={
              <span style={{ fontSize: '14px', lineHeight: '1.6' }}>
                Enter a restaurant name and location. Our AI will automatically find their website, scrape their menu, and add it to your competitor database.
              </span>
            }
            type="info"
            showIcon
            style={{ 
              marginBottom: '32px',
              borderRadius: '8px',
              border: '1px solid #b3d7ff',
              background: '#f0f8ff'
            }}
          />
          
          <Form
            form={scrapeForm}
            layout="vertical"
            onFinish={handleScrapeCompetitor}
            style={{
              fontSize: '14px',
              fontWeight: '500',
              color: '#0a0a0a'
            }}
          >
            <Form.Item
              name="restaurant_name"
              label="Restaurant Name"
              rules={[
                { required: true, message: 'Please enter restaurant name' },
                { min: 2, message: 'Name must be at least 2 characters' }
              ]}
              style={{ marginBottom: '24px' }}
            >
              <Input 
                placeholder="e.g., McDonald's, Starbucks, Local Bistro"
                disabled={scrapingLoading}
                style={{
                  height: '40px',
                  borderRadius: '8px',
                  fontSize: '15px',
                  border: '1px solid #e5e5e7',
                  transition: 'all 0.3s ease'
                }}
              />
            </Form.Item>

            <Form.Item
              name="location"
              label="Location (Optional)"
              extra={
                <span style={{ fontSize: '13px', color: '#8e8e93' }}>
                  Helps find the correct restaurant if there are multiple locations
                </span>
              }
              style={{ marginBottom: '32px' }}
            >
              <Input 
                placeholder="e.g., New York, NY or 123 Main St, Boston"
                disabled={scrapingLoading}
                style={{
                  height: '40px',
                  borderRadius: '8px',
                  fontSize: '15px',
                  border: '1px solid #e5e5e7',
                  transition: 'all 0.3s ease'
                }}
              />
            </Form.Item>

            <Form.Item style={{ marginBottom: 0 }}>
              <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                <Button
                  onClick={() => {
                    setScrapingModalVisible(false);
                    scrapeForm.resetFields();
                  }}
                  disabled={scrapingLoading}
                  style={{
                    height: '40px',
                    padding: '0 24px',
                    borderRadius: '8px',
                    fontSize: '15px',
                    fontWeight: '500',
                    border: '1px solid #e5e5e7',
                    background: '#fff',
                    color: '#0a0a0a'
                  }}
                >
                  Cancel
                </Button>
                <Button 
                  type="primary" 
                  htmlType="submit"
                  loading={scrapingLoading}
                  icon={<SyncOutlined />}
                  style={{
                    height: '40px',
                    padding: '0 24px',
                    borderRadius: '8px',
                    fontSize: '15px',
                    fontWeight: '500',
                    background: '#007AFF',
                    border: 'none',
                    boxShadow: '0 2px 8px rgba(0,122,255,0.2)'
                  }}
                >
                  {scrapingLoading ? 'Scraping...' : 'Start Scraping'}
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Modal>
      </div>
    </div>
    </>
  );
};

export default CompetitorEntities;
