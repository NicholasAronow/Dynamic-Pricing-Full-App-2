import React, { useState, useEffect } from 'react';
import './custom-tabs.css';
import { Card, Table, Typography, Space, Button, Empty, Spin, message, Tabs, Modal, Tooltip, Input, Alert, List, Statistic, AutoComplete, Select, Form, Radio, InputNumber, Divider, Row, Col } from 'antd';
import { PlusOutlined, DollarOutlined, CoffeeOutlined, AppstoreOutlined, ExclamationCircleOutlined, ThunderboltOutlined, DeleteOutlined, EditOutlined, TagsOutlined, UserOutlined, SaveOutlined } from '@ant-design/icons';
import * as recipeService from '../../services/recipeService';
import { generateSuggestionsFromMenu } from '../../services/recipeService';
import itemService, { Item } from '../../services/itemService';
import * as otherCostsService from '../../services/otherCostsService';
import { FixedCost, Employee } from '../../services/otherCostsService';
import { RecipeItem, IngredientItem, RecipeIngredient, RecipeSuggestion, SuggestionIngredient, MenuSuggestionResponse } from '../../types/recipe';
import { MenuItem } from '../../types/menu';
import RecipeModal from './RecipeModal';
import IngredientModal from './IngredientModal';

const { Title, Text } = Typography;

const { TabPane } = Tabs;

const { confirm } = Modal;

