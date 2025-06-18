import api from './api';
import { RecipeItem, IngredientItem, MenuSuggestionResponse } from '../types/recipe';
import { MenuItem } from '../types/menu';

// Recipe service
export const getRecipes = async (): Promise<RecipeItem[]> => {
  const response = await api.get('/api/recipes');
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
  const response = await api.get(`/api/recipes/${id}`);
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
  
  const response = await api.post('/api/recipes', payload);
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
  
  const response = await api.put(`/api/recipes/${recipe.item_id}`, payload);
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
  await api.delete(`/api/recipes/${id}`);
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

// AI-powered suggestion generation
export const generateSuggestionsFromMenu = async (menuItems: MenuItem[]): Promise<MenuSuggestionResponse> => {
  try {
    const response = await api.post('/api/ai-suggestions/menu-suggestions', {
      menu_items: menuItems
    });
    
    return response.data;
  } catch (error: any) {
    console.error('Error generating menu suggestions:', error.response?.data || error.message);
    throw error;
  }
};
