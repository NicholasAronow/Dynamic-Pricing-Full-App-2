#!/usr/bin/env python3
"""
SQLAlchemy-based database manager for competitor analysis system
"""

import logging
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from models import Base, User, CompetitorEntity, CompetitorItem


class CompetitorDatabase:
    """Database manager for competitor entities and their menu items"""
    
    def __init__(self, db_url: str = "sqlite:///competitor_analysis.db"):
        """Initialize the database connection and create tables"""
        self.engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        logging.info(f"Database initialized at {db_url}")
    
    def get_session(self) -> Session:
        """Get a database session"""
        return self.SessionLocal()
    
    def create_or_get_user(self, email: str = "default@example.com") -> int:
        """Create or get a default user (placeholder for future user management)"""
        with self.get_session() as session:
            user = session.query(User).filter(User.email == email).first()
            if not user:
                user = User(email=email)
                session.add(user)
                session.commit()
                session.refresh(user)
                logging.info(f"Created user with ID {user.id}")
            return user.id
    
    def create_competitor_entity(
        self,
        user_id: int,
        name: str,
        address: Optional[str] = None,
        category: Optional[str] = None,
        phone: Optional[str] = None,
        website: Optional[str] = None,
        distance_km: Optional[float] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        menu_url: Optional[str] = None,
        score: Optional[float] = None,
        is_selected: bool = False
    ) -> int:
        """Create a new competitor entity"""
        with self.get_session() as session:
            # Check if competitor already exists for this user
            existing = session.query(CompetitorEntity).filter(
                and_(CompetitorEntity.user_id == user_id, CompetitorEntity.name == name)
            ).first()
            
            if existing:
                logging.info(f"Competitor {name} already exists for user {user_id}")
                return existing.id
            
            competitor = CompetitorEntity(
                user_id=user_id,
                name=name,
                address=address,
                category=category,
                phone=phone,
                website=website,
                distance_km=distance_km,
                latitude=latitude,
                longitude=longitude,
                menu_url=menu_url,
                score=score,
                is_selected=is_selected
            )
            
            session.add(competitor)
            session.commit()
            session.refresh(competitor)
            logging.info(f"Created competitor entity {name} with ID {competitor.id}")
            return competitor.id
    
    def add_competitor_items(
        self,
        competitor_id: int,
        items: List[Dict],
        batch_id: Optional[str] = None,
        competitor_name: Optional[str] = None
    ) -> int:
        """Add menu items for a competitor"""
        if not batch_id:
            batch_id = str(uuid.uuid4())
        
        sync_timestamp = datetime.utcnow()
        items_added = 0
        
        with self.get_session() as session:
            # Get competitor name if not provided
            if not competitor_name:
                competitor = session.query(CompetitorEntity).filter(
                    CompetitorEntity.id == competitor_id
                ).first()
                if competitor:
                    competitor_name = competitor.name
            
            for item_data in items:
                # Extract price as float if it's a string
                price = item_data.get('price')
                if isinstance(price, str):
                    # Remove currency symbols and convert to float
                    price_str = price.replace('$', '').replace(',', '').strip()
                    try:
                        price = float(price_str)
                    except (ValueError, TypeError):
                        price = None
                
                competitor_item = CompetitorItem(
                    competitor_id=competitor_id,
                    competitor_name=competitor_name,
                    item_name=item_data.get('name', ''),
                    description=item_data.get('description'),
                    category=item_data.get('category'),
                    price=price,
                    similarity_score=item_data.get('similarity_score'),
                    url=item_data.get('url'),
                    batch_id=batch_id,
                    sync_timestamp=sync_timestamp
                )
                
                session.add(competitor_item)
                items_added += 1
            
            session.commit()
            logging.info(f"Added {items_added} items for competitor {competitor_id} in batch {batch_id}")
            return items_added
    
    def get_competitor_entities(self, user_id: int, selected_only: bool = False) -> List[CompetitorEntity]:
        """Get competitor entities for a user"""
        with self.get_session() as session:
            query = session.query(CompetitorEntity).filter(CompetitorEntity.user_id == user_id)
            
            if selected_only:
                query = query.filter(CompetitorEntity.is_selected == True)
            
            return query.all()
    
    def get_competitor_items(
        self,
        competitor_id: Optional[int] = None,
        competitor_name: Optional[str] = None,
        batch_id: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[CompetitorItem]:
        """Get competitor items with optional filters"""
        with self.get_session() as session:
            query = session.query(CompetitorItem)
            
            if competitor_id:
                query = query.filter(CompetitorItem.competitor_id == competitor_id)
            
            if competitor_name:
                query = query.filter(CompetitorItem.competitor_name == competitor_name)
            
            if batch_id:
                query = query.filter(CompetitorItem.batch_id == batch_id)
            
            if category:
                query = query.filter(CompetitorItem.category == category)
            
            return query.all()
    
    def update_competitor_selection(self, competitor_id: int, is_selected: bool) -> bool:
        """Update the selection status of a competitor"""
        with self.get_session() as session:
            competitor = session.query(CompetitorEntity).filter(
                CompetitorEntity.id == competitor_id
            ).first()
            
            if competitor:
                competitor.is_selected = is_selected
                session.commit()
                logging.info(f"Updated competitor {competitor_id} selection to {is_selected}")
                return True
            
            return False
    
    def get_latest_batch_items(self, competitor_id: int) -> List[CompetitorItem]:
        """Get the most recent batch of items for a competitor"""
        with self.get_session() as session:
            # Get the latest batch_id for this competitor
            latest_batch = session.query(CompetitorItem.batch_id).filter(
                CompetitorItem.competitor_id == competitor_id
            ).order_by(CompetitorItem.sync_timestamp.desc()).first()
            
            if not latest_batch:
                return []
            
            # Get all items from the latest batch
            return session.query(CompetitorItem).filter(
                and_(
                    CompetitorItem.competitor_id == competitor_id,
                    CompetitorItem.batch_id == latest_batch[0]
                )
            ).all()
    
    def delete_old_batches(self, competitor_id: int, keep_batches: int = 3) -> int:
        """Delete old batches for a competitor, keeping only the most recent ones"""
        with self.get_session() as session:
            # Get all batch_ids for this competitor, ordered by sync_timestamp
            batches = session.query(CompetitorItem.batch_id).filter(
                CompetitorItem.competitor_id == competitor_id
            ).distinct().order_by(CompetitorItem.sync_timestamp.desc()).all()
            
            if len(batches) <= keep_batches:
                return 0
            
            # Get batch_ids to delete (all except the most recent keep_batches)
            batches_to_delete = [batch[0] for batch in batches[keep_batches:]]
            
            # Delete items from old batches
            deleted_count = session.query(CompetitorItem).filter(
                and_(
                    CompetitorItem.competitor_id == competitor_id,
                    CompetitorItem.batch_id.in_(batches_to_delete)
                )
            ).delete(synchronize_session=False)
            
            session.commit()
            logging.info(f"Deleted {deleted_count} items from {len(batches_to_delete)} old batches for competitor {competitor_id}")
            return deleted_count
    
    def get_competitor_summary(self, user_id: int) -> Dict:
        """Get a summary of competitors and their item counts"""
        with self.get_session() as session:
            competitors = session.query(CompetitorEntity).filter(
                CompetitorEntity.user_id == user_id
            ).all()
            
            summary = {
                'total_competitors': len(competitors),
                'selected_competitors': len([c for c in competitors if c.is_selected]),
                'competitors': []
            }
            
            for competitor in competitors:
                item_count = session.query(CompetitorItem).filter(
                    CompetitorItem.competitor_id == competitor.id
                ).count()
                
                latest_batch = session.query(CompetitorItem.sync_timestamp).filter(
                    CompetitorItem.competitor_id == competitor.id
                ).order_by(CompetitorItem.sync_timestamp.desc()).first()
                
                summary['competitors'].append({
                    'id': competitor.id,
                    'name': competitor.name,
                    'category': competitor.category,
                    'is_selected': competitor.is_selected,
                    'item_count': item_count,
                    'last_sync': latest_batch[0] if latest_batch else None
                })
            
            return summary
