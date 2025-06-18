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
    date_created = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="recipes")
    ingredients = relationship("RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan")
    
    def calculate_cost(self):
        """Calculate the total cost of the recipe based on its ingredients."""
        return sum(ingredient.calculate_cost() for ingredient in self.ingredients)

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
            # Calculate based on unit price of the ingredient
            return (self.quantity / self.ingredient.quantity) * self.ingredient.price
        return 0
