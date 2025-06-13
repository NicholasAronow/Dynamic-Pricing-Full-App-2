import React, { useState, useEffect } from 'react';
import { Typography, Card, Button, Table, Space, Tag, message, Spin, Empty, Tooltip, Alert, Modal, Form, Input, Checkbox, List, InputNumber, Tabs, Select } from 'antd';
import { PlusOutlined, DeleteOutlined, EditOutlined, LinkOutlined, QuestionOutlined, SearchOutlined, CloseCircleOutlined, EyeOutlined, FileSearchOutlined, ReloadOutlined, SyncOutlined, BarChartOutlined } from '@ant-design/icons';
import axios from 'axios';
import { api } from '../../services/api';
import { useNavigate } from 'react-router-dom';
import itemService from '../../services/itemService';
import moment from 'moment';

const { Title, Paragraph } = Typography;
const { TabPane } = Tabs;

// TypeScript interface for competitor data
interface Competitor {
  report_id: string;
  name: string;
  category: string;
  address: string;
  distance_km?: number;
  menu_url?: string;
  last_sync?: string;
  menu_items_count?: number;
  menu_items_in_common?: number; // Added for counting common menu items
  selected?: boolean; // For selection in the setup modal
  is_selected?: boolean; // Required by the backend API (duplicate of selected for backend compatibility)
  created_at?: string; // When the competitor was added to the system
  batch?: {
    batch_id: string;
    sync_timestamp: string;
  };
}

// TypeScript interface for business profile data
interface BusinessProfile {
  business_name: string | null;
  industry: string | null;
  street_address: string | null;
  city: string | null;
  state: string | null;
  postal_code: string | null;
  country: string | null;
}

// TypeScript interface for menu item data
interface MenuItem {
  item_name: string;
  category: string;
  description?: string | null;
  price: number | null;
  price_currency: string;
  availability?: string;
  source_confidence?: string;
  source_url?: string;
  batch_id?: string;
  sync_timestamp?: string;
}

// TypeScript interface for menu batch data
interface MenuBatch {
  batch_id: string;
  sync_timestamp: string;
  item_count: number;
}

