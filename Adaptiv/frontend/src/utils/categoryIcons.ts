// Category icon mapping for the product details page
// This maps product categories to appropriate vector icons from Ant Design

import {
  CoffeeOutlined,
  // TeaOutlined doesn't exist, using ExperimentOutlined as a substitute for tea
  ExperimentOutlined,
  ShopOutlined, 
  ShoppingOutlined,
  AppleOutlined,
  FireOutlined,
  GiftOutlined,
  BulbOutlined,
  CrownOutlined,
  RocketOutlined,
  HeartOutlined,
  CarOutlined,
  BookOutlined,
  HomeOutlined,
  SmileOutlined
} from '@ant-design/icons';

// Interface for icon configuration
export interface CategoryIcon {
  icon: any; // Icon component
  color: string; // Primary color for the icon
  backgroundColor: string; // Background color for the icon container
}

// Map of category names to their respective icon configurations
export const categoryIconsMap: Record<string, CategoryIcon> = {
  // Coffee and Tea related categories
  'Coffee': { 
    icon: CoffeeOutlined, 
    color: '#8B4513', 
    backgroundColor: '#FFF8DC' 
  },
  'Tea': { 
    icon: ExperimentOutlined, 
    color: '#006400', 
    backgroundColor: '#F0FFF0' 
  },
  'Espresso': { 
    icon: CoffeeOutlined, 
    color: '#5D4037', 
    backgroundColor: '#EFEBE9' 
  },
  'Cappuccino': { 
    icon: CoffeeOutlined, 
    color: '#6D4C41', 
    backgroundColor: '#F5F5F5' 
  },
  'Latte': { 
    icon: CoffeeOutlined, 
    color: '#795548', 
    backgroundColor: '#FFF8E1' 
  },
  
  // Food categories
  'Baked Goods': { 
    icon: FireOutlined, 
    color: '#FF9800', 
    backgroundColor: '#FFF3E0' 
  },
  'Pastries': { 
    icon: CrownOutlined, 
    color: '#F4511E', 
    backgroundColor: '#FBE9E7' 
  },
  'Sandwiches': { 
    icon: ShopOutlined, 
    color: '#FFA000', 
    backgroundColor: '#FFFDE7' 
  },
  'Salads': { 
    icon: AppleOutlined, 
    color: '#7CB342', 
    backgroundColor: '#F1F8E9' 
  },
  'Breakfast': { 
    icon: ShoppingOutlined, 
    color: '#FB8C00', 
    backgroundColor: '#FFF3E0' 
  },
  'Lunch': { 
    icon: ShoppingOutlined, 
    color: '#0277BD', 
    backgroundColor: '#E1F5FE' 
  },
  'Snacks': { 
    icon: GiftOutlined, 
    color: '#F57C00', 
    backgroundColor: '#FFF3E0' 
  },
  
  // Retail items
  'Merchandise': { 
    icon: ShoppingOutlined, 
    color: '#1976D2', 
    backgroundColor: '#E3F2FD' 
  },
  'Books': { 
    icon: BookOutlined, 
    color: '#5E35B1', 
    backgroundColor: '#EDE7F6' 
  },
  'Gifts': { 
    icon: GiftOutlined, 
    color: '#E91E63', 
    backgroundColor: '#FCE4EC' 
  },
  
  // Specialty categories
  'Seasonal': { 
    icon: RocketOutlined, 
    color: '#D81B60', 
    backgroundColor: '#FCE4EC' 
  },
  'Limited Edition': { 
    icon: CrownOutlined, 
    color: '#C2185B', 
    backgroundColor: '#F8BBD0' 
  },
  'Signature': { 
    icon: HeartOutlined, 
    color: '#D32F2F', 
    backgroundColor: '#FFEBEE' 
  },
  'Premium': { 
    icon: CrownOutlined, 
    color: '#FFD700', 
    backgroundColor: '#FFFDE7' 
  },
  
  // Fallback for unknown categories
  'default': { 
    icon: SmileOutlined, 
    color: '#1976D2', 
    backgroundColor: '#E3F2FD' 
  }
};

/**
 * Get the icon configuration for a specific category
 * @param category The product category
 * @returns The icon configuration (icon component, color, and background color)
 */
export const getCategoryIcon = (category: string): CategoryIcon => {
  // Look for an exact match
  if (categoryIconsMap[category]) {
    return categoryIconsMap[category];
  }
  
  // Try to find a partial match (e.g., "Iced Coffee" should match "Coffee")
  for (const [key, value] of Object.entries(categoryIconsMap)) {
    if (category.toLowerCase().includes(key.toLowerCase())) {
      return value;
    }
  }
  
  // Return default if no match found
  return categoryIconsMap['default'];
};

/**
 * Generate a CSS style object for the icon container
 * @param category The product category
 * @returns CSS style object
 */
export const getCategoryIconStyles = (category: string) => {
  const { color, backgroundColor } = getCategoryIcon(category);
  
  return {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 80,
    height: 80,
    borderRadius: 8,
    backgroundColor,
    color,
    fontSize: 36
  };
};
