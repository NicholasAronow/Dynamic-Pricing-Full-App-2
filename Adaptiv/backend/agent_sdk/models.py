from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Any, Optional
from datetime import datetime

# Base model with configuration to handle SQLAlchemy objects
class BaseModelConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

# Competitor Agent Models
class CompetitorInsight(BaseModelConfig):
    title: str
    description: str

class CompetitorRecommendation(BaseModelConfig):
    product_id: Optional[int] = None
    recommendation: str
    rationale: str

class CompetitorAnalysis(BaseModelConfig):
    summary: str
    insights: Optional[List[CompetitorInsight]] = []
    recommendations: Optional[List[CompetitorRecommendation]] = []
    positioning: Optional[str] = ""

# Customer Agent Models
class DemographicSegment(BaseModelConfig):
    name: str
    characteristics: Optional[List[str]] = []
    price_sensitivity: Optional[float] = 0.5  # 0-1 scale

class CustomerEvent(BaseModelConfig):
    name: str
    date: Optional[str] = ""
    projected_impact: Optional[str] = ""
    impact_level: Optional[float] = 0.5  # 0-1 scale

class CustomerRecommendation(BaseModelConfig):
    segment: Optional[str] = ""
    strategy: str
    expected_outcome: Optional[str] = ""

class CustomerAnalysis(BaseModelConfig):
    summary: str
    demographics: Optional[List[DemographicSegment]] = []
    price_sensitivity: Optional[Dict[str, float]] = {}  # category -> sensitivity
    upcoming_events: Optional[List[CustomerEvent]] = []
    recommendations: Optional[List[CustomerRecommendation]] = []

# Market Agent Models
class SupplyChainFactor(BaseModelConfig):
    factor: str
    impact: Optional[str] = ""
    trend: Optional[str] = "stable"  # increasing, decreasing, stable

class CostTrend(BaseModelConfig):
    input_category: str
    trend: Optional[str] = ""
    forecast: Optional[str] = ""

class MarketRecommendation(BaseModelConfig):
    recommendation: str
    rationale: Optional[str] = ""
    priority: Optional[str] = "medium"  # high, medium, low

class MarketAnalysis(BaseModelConfig):
    summary: str
    supply_chain: Optional[List[SupplyChainFactor]] = []
    cost_trends: Optional[List[CostTrend]] = []
    competitive_landscape: Optional[Dict[str, str]] = {}
    recommendations: Optional[List[MarketRecommendation]] = []

# Pricing Agent Models
class PriceRecommendation(BaseModelConfig):
    product_id: Optional[int] = None
    product_name: str
    current_price: Optional[float] = 0.0
    recommended_price: Optional[float] = 0.0
    change_percentage: Optional[float] = 0.0
    rationale: Optional[str] = ""

class PricingInsight(BaseModelConfig):
    insight: str
    impact: Optional[str] = ""

class ImplementationAdvice(BaseModelConfig):
    timing: Optional[str] = ""
    sequencing: Optional[str] = ""
    monitoring: Optional[str] = ""

class PricingAnalysis(BaseModelConfig):
    summary: str
    product_recommendations: Optional[List[PriceRecommendation]] = []
    pricing_insights: Optional[List[PricingInsight]] = []
    implementation: Optional[ImplementationAdvice] = None

# Experiment Agent Models
class ExperimentProduct(BaseModelConfig):
    product_id: Optional[int] = None
    product_name: str
    current_price: Optional[float] = 0.0
    new_price: Optional[float] = 0.0
    implementation_date: Optional[str] = ""
    evaluation_date: Optional[str] = ""

class EvaluationMetric(BaseModelConfig):
    metric: str
    description: Optional[str] = ""
    target: Optional[str] = ""

class RiskAssessment(BaseModelConfig):
    risk: str
    mitigation: Optional[str] = ""
    impact: Optional[str] = ""

class ExperimentPlan(BaseModelConfig):
    summary: str
    implementation: Optional[List[ExperimentProduct]] = []
    evaluation_criteria: Optional[List[EvaluationMetric]] = []
    risks: Optional[List[RiskAssessment]] = []