const Costs: React.FC = () => {
  // Unit conversion function to convert between different measurement systems
  const getConversionFactor = (fromUnit: string, toUnit: string): number => {
    // Standardize unit formatting
    const from = fromUnit?.toLowerCase().trim() || '';
    const to = toUnit?.toLowerCase().trim() || '';
    
    // Same unit, no conversion needed
    if (from === to) return 1;
    
    // Weight conversions (standardize to grams)
    const weightConversions: Record<string, number> = {
      'g': 1,
      'gram': 1,
      'grams': 1,
      'kg': 1000,
      'oz': 28.3495,
      'ounce': 28.3495,
      'ounces': 28.3495,
      'lb': 453.592,
      'pound': 453.592,
      'pounds': 453.592
    };
    
    // Volume conversions (standardize to ml)
    const volumeConversions: Record<string, number> = {
      'ml': 1,
      'milliliter': 1,
      'milliliters': 1,
      'l': 1000,
      'liter': 1000,
      'liters': 1000,
      'cup': 236.588,
      'cups': 236.588,
      'tbsp': 14.7868,
      'tablespoon': 14.7868,
      'tablespoons': 14.7868,
      'tsp': 4.92892,
      'teaspoon': 4.92892,
      'teaspoons': 4.92892,
      'gallon': 3785.41,
      'gallons': 3785.41,
      'gal': 3785.41,
      'quart': 946.353,
      'quarts': 946.353,
      'pint': 473.176,
      'pints': 473.176,
      'oz': 29.574
    };
    
    // Check if both units are in the same category
    if (weightConversions[from] && weightConversions[to]) {
      // Convert from source unit to grams, then from grams to target unit
      return weightConversions[from] / weightConversions[to];
    } else if (volumeConversions[from] && volumeConversions[to]) {
      // Convert from source unit to ml, then from ml to target unit
      return volumeConversions[from] / volumeConversions[to];
    }
    
    // Units are not compatible or not recognized, return 1 as fallback
    console.warn(`Incompatible units: ${fromUnit} to ${toUnit}`);
    return 1;
  };

  // State for recipes and ingredients
  const [recipes, setRecipes] = useState<RecipeItem[]>([]);
  const [ingredients, setIngredients] = useState<IngredientItem[]>([]);
  const [recipesLoading, setRecipesLoading] = useState<boolean>(true);
  const [ingredientsLoading, setIngredientsLoading] = useState<boolean>(true);
  const [menuItemsForRecipes, setMenuItemsForRecipes] = useState<Item[]>([]);
  const [menuItemsLoading, setMenuItemsLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<string>('1');
  
  // State for other costs
  const [rent, setRent] = useState<number | null>(null);
  const [utilities, setUtilities] = useState<number | null>(null);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [otherCostsLoading, setOtherCostsLoading] = useState<boolean>(true);
  const [savingAllCosts, setSavingAllCosts] = useState<boolean>(false);
  
  // Current date for setting month/year in fixed costs
  const currentDate = new Date();
  const currentMonth = currentDate.getMonth() + 1; // JavaScript months are 0-indexed
  const currentYear = currentDate.getFullYear();
  
  // Modal state
  const [recipeModalVisible, setRecipeModalVisible] = useState<boolean>(false);
  const [ingredientModalVisible, setIngredientModalVisible] = useState<boolean>(false);
  const [selectedRecipe, setSelectedRecipe] = useState<RecipeItem | undefined>();
  const [selectedIngredient, setSelectedIngredient] = useState<IngredientItem | undefined>();
  const [isNewRecipe, setIsNewRecipe] = useState<boolean>(true);
  const [isNewIngredient, setIsNewIngredient] = useState<boolean>(true);
  
  // Viewing recipe details modal
  const [recipeDetailsVisible, setRecipeDetailsVisible] = useState<boolean>(false);
  
  // Quick Setup state
  const [quickSetupVisible, setQuickSetupVisible] = useState<boolean>(false);
  const [screenBlurred, setScreenBlurred] = useState<boolean>(false);
  const [quickSetupLoading, setQuickSetupLoading] = useState<boolean>(false);
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [suggestions, setSuggestions] = useState<MenuSuggestionResponse | null>(null);
  const [generatingAiSuggestions, setGeneratingAiSuggestions] = useState<boolean>(false);
  const [baseIngredients, setBaseIngredients] = useState<Omit<IngredientItem, 'ingredient_id' | 'date_created'>[]>([]);

  // Fetch recipe data
  const loadRecipes = async () => {
    try {
      setRecipesLoading(true);
      const data = await recipeService.getRecipes();
      setRecipes(data);
    } catch (error) {
      message.error('Failed to load recipes');
      console.error(error);
    } finally {
      setRecipesLoading(false);
    }
  };

  const loadIngredients = async () => {
    try {
      setIngredientsLoading(true);
      const data = await recipeService.getIngredients();
      setIngredients(data);
    } catch (error) {
      message.error('Failed to load ingredients');
      console.error(error);
    } finally {
      setIngredientsLoading(false);
    }
  };

  const loadOtherCosts = async () => {
    try {
      setOtherCostsLoading(true);
      
      // Load fixed costs (rent and utilities)
      const fixedCosts = await otherCostsService.getFixedCosts(undefined, currentMonth, currentYear);
      
      // Find rent and utilities from the returned fixed costs
      const rentCost = fixedCosts.find(cost => cost.cost_type === 'rent');
      const utilitiesCost = fixedCosts.find(cost => cost.cost_type === 'utilities');
      
      // Set state for rent and utilities
      setRent(rentCost ? rentCost.amount : null);
      setUtilities(utilitiesCost ? utilitiesCost.amount : null);
      
      // Load employees
      const employeeData = await otherCostsService.getEmployees();
      setEmployees(employeeData);
      
    } catch (error) {
      message.error('Failed to load other costs');
      console.error(error);
    } finally {
      setOtherCostsLoading(false);
    }
  };

  const saveAllCosts = async () => {
    try {
      setSavingAllCosts(true);
      
      // Save fixed costs (rent and utilities)
      // Check if rent and utilities are not null
      if (rent !== null || utilities !== null) {
        // Get existing fixed costs
        const fixedCosts = await otherCostsService.getFixedCosts(undefined, currentMonth, currentYear);
        
        // Find existing rent and utilities costs
        const rentCost = fixedCosts.find(cost => cost.cost_type === 'rent');
        const utilitiesCost = fixedCosts.find(cost => cost.cost_type === 'utilities');
        
        // Handle rent cost
        if (rent !== null) {
          if (rentCost) {
            // Update existing rent cost
            await otherCostsService.updateFixedCost(rentCost.id!, { 
              ...rentCost, 
              amount: rent
            });
          } else {
            // Create new rent cost
            await otherCostsService.createFixedCost({
              cost_type: 'rent',
              amount: rent,
              month: currentMonth,
              year: currentYear
            });
          }
        }
        
        // Handle utilities cost
        if (utilities !== null) {
          if (utilitiesCost) {
            // Update existing utilities cost
            await otherCostsService.updateFixedCost(utilitiesCost.id!, { 
              ...utilitiesCost, 
              amount: utilities
            });
          } else {
            // Create new utilities cost
            await otherCostsService.createFixedCost({
              cost_type: 'utilities',
              amount: utilities,
              month: currentMonth,
              year: currentYear
            });
          }
        }
      }
      
      // Save all employees
      for (const employee of employees) {
        try {
          if (employee.id) {
            // Update existing employee
            await otherCostsService.updateEmployee(employee.id, employee);
          } else {
            // Create new employee
            const createdEmployee = await otherCostsService.createEmployee(employee);
            
            // Replace the local employee with the created one (to get the ID)
            setEmployees(prev => 
              prev.map(emp => 
                emp === employee ? createdEmployee : emp
              )
            );
          }
        } catch (empError) {
          console.error(`Failed to save employee ${employee.name}:`, empError);
          // Continue with other employees even if one fails
        }
      }
      
      message.success('All costs saved successfully');
      
      // Refresh data after saving
      await loadOtherCosts();
      
    } catch (error) {
      message.error('Failed to save costs');
      console.error(error);
    } finally {
      setSavingAllCosts(false);
    }
  };



  // Load menu items for recipe linking
  const loadMenuItemsForRecipes = async () => {
    try {
      setMenuItemsLoading(true);
      const items = await itemService.getItems();
      setMenuItemsForRecipes(items);
    } catch (error) {
      message.error('Failed to load menu items');
      console.error(error);
    } finally {
      setMenuItemsLoading(false);
    }
  };

  useEffect(() => {
    loadRecipes();
    loadIngredients();
    loadOtherCosts();
    loadMenuItemsForRecipes();
  }, []);

  // Columns for recipes table
  const recipeColumns = [
    {
      title: 'Item Name',
      dataIndex: 'item_name',
      key: 'item_name',
    },
    {
      title: 'Ingredients Count',
      dataIndex: 'ingredients',
      key: 'ingredients_count',
      render: (ingredients: any[]) => ingredients.length,
    },
    {
      title: 'Total Ingredient Cost',
      key: 'total_ingredient_cost',
      render: (_: any, record: RecipeItem) => {
        let totalCost = 0;
        record.ingredients.forEach(ing => {
          const ingredient = ingredients.find(i => i.ingredient_id === ing.ingredient_id);
          if (ingredient && ingredient.price && ingredient.quantity) {
            const baseUnitPrice = ingredient.price / ingredient.quantity;
            
            if (ing.unit === ingredient.unit) {
              totalCost += baseUnitPrice * ing.quantity;
            } else {
              const conversionFactor = getConversionFactor(ingredient.unit, ing.unit);
              totalCost += baseUnitPrice * ing.quantity / conversionFactor;
            }
          }
        });
        
        return <span style={{ color: totalCost === 0 ? '#ff4d4f' : 'inherit' }}>${totalCost.toFixed(2)}</span>;
      },
    },
    {
      title: 'Action',
      key: 'action',
      width: '80px',
      render: (_: any, record: RecipeItem) => (
        <Space size="small">
          <Button type="text" icon={<EditOutlined />} onClick={() => handleEditRecipe(record)} />
          <Button type="text" danger icon={<DeleteOutlined />} onClick={() => handleDeleteRecipe(record)} />
        </Space>
      ),
    },
  ];

  // Columns for ingredients table
  const ingredientColumns = [
    {
      title: 'Ingredient Name',
      dataIndex: 'ingredient_name',
      key: 'ingredient_name',
    },
    {
      title: 'Quantity',
      dataIndex: 'quantity',
      key: 'quantity',
      render: (quantity: number, record: IngredientItem) => `${quantity} ${record.unit}`,
    },
    {
      title: 'Price',
      dataIndex: 'price',
      key: 'price',
      render: (price: number) => `$${price.toFixed(2)}`,
    },
    {
      title: 'Unit Price',
      key: 'unit_price',
      render: (text: string, record: IngredientItem) => `$${(record.price / record.quantity).toFixed(2)} / ${record.unit}`,
    },
    {
      title: 'Action',
      key: 'action',
      width: '80px',
      render: (_: any, record: IngredientItem) => (
        <Space size="small">
          <Button type="text" icon={<EditOutlined />} onClick={() => handleEditIngredient(record)} />
          <Button type="text" danger icon={<DeleteOutlined />} onClick={() => handleDeleteIngredient(record)} />
        </Space>
      ),
    },
  ];

  // Recipe modal handlers
  const handleAddRecipe = () => {
    setSelectedRecipe(undefined);
    setIsNewRecipe(true);
    setRecipeModalVisible(true);
  };

  const handleEditRecipe = (recipe: RecipeItem) => {
    setSelectedRecipe(recipe);
    setIsNewRecipe(false);
    setRecipeModalVisible(true);
  };

  const handleSaveRecipe = async (recipe: RecipeItem) => {
    try {
      if (isNewRecipe) {
        // Add new recipe to the list
        const newRecipe = await recipeService.createRecipe(recipe);
        setRecipes([...recipes, newRecipe]);
        message.success('Recipe added successfully');
      } else {
        // Update existing recipe
        const updatedRecipe = await recipeService.updateRecipe(recipe);
        setRecipes(recipes.map(item => 
          item.item_id === recipe.item_id ? updatedRecipe : item
        ));
        message.success('Recipe updated successfully');
      }
      setRecipeModalVisible(false);
    } catch (error) {
      console.error('Failed to save recipe:', error);
      message.error('Failed to save recipe');
    }
  };

  const handleDeleteRecipe = (recipe: RecipeItem) => {
    Modal.confirm({
      title: 'Are you sure you want to delete this recipe?',
      icon: <ExclamationCircleOutlined />,
      content: 'This action cannot be undone.',
      onOk: async () => {
        try {
          await recipeService.deleteRecipe(recipe.item_id);
          setRecipes(recipes.filter(item => item.item_id !== recipe.item_id));
          message.success('Recipe deleted successfully');
        } catch (error) {
          console.error('Failed to delete recipe:', error);
          message.error('Failed to delete recipe');
        }
      }
    });
  };

  // Ingredient modal handlers
  const handleAddIngredient = () => {
    setSelectedIngredient(undefined);
    setIsNewIngredient(true);
    setIngredientModalVisible(true);
  };

  const handleEditIngredient = (ingredient: IngredientItem) => {
    setSelectedIngredient(ingredient);
    setIsNewIngredient(false);
    setIngredientModalVisible(true);
  };

  const handleSaveIngredient = async (ingredient: IngredientItem) => {
    try {
      if (isNewIngredient) {
        // Add new ingredient to the list
        const newIngredient = await recipeService.createIngredient(ingredient);
        setIngredients([...ingredients, newIngredient]);
        message.success('Ingredient added successfully');
      } else {
        // Update existing ingredient
        const updatedIngredient = await recipeService.updateIngredient(ingredient);
        setIngredients(ingredients.map(item => 
          item.ingredient_id === ingredient.ingredient_id ? updatedIngredient : item
        ));
        message.success('Ingredient updated successfully');
      }
      setIngredientModalVisible(false);
    } catch (error) {
      console.error('Failed to save ingredient:', error);
      message.error('Failed to save ingredient');
    }
  };

  const handleDeleteIngredient = (ingredient: IngredientItem) => {
    // Check if the ingredient is used in any recipe
    const isIngredientUsed = recipes.some(recipe => 
      recipe.ingredients.some(ing => ing.ingredient_id === ingredient.ingredient_id)
    );

    if (isIngredientUsed) {
      Modal.error({
        title: 'Cannot Delete Ingredient',
        content: 'This ingredient is being used in one or more recipes. Please remove it from all recipes first.'
      });
      return;
    }
    
    Modal.confirm({
      title: 'Are you sure you want to delete this ingredient?',
      icon: <ExclamationCircleOutlined />,
      content: 'This action cannot be undone.',
      onOk: async () => {
        try {
          await recipeService.deleteIngredient(ingredient.ingredient_id);
          setIngredients(ingredients.filter(item => item.ingredient_id !== ingredient.ingredient_id));
          message.success('Ingredient deleted successfully');
        } catch (error) {
          console.error('Failed to delete ingredient:', error);
          message.error('Failed to delete ingredient');
        }
      }
    });
  };

  // Tab change handler
  const handleTabChange = (key: string) => {
    setActiveTab(key);
  };

  // Quick Setup modal handlers
  const handleQuickSetup = () => {
    setScreenBlurred(true);
    setQuickSetupLoading(true);
    showQuickSetupModal();
  };
  
  // Function to show the quick setup modal
  const showQuickSetupModal = async () => {
    try {
      // Fetch existing menu items from itemService
      const items = await itemService.getItems();
      
      // Convert to our MenuItem format
      const existingMenuItems = items.map(item => ({
        id: item.id.toString(), // Convert number to string for id
        name: item.name,
        description: item.description || '',
        price: item.current_price,
        category: item.category
      }));
      
      setMenuItems(existingMenuItems);
      
      // Process menu items with LLM before showing anything to the user
      if (existingMenuItems.length > 0) {
        const response = await generateSuggestionsFromMenu(existingMenuItems);
        setSuggestions(response);
        // Start directly at step 2 (review suggestions)
        setCurrentStep(2);
      } else {
        message.error('No menu items found. Please add menu items manually.');
        // If no menu items found, still show step 1 so user can add them manually
        setCurrentStep(1);
      }

      // Only show the modal after we have the results
      setQuickSetupVisible(true);
    } catch (error: any) {
      console.error('Error in quick setup:', error);
      message.error(error.message || 'Failed to set up recipes automatically');
      // Clean up on error
      setScreenBlurred(false);
      setMenuItems([]);
    } finally {
      setQuickSetupLoading(false);
    }
  };

  // Render a loading spinner when screen is blurred and loading is true
  const renderLoadingSpinner = () => {
    if (screenBlurred && quickSetupLoading) {
      return (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1001, // Higher than the blur overlay
        }}>
          <div style={{
            background: 'rgba(255, 255, 255, 0.8)',
            borderRadius: '8px',
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)'
          }}>
            <Spin size="large" />
            <div style={{ marginTop: '16px', fontWeight: 'bold' }}>
              Analyzing your menu items...
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  const handleQuickSetupCancel = () => {
    setQuickSetupVisible(false);
    setScreenBlurred(false);
    setCurrentStep(1);
    setMenuItems([]);
    setSuggestions(null);
  };

  // Go to previous step
  const handlePreviousStep = () => {
    setCurrentStep(currentStep - 1);
  };

  // Handle quick setup submission
  // Handle menu item changes
  const handleMenuItemChange = (index: number, field: keyof MenuItem, value: string | number) => {
    const updatedMenuItems = [...menuItems];
    updatedMenuItems[index] = {
      ...updatedMenuItems[index],
      [field]: value
    };
    setMenuItems(updatedMenuItems);
  };
  
  // Remove a menu item
  const removeMenuItem = (index: number) => {
    const updatedMenuItems = [...menuItems];
    updatedMenuItems.splice(index, 1);
    setMenuItems(updatedMenuItems);
  };
  
  // Add a new empty menu item
  const addMenuItem = () => {
    const newMenuItem: MenuItem = {
      id: `new-${Date.now()}`, // Generate temporary ID
      name: ''
    };
    setMenuItems([...menuItems, newMenuItem]);
  };

  // Generate AI suggestions from menu items
  const generateAiSuggestions = async () => {
    if (menuItems.length === 0) {
      message.error('Please add at least one menu item');
      return;
    }

    try {
      setGeneratingAiSuggestions(true);
      const response = await generateSuggestionsFromMenu(menuItems);
      setSuggestions(response);
      setCurrentStep(2); // Move to the next step
    } catch (error: any) {
      message.error(error.message || 'Failed to generate suggestions');
    } finally {
      setGeneratingAiSuggestions(false);
    }
  };

  // Handle quick setup submission - final step
  const handleQuickSetupSubmit = async () => {
    if (!suggestions) {
      message.error('No suggestions available. Please go back and generate suggestions first.');
      return;
    }

    try {
      setQuickSetupLoading(true);
      
      // Use baseIngredients state for price, quantity, and unit instead of default values
      // Create a map of the base ingredients by name for easy lookup
      const baseIngredientsMap = new Map();
      baseIngredients.forEach(ing => {
        baseIngredientsMap.set(ing.ingredient_name.toLowerCase(), ing);
      });

      // Extract all unique ingredients from recipes, using baseIngredients data when available
      const uniqueIngredients = new Map();
      suggestions.recipes.forEach((recipe: RecipeSuggestion) => {
        recipe.ingredients.forEach((ing: SuggestionIngredient) => {
          const key = ing.ingredient.toLowerCase();
          if (!uniqueIngredients.has(key)) {
            const baseIngredient = baseIngredientsMap.get(key);
            uniqueIngredients.set(key, {
              ingredient_name: ing.ingredient,
              quantity: baseIngredient?.quantity || 0, // Use base ingredient quantity when available
              unit: baseIngredient?.unit || ing.unit || '', 
              price: baseIngredient?.price || 0 // Use base ingredient price when available
            });
          }
        });
      });
      
      // Create all unique ingredients sequentially to avoid overwhelming the server
      const createdIngredients = [];
      const uniqueIngredientsArray = Array.from(uniqueIngredients.values());
      
      // Show progress information
      message.info(`Processing ${uniqueIngredientsArray.length} ingredients...`);
      
      // Process ingredients one at a time
      for (const ingredient of uniqueIngredientsArray) {
        try {
          const response = await recipeService.createIngredient(ingredient);
          createdIngredients.push(response);
        } catch (err: any) {
          console.error(`Failed to create ingredient ${ingredient.ingredient_name}:`, err);
          // Continue with other ingredients even if one fails
        }
      }

      // Create ingredient map for easy lookup by name
      const ingredientMap = new Map();
      createdIngredients.forEach(ingredient => {
        ingredientMap.set(ingredient.ingredient_name.toLowerCase(), ingredient);
      });

      // Get menu items to associate with recipes by name
      const existingMenuItems = await itemService.getItems();
      const menuItemMap = new Map();
      existingMenuItems.forEach(item => {
        menuItemMap.set(item.name.toLowerCase(), item.id);
      });
      console.log('Menu items available for linking:', Array.from(menuItemMap.keys()));
      
      // Create recipes using the created ingredients
      const recipesToCreate = suggestions.recipes.map((recipe: RecipeSuggestion) => {
        // Look for matching menu item by name
        const matchedMenuItemId = menuItemMap.get(recipe.item_name.toLowerCase());
        if (matchedMenuItemId) {
          console.log(`Found menu item match: ${recipe.item_name} -> ID ${matchedMenuItemId}`);
        } else {
          console.log(`No menu item match for recipe: ${recipe.item_name}`);
        }
        
        return {
          item_name: recipe.item_name,
          menu_item_id: matchedMenuItemId ? matchedMenuItemId.toString() : undefined,
          ingredients: recipe.ingredients.map((ing: SuggestionIngredient) => {
            // Find the created ingredient by name
            const matchedIngredient = ingredientMap.get(ing.ingredient.toLowerCase());
            
            if (!matchedIngredient) {
              console.warn(`Ingredient not found: ${ing.ingredient}`);
              return null;
            }
            
            return {
              ingredient_id: matchedIngredient.ingredient_id,
              quantity: ing.quantity,
              unit: ing.unit
            };
          }).filter(Boolean as any) // Remove any null values
        };
      });

      // Create recipes sequentially to avoid overwhelming the server
      const validRecipes = recipesToCreate.filter(recipe => recipe.ingredients.length > 0);
      const createdRecipes = [];
      
      // Show progress information
      message.info(`Processing ${validRecipes.length} recipes...`);
      
      // Process recipes one at a time
      for (const recipe of validRecipes) {
        try {
          const response = await recipeService.createRecipe(recipe as Omit<RecipeItem, 'date_created' | 'item_id' | 'total_cost'>);
          createdRecipes.push(response);
        } catch (err: any) {
          console.error(`Failed to create recipe ${recipe.item_name}:`, err);
          // Continue with other recipes even if one fails
        }
      }

      // Update state with new data
      setIngredients(createdIngredients);
      setRecipes(createdRecipes);
      message.success('Quick Setup completed successfully!');
      
      // Reset the wizard state
      setCurrentStep(1);
      setMenuItems([]);
      setSuggestions(null);
      
    } catch (error: any) {
      console.error('Quick Setup failed:', error);
      message.error('Failed to complete Quick Setup: ' + (error.message || 'Unknown error'));
    } finally {
      setQuickSetupLoading(false);
      setQuickSetupVisible(false);
      setScreenBlurred(false);
    }
  };

  // Add employee function
  const handleAddEmployee = () => {
    const newEmployee: Employee = {
      name: '',
      pay_type: 'hourly',
      active: true
    };
    setEmployees([...employees, newEmployee]);
  };

  // Delete employee function
  const handleDeleteEmployee = async (employeeId?: number) => {
    try {
      if (employeeId) {
        await otherCostsService.deleteEmployee(employeeId);
        setEmployees(employees.filter(e => e.id !== employeeId));
        message.success('Employee removed successfully');
      } else {
        // If no ID, it's a local-only employee that hasn't been saved
        setEmployees(prevEmployees => prevEmployees.filter(e => e.id !== employeeId));
      }
    } catch (error) {
      message.error('Failed to remove employee');
      console.error(error);
    }
  };

  return (
    <div style={{ maxWidth: '100%', margin: '0 auto', padding: '24px 0px' }}>
      {renderLoadingSpinner()}
      
      {/* Clean Header */}
      <div style={{ marginBottom: 40 }}>
        <Title level={2} style={{ margin: 0, color: '#1f2937', fontWeight: 600 }}>
          Costs
        </Title>
        <Text style={{ color: '#6b7280', fontSize: '16px' }}>
          Track ingredient costs for your menu items to optimize your margin
        </Text>
      </div>
      
      {/* Minimal Tabs */}
      <div style={{ marginBottom: 32 }}>
        <div style={{
          display: 'flex',
          background: 'white',
          borderRadius: '12px',
          padding: '4px',
          border: '1px solid #e5e7eb',
          boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.05)',
          marginBottom: 24
        }}>
          {[
            { key: '1', label: 'Recipes', icon: <AppstoreOutlined /> },
            { key: '2', label: 'Ingredients', icon: <CoffeeOutlined /> },
            { key: '3', label: 'Others', icon: <TagsOutlined /> }
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => handleTabChange(tab.key)}
              style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                padding: '12px 16px',
                background: activeTab === tab.key ? '#f3f4f6' : 'transparent',
                border: 'none',
                borderRadius: '8px',
                color: activeTab === tab.key ? '#1f2937' : '#6b7280',
                fontSize: '14px',
                fontWeight: activeTab === tab.key ? 500 : 400,
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
            >
              {React.cloneElement(tab.icon, { 
                style: { fontSize: '16px' }
              })}
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {activeTab === '1' && (
          <div style={{
            background: 'white',
            borderRadius: '12px',
            border: '1px solid #e5e7eb',
            boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.05)',
            overflow: 'hidden'
          }}>
            {recipesLoading ? (
              <div style={{ textAlign: 'center', padding: '80px' }}>
                <Spin size="large" />
              </div>
            ) : recipes.length > 0 ? (
              <>
                <Table 
                  dataSource={recipes} 
                  columns={recipeColumns} 
                  rowKey="item_id" 
                  pagination={{ pageSize: 10 }}
                  showHeader={true}
                  expandable={{
                    expandedRowRender: (record: RecipeItem) => (
                      <div style={{ padding: '16px', background: '#f9fafb' }}>
                        <Table 
                          dataSource={record.ingredients.map((ing, idx) => ({ key: idx, ...ing }))} 
                          size="small"
                          pagination={false}
                          columns={[
                            {
                              title: 'Ingredient',
                              key: 'ingredient_name',
                              render: (_, record) => {
                                const ingredient = ingredients.find(ing => ing.ingredient_id === record.ingredient_id);
                                return ingredient ? ingredient.ingredient_name : 'Unknown';
                              }
                            },
                            {
                              title: 'Quantity',
                              dataIndex: 'quantity',
                              key: 'quantity'
                            },
                            {
                              title: 'Unit',
                              dataIndex: 'unit',
                              key: 'unit'
                            },
                            {
                              title: 'Price',
                              key: 'calculated_price',
                              render: (_, record) => {
                                const ingredient = ingredients.find(ing => ing.ingredient_id === record.ingredient_id);
                                if (!ingredient || !ingredient.price || !ingredient.quantity) return '$0.00';
                                
                                const baseUnitPrice = ingredient.price / ingredient.quantity;
                                
                                let finalPrice;
                                if (record.unit === ingredient.unit) {
                                  finalPrice = baseUnitPrice * record.quantity;
                                } else {
                                  const conversionFactor = getConversionFactor(ingredient.unit, record.unit);
                                  finalPrice = baseUnitPrice * record.quantity / conversionFactor;
                                }
                                
                                return (
                                  <span style={{ 
                                    color: finalPrice > 0 ? '#1f2937' : '#ef4444',
                                    fontWeight: 500
                                  }}>
                                    ${finalPrice > 0 ? finalPrice.toFixed(2) : '0.00'}
                                  </span>
                                );
                              }
                            }
                          ]}
                          summary={() => {
                            let totalCost = 0;
                            record.ingredients.forEach(ing => {
                              const ingredient = ingredients.find(i => i.ingredient_id === ing.ingredient_id);
                              if (ingredient && ingredient.price && ingredient.quantity) {
                                const baseUnitPrice = ingredient.price / ingredient.quantity;
                                
                                if (ing.unit === ingredient.unit) {
                                  totalCost += baseUnitPrice * ing.quantity;
                                } else {
                                  const conversionFactor = getConversionFactor(ingredient.unit, ing.unit);
                                  totalCost += baseUnitPrice * ing.quantity / conversionFactor;
                                }
                              }
                            });
                            
                            return (
                              <Table.Summary.Row>
                                <Table.Summary.Cell index={0} colSpan={3}>
                                  <Text strong>Total Ingredient Cost:</Text>
                                </Table.Summary.Cell>
                                <Table.Summary.Cell index={1}>
                                  <Text strong style={{ color: '#059669' }}>
                                    ${totalCost.toFixed(2)}
                                  </Text>
                                </Table.Summary.Cell>
                              </Table.Summary.Row>
                            );
                          }}
                        />
                      </div>
                    ),
                  }}
                />
                <div style={{ padding: '16px', borderTop: '1px solid #f3f4f6' }}>
                  <Button 
                    type="text"
                    block 
                    icon={<PlusOutlined />} 
                    onClick={handleAddRecipe}
                    style={{ 
                      height: '48px',
                      color: '#6b7280',
                      border: '2px dashed #e5e7eb',
                      borderRadius: '8px'
                    }}
                  >
                    Add Recipe
                  </Button>
                </div>
              </>
            ) : (
              <div style={{ 
                display: 'flex', 
                flexDirection: 'column', 
                alignItems: 'center', 
                padding: '80px 40px',
                textAlign: 'center'
              }}>
                <div style={{
                  width: '64px',
                  height: '64px',
                  background: '#f3f4f6',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: '24px'
                }}>
                  <CoffeeOutlined style={{ fontSize: '24px', color: '#6b7280' }} />
                </div>
                <Title level={4} style={{ marginBottom: 12, fontWeight: 600 }}>
                  Track Your Recipes
                </Title>
                <Text style={{ 
                  color: '#6b7280', 
                  fontSize: '16px',
                  marginBottom: 16,
                  display: 'block',
                  maxWidth: '400px'
                }}>
                  Track your recipes and ingredient costs to optimize your menu pricing
                </Text>
                <Text style={{ 
                  color: '#9ca3af', 
                  fontSize: '14px',
                  display: 'block',
                  marginBottom: 32
                }}>
                  Our AI assistant can help you set up all your recipes in just a few clicks
                </Text>
                <Button 
                  type="primary" 
                  size="large"
                  onClick={handleQuickSetup}
                  style={{
                    height: '48px',
                    paddingLeft: '24px',
                    paddingRight: '24px',
                    fontSize: '15px',
                    fontWeight: 500,
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    border: 'none',
                    borderRadius: '8px',
                    boxShadow: '0 4px 14px 0 rgba(102, 126, 234, 0.4)'
                  }}
                >
                  Quick Setup with AI
                </Button>
              </div>
            )}
          </div>
        )}

        {activeTab === '2' && (
          <div style={{
            background: 'white',
            borderRadius: '12px',
            border: '1px solid #e5e7eb',
            boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.05)',
            overflow: 'hidden'
          }}>
            {ingredientsLoading ? (
              <div style={{ textAlign: 'center', padding: '80px' }}>
                <Spin size="large" />
              </div>
            ) : ingredients.length > 0 ? (
              <>
                <Table 
                  dataSource={ingredients} 
                  columns={ingredientColumns} 
                  rowKey="ingredient_id" 
                  pagination={{ pageSize: 10 }}
                  showHeader={true}
                />
                <div style={{ padding: '16px', borderTop: '1px solid #f3f4f6' }}>
                  <Button 
                    type="text"
                    block 
                    icon={<PlusOutlined />} 
                    onClick={handleAddIngredient}
                    style={{ 
                      height: '48px',
                      color: '#6b7280',
                      border: '2px dashed #e5e7eb',
                      borderRadius: '8px'
                    }}
                  >
                    Add Ingredient
                  </Button>
                </div>
              </>
            ) : (
              <div style={{ 
                display: 'flex', 
                flexDirection: 'column', 
                alignItems: 'center', 
                padding: '80px 40px',
                textAlign: 'center'
              }}>
                <div style={{
                  width: '64px',
                  height: '64px',
                  background: '#f3f4f6',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: '24px'
                }}>
                  <DollarOutlined style={{ fontSize: '24px', color: '#6b7280' }} />
                </div>
                <Title level={4} style={{ marginBottom: 12, fontWeight: 600 }}>
                  Add Your Ingredients
                </Title>
                <Text style={{ 
                  color: '#6b7280', 
                  fontSize: '16px',
                  marginBottom: 16,
                  display: 'block',
                  maxWidth: '400px'
                }}>
                  Add ingredients to start tracking your food costs
                </Text>
                <Text style={{ 
                  color: '#9ca3af', 
                  fontSize: '14px',
                  display: 'block',
                  marginBottom: 32
                }}>
                  Our AI can automatically set up ingredients based on your menu
                </Text>
                <Button 
                  type="primary" 
                  size="large"
                  icon={<ThunderboltOutlined />} 
                  onClick={handleQuickSetup}
                  style={{
                    height: '48px',
                    paddingLeft: '24px',
                    paddingRight: '24px',
                    fontSize: '15px',
                    fontWeight: 500,
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    border: 'none',
                    borderRadius: '8px',
                    boxShadow: '0 4px 14px 0 rgba(102, 126, 234, 0.4)'
                  }}
                >
                  Quick Setup with AI
                </Button>
              </div>
            )}
          </div>
        )}

        {activeTab === '3' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            {/* Fixed Monthly Costs */}
            <div style={{
              background: 'white',
              borderRadius: '12px',
              border: '1px solid #e5e7eb',
              boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.05)',
              overflow: 'hidden'
            }}>
              <div style={{ 
                padding: '24px',
                borderBottom: '1px solid #f3f4f6',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <Title level={4} style={{ margin: 0, color: '#1f2937' }}>
                  Fixed Monthly Costs
                </Title>
                <Button 
                  type="primary" 
                  icon={<SaveOutlined />} 
                  onClick={saveAllCosts} 
                  loading={savingAllCosts}
                  style={{
                    background: '#9370DB',
                    border: 'none',
                    borderRadius: '8px',
                    fontWeight: 500
                  }}
                >
                  Save All Costs
                </Button>
              </div>
              <div style={{ padding: '24px' }}>
                <Spin spinning={otherCostsLoading}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
                    <div>
                      <Text strong style={{ color: '#374151', display: 'block', marginBottom: '8px' }}>
                        Monthly Rent
                      </Text>
                      <InputNumber
                        style={{ width: '100%', height: '40px' }}
                        prefix="$"
                        min={0}
                        value={rent}
                        onChange={value => setRent(value)}
                        formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                        parser={value => value ? Number(value.replace(/\$\s?|(,*)/g, '')) : 0}
                        placeholder="0"
                      />
                    </div>
                    <div>
                      <Text strong style={{ color: '#374151', display: 'block', marginBottom: '8px' }}>
                        Monthly Utilities
                      </Text>
                      <InputNumber
                        style={{ width: '100%', height: '40px' }}
                        prefix="$"
                        min={0}
                        value={utilities}
                        onChange={value => setUtilities(value)}
                        formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                        parser={value => value ? Number(value.replace(/\$\s?|(,*)/g, '')) : 0}
                        placeholder="0"
                      />
                    </div>
                  </div>
                </Spin>
              </div>
            </div>

            {/* Employee Costs */}
            <div style={{
              background: 'white',
              borderRadius: '12px',
              border: '1px solid #e5e7eb',
              boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.05)',
              overflow: 'hidden'
            }}>
              <div style={{ 
                padding: '24px',
                borderBottom: '1px solid #f3f4f6'
              }}>
                <Title level={4} style={{ margin: 0, color: '#1f2937' }}>
                  Employee Costs
                </Title>
              </div>
              <div style={{ padding: '24px' }}>
                <Spin spinning={otherCostsLoading}>
                  {employees.length === 0 ? (
                    <div style={{ 
                      display: 'flex', 
                      flexDirection: 'column', 
                      alignItems: 'center', 
                      padding: '40px',
                      textAlign: 'center'
                    }}>
                      <div style={{
                        width: '48px',
                        height: '48px',
                        background: '#f3f4f6',
                        borderRadius: '50%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        marginBottom: '16px'
                      }}>
                        <UserOutlined style={{ fontSize: '20px', color: '#6b7280' }} />
                      </div>
                      <Text style={{ color: '#6b7280' }}>No employees added yet</Text>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                      {employees.map((employee, index) => (
                        <div
                          key={index}
                          style={{
                            border: '1px solid #e5e7eb',
                            borderRadius: '8px',
                            padding: '20px'
                          }}
                        >
                          <div style={{ 
                            display: 'flex', 
                            justifyContent: 'space-between', 
                            alignItems: 'center',
                            marginBottom: '16px'
                          }}>
                            <Text strong style={{ fontSize: '16px' }}>
                              Employee {index + 1}{employee.name ? ': ' + employee.name : ''}
                            </Text>
                            <Button 
                              type="text" 
                              danger 
                              icon={<DeleteOutlined />} 
                              onClick={() => handleDeleteEmployee(employee.id)}
                              style={{ color: '#ef4444' }}
                            />
                          </div>
                          
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                            <div>
                              <Text strong style={{ color: '#374151', display: 'block', marginBottom: '8px' }}>
                                Employee Name
                              </Text>
                              <Input 
                                placeholder="Enter employee name"
                                value={employee.name}
                                onChange={(e) => {
                                  const newEmployees = [...employees];
                                  newEmployees[index] = { ...employee, name: e.target.value };
                                  setEmployees(newEmployees);
                                }}
                                style={{ height: '40px' }}
                              />
                            </div>
                            
                            <div>
                              <Text strong style={{ color: '#374151', display: 'block', marginBottom: '8px' }}>
                                Pay Type
                              </Text>
                              <Radio.Group 
                                value={employee.pay_type}
                                onChange={e => {
                                  const newEmployees = [...employees];
                                  newEmployees[index] = { ...employee, pay_type: e.target.value };
                                  setEmployees(newEmployees);
                                }}
                                style={{ display: 'flex', gap: '16px' }}
                              >
                                <Radio value="salary">Yearly Salary</Radio>
                                <Radio value="hourly">Hourly Rate</Radio>
                              </Radio.Group>
                            </div>
                            
                            {employee.pay_type === 'salary' ? (
                              <div>
                                <Text strong style={{ color: '#374151', display: 'block', marginBottom: '8px' }}>
                                  Yearly Salary
                                </Text>
                                <InputNumber
                                  style={{ width: '100%', height: '40px' }}
                                  placeholder="Enter yearly salary"
                                  prefix="$"
                                  min={0}
                                  value={employee.salary}
                                  onChange={value => {
                                    const newEmployees = [...employees];
                                    newEmployees[index] = { ...employee, salary: value as number };
                                    setEmployees(newEmployees);
                                  }}
                                  formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                                  parser={value => value ? Number(value.replace(/\$\s?|(,*)/g, '')) : 0}
                                />
                              </div>
                            ) : (
                              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                                <div>
                                  <Text strong style={{ color: '#374151', display: 'block', marginBottom: '8px' }}>
                                    Hourly Rate
                                  </Text>
                                  <InputNumber
                                    style={{ width: '100%', height: '40px' }}
                                    placeholder="Enter hourly rate"
                                    prefix="$"
                                    min={0}
                                    value={employee.hourly_rate}
                                    onChange={value => {
                                      const newEmployees = [...employees];
                                      newEmployees[index] = { ...employee, hourly_rate: value as number };
                                      setEmployees(newEmployees);
                                    }}
                                    formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                                    parser={value => value ? Number(value.replace(/\$\s?|(,*)/g, '')) : 0}
                                  />
                                </div>
                                <div>
                                  <Text strong style={{ color: '#374151', display: 'block', marginBottom: '8px' }}>
                                    Weekly Hours
                                  </Text>
                                  <InputNumber
                                    style={{ width: '100%', height: '40px' }}
                                    placeholder="Enter weekly hours"
                                    min={0}
                                    max={168}
                                    value={employee.weekly_hours}
                                    onChange={value => {
                                      const newEmployees = [...employees];
                                      newEmployees[index] = { ...employee, weekly_hours: value as number };
                                      setEmployees(newEmployees);
                                    }}
                                  />
                                </div>
                              </div>
                            )}
                            
                            {employee.pay_type === 'hourly' && employee.hourly_rate && employee.weekly_hours && (
                              <div style={{ 
                                padding: '12px',
                                background: '#f0f9ff',
                                borderRadius: '6px',
                                border: '1px solid #bae6fd'
                              }}>
                                <Text strong style={{ color: '#0c4a6e' }}>Estimated Monthly Cost: </Text>
                                <Text style={{ color: '#0c4a6e' }}>
                                  ${((employee.hourly_rate * employee.weekly_hours * 52) / 12).toFixed(2)}
                                </Text>
                              </div>
                            )}
                            
                            {employee.pay_type === 'salary' && employee.salary && (
                              <div style={{ 
                                padding: '12px',
                                background: '#f0f9ff',
                                borderRadius: '6px',
                                border: '1px solid #bae6fd'
                              }}>
                                <Text strong style={{ color: '#0c4a6e' }}>Monthly Cost: </Text>
                                <Text style={{ color: '#0c4a6e' }}>
                                  ${(employee.salary / 12).toFixed(2)}
                                </Text>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </Spin>
                
                <button
                  onClick={handleAddEmployee}
                  style={{
                    width: '100%',
                    marginTop: '16px',
                    padding: '20px',
                    background: 'transparent',
                    border: '2px dashed #e5e7eb',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    color: '#6b7280',
                    fontSize: '14px',
                    transition: 'all 0.2s ease'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = '#9ca3af';
                    e.currentTarget.style.background = '#f9fafb';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = '#e5e7eb';
                    e.currentTarget.style.background = 'transparent';
                  }}
                >
                  <PlusOutlined style={{ fontSize: '16px' }} />
                  Add New Employee
                </button>
                
                {employees.length > 0 && (
                  <div style={{ 
                    marginTop: '24px',
                    padding: '20px',
                    background: '#f9fafb',
                    borderRadius: '8px',
                    border: '1px solid #e5e7eb'
                  }}>
                    <Text strong style={{ fontSize: '16px', color: '#1f2937', display: 'block', marginBottom: '8px' }}>
                      Total Monthly Employee Costs
                    </Text>
                    <Text style={{ fontSize: '24px', fontWeight: 600, color: '#059669' }}>
                      ${employees.reduce((sum, emp) => {
                        if (emp.pay_type === 'salary' && emp.salary) {
                          return sum + (emp.salary / 12);
                        } else if (emp.pay_type === 'hourly' && emp.hourly_rate && emp.weekly_hours) {
                          return sum + ((emp.hourly_rate * emp.weekly_hours * 52) / 12);
                        }
                        return sum;
                      }, 0).toFixed(2)}
                    </Text>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
      
      {/* All Modals - keeping original functionality */}
      <RecipeModal
        visible={recipeModalVisible}
        onCancel={() => setRecipeModalVisible(false)}
        onSave={handleSaveRecipe}
        recipe={selectedRecipe}
        ingredients={ingredients}
        menuItems={menuItemsForRecipes}
        isNew={isNewRecipe}
      />
      
      <Modal
        title={`Recipe Details: ${selectedRecipe?.item_name || ''}`}
        open={recipeDetailsVisible}
        onCancel={() => setRecipeDetailsVisible(false)}
        footer={[
          <Button key="close" onClick={() => setRecipeDetailsVisible(false)}>
            Close
          </Button>
        ]}
      >
        {selectedRecipe && (
          <div>
            <p><strong>Item Name:</strong> {selectedRecipe?.item_name}</p>
            <p><strong>Date Created:</strong> {selectedRecipe?.date_created}</p>
            <p><strong>Ingredients:</strong></p>
            <ul>
              {selectedRecipe?.ingredients?.map(ing => {
                const ingredientDetails = ingredients.find(i => i.ingredient_id === ing.ingredient_id);
                return (
                  <li key={ing.ingredient_id}>
                    {ingredientDetails?.ingredient_name || 'Unknown'}: {ing.quantity} {ing.unit}
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </Modal>
      
      <IngredientModal
        visible={ingredientModalVisible}
        onCancel={() => setIngredientModalVisible(false)}
        onSave={handleSaveIngredient}
        ingredient={selectedIngredient}
        isNew={isNewIngredient}
      />
      
      <Modal
        title={`Quick Setup - ${currentStep === 1 ? 'Enter Menu Items' : currentStep === 2 ? 'Review Suggestions' : 'Finalizing Setup'}`}
        open={quickSetupVisible}
        onCancel={handleQuickSetupCancel}
        footer={[
          <Button key="cancel" onClick={handleQuickSetupCancel}>
            Cancel
          </Button>,
          currentStep > 1 && (
            <Button key="prev" onClick={handlePreviousStep}>
              Previous
            </Button>
          ),
          currentStep === 1 ? (
            <Button
              key="next"
              type="primary"
              onClick={generateAiSuggestions}
              loading={generatingAiSuggestions}
            >
              Generate Suggestions
            </Button>
          ) : currentStep === 2 ? (
            <Button
              key="next"
              type="primary"
              onClick={() => setCurrentStep(3)}
            >
              Next
            </Button>
          ) : (
            <Button
              key="submit"
              type="primary"
              onClick={handleQuickSetupSubmit}
              loading={quickSetupLoading}
            >
              Finish Setup
            </Button>
          )
        ].filter(Boolean)}
        width={1000}
      >
        {/* All the modal content exactly as before */}
        {currentStep === 1 && (
          <>
            <div className="menu-input-container">
              <Alert
                message="Review Your Menu Items"
                description="We've loaded items from your POS system. Review and make any necessary changes before generating recipe suggestions."
                type="info"
                showIcon
                style={{ marginBottom: 20 }}
              />
              <Table
                dataSource={menuItems.map((item, idx) => ({ ...item, key: idx.toString() }))}
                pagination={false}
                bordered
                size="middle"
                style={{ marginBottom: 16 }}
                columns={[
                  {
                    title: 'Item Name',
                    dataIndex: 'name',
                    key: 'name',
                    width: '30%',
                    render: (text: string, record: any, index: number) => (
                      <Input
                        value={text}
                        onChange={(e) => handleMenuItemChange(index, 'name', e.target.value)}
                        placeholder="Enter item name"
                      />
                    ),
                  },
                  {
                    title: 'Description',
                    dataIndex: 'description',
                    key: 'description',
                    width: '40%',
                    render: (text: string, record: any, index: number) => (
                      <Input
                        value={text || ''}
                        onChange={(e) => handleMenuItemChange(index, 'description', e.target.value)}
                        placeholder="Optional description"
                      />
                    ),
                  },
                  {
                    title: 'Price ($)',
                    dataIndex: 'price',
                    key: 'price',
                    width: '15%',
                    render: (text: number, record: any, index: number) => (
                      <Input
                        type="number"
                        min={0}
                        step={0.01}
                        value={text || ''}
                        onChange={(e) => handleMenuItemChange(index, 'price', parseFloat(e.target.value) || 0)}
                        placeholder="0.00"
                      />
                    ),
                  },
                  {
                    title: 'Action',
                    key: 'action',
                    width: '10%',
                    render: (_, record: any, index: number) => (
                      <Button
                        type="text"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={() => removeMenuItem(index)}
                      />
                    ),
                  },
                ]}
              />
            </div>
            <Button 
              type="dashed" 
              onClick={addMenuItem} 
              block 
              icon={<PlusOutlined />}
              style={{ marginTop: 16 }}
            >
              Add Menu Item
            </Button>
            
            <div style={{ marginTop: 24, backgroundColor: '#f6ffed', border: '1px solid #b7eb8f', padding: 12, borderRadius: 4 }}>
              <Text>
                We'll analyze your menu items and suggest appropriate ingredients and recipes for each item.
                You can review and edit the suggestions in the next step.
              </Text>
            </div>
          </>
        )}

        {currentStep === 2 && suggestions && (
          <>
            <div style={{ marginBottom: 16 }}>
              <Title level={4}>Review Suggested Recipes</Title>
              <Text>We've analyzed your menu and generated recipe suggestions. Review and edit each recipe and its ingredients below.</Text>
            </div>
            
            {suggestions.recipes.map((recipe: RecipeSuggestion, recipeIndex: number) => {
              return (
                <div key={recipeIndex} className="recipe-suggestion" style={{ marginBottom: 24, border: '1px solid #f0f0f0', padding: 16, borderRadius: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', marginBottom: 16 }}>
                    <Title level={5} style={{ margin: 0, marginRight: 16 }}>Recipe:</Title>
                    <Input 
                      value={recipe.item_name}
                      style={{ fontWeight: 'bold', fontSize: '16px' }}
                      onChange={(e) => {
                        const updatedSuggestions = {...suggestions};
                        updatedSuggestions.recipes[recipeIndex].item_name = e.target.value;
                        setSuggestions(updatedSuggestions);
                      }}
                    />
                  </div>
                  
                  <div style={{ marginBottom: 12 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                      <Text strong>Ingredients:</Text>
                      <Button 
                        type="link" 
                        onClick={() => {
                          const updatedSuggestions = {...suggestions};
                          const existingIngredients = Array.from(
                            new Set(
                              suggestions.recipes.flatMap(r => 
                                r.ingredients.map(ing => ing.ingredient)
                              )
                            )
                          );
                          
                          updatedSuggestions.recipes[recipeIndex].ingredients.push({
                            ingredient: existingIngredients.length > 0 ? '' : 'New Ingredient',
                            quantity: 1,
                            unit: 'each'
                          });
                          setSuggestions(updatedSuggestions);
                        }}
                        icon={<PlusOutlined />}
                        size="small"
                      >
                        Add Ingredient
                      </Button>
                    </div>
                    
                    <Table
                      dataSource={recipe.ingredients.map((ing, idx) => ({ ...ing, key: idx.toString() }))}
                      pagination={false}
                      size="small"
                      style={{ marginBottom: 16 }}
                      columns={[
                        {
                          title: 'Ingredient',
                          dataIndex: 'ingredient',
                          key: 'ingredient',
                          width: '50%',
                          render: (text: string, record: any, index: number) => {
                            const allIngredients = Array.from(
                              new Set(
                                suggestions.recipes.flatMap(r => 
                                  r.ingredients.map(ing => ing.ingredient)
                                )
                              )
                            ).filter(Boolean);
                            
                            return (
                              <AutoComplete
                                value={text}
                                style={{ width: '100%' }}
                                options={allIngredients.map(ing => ({ value: ing }))}
                                filterOption={(inputValue, option) =>
                                  option!.value.toUpperCase().indexOf(inputValue.toUpperCase()) !== -1
                                }
                                onChange={(value) => {
                                  const updatedSuggestions = {...suggestions};
                                  updatedSuggestions.recipes[recipeIndex].ingredients[index].ingredient = value;
                                  setSuggestions(updatedSuggestions);
                                }}
                                placeholder="Enter or select an ingredient"
                              />
                            );
                          }
                        },
                        {
                          title: 'Quantity',
                          dataIndex: 'quantity',
                          key: 'quantity',
                          width: '20%',
                          render: (quantityValue: number, record: any, rowIndex: number) => (
                            <Input
                              type="number"
                              min={0}
                              step={0.01}
                              value={quantityValue}
                              onChange={(e) => {
                                const updatedSuggestions = {...suggestions};
                                updatedSuggestions.recipes[recipeIndex].ingredients[rowIndex].quantity = parseFloat(e.target.value) || 0;
                                setSuggestions(updatedSuggestions);
                              }}
                            />
                          )
                        },
                        {
                          title: 'Unit',
                          dataIndex: 'unit',
                          key: 'unit',
                          width: '20%',
                          render: (unitValue: string, record: any, rowIndex: number) => {
                            const units = [
                              'g', 'kg', 'oz', 'lb', 'ml', 'l', 'cup', 'tbsp', 'tsp', 'ea', 'pieces', 'bunch', 'pinch'
                            ];
                            
                            return (
                              <Select
                                value={unitValue}
                                style={{ width: '100%' }}
                                onChange={(value: string) => {
                                  const updatedSuggestions = {...suggestions};
                                  if (updatedSuggestions.recipes[recipeIndex] && 
                                      updatedSuggestions.recipes[recipeIndex].ingredients[rowIndex]) {
                                    updatedSuggestions.recipes[recipeIndex].ingredients[rowIndex].unit = value;
                                    setSuggestions(updatedSuggestions);
                                  }
                                }}
                                showSearch
                                allowClear
                                placeholder="Select unit"
                              >
                                {units.map((unit: string) => (
                                  <Select.Option key={unit} value={unit}>{unit}</Select.Option>
                                ))}
                              </Select>
                            );
                          }
                        },
                        {
                          title: 'Action',
                          key: 'action',
                          width: '10%',
                          render: (_: any, record: any, rowIndex: number) => (
                            <Button
                              type="text"
                              danger
                              icon={<DeleteOutlined />}
                              onClick={() => {
                                const updatedSuggestions = {...suggestions};
                                updatedSuggestions.recipes[recipeIndex].ingredients.splice(rowIndex, 1);
                                setSuggestions(updatedSuggestions);
                              }}
                            />
                          )
                        }
                      ]}
                    />
                  </div>
                </div>
              );
            })}
            
            <div style={{ textAlign: 'center', margin: '16px 0' }}>
              <Button
                type="dashed"
                onClick={() => {
                  const updatedSuggestions = {...suggestions};
                  updatedSuggestions.recipes.push({
                    item_name: 'New Recipe',
                    ingredients: []
                  });
                  setSuggestions(updatedSuggestions);
                }}
                icon={<PlusOutlined />}
              >
                Add New Recipe
              </Button>
            </div>

            <div style={{ marginTop: 24, backgroundColor: '#f0f8ff', border: '1px solid #bae7ff', padding: 12, borderRadius: 4 }}>
              <Text>
                The suggestions are generated based on your menu items. In the next step, we'll create these ingredients and recipes in your account.
                You can always modify them later.
              </Text>
            </div>
          </>
        )}

        {currentStep === 3 && suggestions && (
          <>
            <div style={{ marginBottom: 16 }}>
              <Title level={4}>Set Up Your Ingredients</Title>
              <Text>Set the price, quantity, and unit for each unique ingredient below. These values will be used for cost calculations.</Text>
            </div>
                <Table
                  dataSource={
                    (() => {
                      if (suggestions && baseIngredients.length === 0) {
                        const uniqueIngredients = Array.from(
                          new Map(
                            suggestions.recipes.flatMap(recipe => 
                              recipe.ingredients.map(ing => [
                                ing.ingredient.toLowerCase(), 
                                { 
                                  ingredient_name: ing.ingredient, 
                                  unit: ing.unit,
                                  quantity: ing.quantity || 100,
                                  price: ing.price || 0,
                                  unit_price: 0
                                }
                              ])
                            )
                          ).values()
                        );
                        
                        if (uniqueIngredients.length > 0 && baseIngredients.length === 0) {
                          setBaseIngredients(uniqueIngredients);
                        }
                      }
                      
                      return baseIngredients.map((ing, idx) => ({ key: idx, ...ing }));
                    })()
                  }
                  columns={[
                    {
                      title: 'Ingredient Name',
                      dataIndex: 'ingredient_name',
                      key: 'ingredient_name',
                      render: (text: string, record: any) => (
                        <Input
                          value={text}
                          onChange={(e) => {
                            const updatedBaseIngredients = baseIngredients.map(ing => 
                              ing.ingredient_name === text 
                                ? { ...ing, ingredient_name: e.target.value }
                                : ing
                            );
                            setBaseIngredients(updatedBaseIngredients);
                            
                            const updatedSuggestions = {...suggestions};
                            updatedSuggestions.recipes = updatedSuggestions.recipes.map(recipe => ({
                              ...recipe,
                              ingredients: recipe.ingredients.map(ing => 
                                ing.ingredient === text 
                                  ? { ...ing, ingredient: e.target.value }
                                  : ing
                              )
                            }));
                            setSuggestions(updatedSuggestions);
                          }}
                        />
                      ),
                    },
                    {
                      title: 'Price ($)',
                      key: 'price',
                      dataIndex: 'price',
                      render: (price: number, record: any) => (
                        <Input
                          type="number"
                          min={0}
                          step={0.01}
                          defaultValue={price || 0}
                          prefix="$"
                          onChange={(e) => {
                            let inputVal = e.target.value;
                            const newPrice = inputVal === '' ? 0 : parseFloat(inputVal) || 0;
                            
                            const updatedBaseIngredients = baseIngredients.map(ing => 
                              ing.ingredient_name === record.ingredient_name 
                                ? { ...ing, price: newPrice }
                                : ing
                            );
                            setBaseIngredients(updatedBaseIngredients);
                          }}
                        />
                      ),
                    },
                    {
                      title: 'Quantity',
                      key: 'quantity',
                      dataIndex: 'quantity',
                      render: (quantity: number, record: any) => (
                        <Input
                          type="number"
                          min={0}
                          step={0.01}
                          defaultValue={quantity || 100}
                          onChange={(e) => {
                            let inputVal = e.target.value;
                            const newQuantity = inputVal === '' ? 0 : parseFloat(inputVal) || 0;
                            
                            const updatedBaseIngredients = baseIngredients.map(ing => 
                              ing.ingredient_name === record.ingredient_name 
                                ? { ...ing, quantity: newQuantity }
                                : ing
                            );
                            setBaseIngredients(updatedBaseIngredients);
                          }}
                        />
                      ),
                    },
                    {
                      title: 'Unit',
                      dataIndex: 'unit',
                      key: 'unit',
                      render: (text: string, record: any) => {
                        const commonUnits = [
                          'each', 'gram', 'kg', 'oz', 'lb', 'cup', 'tbsp', 'tsp', 
                          'ml', 'l', 'gallon', 'quart', 'pint', 'slice', 'piece', 
                          'bunch', 'pinch', 'dash', 'clove', 'leaf', 'sprig'
                        ];
                        
                        return (
                          <Select
                            value={text}
                            style={{ width: '100%' }}
                            onChange={(value) => {
                              const updatedBaseIngredients = baseIngredients.map(ing => 
                                ing.ingredient_name === record.ingredient_name 
                                  ? { ...ing, unit: value }
                                  : ing
                              );
                              setBaseIngredients(updatedBaseIngredients);
                            }}
                            showSearch
                            allowClear
                            placeholder="Select unit"
                          >
                            {commonUnits.map((unit) => (
                              <Select.Option key={unit} value={unit}>{unit}</Select.Option>
                            ))}
                          </Select>
                        );
                      },
                    }
                  ]}
                  pagination={false}
                  size="small"
                />
          </>
        )}
      </Modal>
      
      {/* Blur overlay when Quick Setup is active */}
      {screenBlurred && (
        <div 
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            width: '100vw',
            height: '100vh',
            backgroundColor: 'rgba(255, 255, 255, 0.8)',
            backdropFilter: 'blur(5px)',
            zIndex: 999,
            pointerEvents: 'none',
          }}
        />
      )}
    </div>
  );
};

export default Costs;
