export interface RecipeIngredient {
  ingredient_id: string;
  ingredient_name?: string; // Optional as it might not be available when creating a recipe
  quantity: number;
  unit: string;
  cost?: number; // Optional as it's calculated on the server
}

// For AI-generated recipe suggestions
export interface SuggestionIngredient {
  ingredient: string;
  quantity: number;
  unit: string;
  price?: number; // Added for ingredient pricing in the form
}

export interface RecipeSuggestion {
  item_name: string;
  ingredients: SuggestionIngredient[];
}

// For the API response containing recipe suggestions
export interface MenuSuggestionResponse {
  recipes: RecipeSuggestion[];
}

export interface RecipeItem {
  item_id: string;
  item_name: string;
  ingredients: RecipeIngredient[];
  total_cost?: number; // Optional as it's calculated on the server
  date_created: string;
}

export interface IngredientItem {
  ingredient_id: string;
  ingredient_name: string;
  quantity: number;
  unit: string;
  price: number;
  unit_price?: number; // Optional as it's calculated on the server
  date_created: string;
}
