import React, { useState, useEffect } from 'react';
import { Alert, Badge, Button, Card, Col, Empty, Input, Modal, Radio, Row, Select, Space, Spin, Statistic, Steps, Tabs, Tag, Timeline, message } from 'antd';
import { CheckCircleOutlined, CheckOutlined, ClockCircleOutlined, CloseOutlined, DownOutlined, ExperimentOutlined, LineChartOutlined, PlayCircleOutlined, RobotOutlined, SearchOutlined, ThunderboltOutlined, UpOutlined, WarningOutlined } from '@ant-design/icons';
import axios from 'axios';
import { API_BASE_URL } from 'config';
import pricingService, { AgentPricingRecommendation } from '../../services/pricingService';

const { TabPane } = Tabs;
const { Option } = Select;

interface AgentStatus {
  name: string;
  status: 'idle' | 'running' | 'completed' | 'error';
  lastRun?: string;
  icon: React.ReactNode;
}

interface BatchInfo {
  batch_id: string;
  recommendation_date: string;
  count: number;
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

// Modal removed as per requirements

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
  const [availableBatches, setAvailableBatches] = useState<BatchInfo[]>([]);
  const [selectedBatchId, setSelectedBatchId] = useState<string | null>(null);
  const [loadingBatches, setLoadingBatches] = useState<boolean>(false);
  // Feedback modal state removed as per requirements
  const [agentStatuses, setAgentStatuses] = useState<AgentStatus[]>([
    { name: 'Data Collection', status: 'idle', icon: <SearchOutlined /> },
    { name: 'Market Analysis', status: 'idle', icon: <LineChartOutlined /> },
    { name: 'Pricing Strategy', status: 'idle', icon: <ThunderboltOutlined /> },
    { name: 'Performance Monitor', status: 'idle', icon: <CheckCircleOutlined /> },
    { name: 'Experimentation', status: 'idle', icon: <ExperimentOutlined /> }
  ]);

  // Load recommendations and previous analysis results on component mount
  useEffect(() => {
    // Load recommendations from localStorage
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
    
    // Load available batches
    fetchAvailableBatches();
    
    // Load previous analysis results
    fetchLatestAnalysisResults();
  }, []);
  
  // Fetch available recommendation batches
  const fetchAvailableBatches = async () => {
    try {
      setLoadingBatches(true);
      const batchesResponse = await pricingService.getAvailableBatches();
      
      if (batchesResponse && batchesResponse.length > 0) {
        console.log('Available batches:', batchesResponse);
        
        // Type assertion to handle potential shape differences in the API response
        type ApiResponse = {
          batch_id: string;
          recommendation_date: string;
          count?: number;
        }[];
        
        // Ensure all batch objects have the expected properties from the BatchInfo interface
        const validBatches: BatchInfo[] = (batchesResponse as ApiResponse).map(batch => ({
          batch_id: batch.batch_id,
          recommendation_date: batch.recommendation_date,
          count: typeof batch.count === 'number' ? batch.count : 0 // Default to 0 if count is missing
        }));
        
        setAvailableBatches(validBatches);
        
        // Select the most recent batch by default (already sorted by date)
        if (!selectedBatchId && validBatches.length > 0) {
          setSelectedBatchId(validBatches[0].batch_id);
        }
      }
    } catch (error) {
      console.error('Error fetching recommendation batches:', error);
    } finally {
      setLoadingBatches(false);
    }
  };
  
  // State variable for analysis date
  const [analysisDate, setAnalysisDate] = useState<string | null>(null);
  
  // State to track expanded rationale cards
  const [expandedRationales, setExpandedRationales] = useState<{[key: string]: boolean}>({});
  
  // State for recommendation sorting
  const [sortOption, setSortOption] = useState<string>('default');
  
