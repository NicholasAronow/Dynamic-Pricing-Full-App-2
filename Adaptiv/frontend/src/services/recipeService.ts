import api from './api';
import { RecipeItem, IngredientItem, MenuSuggestionResponse } from '../types/recipe';
import { MenuItem } from '../types/menu';

// Recipe service
export const getRecipes = async (): Promise<RecipeItem[]> => {
  // Removed redundant /api/ prefix and added trailing slash
  const response = await api.get('recipes/');
  return response.data.map((recipe: any) => ({
    item_id: recipe.id.toString(),
    item_name: recipe.name,
    ingredients: recipe.ingredients.map((ing: any) => ({
      ingredient_id: ing.ingredient_id.toString(),
      ingredient_name: ing.name,
      quantity: ing.quantity,
      unit: ing.unit,
      cost: ing.cost
    })),
    total_cost: recipe.total_cost,
    date_created: recipe.date_created
  }));
};

export const getRecipe = async (id: string): Promise<RecipeItem> => {
  // Removed redundant /api/ prefix
  const response = await api.get(`recipes/${id}/`);
  const recipe = response.data;
  return {
    item_id: recipe.id.toString(),
    item_name: recipe.name,
    ingredients: recipe.ingredients.map((ing: any) => ({
      ingredient_id: ing.ingredient_id.toString(),
      ingredient_name: ing.name,
      quantity: ing.quantity,
      unit: ing.unit,
      cost: ing.cost
    })),
    total_cost: recipe.total_cost,
    date_created: recipe.date_created
  };
};

export const createRecipe = async (recipe: Omit<RecipeItem, 'item_id' | 'date_created' | 'total_cost'>): Promise<RecipeItem> => {
  const payload = {
    name: recipe.item_name,
    ingredients: recipe.ingredients.map(ing => ({
      ingredient_id: parseInt(ing.ingredient_id),
      quantity: ing.quantity,
      unit: ing.unit
    }))
  };
  
  // Removed redundant /api/ prefix and added trailing slash
  const response = await api.post('recipes/', payload);
  const newRecipe = response.data;
  
  return {
    item_id: newRecipe.id.toString(),
    item_name: newRecipe.name,
    ingredients: newRecipe.ingredients.map((ing: any) => ({
      ingredient_id: ing.ingredient_id.toString(),
      ingredient_name: ing.name,
      quantity: ing.quantity,
      unit: ing.unit,
      cost: ing.cost
    })),
    total_cost: newRecipe.total_cost,
    date_created: newRecipe.date_created
  };
};

export const updateRecipe = async (recipe: Omit<RecipeItem, 'date_created' | 'total_cost'>): Promise<RecipeItem> => {
  const payload = {
    name: recipe.item_name,
    ingredients: recipe.ingredients.map(ing => ({
      ingredient_id: parseInt(ing.ingredient_id),
      quantity: ing.quantity,
      unit: ing.unit
    }))
  };
  
  // Removed redundant /api/ prefix and added trailing slash
  const response = await api.put(`recipes/${recipe.item_id}/`, payload);
  const updatedRecipe = response.data;
  
  return {
    item_id: updatedRecipe.id.toString(),
    item_name: updatedRecipe.name,
    ingredients: updatedRecipe.ingredients.map((ing: any) => ({
      ingredient_id: ing.ingredient_id.toString(),
      ingredient_name: ing.name,
      quantity: ing.quantity,
      unit: ing.unit,
      cost: ing.cost
    })),
    total_cost: updatedRecipe.total_cost,
    date_created: updatedRecipe.date_created
  };
};

export const deleteRecipe = async (id: string): Promise<void> => {
  // Removed redundant /api/ prefix and added trailing slash
  await api.delete(`recipes/${id}/`);
};

// Ingredient service
export const getIngredients = async (): Promise<IngredientItem[]> => {
  const response = await api.get('/api/recipes/ingredients');
  return response.data.map((ing: any) => ({
    ingredient_id: ing.id.toString(),
    ingredient_name: ing.name,
    quantity: ing.quantity,
    unit: ing.unit,
    price: ing.price,
    unit_price: ing.unit_price,
    date_created: ing.date_created
  }));
};

export const getIngredient = async (id: string): Promise<IngredientItem> => {
  const response = await api.get(`/api/recipes/ingredients/${id}`);
  const ing = response.data;
  return {
    ingredient_id: ing.id.toString(),
    ingredient_name: ing.name,
    quantity: ing.quantity,
    unit: ing.unit,
    price: ing.price,
    unit_price: ing.unit_price,
    date_created: ing.date_created
  };
};

