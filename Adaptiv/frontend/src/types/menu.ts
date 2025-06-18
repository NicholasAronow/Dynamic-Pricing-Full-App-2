// Menu types
export interface MenuItem {
  id: string;
  name: string;
  description?: string;
  category?: string;
  price?: number;
  cost?: number;
  image?: string;
  status?: 'active' | 'inactive';
}

export interface MenuCategory {
  id: string;
  name: string;
  description?: string;
}