  // Fetch the latest analysis results from the backend
  const fetchLatestAnalysisResults = async () => {
    try {
      console.log('Fetching latest analysis results from API...');
      
      // First, try to get results from the API
      const response = await axios.get(
        `${API_BASE_URL}/api/agents/dynamic-pricing/latest-results`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`
          }
        }
      );
      
      console.log('Latest analysis results response:', response.data);
      
      if (response.data && response.data.results) {
        // Set the results in state
        setResults(response.data.results);
        setAnalysisStatus('completed');
        
        // Store the analysis date from the API response
        if (response.data.analysis_date) {
          setAnalysisDate(response.data.analysis_date);
          console.log('Analysis date from API:', response.data.analysis_date);
        }
        
        // Update agent statuses based on the latest run
        if (response.data.agent_statuses) {
          setAgentStatuses(prev => prev.map(agent => {
            const matchingStatus = response.data.agent_statuses.find((status: any) => 
              status.name === agent.name
            );
            
            if (matchingStatus) {
              return {
                ...agent,
                status: matchingStatus.status || 'completed',
                lastRun: matchingStatus.lastRun || ''
              };
            }
            return {
              ...agent,
              status: 'completed',
              lastRun: ''
            };
          }));
        } else {
          // If no agent statuses in response, mark all as completed
          // Use timestamp from the response instead of current time
          const reportTimestamp = response.data.timestamp || '';
          setAgentStatuses(prev => prev.map(agent => ({
            ...agent,
            status: 'completed',
            lastRun: reportTimestamp
          })));
        }
        
        // Save results to localStorage
        localStorage.setItem('adaptiv_analysis_results', JSON.stringify(response.data.results));
        localStorage.setItem('adaptiv_analysis_timestamp', Date.now().toString());
        
        console.log('Analysis results loaded from API and saved to localStorage');
      } else {
        // If API doesn't return results, try localStorage
        const savedResults = localStorage.getItem('adaptiv_analysis_results');
        const savedTimestamp = localStorage.getItem('adaptiv_analysis_timestamp');
        
        if (savedResults && savedTimestamp) {
          try {
            const results = JSON.parse(savedResults);
            const timestamp = parseInt(savedTimestamp, 10);
            
            // Only use saved results if they're less than 24 hours old
            const isRecent = (Date.now() - timestamp) < 24 * 60 * 60 * 1000;
            
            if (isRecent) {
              setResults(results);
              setAnalysisStatus('completed');
              
              // Mark all agents as completed with the saved timestamp
              setAgentStatuses(prev => prev.map(agent => ({
                ...agent,
                status: 'completed',
                lastRun: new Date(timestamp).toLocaleTimeString()
              })));
              
              console.log('Loaded saved analysis results from localStorage');
            }
          } catch (e) {
            console.error('Error parsing saved analysis results:', e);
          }
        }
      }
    } catch (error) {
      console.error('Error fetching latest analysis results:', error);
      
      // Try to load from localStorage if API fails
      const savedResults = localStorage.getItem('adaptiv_analysis_results');
      const savedTimestamp = localStorage.getItem('adaptiv_analysis_timestamp');
      
      if (savedResults && savedTimestamp) {
        try {
          const results = JSON.parse(savedResults);
          const timestamp = parseInt(savedTimestamp, 10);
          
          // Only use saved results if they're less than 24 hours old
          const isRecent = (Date.now() - timestamp) < 24 * 60 * 60 * 1000;
          
          if (isRecent) {
            setResults(results);
            setAnalysisStatus('completed');
            
            // Mark all agents as completed with the saved timestamp
            setAgentStatuses(prev => prev.map(agent => ({
              ...agent,
              status: 'completed',
              lastRun: new Date(timestamp).toLocaleTimeString()
            })));
            
            console.log('Loaded saved analysis results from localStorage after API failure');
          }
        } catch (e) {
          console.error('Error parsing saved analysis results:', e);
        }
      }
    }
  };

  const fetchAgentRecommendations = async (batchId?: string) => {
    try {
      setLoadingRecommendations(true);
      
      // Fetch recommendations, optionally filtered by batch_id
      const data = await pricingService.getAgentRecommendations(undefined, batchId || selectedBatchId || undefined);
      
      // Debug log the received data
      console.log('Pricing recommendations received:', data);
      if (data && data.length > 0) {
        data.forEach((rec: AgentPricingRecommendation) => {
          console.log(`${rec.item_name}: Current: $${rec.current_price}, Recommended: $${rec.recommended_price}, Change %: ${rec.price_change_percent}, Batch: ${rec.batch_id}`);
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
  
  // Handle batch selection change
  const handleBatchChange = (batchId: string) => {
    setSelectedBatchId(batchId);
    fetchAgentRecommendations(batchId);
  };

  const handleActionClick = async (recommendation: AgentPricingRecommendation, action: 'accept' | 'reject') => {
    try {
      const result = await pricingService.updateRecommendationAction(
        recommendation.id, 
        action, 
        '' // No feedback since we're bypassing the modal
      );
      
      if (result) {
        message.success(`Successfully ${action}ed the price recommendation`);
        
        // If approved, also update the price in Square
        if (action === 'accept') {
          try {
            // Call an API to update the price in Square
            await axios.post(
              `${API_BASE_URL}/api/integrations/square/update-price`,
              {
                item_id: recommendation.item_id,
                new_price: recommendation.recommended_price
              },
              {
                headers: {
                  Authorization: `Bearer ${localStorage.getItem('token')}`
                }
              }
            );
            message.success(`Price updated to $${Number(recommendation.recommended_price).toFixed(2)} in Square`);
          } catch (squareError) {
            console.error('Error updating price in Square:', squareError);
            message.error('Failed to update price in Square');
          }
        }
        
        // Update the local state without making another API call
        const updatedRecommendations = recommendations.map((rec: AgentPricingRecommendation) => {
          if (rec.id === recommendation.id) {
            return {
              ...rec,
              user_action: action,
              user_feedback: ''
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
    }
  };

  // Action confirmation handler removed as per requirements - functionality moved to handleActionClick
  
  // Function to save pricing recommendations to the database
  const saveRecommendationsToDatabase = async (recommendations: any[], batchId: string) => {
    try {
      console.log(`Saving ${recommendations.length} recommendations to database with batch ID: ${batchId}`);
      
      // Format to match our backend schema
      const formattedRecommendations = recommendations.map(rec => {
        // Clean up price strings by removing $ and % symbols
        const currentPrice = typeof rec.current_price === 'string' ? 
          parseFloat(rec.current_price.replace('$', '').trim()) : 
          typeof rec.current_price === 'number' ? 
          rec.current_price : 0;
          
        const suggestedPrice = typeof rec.suggested_price === 'string' ? 
          parseFloat(rec.suggested_price.replace('$', '').trim()) : 
          typeof rec.suggested_price === 'number' ? 
          rec.suggested_price : 0;
        
        // Calculate price change amount if not provided
        const changeAmount = suggestedPrice - currentPrice;
        
        // Parse change percentage
        let changePercent = 0;
        if (rec.change_percentage) {
          const percentStr = rec.change_percentage.toString().replace('%', '').trim();
          changePercent = parseFloat(percentStr);
        } else if (currentPrice > 0) {
          changePercent = (changeAmount / currentPrice) * 100;
        }
        
        // Calculate re-evaluation date
        const daysToReEvaluate = rec.re_evaluation_days ? parseInt(rec.re_evaluation_days.toString()) : 30;
        const reevalDate = new Date(Date.now() + daysToReEvaluate * 24 * 60 * 60 * 1000);
        
        console.log(`Processing item ${rec.item_name}: Current $${currentPrice}, Suggested $${suggestedPrice}, Change ${changePercent}%`);
        
        return {
          item_id: rec.item_id,
          item_name: rec.item_name,
          current_price: currentPrice,
          recommended_price: suggestedPrice,
          price_change_percent: changePercent,
          price_change_amount: changeAmount,
          confidence_score: 0.85, // Default confidence score
          rationale: rec.rationale || '',
          implementation_status: 'pending',
          batch_id: batchId,
          reevaluation_date: reevalDate.toISOString()
        };
      });
      
      // Call our backend API to save recommendations
      const response = await axios.post(
        `${API_BASE_URL}/api/pricing/bulk-recommendations`,
        {
          recommendations: formattedRecommendations
        },
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`
          }
        }
      );
      