export const createIngredient = async (ingredient: Omit<IngredientItem, 'ingredient_id' | 'date_created' | 'unit_price'>): Promise<IngredientItem> => {
  const payload = {
    name: ingredient.ingredient_name,
    quantity: ingredient.quantity,
    unit: ingredient.unit,
    price: ingredient.price
  };
  
  const response = await api.post('/api/recipes/ingredients', payload);
  const newIng = response.data;
  
  return {
    ingredient_id: newIng.id.toString(),
    ingredient_name: newIng.name,
    quantity: newIng.quantity,
    unit: newIng.unit,
    price: newIng.price,
    unit_price: newIng.unit_price,
    date_created: newIng.date_created
  };
};

export const updateIngredient = async (ingredient: Omit<IngredientItem, 'date_created' | 'unit_price'>): Promise<IngredientItem> => {
  const payload = {
    name: ingredient.ingredient_name,
    quantity: ingredient.quantity,
    unit: ingredient.unit,
    price: ingredient.price
  };
  
  const response = await api.put(`/api/recipes/ingredients/${ingredient.ingredient_id}`, payload);
  const updatedIng = response.data;
  
  return {
    ingredient_id: updatedIng.id.toString(),
    ingredient_name: updatedIng.name,
    quantity: updatedIng.quantity,
    unit: updatedIng.unit,
    price: updatedIng.price,
    unit_price: updatedIng.unit_price,
    date_created: updatedIng.date_created
  };
};

export const deleteIngredient = async (id: string): Promise<void> => {
  await api.delete(`/api/recipes/ingredients/${id}`);
};

// Types for the task status and response
export interface MenuSuggestionTaskResponse {
  task_id: string;
  status: string;
  message: string;
}

export interface MenuSuggestionTaskStatusResponse {
  status: string;
  message: string;
  completed: boolean;
  recipes?: any[];
  error?: string;
}

// AI-powered suggestion generation with asynchronous task processing
export const generateSuggestionsFromMenu = async (menuItems: MenuItem[]): Promise<MenuSuggestionResponse> => {
  try {
    // Step 1: Start the asynchronous task
    console.log('Starting menu suggestion generation task');
    const startResponse = await api.post('/api/ai-suggestions/menu-suggestions', {
      menu_items: menuItems
    });
    
    const taskResponse: MenuSuggestionTaskResponse = startResponse.data;
    const taskId = taskResponse.task_id;
    
    if (!taskId) {
      throw new Error('No task ID returned from server');
    }
    
    console.log(`Menu suggestion task started with ID: ${taskId}`);
    
    // Step 2: Poll for task completion
    return await pollTaskUntilComplete(taskId);
  } catch (error: any) {
    console.error('Error generating menu suggestions:', error.response?.data || error.message);
    throw error;
  }
};

// Poll the task status endpoint until the task is complete
async function pollTaskUntilComplete(taskId: string): Promise<MenuSuggestionResponse> {
  const maxAttempts = 30; // Maximum number of polling attempts
  const pollingInterval = 2000; // Poll every 2 seconds
  
  let attempts = 0;
  
  // Create a promise that resolves when the polling is complete
  return new Promise((resolve, reject) => {
    // Define the polling function
    const checkTaskStatus = async () => {
      try {
        // Check the status of the task
        const statusResponse = await api.get(`/api/ai-suggestions/menu-suggestions/status/${taskId}`);
        const statusData: MenuSuggestionTaskStatusResponse = statusResponse.data;
        
        // Log the current status
        console.log(`Task ${taskId} status: ${statusData.status} - ${statusData.message}`);
        
        // If the task is completed
        if (statusData.completed) {
          // Check if it was successful and has recipes
          if (statusData.recipes && statusData.recipes.length > 0) {
            console.log(`Task completed successfully with ${statusData.recipes.length} recipes`);
            resolve({ recipes: statusData.recipes });
            return;
          } else if (statusData.error) {
            // Task completed but with an error
            reject(new Error(`Task failed: ${statusData.error}`));
            return;
          }
        }
        
        // Increment attempts counter
        attempts++;
        
        // If we've reached the maximum attempts, reject with timeout error
        if (attempts >= maxAttempts) {
          reject(new Error(`Task timed out after ${maxAttempts} polling attempts`));
          return;
        }
        
        // Schedule the next poll
        setTimeout(checkTaskStatus, pollingInterval);
      } catch (error: any) {
        console.error('Error polling task status:', error);
        reject(error);
      }
    };
    
    // Start polling
    checkTaskStatus();
  });
};

// Fetch net margin data (including ingredient costs and fixed costs allocation)
export const getRecipeNetMargin = async (recipeId: string, sellingPrice: number): Promise<any> => {
  try {
    const response = await api.get(`/api/recipes/${recipeId}/net-margin`, {
      params: {
        selling_price: sellingPrice
      }
    });
    return response.data;
  } catch (error: any) {
    console.error(`Error fetching net margin for recipe ${recipeId}:`, error.response?.data || error.message);
    throw error;
  }
};
