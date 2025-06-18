import React, { useState, useEffect } from 'react';
import { Card, Table, Typography, Space, Button, Empty, Spin, message, Tabs, Modal, Tooltip, Input, Alert, List, Statistic, AutoComplete, Select } from 'antd';
import { PlusOutlined, DollarOutlined, CoffeeOutlined, AppstoreOutlined, ExclamationCircleOutlined, ThunderboltOutlined, DeleteOutlined } from '@ant-design/icons';
import * as recipeService from '../../services/recipeService';
import { generateSuggestionsFromMenu } from '../../services/recipeService';
import itemService from '../../services/itemService';
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
      'quart': 946.353,
      'quarts': 946.353,
      'pint': 473.176,
      'pints': 473.176
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
  const [activeTab, setActiveTab] = useState<string>('1');
  
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
  useEffect(() => {
    const fetchRecipes = async () => {
      try {
        const data = await recipeService.getRecipes();
        setRecipes(data);
      } catch (error) {
        console.error('Failed to fetch recipes:', error);
        message.error('Failed to load recipes');
      } finally {
        setRecipesLoading(false);
      }
    };
    
    fetchRecipes();
  }, []);

  // Fetch ingredient data
  useEffect(() => {
    const fetchIngredients = async () => {
      try {
        const data = await recipeService.getIngredients();
        setIngredients(data);
      } catch (error) {
        console.error('Failed to fetch ingredients:', error);
        message.error('Failed to load ingredients');
      } finally {
        setIngredientsLoading(false);
      }
    };
    
    fetchIngredients();
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
      render: (_: any, record: RecipeItem) => (
        <Space size="middle">
          <Button type="link" onClick={() => handleEditRecipe(record)}>Edit</Button>
          <Button type="link" danger onClick={() => handleDeleteRecipe(record)}>Delete</Button>
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
      render: (_: any, record: IngredientItem) => (
        <Space size="middle">
          <Button type="link" onClick={() => handleEditIngredient(record)}>Edit</Button>
          <Button type="link" danger onClick={() => handleDeleteIngredient(record)}>Delete</Button>
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
    showQuickSetupModal();
  };
  
  // Function to show the quick setup modal
  const showQuickSetupModal = async () => {
    setQuickSetupLoading(true);
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
    } catch (error) {
      console.error('Error fetching menu items:', error);
      message.error('Could not load menu items. Starting with empty list.');
      setMenuItems([]);
    } finally {
      setQuickSetupLoading(false);
      setCurrentStep(1);
      setQuickSetupVisible(true);
      setScreenBlurred(true);
    }
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
      
      // Create all unique ingredients
      const createdIngredients = await Promise.all(
        Array.from(uniqueIngredients.values()).map(async (ingredient) => {
          const response = await recipeService.createIngredient(ingredient);
          return response;
        })
      );

      // Create ingredient map for easy lookup by name
      const ingredientMap = new Map();
      createdIngredients.forEach(ingredient => {
        ingredientMap.set(ingredient.ingredient_name.toLowerCase(), ingredient);
      });

      // Create recipes using the created ingredients
      const recipesToCreate = suggestions.recipes.map((recipe: RecipeSuggestion) => ({
        item_name: recipe.item_name,
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
      }));

      // Create all recipes
      const createdRecipes = await Promise.all(
        recipesToCreate
          .filter(recipe => recipe.ingredients.length > 0)
          .map(async (recipe) => {
            const response = await recipeService.createRecipe(recipe as Omit<RecipeItem, 'date_created' | 'item_id' | 'total_cost'>);
            return response;
          })
      );

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

  return (
    <div>
      <Tabs activeKey={activeTab} onChange={handleTabChange} style={{ marginBottom: 20 }}>
        <TabPane
          tab={<span><AppstoreOutlined /> Recipes</span>}
          key="1"
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20 }}>
            <Title level={3}>Menu Item Recipes</Title>
            <Button 
              type="primary" 
              icon={<PlusOutlined />} 
              onClick={handleAddRecipe}
            >
              Add Recipe
            </Button>
          </div>

          <Card>
            {recipesLoading ? (
              <div style={{ textAlign: 'center', padding: '50px' }}>
                <Spin size="large" />
              </div>
            ) : recipes.length > 0 ? (
              <Table 
                dataSource={recipes} 
                columns={recipeColumns} 
                rowKey="item_id" 
                pagination={{ pageSize: 10 }}
                expandable={{
                  expandedRowRender: (record: RecipeItem) => (
                    <div style={{ padding: '8px 0' }}>
                      <div>
                        <Table 
                          dataSource={record.ingredients.map((ing, idx) => ({ key: idx, ...ing }))} 
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
                                // Find the base ingredient
                                const ingredient = ingredients.find(ing => ing.ingredient_id === record.ingredient_id);
                                if (!ingredient || !ingredient.price || !ingredient.quantity) return '$0.00';
                                
                                // Calculate the unit price for the base ingredient (price per unit)
                                const baseUnitPrice = ingredient.price / ingredient.quantity;
                                
                                let finalPrice;
                                // Check if units need conversion
                                if (record.unit === ingredient.unit) {
                                  // No conversion needed, simple multiplication
                                  finalPrice = baseUnitPrice * record.quantity;
                                } else {
                                  // Handle unit conversions
                                  const conversionFactor = getConversionFactor(ingredient.unit, record.unit);
                                  // When converting from larger to smaller units, we divide by conversion factor
                                  // e.g., if ingredient is in kg but recipe uses g, conversion factor is 1000/1 = 1000
                                  // so we calculate: (price per kg) * (grams / 1000) = price for the grams used
                                  finalPrice = baseUnitPrice * record.quantity / conversionFactor;
                                }
                                
                                return (
                                  <span style={{ color: finalPrice > 0 ? 'inherit' : 'red' }}>
                                    ${finalPrice > 0 ? finalPrice.toFixed(2) : '0.00'}
                                  </span>
                                );
                              }
                            }
                          ]}
                          pagination={false}
                          size="small"
                          summary={() => {
                            // Calculate total ingredient cost
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
                                  Total Ingredient Cost:
                                </Table.Summary.Cell>
                                <Table.Summary.Cell index={1}>
                                  ${totalCost.toFixed(2)}
                                </Table.Summary.Cell>
                              </Table.Summary.Row>
                            );
                          }}
                        />
                      </div>
                    </div>
                  ),
                }}
              />
            ) : (
              <Empty 
                description="No recipes recorded yet"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              >
                <Button 
                  type="primary" 
                  icon={<ThunderboltOutlined />} 
                  onClick={handleQuickSetup}
                >
                  Quick Setup
                </Button>
              </Empty>
            )}
          </Card>
        </TabPane>

        <TabPane
          tab={<span><CoffeeOutlined /> Ingredients</span>}
          key="2"
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20 }}>
            <Title level={3}>Ingredient Management</Title>
            <Button 
              type="primary" 
              icon={<PlusOutlined />} 
              onClick={handleAddIngredient}
            >
              Add Ingredient
            </Button>
          </div>

          <Card>
            {ingredientsLoading ? (
              <div style={{ textAlign: 'center', padding: '50px' }}>
                <Spin size="large" />
              </div>
            ) : ingredients.length > 0 ? (
              <Table 
                dataSource={ingredients} 
                columns={ingredientColumns} 
                rowKey="ingredient_id" 
                pagination={{ pageSize: 10 }}
              />
            ) : (
              <Empty 
                description="No ingredients recorded yet"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              >
                <Button 
                  type="primary" 
                  icon={<ThunderboltOutlined />} 
                  onClick={handleQuickSetup}
                >
                  Quick Setup
                </Button>
              </Empty>
            )}
          </Card>
        </TabPane>
      </Tabs>
      
      {/* Recipe Modal */}
      <RecipeModal
        visible={recipeModalVisible}
        onCancel={() => setRecipeModalVisible(false)}
        onSave={handleSaveRecipe}
        recipe={selectedRecipe}
        ingredients={ingredients}
        isNew={isNewRecipe}
      />
      
      {/* View Recipe Details Modal */}
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
            <p><strong>Item Name:</strong> {selectedRecipe.item_name}</p>
            <p><strong>Date Created:</strong> {selectedRecipe.date_created}</p>
            <p><strong>Ingredients:</strong></p>
            <ul>
              {selectedRecipe.ingredients.map(ing => {
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
      
      {/* Ingredient Modal */}
      <IngredientModal
        visible={ingredientModalVisible}
        onCancel={() => setIngredientModalVisible(false)}
        onSave={handleSaveIngredient}
        ingredient={selectedIngredient}
        isNew={isNewIngredient}
      />
      
      {/* Quick Setup Modal */}
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
                        type="link"
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
                          // Get all unique ingredients already in use
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
                            // Get all unique ingredients from all recipes
                            const allIngredients = Array.from(
                              new Set(
                                suggestions.recipes.flatMap(r => 
                                  r.ingredients.map(ing => ing.ingredient)
                                )
                              )
                            ).filter(Boolean); // Filter out any null or empty strings
                            
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
                             // Define units for dropdown selection
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
                              type="link"
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
              <Title level={4}>Ready to Set Up Your Recipes</Title>
              <Text>We'll create the following in your account:</Text>
            </div>
            
            <div className="summary-container" style={{ marginBottom: 24 }}>
              <Card title="Summary" bordered={false} className="summary-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
                  <div>
                    <Statistic 
                      title="Unique Ingredients" 
                      value={Array.from(
                        new Set(
                          suggestions.recipes.flatMap(recipe => 
                            recipe.ingredients.map(ing => ing.ingredient.toLowerCase())
                          )
                        )
                      ).length} 
                      suffix="items"
                    />
                  </div>
                  <div>
                    <Statistic 
                      title="Recipes" 
                      value={suggestions.recipes.length} 
                      suffix="items"
                    />
                  </div>
                </div>
              </Card>
            </div>

            <Tabs defaultActiveKey="1" style={{ marginBottom: 24 }}>
              <TabPane tab="Recipes" key="1">
                <Table
                  dataSource={suggestions.recipes.map((recipe, idx) => ({ key: idx, ...recipe }))}
                  columns={[
                    {
                      title: 'Recipe Name',
                      dataIndex: 'item_name',
                      key: 'item_name',
                    },
                    {
                      title: 'Ingredients Count',
                      key: 'ingredients_count',
                      render: (_, record: RecipeSuggestion) => record.ingredients.length
                    }
                  ]}
                  pagination={false}
                  size="small"
                  expandable={{
                    expandedRowRender: (record: RecipeSuggestion) => (
                      <Table
                        dataSource={record.ingredients.map((ing, idx) => ({ key: idx, ...ing }))}
                        columns={[
                          {
                            title: 'Ingredient',
                            dataIndex: 'ingredient',
                            key: 'ingredient',
                          },
                          {
                            title: 'Quantity',
                            dataIndex: 'quantity',
                            key: 'quantity',
                          },
                          {
                            title: 'Unit',
                            dataIndex: 'unit',
                            key: 'unit',
                          }
                        ]}
                        pagination={false}
                        size="small"
                      />
                    ),
                    rowExpandable: (record) => record.ingredients.length > 0,
                  }}
                />
              </TabPane>
              <TabPane tab="Ingredients" key="2">
                <div style={{ marginBottom: 16 }}>
                  <Alert
                    message="Ingredient Setup"
                    description="Set the price, quantity, and unit for each unique ingredient below. These values will be used for cost calculations."
                    type="info"
                    showIcon
                  />
                </div>
                <Table
                  dataSource={
                    (() => {
                      // Initialize base ingredients if they don't exist yet
                      if (suggestions && baseIngredients.length === 0) {
                        const uniqueIngredients = Array.from(
                          new Map(
                            suggestions.recipes.flatMap(recipe => 
                              recipe.ingredients.map(ing => [
                                ing.ingredient.toLowerCase(), 
                                { 
                                  ingredient_name: ing.ingredient, 
                                  unit: ing.unit,
                                  quantity: ing.quantity || 100, // Default quantity
                                  price: ing.price || 0, // Default price
                                  unit_price: 0 // Will be calculated on the backend
                                }
                              ])
                            )
                          ).values()
                        );
                        
                        // Set the base ingredients once
                        if (uniqueIngredients.length > 0 && baseIngredients.length === 0) {
                          setBaseIngredients(uniqueIngredients);
                        }
                      }
                      
                      // Always return the current state of baseIngredients for rendering
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
                            // Update the ingredient name in baseIngredients
                            const updatedBaseIngredients = baseIngredients.map(ing => 
                              ing.ingredient_name === text 
                                ? { ...ing, ingredient_name: e.target.value }
                                : ing
                            );
                            setBaseIngredients(updatedBaseIngredients);
                            
                            // Also update in recipes for display purposes (the recipes use ingredient names from baseIngredients)
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
                            // Get the current input value
                            let inputVal = e.target.value;
                            // Allow empty input for user to type
                            const newPrice = inputVal === '' ? 0 : parseFloat(inputVal) || 0;
                            
                            // Only update this specific base ingredient's price
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
                            // Get the current input value
                            let inputVal = e.target.value;
                            // Allow empty input for user to type
                            const newQuantity = inputVal === '' ? 0 : parseFloat(inputVal) || 0;
                            
                            // Only update this specific base ingredient's quantity
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
                        // Common units for cooking/food
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
                              // Only update this specific base ingredient's unit
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
              </TabPane>
            </Tabs>
            
            <Alert
              message="Ready to Proceed"
              description="Click 'Finish Setup' to create all these items in your account. This process can't be automatically undone, but you can edit or delete any items later."
              type="info"
              showIcon
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
