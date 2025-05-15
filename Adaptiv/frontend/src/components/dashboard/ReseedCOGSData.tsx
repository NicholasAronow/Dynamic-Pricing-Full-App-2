import React, { useState } from 'react';
import { Button, Modal, Progress, Typography, message } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import moment from 'moment';
import authService from '../../services/authService';
import api from '../../services/api';

const { Title, Text, Paragraph } = Typography;

// Function to delete all existing COGS data for a user through the API
const clearExistingCOGSData = async (userId: string): Promise<number> => {
  try {
    const response = await api.delete(`cogs?account_id=${userId}`);
    return response.data?.deleted_count || 0;
  } catch (error) {
    console.error('Error deleting COGS data:', error);
    return 0;
  }
};

// Function to submit COGS data for a specific week through the API
const submitCOGSData = async (data: any): Promise<boolean> => {
  try {
    await api.post('cogs', data);
    return true;
  } catch (error) {
    console.error('Error submitting COGS data:', error);
    return false;
  }
};

// Function to generate COGS data for a specific week
const generateCOGSDataForWeek = (userId: string, weekNumber: number) => {
  // If it's the current week (weekNumber = 0), use a more predictable amount for testing
  if (weekNumber === 0) {
    const weekStart = moment().startOf('week');
    const weekEnd = moment().endOf('week');
    
    return {
      user_id: userId,
      week_start_date: weekStart.toISOString(),
      week_end_date: weekEnd.toISOString(),
      amount: 5000, // Reduced to $5,000 for current week (from $20,000)
    };
  }
  
  // For historical weeks
  const weekEnd = moment().subtract(weekNumber, 'weeks').endOf('week');
  const weekStart = moment(weekEnd).startOf('week');
  
  // Base COGS amount - dramatically reduced from $15,000 to $4,000
  let amount = 4000 + Math.random() * 1000;
  
  // Add seasonal variation
  const month = weekEnd.month();
  
  // Higher costs during holiday season (November, December) but still lower than before
  if (month === 10 || month === 11) {
    amount *= 1.25; // 25% increase (reduced from 40%)
  } 
  // Higher costs during summer (June, July, August)
  else if (month >= 5 && month <= 7) {
    amount *= 1.15; // 15% increase (reduced from 20%)
  }
  // Slightly lower in slow months (January, February)
  else if (month === 0 || month === 1) {
    amount *= 0.9; // 10% decrease (same as before)
  }
  
  // Random variation
  amount *= 0.95 + Math.random() * 0.1;
  
  return {
    user_id: userId,
    week_start_date: weekStart.toISOString(),
    week_end_date: weekEnd.toISOString(),
    amount: Math.round(amount),
  };
};

const ReseedCOGSData: React.FC = () => {
  const [visible, setVisible] = useState(false);
  const [reseeding, setReseeding] = useState(false);
  const [progress, setProgress] = useState(0);
  const [log, setLog] = useState<string[]>([]);
  
  const showModal = () => {
    setVisible(true);
    setProgress(0);
    setLog([]);
  };
  
  const handleClose = () => {
    if (!reseeding) {
      setVisible(false);
    }
  };
  
  const reseedCOGSData = async () => {
    setReseeding(true);
    
    try {
      const currentUser = authService.getCurrentUser();
      if (!currentUser) {
        message.error('No user logged in');
        setLog(prev => [...prev, 'Error: No user logged in']);
        return;
      }
      
      const userId = String(currentUser.id);
      
      // Special handling for testprofessional@test.com
      if (!userId.includes('test')) {
        message.error('COGS reseeding is only available for test accounts');
        setLog(prev => [...prev, 'Error: COGS reseeding is only available for test accounts']);
        setReseeding(false);
        return;
      }
      
      setLog(prev => [...prev, `Starting COGS data reseeding for user ${userId}`]);
      
      // Clear existing COGS data
      setLog(prev => [...prev, 'Deleting existing COGS entries from database...']);
      const removedCount = await clearExistingCOGSData(userId);
      setLog(prev => [...prev, `Cleared ${removedCount} existing COGS entries`]);
      
      // Generate and store 55 weeks of data (including current week)
      const totalWeeks = 55;
      let successCount = 0;
      
      for (let i = 0; i < totalWeeks; i++) {
        const weekData = generateCOGSDataForWeek(userId, i);
        
        // Send to API
        const success = await submitCOGSData(weekData);
        if (success) {
          successCount++;
        }
        
        // Update progress
        const newProgress = Math.round(((i + 1) / totalWeeks) * 100);
        setProgress(newProgress);
        
        // Format dates for display
        const startDisplay = moment(weekData.week_start_date).format('YYYY-MM-DD');
        const endDisplay = moment(weekData.week_end_date).format('YYYY-MM-DD');
        
        if (i === 0) {
          setLog(prev => [...prev, `Added current week COGS data (${startDisplay} to ${endDisplay}): $${weekData.amount.toLocaleString()}`]);
        } else if (i === totalWeeks - 1) {
          setLog(prev => [...prev, `Added oldest week COGS data (${startDisplay} to ${endDisplay}): $${weekData.amount.toLocaleString()}`]);
        } else if (i % 10 === 0) {
          setLog(prev => [...prev, `Added week ${i} COGS data (${startDisplay}): $${weekData.amount.toLocaleString()}`]);
        }
        
        // Small delay to allow UI updates
        await new Promise(resolve => setTimeout(resolve, 10));
      }
      
      message.success(`Successfully reseeded ${successCount} of ${totalWeeks} weeks of COGS data for ${userId}`);
      setLog(prev => [...prev, `✅ Reseeding completed successfully (${successCount}/${totalWeeks} weeks)`]);
      
    } catch (error) {
      console.error('Error reseeding COGS data:', error);
      message.error('Failed to reseed COGS data');
      setLog(prev => [...prev, `❌ Error: ${error instanceof Error ? error.message : String(error)}`]);
    } finally {
      setReseeding(false);
    }
  };
  
  return (
    <>
      <Button 
        type="default" 
        icon={<ReloadOutlined />} 
        onClick={showModal}
        style={{ position: 'fixed', right: 24, bottom: 130, zIndex: 1000 }}
      >
        Reseed COGS
      </Button>
      
      <Modal
        title={<Title level={4}>Reseed COGS Data</Title>}
        open={visible}
        onCancel={handleClose}
        footer={[
          <Button key="close" onClick={handleClose} disabled={reseeding}>
            Close
          </Button>,
          <Button 
            key="reseed" 
            type="primary" 
            onClick={reseedCOGSData} 
            loading={reseeding}
            disabled={reseeding}
          >
            Reseed 55 Weeks of COGS Data
          </Button>
        ]}
        width={600}
      >
        <Paragraph>
          This will clear all existing COGS data for the testprofessional@test.com account and 
          generate fresh data for the last 55 weeks, including the current week.
        </Paragraph>
        
        {reseeding && (
          <div style={{ marginBottom: 20 }}>
            <Progress percent={progress} status="active" />
          </div>
        )}
        
        {log.length > 0 && (
          <div 
            style={{ 
              maxHeight: '200px', 
              overflowY: 'auto', 
              padding: '10px', 
              border: '1px solid #d9d9d9', 
              borderRadius: '4px',
              marginTop: '20px', 
              backgroundColor: '#f5f5f5' 
            }}
          >
            {log.map((message, index) => (
              <div key={index} style={{ fontFamily: 'monospace', marginBottom: '4px' }}>
                {message}
              </div>
            ))}
          </div>
        )}
      </Modal>
    </>
  );
};

export default ReseedCOGSData;