const Competitors: React.FC = () => {
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [trackingEnabled, setTrackingEnabled] = useState<boolean>(false);
  const [trackingStatusLoading, setTrackingStatusLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<string>('1');
  
  // State variables for competitor comparison tab
  const [selectedCompetitorId, setSelectedCompetitorId] = useState<string | null>(null);
  const [competitorMenuItems, setCompetitorMenuItems] = useState<MenuItem[]>([]);
  const [competitorMenuLoading, setCompetitorMenuLoading] = useState<boolean>(false);
  const [menuBatches, setMenuBatches] = useState<MenuBatch[]>([]);
  const [selectedBatchId, setSelectedBatchId] = useState<string | null>(null);
  const [batchesLoading, setBatchesLoading] = useState<boolean>(false);
  
  // Setup modal related states
  const [setupModalVisible, setSetupModalVisible] = useState<boolean>(false);
  const [searchResults, setSearchResults] = useState<Competitor[]>([]);
  const [searchLoading, setSearchLoading] = useState<boolean>(false);
  const [searchCompleted, setSearchCompleted] = useState<boolean>(false);
  const [businessProfile, setBusinessProfile] = useState<BusinessProfile | null>(null);
  const [businessProfileLoading, setBusinessProfileLoading] = useState<boolean>(false);
  const [businessFormVisible, setBusinessFormVisible] = useState<boolean>(false);
  
  // Setup process step
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [editingCompetitor, setEditingCompetitor] = useState<Competitor | null>(null);
  const [editModalVisible, setEditModalVisible] = useState<boolean>(false);
  const [addModalVisible, setAddModalVisible] = useState<boolean>(false);
  
  // Form references
  const [searchForm] = Form.useForm();
  const [editForm] = Form.useForm();
  const [addForm] = Form.useForm();
  
  // State for processing indicator
  const [processing, setProcessing] = useState<boolean>(false);
  
  // State for menu viewing
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [menuLoading, setMenuLoading] = useState<boolean>(false);
  const [menuVisible, setMenuVisible] = useState<boolean>(false);
  const [selectedCompetitorForMenu, setSelectedCompetitorForMenu] = useState<Competitor | null>(null);
  
  const navigate = useNavigate();

  useEffect(() => {
    checkTrackingStatus();
  }, []);
  
  const checkTrackingStatus = async () => {
    try {
      setTrackingStatusLoading(true);
      const token = localStorage.getItem('token');
      
      if (!token) {
        message.error('Authentication required');
        return;
      }
      
      // Use the configured api service instead of direct axios
      const response = await api.get('competitor-settings/tracking-status');
      
      if (response.data.success) {
        setTrackingEnabled(response.data.competitor_tracking_enabled);
        
        // Only load competitors if tracking is enabled
        if (response.data.competitor_tracking_enabled) {
          loadCompetitors();
        } else {
          setLoading(false);
        }
      }
    } catch (err: any) {
      console.error('Error checking tracking status:', err);
      message.error(err.response?.data?.detail || 'Failed to check tracking status');
      setLoading(false);
    } finally {
      setTrackingStatusLoading(false);
    }
  };

  // Debug function to reset competitor tracking status
  const resetCompetitorTracking = async () => {
    try {
      const token = localStorage.getItem('token');
      
      if (!token) {
        message.error('Authentication required');
        return;
      }

      // First, get all current competitors
      const getResponse = await api.get('gemini-competitors/competitors', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      const allCompetitors = getResponse.data.competitors || [];
      console.log(`Found ${allCompetitors.length} competitors to delete`);
      
      // Delete each competitor one by one
      if (allCompetitors.length > 0) {
        message.loading(`Deleting ${allCompetitors.length} competitors...`, 3);
        
        // Process deletions sequentially to avoid overwhelming the server
        for (const competitor of allCompetitors) {
          if (competitor.report_id) {
            console.log(`Deleting competitor: ${competitor.name} (${competitor.report_id})`);
            try {
              await api.delete(`gemini-competitors/competitors/${competitor.report_id}`);
            } catch (deleteErr) {
              console.error(`Error deleting competitor ${competitor.name}:`, deleteErr);
            }
          }
        }
      }
      
      // Update the user's competitor tracking status to false
      // Use the configured api service instead of direct axios
      const response = await api.put('competitor-settings/tracking-status', { enabled: false });
      
      if (response.data.success) {
        message.success('Competitor tracking reset successfully');
        setTrackingEnabled(false);
        setCompetitors([]);
        // Force reload the page to reset all states
        window.location.reload();
      } else {
        message.error('Failed to reset competitor tracking');
      }
    } catch (err: any) {
      console.error('Error resetting competitor tracking:', err);
      message.error('Failed to reset competitor tracking');
    }
  };

  // Add a helper function to get our menu items
  const fetchOurMenuItems = async () => {
    try {
      // Use the existing itemService which already has the correct endpoint and auth logic
      const items = await itemService.getItems();
      return items;
    } catch (err) {
      console.error('Error fetching our menu items:', err);
      return [];
    }
  };

  // Add a function to fetch competitor menu items
  const fetchCompetitorMenuItems = async (reportId: string) => {
    try {
      const token = localStorage.getItem('token');
      if (!token || !reportId) return [];
      
      // Fix endpoint to use the correct API path that exists in the backend
      // Use the same endpoint as CompetitorDetail.tsx - get-stored-menu/{report_id}
      // Use the configured api service instead of direct axios
      const response = await api.get(`gemini-competitors/get-stored-menu/${reportId}`);
      
      if (response.data.success && response.data.menu_items) {
        return response.data.menu_items;
      }
      return [];
    } catch (err) {
      console.error(`Error fetching menu items for competitor ${reportId}:`, err);
      return [];
    }
  };
  
  // Helper function to normalize text for matching
  const normalizeText = (text: string): string => {
    return text
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, '')
      .replace(/\s+/g, ' ')
      .trim();
  };

  // Function to find common menu items between our menu and competitor menu
  const findCommonMenuItems = (ourItems: any[], competitorItems: any[]) => {
    // Common words to exclude from matching logic
    const commonWords = ['a', 'an', 'the', 'with', 'and', 'or', 'of', 'in', 'on', 'at', 'to', 'for'];
    
    // Helper to extract relevant keywords
    const getKeywords = (text: string): string[] => {
      if (!text) return [];
      return normalizeText(text)
        .split(' ')
        .filter(word => word.length > 2 && !commonWords.includes(word));
    };
    
    // Calculate Levenshtein distance for string similarity
    const calculateStringSimilarity = (str1: string, str2: string): number => {
      // Levenshtein distance implementation
      const track = Array(str2.length + 1).fill(null).map(() => 
        Array(str1.length + 1).fill(null));
      
      for (let i = 0; i <= str1.length; i += 1) {
        track[0][i] = i;
      }
      
      for (let j = 0; j <= str2.length; j += 1) {
        track[j][0] = j;
      }
      
      for (let j = 1; j <= str2.length; j += 1) {
        for (let i = 1; i <= str1.length; i += 1) {
          const indicator = str1[i - 1] === str2[j - 1] ? 0 : 1;
          track[j][i] = Math.min(
            track[j][i - 1] + 1,                  // deletion
            track[j - 1][i] + 1,                  // insertion
            track[j - 1][i - 1] + indicator,      // substitution
          );
        }
      }
      
      const distance = track[str2.length][str1.length];
      const maxLength = Math.max(str1.length, str2.length);
      if (maxLength === 0) return 1; // Both strings are empty, consider them identical
      
      // Return similarity score between 0 and 1, where 1 is perfect match
      return 1 - distance / maxLength;
    };
    
    // Keyword matching function
    const keywordMatch = (keywords1: string[], keywords2: string[]): number => {
      // Count how many keywords from keywords1 appear in keywords2
      const matches = keywords1.filter(kw1 => keywords2.some(kw2 => kw2.includes(kw1) || kw1.includes(kw2)));
      const maxKeywords = Math.max(keywords1.length, keywords2.length);
      if (maxKeywords === 0) return 0;
      
      return matches.length / maxKeywords;
    };
    
    // Find matches based on enhanced similarity algorithm
    let commonItems = 0;
    
    // Process each competitor item
    competitorItems.forEach(compItem => {
      // Skip items without names or with zero price
      if (!compItem.item_name || compItem.price === 0) return;
      
      const normalizedCompName = normalizeText(compItem.item_name);
      const compItemKeywords = getKeywords(compItem.item_name);
      let bestMatchScore = 0;
      
      // Find best match among our items
      ourItems.forEach(ourItem => {
        if (!ourItem.name) return;
        
        const normalizedOurName = normalizeText(ourItem.name);
        const ourItemKeywords = getKeywords(ourItem.name);
        
        // Calculate string similarity using Levenshtein
        const nameSimilarity = calculateStringSimilarity(normalizedOurName, normalizedCompName);
        
        // Calculate keyword match percentage
        const keywordSimilarity = keywordMatch(ourItemKeywords, compItemKeywords);
        
        // Combine scores with different weights (same as detail view)
        const combinedScore = (nameSimilarity * 0.6) + (keywordSimilarity * 0.4);
        
        // Update best match if better
        if (combinedScore > bestMatchScore) {
          bestMatchScore = combinedScore;
        }
      });
      
      // Consider it a match if score exceeds threshold (same as detail view)
      if (bestMatchScore > 0.5) {
        commonItems++;
      }
    });
    
    return commonItems;
  };

  // Load competitors and calculate common menu items
  const loadCompetitors = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
      if (!token) {
        message.error('Authentication required');
        return;
      }
      
      // First, fetch competitors
      const response = await api.get('gemini-competitors/competitors', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.data.success && response.data.competitors) {
        const competitors = response.data.competitors;
        setCompetitors(competitors);
        
        // Try to fetch our own menu items
        try {
          const ourItems = await fetchOurMenuItems();
          
          // If we have our items, then try to calculate common items
          if (ourItems && ourItems.length > 0) {
            // Process each competitor sequentially to avoid overwhelming the server
            for (const competitor of competitors) {
              if (!competitor.report_id) continue;
              
              try {
                // Fetch this competitor's menu items
                const competitorItems = await fetchCompetitorMenuItems(competitor.report_id);
                
                // If we have menu items, calculate common items
                if (competitorItems && competitorItems.length > 0) {
                  const commonCount = findCommonMenuItems(ourItems, competitorItems);
                  
                  // Update the competitor with common items count
                  setCompetitors(prevCompetitors => 
                    prevCompetitors.map(comp => 
                      comp.report_id === competitor.report_id ? 
                      { ...comp, menu_items_in_common: commonCount } : 
                      comp
                    )
                  );
                }
              } catch (innerErr) {
                console.error(`Error processing competitor ${competitor.name}:`, innerErr);
                // Continue with next competitor even if one fails
              }
            }
          } else {
            console.warn('No menu items found for our business');
          }
        } catch (menuErr) {
          console.error('Could not fetch menu items:', menuErr);
          // Still show competitors even if we can't calculate common items
        }
      } else {
        setCompetitors([]);
      }
    } catch (err: any) {
      console.error('Error loading competitors:', err);
      message.error(err.response?.data?.detail || 'Failed to load competitors');
      setCompetitors([]);
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: Competitor) => (
        <Button 
          type="link" 
          onClick={() => navigate(`/competitor/${record.report_id}`)}
          style={{ padding: 0, height: 'auto', fontSize: '14px', fontWeight: 'bold', color: '#333' }}
          icon={<EyeOutlined />}
        >
          {text}
        </Button>
      ),
    },
    {
      title: 'Address',
      dataIndex: 'address',
      key: 'address',
    },
    {
      title: 'Distance',
      dataIndex: 'distance_km',
      key: 'distance',
      render: (distance: number | null) => (
        distance ? `${distance.toFixed(1)} km` : '-'
      ),
    },
    // Menu URL column removed as requested
    {
      title: 'Menu Items in Common',
      dataIndex: 'menu_items_in_common',
      key: 'menu_items_in_common',
      render: (count: number, record: Competitor) => {
        // If we have the count already, display it
        if (typeof count === 'number') {
          return count;
        }
        // Otherwise show a loading or dash indicator
        return record.menu_items_count ? 
          <Tag color="blue">Calculating...</Tag> : 
          '-';
      },
    },
    {
      title: 'Last Updated',
      dataIndex: 'last_sync',
      key: 'last_sync',
      render: (text: string, record: Competitor) => {
        // Check for sync date in multiple possible locations
        let syncDate = null;
        let isCreationDate = false;
        
        if (record.last_sync) {
          syncDate = record.last_sync;
        } else if (record.batch && record.batch.sync_timestamp) {
          syncDate = record.batch.sync_timestamp;
        } else if (record.created_at) {
          // Fallback to competitor creation date, but mark it as such
          syncDate = record.created_at;
          isCreationDate = true;
        }
        
        return syncDate ? (
          <Tooltip title={isCreationDate 
            ? `Competitor added on ${moment(syncDate).format('MMMM D, YYYY h:mm A')} (menu sync date unavailable)`
            : `Menu synced on ${moment(syncDate).format('MMMM D, YYYY h:mm A')}`}>
            {isCreationDate 
              ? <span>{moment(syncDate).format('MMM D, YYYY')} <small>(added date)</small></span>
              : moment(syncDate).format('MMM D, YYYY')}
          </Tooltip>
        ) : (
          <span>Never</span>
        );
      },
    },
    {
      title: '',
      key: 'actions',
      render: (text: string, record: Competitor) => (
        <Space>
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => handleEditCompetitor(record)}
            size="small"
          />
          <Button 
            type="text" 
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDeleteCompetitor(record)}
            size="small"
          />
        </Space>
      ),
    },
  ];

  // Function to fetch business profile and auto-search for competitors
  const fetchBusinessProfile = async () => {
    try {
      setBusinessProfileLoading(true);
      const token = localStorage.getItem('token');
      
      if (!token) {
        message.error('Authentication required');
        return;
      }
      
      // Use the configured api service instead of direct axios calls
      const response = await api.get('competitor-settings/business-profile');
      
      setBusinessProfile(response.data);
      
      // Extract business data for competitor search
      const businessType = response.data.industry || '';
      let location = '';
      
      // Construct location from address fields
      if (response.data.street_address || response.data.city || response.data.state) {
        const addressParts = [
          response.data.street_address,
          response.data.city,
          response.data.state,
          response.data.postal_code,
          response.data.country !== 'USA' ? response.data.country : ''
        ].filter(Boolean); // Remove null/empty values
        
        location = addressParts.join(', ');
      }
      
      // Proceed with search only if we have minimum required data
      if (businessType && location) {
        // Set loading state before searching
        setSearchLoading(true);
        // Auto-search for competitors using the profile data
        searchLocalCompetitors({
          businessType,
          location
        });
      } else {
        // Show form instead if we don't have enough data
        setBusinessFormVisible(true);
        searchForm.setFieldsValue({
          businessType,
          location
        });
        message.warning('Please complete your business profile information to find competitors');
      }
      
    } catch (err: any) {
      console.error('Error fetching business profile:', err);
      message.error(err.response?.data?.detail || 'Failed to fetch business profile');
      setBusinessFormVisible(true);
    } finally {
      setBusinessProfileLoading(false);
    }
  };

  // Function to search for local competitors
  const searchLocalCompetitors = async (values: any) => {
    try {
      setSearchLoading(true);
      setSearchCompleted(false);
      setSearchResults([]);
      
      const token = localStorage.getItem('token');
      
      if (!token) {
        message.error('Authentication required');
        return;
      }
      
      // Search for competitors but don't save them to database yet
      // Use the configured api service instead of direct axios
      const response = await api.post('gemini-competitors/search', { 
        business_type: values.businessType, 
        location: values.location,
        save_to_db: false // Include as part of request body instead of URL parameter
      });
      
      if (response.data.success && response.data.competitors) {
        // Add selected property to each competitor and convert to proper interface
        const formattedResults: Competitor[] = response.data.competitors.map((comp: any) => ({
          report_id: comp.report_id || '',
          name: comp.name,
          category: comp.category,
          address: comp.address,
          distance_km: comp.distance_km,
          selected: true // All competitors are selected by default
        }));
        
        setSearchResults(formattedResults);
        setBusinessFormVisible(false);
        setCurrentStep(1);
        message.success(`Found ${formattedResults.length} potential competitors`);
      } else {
        message.warning('No competitors found');
      }
      
      setSearchCompleted(true);
    } catch (err: any) {
      console.error('Error searching for competitors:', err);
      message.error(err.response?.data?.detail || 'Failed to search for competitors');
    } finally {
      setSearchLoading(false);
    }
  };

  // Function to handle competitor removal/selection
  const handleCompetitorSelectionChange = (competitorIndex: number, checked: boolean) => {
    const updatedResults = [...searchResults];
    updatedResults[competitorIndex].selected = checked;
    setSearchResults(updatedResults);
  };
  
  // Function to remove a competitor
  const removeCompetitor = (competitorIndex: number) => {
    const updatedResults = [...searchResults];
    updatedResults[competitorIndex].selected = false;
    setSearchResults(updatedResults);
    message.success('Competitor removed from tracking');
  };

  // Function to edit a competitor
  const openEditModal = (competitor: Competitor) => {
    setEditingCompetitor(competitor);
    editForm.setFieldsValue({
      name: competitor.name,
      category: competitor.category,
      address: competitor.address,
      menu_url: competitor.menu_url || ''
    });
    setEditModalVisible(true);
  };

  // Function to save edited competitor
  const handleSaveCompetitor = async (values: any) => {
    if (!editingCompetitor) return;
    
    try {
      const token = localStorage.getItem('token');
      
      if (!token) {
        message.error('Authentication required');
        return;
      }
      
      // Check if this is a new competitor (manually added)
      if (!editingCompetitor.report_id) {
        // Generate a temporary ID for the new competitor
        const newId = `manual-${Date.now()}`;
        const newCompetitor = { 
          ...values, 
          report_id: newId,
          selected: true // Manually added competitors are selected by default
        };
        
        // Add the new competitor to the search results
        setSearchResults([...searchResults, newCompetitor]);
        message.success('Competitor added successfully');
      } else {
        // Update the existing competitor in the search results
        const updatedResults = searchResults.map(comp => 
          comp.report_id === editingCompetitor.report_id 
            ? { ...comp, ...values }
            : comp
        );
        
        setSearchResults(updatedResults);
        message.success('Competitor updated successfully');
        
        // If we have a report_id that's not manually generated, update it on the server
        if (!editingCompetitor.report_id.startsWith('manual-')) {
          // Use the configured api service instead of direct axios
          await api.put(
            `gemini-competitors/${editingCompetitor.report_id}`, 
            values
          );
        }
      }
    } catch (err: any) {
      console.error('Error updating competitor:', err);
      message.error(err.response?.data?.detail || 'Failed to update competitor');
    }
    
    setEditModalVisible(false);
  };

  // Function to complete the setup process
  const completeSetup = async () => {
    try {
      const token = localStorage.getItem('token');
      
      if (!token) {
        message.error('Authentication required');
        return;
      }
      
      // Filter to get ONLY the selected competitors - unselected competitors will NOT be saved
      const selectedCompetitors = searchResults.filter(comp => comp.selected);
      const unselectedCompetitors = searchResults.filter(comp => !comp.selected);
      
      // Log to verify we're only saving selected competitors
      console.log(`Saving only ${selectedCompetitors.length} selected competitors. Skipping ${unselectedCompetitors.length} unselected competitors.`);
      console.log('Selected competitors:', selectedCompetitors.map(comp => comp.name));
      
      if (selectedCompetitors.length === 0) {
        message.warning('Please select at least one competitor to track');
        return;
      }
      
      // Set processing state to show loading
      setProcessing(true);
      message.loading('Saving your selected competitors...', 2);
      
      // Update the user's competitor tracking status
      // Use the configured api service instead of direct axios
      const statusResponse = await api.put('competitor-settings/tracking-status', { enabled: true });
      
      // Group the selected competitors by type (search results vs manually added)
      const manualCompetitors = selectedCompetitors.filter(comp => comp.report_id?.toString().startsWith('manual-'));
      const searchCompetitors = selectedCompetitors.filter(comp => !comp.report_id || !comp.report_id.toString().startsWith('manual-'));
      
      console.log(`Saving ${selectedCompetitors.length} selected competitors:`);
      console.log(` - ${searchCompetitors.length} from search results`);
      console.log(` - ${manualCompetitors.length} manually added`);
      console.log(`Competitor names: ${selectedCompetitors.map(c => c.name).join(', ')}`);
      
      // STEP 1: Save competitors with report_ids using the new bulk-select endpoint
      const existingCompetitorIds = searchResults
        .filter(comp => comp.report_id && !comp.report_id.toString().startsWith('manual-'))
        .map(comp => comp.report_id);
      
      if (existingCompetitorIds.length > 0) {
        try {
          // Separate into selected and unselected IDs
          const selectedIds = selectedCompetitors
            .filter(comp => comp.report_id && !comp.report_id.toString().startsWith('manual-'))
            .map(comp => comp.report_id);
            
          const unselectedIds = unselectedCompetitors
            .filter(comp => comp.report_id && !comp.report_id.toString().startsWith('manual-'))
            .map(comp => comp.report_id);
          
          // Use the bulk-select endpoint to efficiently mark which competitors should be selected/tracked
          if (selectedIds.length > 0 || unselectedIds.length > 0) {
            await api.post('gemini-competitors/bulk-select',
              {
                selected_ids: selectedIds,
                unselected_ids: unselectedIds
              },
              {
                headers: {
                  'Authorization': `Bearer ${token}`
                }
              }
            );
            console.log(`Successfully updated selection status for ${selectedIds.length} selected and ${unselectedIds.length} unselected competitors`);
          }
        } catch (err: any) {
          console.error('Error updating competitor selection status:', err);
          message.error('Failed to update competitor selection status: ' + (err?.message || ''));
        }
      }
      
      // STEP 2: Save new search-based competitors that don't have report_ids yet
      const newSearchCompetitors = searchCompetitors.filter(comp => !comp.report_id || comp.report_id.toString().startsWith('manual-'));
      if (newSearchCompetitors.length > 0) {
        try {
          const savePromises = newSearchCompetitors.map(competitor => {
            return api.post('gemini-competitors/manually-add',
              {
                ...competitor,
                selected: true, // Ensure they're saved as selected
                is_selected: true // CRITICAL: This is the flag the backend uses
              }
            ).catch(err => {
              console.error(`Error adding competitor ${competitor.name}:`, err);
              return null;
            });
          });
          
          await Promise.all(savePromises);
          console.log(`Successfully saved ${newSearchCompetitors.length} new competitors`);
        } catch (err: any) {
          console.error('Error saving new competitors:', err);
          message.error('Failed to save some new competitors: ' + (err?.message || ''));
        }
      }
      
      // STEP 3: Save manually added competitors (ones with manual- prefixed IDs)
      // Using the manualCompetitors variable already defined above
      if (manualCompetitors.length > 0) {
        try {
          // For manually added competitors, we need to use the manual-add endpoint
          const manualPromises = manualCompetitors.map(competitor => {
            return api.post('gemini-competitors/manually-add',
              {
                ...competitor,
                selected: true, // Ensure they're saved as selected
                is_selected: true // CRITICAL: This is the flag the backend uses
              }
            ).catch(err => {
              console.error(`Error saving manually added competitor ${competitor.name}:`, err);
              return null; // Return null so Promise.all continues even if one fails
            });
          });
          
          // Wait for all manual competitors to be saved
          await Promise.all(manualPromises);
          console.log(`Successfully saved ${manualCompetitors.length} manually added competitors`);
        } catch (err: any) {
          console.error('Error saving manually added competitors:', err);
          message.error('Failed to save some manually added competitors: ' + (err?.message || ''));
        }
      }
            
      if (statusResponse.data.success) {
        setSetupModalVisible(false);
        message.success('Competitor tracking setup complete!', 2);
        
        try {
          // Explicit debugging to verify our token and authorization
          console.log('Token available for API calls:', !!token);
          if (!token) {
            message.error('Authentication token is missing. Please log in again.');
            return;
          }
          
          // First force a refresh to get the latest competitor data with proper report_ids
          console.log('Refreshing competitor data to ensure we have the latest report_ids...');
          const refreshResponse = await api.get('gemini-competitors/competitors', {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          
          const freshCompetitors = refreshResponse.data.competitors || [];
          console.log('Successfully retrieved fresh competitor data:', 
            freshCompetitors.map((c: any) => `${c.name} (${c.report_id})`).join(', '));
            
          // DEBUG: Examine the complete competitor objects 
          console.log('DETAILED DEBUG - All competitor data:', JSON.stringify(freshCompetitors, null, 2));
          console.log('DETAILED DEBUG - Selection flags:', 
            freshCompetitors.map((c: any) => `${c.name}: is_selected=${c.is_selected}, selected=${c.selected}`));
          
          // IMPORTANT: The /competitors endpoint ONLY returns selected competitors already
          // But doesn't include the is_selected flag in the response
          // So ALL returned competitors should be considered selected
          const competitorsToFetch = freshCompetitors;
          console.log(`Found ${competitorsToFetch.length} selected competitors to fetch menus for:`, 
            competitorsToFetch.map((c: any) => `${c.name} (${c.report_id})`).join(', '));
          
          if (competitorsToFetch.length === 0) {
            message.warning('No selected competitors found with valid IDs. Cannot fetch menus.');
          } else {
            // Start the background process to fetch menus for all competitors
            message.loading(`Collecting menu data for ${competitorsToFetch.length} competitors...`, 3);
            
            // Process competitors one by one with visible feedback
            for (const comp of competitorsToFetch) {
              try {
                message.loading(`Fetching menu for ${comp.name}...`, 3);
                console.log(`Fetching menu data for ${comp.name} (ID: ${comp.report_id})`);
                console.log('Request URL:', `gemini-competitors/fetch-menu/${comp.report_id}`);
                
                // Call the fetch-menu endpoint for this competitor - IMPORTANT: This triggers backend menu extraction
                // Use the configured api service instead of direct axios
                const menuResponse = await api.post(
                  `gemini-competitors/fetch-menu/${comp.report_id}`,
                  { force_refresh: true },  // Force a fresh menu extraction
                  {
                    timeout: 30000 // 30 second timeout for each competitor
                  }
                );
                
                console.log(`Menu fetch response for ${comp.name}:`, menuResponse.data);
                message.success(`Successfully fetched menu for ${comp.name}!`, 3);
              } catch (error: any) {
                console.error(`Error fetching menu for ${comp.name}:`, error);
                console.error('Full error details:', error.response?.data || error.message);
                message.error(`Could not fetch menu for ${comp.name}: ${error.response?.data?.detail || error.message}`, 3);
              }
              
              // Brief pause between requests to avoid overwhelming the server
              await new Promise(resolve => setTimeout(resolve, 500));
            }
            
            message.success(`Menu data collection complete for ${competitorsToFetch.length} competitors`, 5);
          }
        } catch (err: any) {
          console.error('Error during menu fetching process:', err);
          message.error('Failed to fetch competitor menu data: ' + (err?.response?.data?.detail || err.message));
        }
        
        // Refresh the UI to show the selected competitors
        loadCompetitors();
      } else {
        message.error('Failed to set up competitor tracking');
      }
    } catch (err: any) {
      console.error('Error setting up competitor tracking:', err);
      message.error(err.response?.data?.detail || 'Failed to set up competitor tracking');
    } finally {
      setProcessing(false);
    }
  };

  // Function to refresh menu data for a competitor
  // Handle editing a competitor
  const handleEditCompetitor = (competitor: Competitor) => {
    setEditingCompetitor(competitor);
    setEditModalVisible(true);
  };

  // Handle edit form submission
  const handleEditFinish = async (values: any) => {
    if (!editingCompetitor || !editingCompetitor.report_id) {
      message.error('Missing competitor information');
      return;
    }
    
    try {
      setProcessing(true);
      const token = localStorage.getItem('token');
      
      if (!token) {
        message.error('Authentication required');
        return;
      }
      
      // Update the competitor in the backend - correct endpoint for updating
      // Use the configured api service instead of direct axios
      const response = await api.put(`gemini-competitors/${editingCompetitor.report_id}`, 
        {
          ...values,
          report_id: editingCompetitor.report_id,
          selected: true // Ensure it stays selected (backend parameter is 'selected' not 'is_selected')
        }
      );
      
      if (response.data.success) {
        message.success('Competitor updated successfully');
        setEditModalVisible(false);
        // Refresh the competitor list
        loadCompetitors();
      } else {
        message.error('Failed to update competitor');
      }
    } catch (err: any) {
      console.error('Error updating competitor:', err);
      message.error(err.response?.data?.detail || 'Failed to update competitor');
    } finally {
      setProcessing(false);
    }
  };

  // Handle refreshing menu data for a competitor directly from edit modal
  const handleRefreshMenuForCompetitor = () => {
    if (editingCompetitor) {
      refreshMenuData(editingCompetitor);
    }
    // Keep the edit modal open
  };

  const refreshMenuData = async (competitor: Competitor) => {
    if (!competitor.report_id) {
      message.error('Cannot refresh menu: Missing competitor ID');
      return;
    }
    
    try {
      const token = localStorage.getItem('token');
      
      if (!token) {
        message.error('Authentication required');
        return;
      }
      
      setMenuLoading(true);
      message.info('Initiating menu data refresh...');
      
      // Step 1: Initiate the menu fetch process
      const initiateResponse = await api.post(
        `gemini-competitors/fetch-menu/${competitor.report_id}`,
        {}
      );
      
      if (!initiateResponse.data.success) {
        throw new Error(initiateResponse.data.error || 'Failed to initiate menu fetch');
      }
      
      // Step 2: Show notification that processing has started
      const loadingMessage = message.loading({
        content: 'Processing menu data... This may take a minute.',
        duration: 0,
      });
      
      // Step 3: Poll for status until complete
      const pollStatus = async () => {
        try {
          const statusResponse = await api.get(
            `gemini-competitors/fetch-status/${competitor.report_id}`
          );
          
          const status = statusResponse.data.status;
          
          if (status === 'completed' && statusResponse.data.menu_items) {
            // Success! We have the menu items
            loadingMessage(); // Dismiss the loading message
            setMenuItems(statusResponse.data.menu_items);
            
            if (statusResponse.data.batch && statusResponse.data.batch.sync_timestamp) {
              const date = new Date(statusResponse.data.batch.sync_timestamp);
              message.success(`Menu updated! Latest data from ${date.toLocaleDateString()} ${date.toLocaleTimeString()}`);
            } else {
              message.success('Menu data refreshed successfully');
            }
            
            setMenuLoading(false);
            return true;
          } 
          else if (status === 'failed') {
            // Process failed
            loadingMessage(); // Dismiss the loading message
            throw new Error(statusResponse.data.error || 'Menu extraction failed');
          }
          else {
            // Still processing, wait and try again
            return false;
          }
        } catch (pollError) {
          loadingMessage(); // Dismiss the loading message
          throw pollError;
        }
      };
      
      // Poll every 3 seconds for up to 2 minutes
      let attempts = 0;
      const maxAttempts = 40; // 2 minutes (40 * 3 seconds)
      
      const poll = async () => {
        if (attempts >= maxAttempts) {
          loadingMessage(); // Dismiss the loading message
          throw new Error('Menu extraction timed out after 2 minutes');
        }
        
        const completed = await pollStatus();
        
        if (!completed) {
          attempts++;
          setTimeout(poll, 3000); // Check again in 3 seconds
        }
      };
      
      // Start polling
      setTimeout(poll, 3000);
      
    } catch (err: any) {
      console.error('Error refreshing menu data:', err);
      message.error(err.response?.data?.detail || err.message || 'Failed to refresh menu data');
      setMenuLoading(false);
    }
  };
  
  // Function to load competitor menu
  const handleViewMenu = async (competitor: Competitor) => {
    if (!competitor.report_id) {
      message.error('Cannot view menu: Missing competitor ID');
      return;
    }
    
    setSelectedCompetitorForMenu(competitor);
    setMenuVisible(true);
    setMenuLoading(true);
    setMenuItems([]);
    
    try {
      const token = localStorage.getItem('token');
      
      if (!token) {
        message.error('Authentication required');
        return;
      }
      
      // Use the get-stored-menu endpoint to retrieve menu data
      // Use the configured api service instead of direct axios
      const response = await api.get(
        `gemini-competitors/get-stored-menu/${competitor.report_id}`
      );
      
      if (response.data.success && response.data.menu_items && response.data.menu_items.length > 0) {
        setMenuItems(response.data.menu_items);
        if (response.data.batch && response.data.batch.sync_timestamp) {
          const date = new Date(response.data.batch.sync_timestamp);
          message.info(`Showing menu from ${date.toLocaleDateString()} ${date.toLocaleTimeString()}`);
        }
      } else {
        // If no stored menu data is available, ask the user if they want to run extraction
        Modal.confirm({
          title: 'No menu data available',
          content: 'This competitor doesn\'t have any menu data stored yet. Would you like to extract menu data now?',
          okText: 'Extract Menu Data',
          cancelText: 'Cancel',
          onOk: async () => {
            refreshMenuData(competitor);
          },
          onCancel: () => {
            setMenuLoading(false);
          }
        });
      }
    } catch (err: any) {
      console.error('Error loading competitor menu:', err);
      message.error('Failed to load menu');
    } finally {
      setMenuLoading(false);
    }
  };

  // Function to load menu batches for a competitor
  const loadMenuBatches = async (reportId: string) => {
    try {
      setBatchesLoading(true);
      setMenuBatches([]);
      
      const token = localStorage.getItem('token');
      if (!token) return;
      
      // Use the configured api service instead of direct axios
      const response = await api.get(`gemini-competitors/get-menu-batches/${reportId}`);
      
      if (response.data.success && response.data.batches && response.data.batches.length > 0) {
        // Sort batches by timestamp (newest first)
        const sortedBatches = [...response.data.batches].sort(
          (a, b) => new Date(b.sync_timestamp).getTime() - new Date(a.sync_timestamp).getTime()
        );
        setMenuBatches(sortedBatches);
        // Automatically select the most recent batch
        setSelectedBatchId(sortedBatches[0].batch_id);
        
        // Load menu items with the most recent batch
        if (reportId && sortedBatches[0].batch_id) {
          loadCompetitorMenuWithBatch(reportId, sortedBatches[0].batch_id);
        }
      } else {
        setMenuBatches([]);
        setSelectedBatchId(null);
      }
    } catch (error) {
      console.error("Error loading menu batches:", error);
      message.error("Failed to load menu sync history");
    } finally {
      setBatchesLoading(false);
    }
  };
  
  // Function to load a competitor's menu items with specific batch selection
  const loadCompetitorMenuWithBatch = async (reportId: string, batchId?: string | null) => {
    try {
      setCompetitorMenuLoading(true);
      setCompetitorMenuItems([]);
      
      const token = localStorage.getItem('token');
      if (!token) return;
      
      // Set up query parameters for the API call
      const params: any = {};
      if (batchId) {
        params.batch_id = batchId;
      }
      
      // Use the configured api service instead of direct axios
      const response = await api.get(`gemini-competitors/get-stored-menu/${reportId}`, { params: params });
      
      if (response.data.success) {
        setCompetitorMenuItems(response.data.menu_items);
        
        // Update selected batch from response if not explicitly provided
        if (!batchId && response.data.batch) {
          setSelectedBatchId(response.data.batch.batch_id);
        }

        if (response.data.batch && response.data.batch.sync_timestamp) {
          const date = new Date(response.data.batch.sync_timestamp);
          message.info(`Showing menu from ${date.toLocaleDateString()} ${date.toLocaleTimeString()}`);
        }
      } else {
        message.warning("No menu data available for this competitor");
      }
    } catch (error) {
      console.error("Error loading competitor menu:", error);
      message.error("Failed to load menu data");
    } finally {
      setCompetitorMenuLoading(false);
    }
  };

  // Handle adding a new manual competitor
  const handleAddCompetitor = async (values: any) => {
    try {
      setProcessing(true);
      const token = localStorage.getItem('token');
      if (!token) {
        message.error('Authentication required');
        return;
      }
      
      // Generate temporary ID (will be replaced by backend)
      const tempId = `manual-${Date.now()}`;
      
      // Create a competitor object with the form values
      const competitor: Competitor = {
        report_id: tempId,
        name: values.name,
        category: values.category,
        address: values.address,
        menu_url: values.menu_url || '',
        distance_km: undefined,
        selected: true,
        is_selected: true // CRITICAL: This is the flag the backend uses
      };
      
      // Save the competitor to the backend using the manually-add endpoint
      // This endpoint is used elsewhere in the code for adding manual competitors
      const response = await api.post('gemini-competitors/manually-add', 
        competitor,
        {
          headers: {
            Authorization: `Bearer ${token}`
          }
        }
      );
      
      if (response.data.success) {
        message.success('Competitor added successfully');
        setAddModalVisible(false);
        addForm.resetFields();
        
        // If we have a valid response with a report_id and the competitor has a menu URL, 
        // trigger the menu fetch process
        if (response.data.competitor && response.data.competitor.report_id && values.menu_url) {
          const newReportId = response.data.competitor.report_id;
          const competitorName = values.name;
          
          message.loading(`Fetching menu for ${competitorName}...`, 3);
          console.log(`Fetching menu data for ${competitorName} (ID: ${newReportId})`);
          
          try {
            // Call the fetch-menu endpoint to trigger menu extraction
            // Use the configured api service instead of direct axios
            const menuResponse = await api.post(
              `gemini-competitors/fetch-menu/${newReportId}`,
              { force_refresh: true },  // Force a fresh menu extraction
              {
                timeout: 30000 // 30 second timeout
              }
            );
            
            console.log(`Menu fetch response for ${competitorName}:`, menuResponse.data);
            message.success(`Successfully fetched menu for ${competitorName}!`, 3);
            
            // Add a slight delay to ensure the backend has processed the menu data
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            // Update distance if available in the response
            if (menuResponse.data && menuResponse.data.competitor && 
                menuResponse.data.competitor.distance_km !== undefined) {
              console.log(`Got distance for ${competitorName}: ${menuResponse.data.competitor.distance_km} km`);
            }
            
            // Now refresh competitor list to get updated data including distance and menu items
            await loadCompetitors();
            return; // Skip the second loadCompetitors call below
          } catch (menuError: any) {
            console.error(`Error fetching menu for ${competitorName}:`, menuError);
            message.error(`Could not fetch menu: ${menuError.response?.data?.detail || menuError.message}`, 3);
          }
        }
        
        // Refresh competitor list (only reached if menu wasn't fetched)
        loadCompetitors();
      } else {
        message.error('Failed to add competitor');
      }
    } catch (err: any) {
      console.error('Error adding competitor:', err);
      message.error(err.response?.data?.detail || 'Failed to add competitor');
    } finally {
      setProcessing(false);
    }
  };

  // Function to handle delete competitor action
  const handleDeleteCompetitor = async (competitor: Competitor) => {
    if (!competitor.report_id) return;
    
    Modal.confirm({
      title: `Delete ${competitor.name}?`,
      content: 'This will permanently remove this competitor and all associated menu data.',
      okText: 'Yes, Delete',
      okType: 'danger',
      cancelText: 'Cancel',
      onOk: async () => {
        try {
          const token = localStorage.getItem('token');
          if (!token) {
            message.error('Authentication required');
            return;
          }
          
          const response = await api.delete(`gemini-competitors/competitors/${competitor.report_id}`, {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          });
          
          if (response.data.success) {
            message.success(`${competitor.name} deleted successfully`);
            loadCompetitors(); // Refresh the list
          } else {
            message.error('Failed to delete competitor');
          }
        } catch (err: any) {
          console.error('Error deleting competitor:', err);
          message.error(err.response?.data?.detail || 'Failed to delete competitor');
        }
      },
    });
  };

  return (
    <div className="competitors-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <Title level={2}>Competitor Analysis</Title>
          <Title level={5} type="secondary" style={{ marginTop: 0 }}>
            Monitor competitor pricing and features
          </Title>
        </div>
      
      <Space>
          {/* Debug Reset Button - Always visible 
          <Button 
            type="primary" 
            danger 
            size="large"
            onClick={resetCompetitorTracking}
            icon={<ReloadOutlined />}
          >
            RESET TRACKING (Debug)
          </Button>
          */}
          
          {trackingEnabled && (
            <Button 
              type="primary" 
              icon={<PlusOutlined />}
              onClick={() => setAddModalVisible(true)}
            >
              Add Competitor
            </Button>
          )}
        </Space>
      </div>
      
      <Tabs defaultActiveKey="1" onChange={(key) => setActiveTab(key)} style={{ marginTop: 24 }}>
        <TabPane tab={<span><FileSearchOutlined /> Competitors</span>} key="1">
      {/* Menu Modal */}
      <Modal
        title={
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>{selectedCompetitorForMenu ? `${selectedCompetitorForMenu.name} Menu` : 'Menu'}</span>
            {selectedCompetitorForMenu && (
              <Button 
                type="primary" 
                icon={<SyncOutlined />} 
                onClick={() => refreshMenuData(selectedCompetitorForMenu)}
                loading={menuLoading}
              >
                Refresh Menu
              </Button>
            )}
          </div>
        }
        open={menuVisible}
        onCancel={() => setMenuVisible(false)}
        width={1000}
        footer={null}
      >
        {menuLoading ? (
          <div style={{ textAlign: 'center', padding: '50px 0' }}>
            <Spin size="large" />
            <p>Loading menu data...</p>
          </div>
        ) : menuItems.length > 0 ? (
          <div>
            <p>{menuItems.length} items found</p>
            <Table
              dataSource={menuItems}
              columns={[
                {
                  title: 'Item',
                  dataIndex: 'item_name',
                  key: 'item_name',
                  render: (text: string) => <strong>{text}</strong>,
                },
                {
                  title: 'Category',
                  dataIndex: 'category',
                  key: 'category',
                  render: (category: string) => (
                    <Tag color="blue">{category.replace('_', ' ')}</Tag>
                  ),
                },
                {
                  title: 'Description',
                  dataIndex: 'description',
                  key: 'description',
                  ellipsis: true,
                  render: (text: string | null) => text || '-',
                },
                {
                  title: 'Price',
                  dataIndex: 'price',
                  key: 'price',
                  render: (price: number | null, record: MenuItem) => (
                    price ? `${record.price_currency || '$'}${price.toFixed(2)}` : '-'
                  ),
                }
              ]}
              pagination={{ pageSize: 10 }}
              rowKey={(record) => record.item_name + (record.price || 0)}
              size="small"
            />
          </div>
        ) : (
          <Empty description="No menu items found" />
        )}
      </Modal>
      {!trackingEnabled ? (
        <Card>
          <Alert
            message="Competitor tracking not set up"
            description={
              <div>
                <p>You haven't set up competitor tracking yet. Setting up competitor tracking allows you to:</p>
                <ul>
                  <li>Monitor competitors' menu items and prices</li>
                  <li>Compare your pricing with competitors</li>
                  <li>Get price optimization recommendations based on competitor data</li>
                  <li>Track price changes over time</li>
                </ul>
              </div>
            }
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
          <div style={{ textAlign: 'center', padding: '30px 0' }}>
            <Button 
              type="primary" 
              size="large"
              icon={<FileSearchOutlined />}
              onClick={() => {
                setSetupModalVisible(true);
                fetchBusinessProfile();
              }}
            >
              Set up competitor tracking
            </Button>
          </div>
        </Card>
      ) : (
        <Card>
          <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Space>
              <FileSearchOutlined />
              <span>Track your competitors' menus and pricing to optimize your own pricing strategy.</span>
            </Space>
            
          </div>

          {loading ? (
            <div style={{ textAlign: 'center', padding: '50px 0' }}>
              <Spin size="large" />
            </div>
          ) : competitors.length > 0 ? (
            <Table 
              columns={columns}
              dataSource={competitors.map(comp => ({ ...comp, key: comp.report_id }))}
              pagination={{ pageSize: 10 }}
              rowKey="report_id"
            />
          ) : (
            <Empty
              description="No competitors found"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            >
              <Button 
                type="primary" 
                icon={<PlusOutlined />}
                onClick={() => navigate('/feature')}
              >
                Add Your First Competitor
              </Button>
            </Empty>
          )}
        </Card>
      )}
        </TabPane>
        
        <TabPane tab={<span><BarChartOutlined /> Competitor Comparison</span>} key="2">
          <Card>
            <div style={{ marginBottom: 16 }}>
              <Title level={5} style={{ marginTop: 0 }}>Select a competitor to view their menu and price data:</Title>
              <div style={{ display: 'flex', marginTop: 12 }}>
                <Select 
                  style={{ width: '60%', marginRight: '12px' }} 
                  placeholder="Select a competitor" 
                  onChange={(value) => {
                    const reportId = value as string;
                    setSelectedCompetitorId(reportId);
                    setSelectedBatchId(null);
                    setMenuBatches([]);
                    // We only need to load the batches - loadMenuBatches will automatically
                    // load the most recent batch's menu items
                    loadMenuBatches(reportId);
                  }}
                  loading={loading}
                  disabled={competitors.length === 0}
                  allowClear
                >
                  {competitors.map((competitor) => (
                    <Select.Option key={competitor.report_id} value={competitor.report_id}>
                      {competitor.name} - {competitor.category} {competitor.distance_km ? `(${competitor.distance_km} km away)` : ''}
                    </Select.Option>
                  ))}
                </Select>
                {menuBatches.length > 0 && (
                  <Select
                    style={{ width: '35%' }}
                    placeholder="Select menu sync"
                    loading={batchesLoading}
                    value={selectedBatchId || undefined}
                    onChange={(batchId: string) => {
                      setSelectedBatchId(batchId);
                      if (selectedCompetitorId) {
                        loadCompetitorMenuWithBatch(selectedCompetitorId, batchId);
                      }
                    }}
                  >
                    {[...menuBatches]
                      .sort((a, b) => new Date(b.sync_timestamp).getTime() - new Date(a.sync_timestamp).getTime())
                      .map((batch) => {
                        const date = new Date(batch.sync_timestamp);
                        const formattedDate = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
                        return (
                          <Select.Option key={batch.batch_id} value={batch.batch_id}>
                            {formattedDate} ({batch.item_count} items)
                          </Select.Option>
                        );
                      })}
                  </Select>
                )}
              </div>
            </div>
            
            <div style={{ marginTop: 16 }}>
              <Title level={5}>Menu Items</Title>
              
              {competitorMenuLoading ? (
                <div style={{ display: 'flex', justifyContent: 'center', padding: '40px 0' }}>
                  <Space direction="vertical" align="center">
                    <Spin size="large" />
                    <Paragraph>Loading competitor menu data...</Paragraph>
                  </Space>
                </div>
              ) : competitorMenuItems.length > 0 ? (
                <Table 
                  dataSource={competitorMenuItems}
                  rowKey={(item) => `${item.item_name}-${item.price}`}
                  pagination={{ pageSize: 10 }}
                  columns={[
                    {
                      title: 'Item Name',
                      dataIndex: 'item_name',
                      key: 'item_name',
                      sorter: (a, b) => a.item_name.localeCompare(b.item_name)
                    },
                    {
                      title: 'Category',
                      dataIndex: 'category',
                      key: 'category',
                      render: (category) => <Tag color="blue">{category}</Tag>,
                      filters: Array.from(new Set(competitorMenuItems.map(item => item.category)))
                        .map(category => ({ text: category, value: category })),
                      onFilter: (value, record) => record.category === value
                    },
                    {
                      title: 'Description',
                      dataIndex: 'description',
                      key: 'description',
                      ellipsis: true
                    },
                    {
                      title: 'Price',
                      dataIndex: 'price',
                      key: 'price',
                      render: (price, record) => (
                        price !== null ? 
                        <Tag color="green">{price} {record.price_currency || '$'}</Tag> : 
                        <Tag color="orange">N/A</Tag>
                      ),
                      sorter: (a, b) => (a.price || 0) - (b.price || 0)
                    },
                    {
                      title: 'Confidence',
                      dataIndex: 'source_confidence',
                      key: 'source_confidence',
                      render: (confidence) => confidence ? (
                        <Tag color={confidence === 'high' ? 'green' : confidence === 'medium' ? 'orange' : 'red'}>
                          {confidence.toUpperCase()}
                        </Tag>
                      ) : '-'
                    },
                    {
                      title: 'Source',
                      dataIndex: 'source_url',
                      key: 'source_url',
                      render: (url) => url ? (
                        <a href={url} target="_blank" rel="noreferrer">
                          <LinkOutlined />
                        </a>
                      ) : '-'
                    }
                  ]}
                />
              ) : (
                <Empty 
                  description={
                    selectedCompetitorId ? 
                    "No menu data available for this competitor" : 
                    "Select a competitor to view their menu data"
                  }
                  image={Empty.PRESENTED_IMAGE_SIMPLE} 
                />
              )}
            </div>
          </Card>
        </TabPane>
      </Tabs>
      
      {/* Competitor Setup Modal */}
      <Modal
        title="Set Up Competitor Tracking"
        open={setupModalVisible}
        onCancel={() => setSetupModalVisible(false)}
        footer={null}
        width={1000}
        style={{ top: 20 }}
        maskClosable={false}
      >
        {/* Step 1: Search Form (only shown if profile data is incomplete) */}
        {currentStep === 0 && businessFormVisible && (
          <div>
            <p>To get started with competitor tracking, we need your business information.</p>
            {businessProfileLoading ? (
              <div style={{ textAlign: 'center', padding: '20px 0' }}>
                <Spin size="large" />
                <p>Loading your business information and searching for competitors...</p>
              </div>
            ) : (
              <>
                <Alert 
                  message="Your business profile is incomplete. Please provide the missing information to find competitors." 
                  description="This information helps us identify nearby businesses similar to yours."
                  type="info" 
                  showIcon 
                  style={{ marginBottom: 16 }} 
                />
                <Form
                  form={searchForm}
                  layout="vertical"
                  onFinish={searchLocalCompetitors}
                >
                  <Form.Item
                    label="Business Type"
                    name="businessType"
                    rules={[{ required: true, message: 'Please enter your business type' }]}
                  >
                    <Input placeholder="e.g., Coffee Shop, Restaurant, Bakery" />
                  </Form.Item>
                  
                  <Form.Item
                    label="Location"
                    name="location"
                    rules={[{ required: true, message: 'Please enter your business location' }]}
                  >
                    <Input placeholder="e.g., 123 Main St, New York, NY" />
                  </Form.Item>
                  
                  <Form.Item>
                    <Button 
                      type="primary" 
                      htmlType="submit" 
                      icon={<SearchOutlined />}
                      loading={searchLoading}
                    >
                      Find Competitors
                    </Button>
                  </Form.Item>
                </Form>
              </>
            )}
          </div>
        )}
        
        {/* Step 2: Search Results and Selection */}
        {currentStep === 1 && searchCompleted && (
          <div>
            <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h3>Found {searchResults.length} competitors ({searchResults.filter(comp => comp.selected).length} active)</h3>
                <p style={{ color: '#888', marginTop: -5 }}>Click on competitors to remove them from tracking</p>
              </div>
              <div>
                <Button 
                  style={{ marginRight: 8 }} 
                  onClick={() => {
                    setBusinessFormVisible(true);
                    setCurrentStep(0);
                  }}
                >
                  Modify Search
                </Button>
                <Button 
                  type="primary" 
                  onClick={completeSetup}
                  disabled={searchResults.filter(comp => comp.selected).length === 0 || processing}
                  loading={processing}
                >
                  {processing ? 'Processing...' : 'Complete Setup'}
                </Button>
              </div>
            </div>
            
            <div style={{ marginBottom: 16 }}>
              <Button 
                type="dashed" 
                icon={<PlusOutlined />}
                onClick={() => openEditModal({ name: '', category: '', address: '' } as Competitor)}
              >
                Add Competitor Manually
              </Button>
            </div>
            
            <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
              <List
                size="small"
                itemLayout="horizontal"
                dataSource={searchResults}
                renderItem={(competitor, index) => (
                  <List.Item
                    className={competitor.selected ? 'selected-competitor' : 'deselected-competitor'}
                    style={{
                      background: competitor.selected ? 'rgba(24, 144, 255, 0.05)' : 'rgba(0, 0, 0, 0.02)',
                      border: competitor.selected ? '1px solid rgba(24, 144, 255, 0.2)' : '1px solid transparent',
                      borderRadius: '4px',
                      marginBottom: '4px',
                      cursor: 'pointer',
                      opacity: competitor.selected ? 1 : 0.5
                    }}
                    actions={[
                      <Button 
                        type="text" 
                        size="small"
                        icon={<EditOutlined />} 
                        onClick={(e) => {
                          e.stopPropagation();
                          openEditModal(competitor);
                        }}
                      >
                        Edit
                      </Button>,
                      competitor.selected ? (
                        <Button 
                          type="text" 
                          size="small"
                          danger
                          onClick={(e) => {
                            e.stopPropagation();
                            removeCompetitor(searchResults.findIndex(c => c.name === competitor.name));
                          }}
                        >
                          Remove
                        </Button>
                      ) : (
                        <Button 
                          type="text" 
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleCompetitorSelectionChange(searchResults.findIndex(c => c.name === competitor.name), true);
                          }}
                        >
                          Add Back
                        </Button>
                      ),
                      <Space>
                        <Button type="text" size="small" onClick={() => handleViewMenu(competitor)}>View Menu</Button>
                      </Space>
                    ]}
                  >
                    <List.Item.Meta
                      title={
                        <div style={{ display: 'flex', alignItems: 'center' }}>
                          <span>{competitor.name}</span>
                          {competitor.distance_km && <span style={{ marginLeft: 8, fontSize: '0.85em', color: '#888' }}>({competitor.distance_km.toFixed(1)} km)</span>}
                        </div>
                      }
                      description={
                        <div style={{ fontSize: '0.9em' }}>
                          <div>{competitor.address}</div>
                          {competitor.menu_url && (
                            <a href={competitor.menu_url} target="_blank" rel="noopener noreferrer">
                              <LinkOutlined /> Menu
                            </a>
                          )}
                        </div>
                      }
                    />
                  </List.Item>
                )}
              />
            </div>
          </div>
        )}
        
        {searchLoading && (
          <div style={{ textAlign: 'center', padding: '50px 0' }}>
            <Spin size="large" />
            <p style={{ marginTop: 16 }}>Searching for competitors in your area...</p>
          </div>
        )}
      </Modal>
      
      {/* Competitor Edit Modal */}
      <Modal
        title="Edit Competitor Information"
        open={editModalVisible}
        onCancel={() => setEditModalVisible(false)}
        footer={null}
      >
        <Form
          form={editForm}
          layout="vertical"
          onFinish={handleSaveCompetitor}
        >
          <Form.Item
            label="Name"
            name="name"
            rules={[{ required: true, message: 'Please enter competitor name' }]}
          >
            <Input placeholder="Competitor name" />
          </Form.Item>
          
          <Form.Item
            label="Category"
            name="category"
            rules={[{ required: true, message: 'Please enter competitor category' }]}
          >
            <Input placeholder="e.g., Restaurant, Cafe" />
          </Form.Item>
          
          <Form.Item
            label="Address"
            name="address"
            rules={[{ required: true, message: 'Please enter competitor address' }]}
          >
            <Input placeholder="Full address" />
          </Form.Item>
          
          <Form.Item
            label="Menu URL"
            name="menu_url"
          >
            <Input placeholder="https://..." />
          </Form.Item>
          
          <Form.Item>
            <Button type="primary" htmlType="submit">
              Save Changes
            </Button>
          </Form.Item>
        </Form>
      </Modal>

      {/* Competitor Add Modal */}
      <Modal
        title="Add Competitor"
        open={addModalVisible}
        onCancel={() => setAddModalVisible(false)}
        footer={null}
      >
        <Form
          form={addForm}
          layout="vertical"
          onFinish={handleAddCompetitor}
        >
          <Form.Item
            label="Name"
            name="name"
            rules={[{ required: true, message: 'Please enter competitor name' }]}
          >
            <Input placeholder="Competitor name" />
          </Form.Item>
          
          <Form.Item
            label="Category"
            name="category"
            rules={[{ required: true, message: 'Please enter competitor category' }]}
          >
            <Input placeholder="e.g., Restaurant, Cafe" />
          </Form.Item>
          
          <Form.Item
            label="Address"
            name="address"
            rules={[{ required: true, message: 'Please enter competitor address' }]}
          >
            <Input placeholder="Full address" />
          </Form.Item>
          
          <Form.Item
            label="Menu URL"
            name="menu_url"
          >
            <Input placeholder="https://..." />
          </Form.Item>
          
          <Form.Item>
            <Button type="primary" htmlType="submit">
              Add Competitor
            </Button>
          </Form.Item>
        </Form>
      </Modal>

      {/* Edit Competitor Modal */}
      <Modal
        title="Edit Competitor"
        open={editModalVisible}
        onCancel={() => setEditModalVisible(false)}
        footer={null}
        destroyOnClose
      >
        {editingCompetitor && (
          <Form
            layout="vertical"
            initialValues={{
              name: editingCompetitor.name,
              category: editingCompetitor.category,
              address: editingCompetitor.address,
              menu_url: editingCompetitor.menu_url || ''
            }}
            onFinish={handleEditFinish}
          >
            <Form.Item
              label="Name"
              name="name"
              rules={[{ required: true, message: 'Please enter competitor name' }]}
            >
              <Input placeholder="Competitor name" />
            </Form.Item>
            
            <Form.Item
              label="Category"
              name="category"
              rules={[{ required: true, message: 'Please enter category' }]}
            >
              <Input placeholder="e.g. Coffee Shop, Restaurant, etc." />
            </Form.Item>
            
            <Form.Item
              label="Address"
              name="address"
              rules={[{ required: true, message: 'Please enter address' }]}
            >
              <Input.TextArea placeholder="Full address" rows={2} />
            </Form.Item>
            
            <Form.Item
              label="Menu URL"
              name="menu_url"
            >
              <Input placeholder="https://example.com/menu" />
            </Form.Item>
            
            <Form.Item>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Button onClick={() => setEditModalVisible(false)}>
                  Cancel
                </Button>
                <Space>
                  <Button type="primary" htmlType="submit" loading={processing}>
                    Save Changes
                  </Button>
                  <Button type="primary" danger onClick={handleRefreshMenuForCompetitor}>
                    Refresh Menu
                  </Button>
                </Space>
              </div>
            </Form.Item>
          </Form>
        )}
      </Modal>
    </div>
  );
};

export default Competitors;
