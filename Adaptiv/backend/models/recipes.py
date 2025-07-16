from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Ingredient(Base):
    __tablename__ = "ingredients"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, index=True)
    quantity = Column(Float, nullable=False)  # Purchase quantity
    unit = Column(String, nullable=False)  # Unit of measurement (g, kg, ml, etc.)
    price = Column(Float, nullable=False)  # Purchase price
    date_created = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="ingredients")
    recipe_ingredients = relationship("RecipeIngredient", back_populates="ingredient")
    
    def unit_price(self):
        """Calculate the unit price of the ingredient."""
        if self.quantity and self.quantity > 0:
            return self.price / self.quantity
        return 0

class Recipe(Base):
    __tablename__ = "recipes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, index=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=True, index=True)
    date_created = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="recipes")
    item = relationship("Item")
    ingredients = relationship("RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan")
    
    def calculate_cost(self):
        """Calculate the total cost of the recipe based on its ingredients."""
        return sum(ingredient.calculate_cost() for ingredient in self.ingredients)
    
    @classmethod
    def calculate_fixed_costs(cls, db, user_id):
        """Calculate fixed costs that can be reused across multiple recipes.
        
        Args:
            db: Database session
            user_id: User ID for filtering costs
            
        Returns:
            Dict with fixed cost data including fixed cost per item
        """
        from datetime import datetime, timedelta
        from sqlalchemy import func
        from models.core import FixedCost, Employee
        from models.orders import Order, OrderItem
        
        # Get trailing month date range (last 30 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Get the current month and year for fixed costs
        current_month = datetime.now().month
        current_year = datetime.now().year
        fixed_costs = db.query(FixedCost).filter(
            FixedCost.user_id == user_id,
            FixedCost.month <= current_month,
            FixedCost.year <= current_year
        ).order_by(
            FixedCost.year.desc(),
            FixedCost.month.desc()
        ).all()
        
        # Calculate total monthly fixed costs
        total_rent = 0
        total_utilities = 0
        
        for cost in fixed_costs:
            if cost.cost_type.lower() == 'rent':
                total_rent = cost.amount
                break
                
        for cost in fixed_costs:
            if cost.cost_type.lower() == 'utilities':
                total_utilities = cost.amount
                break
        
        # Get active employees
        employees = db.query(Employee).filter(
            Employee.user_id == user_id,
            Employee.active == True
        ).all()
        
        # Calculate total monthly labor cost
        total_monthly_labor = 0
        for employee in employees:
            if employee.pay_type == 'salary':
                total_monthly_labor += employee.salary / 12  # Convert yearly to monthly
            elif employee.pay_type == 'hourly' and employee.weekly_hours is not None:
                # Assume 4.33 weeks per month on average
                total_monthly_labor += employee.hourly_rate * employee.weekly_hours * 4.33
        
        # Calculate total items sold in the trailing month from order data
        total_items_sold = db.query(func.sum(OrderItem.quantity)).join(Order).filter(
            Order.user_id == user_id,
            Order.order_date >= start_date,
            Order.order_date <= end_date
        ).scalar() or 1  # Default to 1 to avoid division by zero
        
        # Calculate total monthly fixed costs (rent + utilities + labor)
        total_monthly_fixed_costs = total_rent + total_utilities + total_monthly_labor
        
        # Calculate fixed cost per item based on actual sales volume
        fixed_cost_per_item = total_monthly_fixed_costs / total_items_sold if total_items_sold > 0 else 0
        
        return {
            'fixed_cost_per_item': fixed_cost_per_item,
            'total_monthly_fixed_costs': total_monthly_fixed_costs,
            'total_items_sold': total_items_sold
        }
    
    def calculate_net_margin(self, db, selling_price):
        """Calculate net margin for a recipe based on ingredient costs and fixed costs.
        
        Args:
            db: Database session
            selling_price: Selling price of the menu item
        
        Returns:
            Dict with net margin percentage, total cost, and breakdown of costs
        """
        # Get ingredient costs (already implemented)
        ingredient_cost = self.calculate_cost()
        
        # Get fixed costs (reusing shared calculation)
        fixed_costs = self.calculate_fixed_costs(db, self.user_id)
        fixed_cost_per_item = fixed_costs['fixed_cost_per_item']
        
        # Calculate total cost (ingredient cost + fixed costs)
        total_cost = ingredient_cost + fixed_cost_per_item
        
        # Calculate net margin
        if selling_price > 0:
            net_margin_percentage = ((selling_price - total_cost) / selling_price) * 100
        else:
            net_margin_percentage = 0
        
        return {
            'net_margin_percentage': round(net_margin_percentage, 2),
            'total_cost': round(total_cost, 2),
            'ingredient_cost': round(ingredient_cost, 2),
            'fixed_cost': round(fixed_cost_per_item, 2),
            'total_monthly_fixed_costs': round(fixed_costs['total_monthly_fixed_costs'], 2),
            'total_items_sold_last_month': fixed_costs['total_items_sold'],
            'selling_price': selling_price
        }