      console.log('Recommendations saved to database:', response.data);
      message.success(`${recommendations.length} pricing recommendations saved successfully`);
      return response.data;
    } catch (error: any) {
      console.error('Error saving recommendations to database:', error);
      message.error(`Failed to save recommendations: ${error.message || 'Unknown error'}`);
      return null;
    }
  };
  
  const runFullAnalysis = async () => {
    try {
      setLoading(true);
      setAnalysisStatus('running');
      
      // Update all agents to running
      setAgentStatuses(prev => prev.map(agent => ({ ...agent, status: 'running' })));
      
      // Debug logging
      console.log('Calling API to run aggregate pricing agent...');
      
      // Run the aggregate pricing agent
      const response = await axios.post(
        `${API_BASE_URL}/api/agents/dynamic-pricing/run-agent`,
        {
          agent_name: 'aggregate_pricing',
          action: 'process',
          parameters: {}
        },
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`
          }
        }
      );
      
      // Debug logging
      console.log('Aggregate pricing agent response:', response.data);

      if (response.data && response.data.success) {
        // Process pricing recommendations
        if (response.data.pricing_recommendations && 
            Array.isArray(response.data.pricing_recommendations)) {
          
          console.log('Received pricing recommendations:', response.data.pricing_recommendations);
          
          // Generate a unique batch ID for this set of recommendations
          const batchId = `batch_${Date.now()}`;
          
          // Save recommendations to database
          await saveRecommendationsToDatabase(response.data.pricing_recommendations, batchId);
          
          // Fetch the newly saved recommendations
          await fetchAgentRecommendations(batchId);
          
          // Mark analysis as completed
          setAnalysisStatus('completed');
          setAgentStatuses(prev => prev.map(agent => ({ ...agent, status: 'completed' })));
          message.success('Pricing analysis completed successfully!');
        } else {
          console.error('No valid pricing recommendations returned');
          message.warning('Analysis completed but no pricing recommendations were generated');
          setAnalysisStatus('error');
        }
      } else {
        // Handle error response
        message.warning(`Analysis failed: ${response.data.error || 'unknown error'}`);
        setAnalysisStatus('error');
        setAgentStatuses(prev => prev.map(agent => ({ ...agent, status: 'error' })));
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

  // Helper function to get first sentence of rationale
  const getFirstSentence = (text: string) => {
    const firstSentenceMatch = text.match(/^.*?[.!?](?:\s|$)/i);
    return text.substring(0, 170);
  };
  
  // Toggle rationale expansion
  const toggleRationale = (id: string | number) => {
    const strId = String(id);
    setExpandedRationales(prev => ({
      ...prev,
      [strId]: !prev[strId]
    }));
  };
  
  // Function to sort recommendations based on selected option
  const sortRecommendations = (recommendations: AgentPricingRecommendation[], sortType: string) => {
    const sortedRecs = [...recommendations];
    
    switch (sortType) {
      case 'a-z':
        return sortedRecs.sort((a, b) => a.item_name.localeCompare(b.item_name));
      case 'percent-inc':
        return sortedRecs.sort((a, b) => a.price_change_percent - b.price_change_percent);
      case 'percent-dec':
        return sortedRecs.sort((a, b) => b.price_change_percent - a.price_change_percent);
      case 'date-new':
        return sortedRecs.sort((a, b) => new Date(b.reevaluation_date || '').getTime() - new Date(a.reevaluation_date || '').getTime());
      case 'date-old':
        return sortedRecs.sort((a, b) => new Date(a.reevaluation_date || '').getTime() - new Date(b.reevaluation_date || '').getTime());
      default:
        return sortedRecs;
    }
  };
  
  // Handle sort option change
  const handleSortChange = (option: string) => {
    setSortOption(option);
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
    <div style={{ 
      minHeight: '100vh', 
      padding: '32px'
    }}>
      {/* Modern Header */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        marginBottom: '32px',
        background: 'rgba(255, 255, 255, 0.9)',
        backdropFilter: 'blur(10px)',
        borderRadius: '16px',
        padding: '24px 32px',
        boxShadow: '0 4px 24px rgba(0, 0, 0, 0.06)'
      }}>
        <Space size="large" align="center">
          <div style={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            borderRadius: '12px',
            padding: '12px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <RobotOutlined style={{ fontSize: '32px', color: '#fff' }} />
          </div>
          <div>
            <h1 style={{ 
              fontSize: '28px', 
              margin: 0, 
              fontWeight: '700',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent'
            }}>
              Dynamic Pricing Agent
            </h1>
            <p style={{ margin: 0, color: '#8492a6', fontSize: '14px' }}>
              AI-powered pricing optimization system
            </p>
          </div>
        </Space>
        <Button
          type="primary"
          icon={<PlayCircleOutlined />}
          loading={loading}
          onClick={runFullAnalysis}
          disabled={analysisStatus === 'running'}
          size="large"
          style={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            border: 'none',
            height: '48px',
            paddingLeft: '32px',
            paddingRight: '32px',
            borderRadius: '12px',
            fontWeight: '600',
            boxShadow: '0 4px 12px rgba(102, 126, 234, 0.4)'
          }}
        >
          {analysisStatus === 'running' ? 'Analysis Running...' : 'Run Full Analysis'}
        </Button>
      </div>
      
      {/* Main Content Area */}
      <div style={{ 
        background: 'rgba(255, 255, 255, 0.95)',
        backdropFilter: 'blur(10px)',
        padding: '32px',
        borderRadius: '16px',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.08)'
      }}>
        {/* Report Header */}
        <div style={{ 
          marginBottom: '32px', 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          borderBottom: '1px solid #e8ecf1',
          paddingBottom: '24px'
        }}>
          <div>
            <h2 style={{ 
              margin: 0, 
              fontSize: '24px', 
              fontWeight: '600',
              color: '#1a202c'
            }}>
              Pricing Analysis Report
            </h2>
            <div style={{ 
              color: '#718096', 
              marginTop: '8px',
              fontSize: '14px'
            }}>
              <span style={{ fontWeight: '500' }}>Report Date:</span> {analysisDate ? new Date(analysisDate).toLocaleDateString('en-US', { 
                weekday: 'long', 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
              }) : 'Not available'}
            </div>
          </div>
          {analysisStatus === 'running' && (
            <Badge 
              status="processing" 
              text="Analysis in progress"
              style={{ 
                fontSize: '14px',
                color: '#667eea'
              }}
            />
          )}
        </div>

        {results && (
          <Tabs 
            defaultActiveKey="agent-recommendations"
            style={{
              marginBottom: '24px'
            }}
          >
            <TabPane 
              tab={
                <span style={{ fontSize: '16px', fontWeight: '500' }}>
                  <Badge 
                    count={pendingRecommendations.length} 
                    style={{ 
                      marginRight: '8px',
                      backgroundColor: '#667eea'
                    }} 
                  />
                  Recommendations
                </span>
              } 
              key="agent-recommendations"
            >
              {loadingRecommendations ? (
                <div style={{ textAlign: 'center', padding: '60px' }}>
                  <Spin size="large" />
                  <div style={{ marginTop: '16px', color: '#718096' }}>
                    Loading recommendations...
                  </div>
                </div>
              ) : pendingRecommendations.length > 0 ? (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
                    <div>
                      <span style={{ marginRight: '8px', color: '#4b5563' }}>Batch:</span>
                      <Select
                        placeholder="Select batch"
                        loading={loadingBatches}
                        style={{ width: 300 }}
                        onChange={handleBatchChange}
                        value={selectedBatchId || undefined}
                      >
                        {availableBatches.map(batch => (
                          <Option key={batch.batch_id} value={batch.batch_id}>
                            {batch.batch_id.startsWith('legacy_batch_') 
                              ? `Legacy Batch (${new Date(batch.recommendation_date).toLocaleDateString()})` 
                              : `Batch ${batch.batch_id.substring(0, 8)}... (${new Date(batch.recommendation_date).toLocaleDateString()}) - ${batch.count} items`}
                          </Option>
                        ))}
                      </Select>
                    </div>
                    <div>
                      <span style={{ marginRight: '8px', color: '#4b5563' }}>Sort by:</span>
                      <Radio.Group 
                        value={sortOption} 
                        onChange={(e) => handleSortChange(e.target.value)}
                        size="small"
                        buttonStyle="solid"
                      >
                        <Radio.Button value="default">Default</Radio.Button>
                        <Radio.Button value="a-z">A-Z</Radio.Button>
                        <Radio.Button value="percent-dec">% ↓</Radio.Button>
                        <Radio.Button value="percent-inc">% ↑</Radio.Button>
                        <Radio.Button value="date-new">Newest</Radio.Button>
                        <Radio.Button value="date-old">Oldest</Radio.Button>
                      </Radio.Group>
                    </div>
                  </div>
                  
                  {sortRecommendations(pendingRecommendations, sortOption).map((rec) => (
                    <Card 
                      key={rec.id} 
                      size="small" 
                      style={{ 
                        marginBottom: '20px',
                        borderRadius: '12px',
                        border: '1px solid #e8ecf1',
                        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)',
                        transition: 'all 0.3s ease',
                        cursor: 'default'
                      }}
                      bodyStyle={{ padding: '24px' }}
                      hoverable
                    >
                      <Row gutter={24} align="middle">
                        <Col span={5}>
                          <div>
                            <div style={{ 
                              color: '#718096', 
                              fontSize: '12px', 
                              marginBottom: '4px',
                              textTransform: 'uppercase',
                              letterSpacing: '0.5px'
                            }}>
                              Product
                            </div>
                            <strong style={{ fontSize: '16px', color: '#1a202c' }}>
                              {rec.item_name}
                            </strong>
                          </div>
                        </Col>
                        <Col span={4}>
                          <div>
                            <div style={{ color: '#718096', fontSize: '12px', marginBottom: '4px' }}>
                              Current Price
                            </div>
                            <span style={{ 
                              fontWeight: '600', 
                              fontSize: '18px',
                              color: '#4a5568'
                            }}>
                              ${Number(rec.current_price).toFixed(2)}
                            </span>
                          </div>
                        </Col>
                        <Col span={4}>
                          <div>
                            <div style={{ color: '#718096', fontSize: '12px', marginBottom: '4px' }}>
                              Recommended
                            </div>
                            <span style={{ 
                              fontWeight: '600', 
                              fontSize: '18px',
                              color: '#667eea'
                            }}>
                              ${Number(rec.recommended_price).toFixed(2)}
                            </span>
                          </div>
                        </Col>
                        <Col span={3}>
                          <Tag 
                            color={rec.price_change_amount >= 0 ? '#f0fdf4' : '#fef2f2'}
                            style={{
                              color: rec.price_change_amount >= 0 ? '#15803d' : '#dc2626',
                              border: `1px solid ${rec.price_change_amount >= 0 ? '#86efac' : '#fca5a5'}`,
                              borderRadius: '6px',
                              padding: '4px 12px',
                              fontSize: '14px',
                              fontWeight: '600'
                            }}
                          >
                            {rec.price_change_amount >= 0 ? '+' : ''}
                            {Math.abs(rec.price_change_percent) > 1 ? 
                              rec.price_change_percent.toFixed(1) : 
                              (rec.price_change_percent * 100).toFixed(1)
                            }%
                          </Tag>
                        </Col>
                        <Col span={4}>
                          <div>
                            <div style={{ color: '#718096', fontSize: '12px', marginBottom: '4px' }}>
                              Reevaluation Date
                            </div>
                            <span style={{ 
                              fontWeight: '500', 
                              fontSize: '14px',
                              color: '#4b5563',
                              display: 'flex',
                              alignItems: 'center'
                            }}>
                              <ClockCircleOutlined style={{ marginRight: '4px', color: '#667eea', fontSize: '12px' }} />
                              {rec.reevaluation_date ? 
                                new Date(rec.reevaluation_date).toLocaleDateString('en-US', {
                                  month: 'short',
                                  day: 'numeric',
                                  year: 'numeric'
                                }) : 
                                'Not scheduled'}
                            </span>
                          </div>
                        </Col>
                        <Col span={4}>
                          <Space size={12}>
                            <Button 
                              type="primary" 
                              size="middle" 
                              icon={<CheckOutlined />} 
                              onClick={() => handleActionClick(rec, 'accept')}
                              style={{
                                background: '#10b981',
                                border: 'none',
                                borderRadius: '8px',
                                fontWeight: '500',
                                boxShadow: '0 2px 4px rgba(16, 185, 129, 0.2)'
                              }}
                            >
                              Accept
                            </Button>
                            <Button 
                              size="middle" 
                              icon={<CloseOutlined />} 
                              onClick={() => handleActionClick(rec, 'reject')}
                              style={{
                                borderRadius: '8px',
                                fontWeight: '500',
                                border: '1px solid #e5e7eb'
                              }}
                            >
                              Reject
                            </Button>
                          </Space>
                        </Col>
                      </Row>
                      <div 
                        style={{ 
                          marginTop: '20px',
                          padding: '16px',
                          background: '#f9fafb',
                          borderRadius: '8px',
                          cursor: 'pointer',
                          position: 'relative'
                        }}
                        onClick={() => toggleRationale(rec.id)}
                      >
                        <Button 
                          type="link" 
                          icon={expandedRationales[String(rec.id)] ? <UpOutlined /> : <DownOutlined />}
                          size="small"
                          style={{ 
                            color: '#4b5563', 
                            position: 'absolute',
                            top: '12px',
                            right: '12px'
                          }}
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleRationale(rec.id);
                          }}
                        />
                        <p style={{ margin: '0', color: '#6b7280', lineHeight: '1.6', paddingRight: '30px' }}>
                          {expandedRationales[String(rec.id)] ? rec.rationale : getFirstSentence(rec.rationale) + (rec.rationale.length > getFirstSentence(rec.rationale).length ? '...' : '')}
                        </p>
                      </div>
                    </Card>
                  ))}
                </div>
              ) : (
                <Empty 
                  description="No pending pricing recommendations"
                  style={{ padding: '60px 0' }}
                />
              )}
            </TabPane>
            <TabPane 
              tab={
                <span style={{ fontSize: '16px', fontWeight: '500' }}>
                  <Tag 
                    color="#52c41a"
                    style={{ marginRight: '8px' }}
                  >
                    {completedRecommendations.length}
                  </Tag>
                  Completed
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
                    style={{ 
                      marginBottom: '16px',
                      borderRadius: '12px',
                      border: '1px solid #d9f7be',
                      background: '#f6ffed'
                    }}
                  />
                  
                  <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '16px' }}>
                    <div>
                      <span style={{ marginRight: '8px', borderRadius: '8px',
                                fontWeight: '500',
                                border: '1px solid #e5e7eb'}}>Sort by:</span>
                      <Radio.Group 
                        value={sortOption} 
                        onChange={(e) => handleSortChange(e.target.value)}
                        size="small"
                        buttonStyle="solid"
                      >
                        <Radio.Button value="default">Default</Radio.Button>
                        <Radio.Button value="a-z">A-Z</Radio.Button>
                        <Radio.Button value="percent-dec">% ↓</Radio.Button>
                        <Radio.Button value="percent-inc">% ↑</Radio.Button>
                        <Radio.Button value="date-new">Newest</Radio.Button>
                        <Radio.Button value="date-old">Oldest</Radio.Button>
                      </Radio.Group>
                    </div>
                  </div>
                  
                  {sortRecommendations(completedRecommendations, sortOption).map((rec) => (
                    <Card 
                      key={rec.id} 
                      size="small" 
                      style={{ 
                        marginBottom: '20px',
                        borderRadius: '12px',
                        border: '1px solid #e8ecf1',
                        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)'
                      }}
                      bodyStyle={{ padding: '24px' }}
                    >
                      <Row gutter={24} align="middle">
                        <Col span={5}>
                          <div>
                            <div style={{ color: '#718096', fontSize: '12px', marginBottom: '4px' }}>
                              Product
                            </div>
                            <strong style={{ fontSize: '16px', color: '#1a202c' }}>
                              {rec.item_name}
                            </strong>
                          </div>
                        </Col>
                        <Col span={4}>
                          <div>
                            <div style={{ color: '#718096', fontSize: '12px', marginBottom: '4px' }}>
                              Original
                            </div>
                            <span style={{ fontWeight: '600', fontSize: '18px', color: '#4a5568' }}>
                              ${Number(rec.current_price).toFixed(2)}
                            </span>
                          </div>
                        </Col>
                        <Col span={4}>
                          <div>
                            <div style={{ color: '#718096', fontSize: '12px', marginBottom: '4px' }}>
                              Suggested
                            </div>
                            <span style={{ fontWeight: '600', fontSize: '18px', color: '#667eea' }}>
                              ${Number(rec.recommended_price).toFixed(2)}
                            </span>
                          </div>
                        </Col>
                        <Col span={3}>
                          <Tag 
                            color={rec.price_change_amount >= 0 ? '#f0fdf4' : '#fef2f2'}
                            style={{
                              color: rec.price_change_amount >= 0 ? '#15803d' : '#dc2626',
                              border: `1px solid ${rec.price_change_amount >= 0 ? '#86efac' : '#fca5a5'}`,
                              borderRadius: '6px',
                              padding: '4px 12px',
                              fontSize: '14px',
                              fontWeight: '600'
                            }}
                          >
                            {rec.price_change_amount >= 0 ? '+' : ''}
                            {Math.abs(rec.price_change_percent) > 1 ? 
                              rec.price_change_percent.toFixed(1) : 
                              (rec.price_change_percent * 100).toFixed(1)
                            }%
                          </Tag>
                        </Col>
                        <Col span={4}>
                          <div>
                            <div style={{ color: '#718096', fontSize: '12px', marginBottom: '4px' }}>
                              Reevaluation Date
                            </div>
                            <span style={{ 
                              fontWeight: '500', 
                              fontSize: '14px',
                              color: '#4b5563',
                              display: 'flex',
                              alignItems: 'center'
                            }}>
                              <ClockCircleOutlined style={{ marginRight: '4px', color: '#667eea', fontSize: '12px' }} />
                              {rec.reevaluation_date ? 
                                new Date(rec.reevaluation_date).toLocaleDateString('en-US', {
                                  month: 'short',
                                  day: 'numeric',
                                  year: 'numeric'
                                }) : 
                                'Not scheduled'}
                            </span>
                          </div>
                        </Col>
                        <Col span={4}>
                          {rec.user_action === 'accept' ? (
                            <Tag 
                              color="#f0fdf4" 
                              icon={<CheckOutlined />}
                              style={{
                                color: '#15803d',
                                border: '1px solid #86efac',
                                borderRadius: '6px',
                                padding: '4px 12px',
                                fontSize: '14px'
                              }}
                            >
                              Accepted
                            </Tag>
                          ) : (
                            <Tag 
                              color="#fef2f2" 
                              icon={<CloseOutlined />}
                              style={{
                                color: '#dc2626',
                                border: '1px solid #fca5a5',
                                borderRadius: '6px',
                                padding: '4px 12px',
                                fontSize: '14px'
                              }}
                            >
                              Rejected
                            </Tag>
                          )}
                        </Col>
                      </Row>
                      <div 
                        style={{ 
                          marginTop: '20px',
                          padding: '16px',
                          background: '#f9fafb',
                          borderRadius: '8px',
                          cursor: 'pointer',
                          position: 'relative'
                        }}
                        onClick={() => toggleRationale(rec.id)}
                      >
                        <Button 
                          type="link" 
                          icon={expandedRationales[String(rec.id)] ? <UpOutlined /> : <DownOutlined />}
                          size="small"
                          style={{ 
                            color: '#4b5563', 
                            position: 'absolute',
                            top: '12px',
                            right: '12px'
                          }}
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleRationale(rec.id);
                          }}
                        />
                        <p style={{ margin: '0', color: '#6b7280', lineHeight: '1.6', paddingRight: '30px' }}>
                          {expandedRationales[String(rec.id)] ? rec.rationale : getFirstSentence(rec.rationale) + (rec.rationale.length > getFirstSentence(rec.rationale).length ? '...' : '')}
                        </p>
                      </div>
                      {rec.user_feedback && (
                        <div style={{ 
                          marginTop: '12px',
                          padding: '16px',
                          background: '#eef2ff',
                          borderRadius: '8px',
                          border: '1px solid #e0e7ff'
                        }}>
                          <strong style={{ color: '#4338ca' }}>Your feedback:</strong>
                          <p style={{ margin: '8px 0 0 0', color: '#6366f1' }}>
                            {rec.user_feedback}
                          </p>
                        </div>
                      )}
                    </Card>
                  ))}
                </div>
              ) : (
                <Empty 
                  description="No completed pricing recommendations"
                  style={{ padding: '60px 0' }}
                />
              )}
            </TabPane>
          </Tabs>
        )}

        {!results && analysisStatus === 'idle' && (
          <div style={{ textAlign: 'center', padding: '80px 0' }}>
            <div style={{
              width: '80px',
              height: '80px',
              margin: '0 auto 24px',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              borderRadius: '20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <RobotOutlined style={{ fontSize: '40px', color: '#fff' }} />
            </div>
            <h3 style={{ fontSize: '20px', color: '#1a202c', marginBottom: '12px' }}>
              No Analysis Results Yet
            </h3>
            <p style={{ color: '#718096', fontSize: '16px', marginBottom: '32px' }}>
              Click 'Run Full Analysis' to start the AI pricing optimization
            </p>
            <Button
              type="primary"
              size="large"
              icon={<PlayCircleOutlined />}
              onClick={runFullAnalysis}
              style={{
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                border: 'none',
                height: '48px',
                paddingLeft: '32px',
                paddingRight: '32px',
                borderRadius: '12px',
                fontWeight: '600',
                boxShadow: '0 4px 12px rgba(102, 126, 234, 0.4)'
              }}
            >
              Start Analysis
            </Button>
          </div>
        )}

        {analysisStatus === 'running' && (
          <div style={{ textAlign: 'center', padding: '80px 0' }}>
            <Spin size="large" />
            <h3 style={{ 
              marginTop: '24px', 
              color: '#1a202c',
              fontSize: '20px',
              fontWeight: '600'
            }}>
              AI Agents Analyzing Your Data
            </h3>
            <p style={{ 
              marginTop: '12px',
              color: '#718096',
              fontSize: '16px'
            }}>
              This may take a few moments...
            </p>
          </div>
        )}
      </div>

      {/* Feedback modal removed as per requirements */}
    </div>
  );
}
export default DynamicPricingAgents;
