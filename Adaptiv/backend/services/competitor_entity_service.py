from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional, Dict, Any
import models, schemas
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload, noload, lazyload

class CompetitorEntityService:
    """Service layer for CompetitorEntity business logic"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_competitor_entities(
        self, 
        user_id: int, 
        include_items: bool = False,
        skip: int = 0, 
        limit: int = 100
    ) -> List[models.CompetitorEntity]:
        """Get all competitor entities for a user"""
        query = self.db.query(models.CompetitorEntity).filter(
            models.CompetitorEntity.user_id == user_id
        )
        
        if include_items:
            query = query.options(joinedload(models.CompetitorEntity.items))
        else:
            # Explicitly don't load relationships to avoid circular references
            query = query.options(
                noload(models.CompetitorEntity.items),
                noload(models.CompetitorEntity.user)
            )
        
        return query.offset(skip).limit(limit).all()
    
    from sqlalchemy.orm import Session, joinedload, lazyload

    def get_competitor_entity(
        self, 
        competitor_id: int, 
        user_id: int,
        include_items: bool = False
    ) -> Optional[models.CompetitorEntity]:
        """Get a specific competitor entity by ID"""
        query = self.db.query(models.CompetitorEntity).filter(
            models.CompetitorEntity.id == competitor_id,
            models.CompetitorEntity.user_id == user_id
        )
        
        if include_items:
            # Load items but NOT the competitor relationship within items
            query = query.options(
                joinedload(models.CompetitorEntity.items)
            )
        else:
            query = query.options(
                lazyload(models.CompetitorEntity.items),
                lazyload(models.CompetitorEntity.user)
            )
        
        return query.first()
    
    def create_competitor_entity(
        self, 
        competitor_data: schemas.CompetitorEntityCreate, 
        user_id: int
    ) -> models.CompetitorEntity:
        """Create a new competitor entity"""
        # Check if competitor with same name already exists for this user
        existing = self.db.query(models.CompetitorEntity).filter(
            models.CompetitorEntity.user_id == user_id,
            models.CompetitorEntity.name == competitor_data.name
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400, 
                detail=f"Competitor with name '{competitor_data.name}' already exists"
            )
        
        db_competitor = models.CompetitorEntity(
            user_id=user_id,
            **competitor_data.dict()
        )
        self.db.add(db_competitor)
        self.db.commit()
        self.db.refresh(db_competitor)
        return db_competitor
    
    def update_competitor_entity(
        self, 
        competitor_id: int, 
        competitor_data: schemas.CompetitorEntityUpdate, 
        user_id: int
    ) -> Optional[models.CompetitorEntity]:
        """Update a competitor entity"""
        db_competitor = self.db.query(models.CompetitorEntity).filter(
            models.CompetitorEntity.id == competitor_id,
            models.CompetitorEntity.user_id == user_id
        ).first()
        
        if not db_competitor:
            return None
        
        # Check for name conflicts if name is being updated
        if competitor_data.name and competitor_data.name != db_competitor.name:
            existing = self.db.query(models.CompetitorEntity).filter(
                models.CompetitorEntity.user_id == user_id,
                models.CompetitorEntity.name == competitor_data.name,
                models.CompetitorEntity.id != competitor_id
            ).first()
            
            if existing:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Competitor with name '{competitor_data.name}' already exists"
                )
        
        # Update only provided fields
        update_data = competitor_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_competitor, field, value)
        
        self.db.commit()
        self.db.refresh(db_competitor)
        return db_competitor
    
    def delete_competitor_entity(
        self, 
        competitor_id: int, 
        user_id: int
    ) -> bool:
        """Delete a competitor entity and all its items"""
        db_competitor = self.db.query(models.CompetitorEntity).filter(
            models.CompetitorEntity.id == competitor_id,
            models.CompetitorEntity.user_id == user_id
        ).first()
        
        if not db_competitor:
            return False
        
        self.db.delete(db_competitor)
        self.db.commit()
        return True
    
    def toggle_competitor_selection(
        self, 
        competitor_id: int, 
        user_id: int,
        is_selected: bool
    ) -> Optional[models.CompetitorEntity]:
        """Toggle competitor selection for tracking"""
        db_competitor = self.db.query(models.CompetitorEntity).filter(
            models.CompetitorEntity.id == competitor_id,
            models.CompetitorEntity.user_id == user_id
        ).first()
        
        if not db_competitor:
            return None
        
        db_competitor.is_selected = is_selected
        self.db.commit()
        self.db.refresh(db_competitor)
        return db_competitor
    
    def get_competitor_items(
        self,
        competitor_id: int,
        user_id: int,
        category: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[models.CompetitorItem]:
        """Get all items for a specific competitor"""
        # Verify competitor belongs to current user
        competitor = self.db.query(models.CompetitorEntity).filter(
            models.CompetitorEntity.id == competitor_id,
            models.CompetitorEntity.user_id == user_id
        ).first()
        
        if not competitor:
            raise HTTPException(status_code=404, detail="Competitor not found")
        
        query = self.db.query(models.CompetitorItem).filter(
            models.CompetitorItem.competitor_id == competitor_id
        )
        
        if category:
            query = query.filter(models.CompetitorItem.category == category)
        
        return query.offset(skip).limit(limit).all()
    
    def get_competitor_stats(
        self,
        competitor_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """Get statistics for a specific competitor"""
        # Verify competitor belongs to current user
        competitor = self.db.query(models.CompetitorEntity).filter(
            models.CompetitorEntity.id == competitor_id,
            models.CompetitorEntity.user_id == user_id
        ).first()
        
        if not competitor:
            raise HTTPException(status_code=404, detail="Competitor not found")
        
        # Get item statistics
        total_items = self.db.query(models.CompetitorItem).filter(
            models.CompetitorItem.competitor_id == competitor_id
        ).count()
        
        # Get category breakdown
        category_stats = self.db.query(
            models.CompetitorItem.category,
            func.count(models.CompetitorItem.id).label('count'),
            func.avg(models.CompetitorItem.price).label('avg_price')
        ).filter(
            models.CompetitorItem.competitor_id == competitor_id
        ).group_by(models.CompetitorItem.category).all()
        
        # Get price statistics
        price_stats = self.db.query(
            func.min(models.CompetitorItem.price).label('min_price'),
            func.max(models.CompetitorItem.price).label('max_price'),
            func.avg(models.CompetitorItem.price).label('avg_price')
        ).filter(
            models.CompetitorItem.competitor_id == competitor_id
        ).first()
        
        return {
            "competitor_id": competitor_id,
            "competitor_name": competitor.name,
            "total_items": total_items,
            "price_stats": {
                "min_price": float(price_stats.min_price) if price_stats.min_price else 0,
                "max_price": float(price_stats.max_price) if price_stats.max_price else 0,
                "avg_price": float(price_stats.avg_price) if price_stats.avg_price else 0
            },
            "category_breakdown": [
                {
                    "category": stat.category,
                    "item_count": stat.count,
                    "avg_price": float(stat.avg_price) if stat.avg_price else 0
                }
                for stat in category_stats
            ]
        }
    
    def get_selected_competitors(self, user_id: int) -> List[models.CompetitorEntity]:
        """Get all competitors selected for tracking by a user"""
        return self.db.query(models.CompetitorEntity).filter(
            models.CompetitorEntity.user_id == user_id,
            models.CompetitorEntity.is_selected == True
        ).all()
    
    def migrate_legacy_competitor_data(self, user_id: int) -> Dict[str, Any]:
        """
        Migrate legacy competitor data from competitor_items.competitor_name 
        to CompetitorEntity structure
        """
        # Get unique competitor names from existing items for this user
        legacy_competitors = self.db.query(
            models.CompetitorItem.competitor_name
        ).join(
            models.CompetitorEntity,
            models.CompetitorItem.competitor_id == models.CompetitorEntity.id
        ).filter(
            models.CompetitorEntity.user_id == user_id,
            models.CompetitorItem.competitor_name.isnot(None)
        ).distinct().all()
        
        migrated_count = 0
        existing_count = 0
        
        for (competitor_name,) in legacy_competitors:
            if not competitor_name:
                continue
                
            # Check if CompetitorEntity already exists
            existing_entity = self.db.query(models.CompetitorEntity).filter(
                models.CompetitorEntity.user_id == user_id,
                models.CompetitorEntity.name == competitor_name
            ).first()
            
            if existing_entity:
                existing_count += 1
                continue
            
            # Create new CompetitorEntity
            new_entity = models.CompetitorEntity(
                user_id=user_id,
                name=competitor_name,
                website=None,
                description=f"Migrated competitor: {competitor_name}",
                is_selected=False
            )
            self.db.add(new_entity)
            self.db.flush()  # Get the ID
            
            # Update all items with this competitor_name to reference the new entity
            self.db.query(models.CompetitorItem).filter(
                models.CompetitorItem.competitor_name == competitor_name
            ).update({
                models.CompetitorItem.competitor_id: new_entity.id
            })
            
            migrated_count += 1
        
        self.db.commit()
        
        return {
            "migrated_competitors": migrated_count,
            "existing_competitors": existing_count,
            "total_processed": migrated_count + existing_count
        }