class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"
    
    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id", ondelete="RESTRICT"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    
    # Relationships
    recipe = relationship("Recipe", back_populates="ingredients")
    ingredient = relationship("Ingredient", back_populates="recipe_ingredients")
    
    def calculate_cost(self):
        """Calculate the cost of this ingredient in this recipe."""
        if self.ingredient and self.ingredient.quantity > 0:
            # Get units for conversion calculation
            recipe_unit = self.unit.lower().strip() if self.unit else ''
            inventory_unit = self.ingredient.unit.lower().strip() if self.ingredient.unit else ''
            
            # Define comprehensive unit conversion tables (from Costs.tsx)
            # Weight conversions (standardize to grams)
            weight_conversions = {
                'g': 1,
                'gram': 1,
                'grams': 1,
                'kg': 1000,
                'kilogram': 1000,
                'kilograms': 1000,
                'oz': 28.3495,
                'ounce': 28.3495,
                'ounces': 28.3495,
                'lb': 453.592,
                'pound': 453.592,
                'pounds': 453.592
            }
            
            # Volume conversions (standardize to ml)
            volume_conversions = {
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
                'gals': 3785.41,
                'quart': 946.353,
                'quarts': 946.353,
                'pint': 473.176,
                'pints': 473.176
            }
                        
            # Check if both units are in the same system
            if recipe_unit in weight_conversions and inventory_unit in weight_conversions:
                # Convert both to standard unit (grams), then calculate ratio
                recipe_in_standard = self.quantity * weight_conversions.get(recipe_unit, 1)
                inventory_in_standard = self.ingredient.quantity * weight_conversions.get(inventory_unit, 1)
                # Calculate how much of inventory unit is needed for recipe (in standard unit)
                return (recipe_in_standard / inventory_in_standard) * self.ingredient.price
                
            elif recipe_unit in volume_conversions and inventory_unit in volume_conversions:
                # Convert both to standard unit (ml), then calculate ratio
                recipe_in_standard = self.quantity * volume_conversions.get(recipe_unit, 1)
                inventory_in_standard = self.ingredient.quantity * volume_conversions.get(inventory_unit, 1)
                # Calculate how much of inventory unit is needed for recipe (in standard unit)
                return (recipe_in_standard / inventory_in_standard) * self.ingredient.price
            
            # If units are different or unrecognized, use default calculation
            # with a warning in the logs
            else:
                import logging
                logging.warning(
                    f"Potential unit mismatch: recipe uses {self.quantity} {recipe_unit} "
                    f"but inventory uses {self.ingredient.quantity} {inventory_unit} "
                    f"for ingredient {self.ingredient.name}"
                )
                # Use direct ratio without conversion
                # This might lead to unrealistic costs but won't break calculations
                return (self.quantity / self.ingredient.quantity) * self.ingredient.price
        return 0
