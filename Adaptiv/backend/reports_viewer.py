"""
Simple Flask app to view all reports in a browser.
This bypasses the React frontend to help with debugging.
"""

from flask import Flask, jsonify, render_template_string
from sqlalchemy.orm import Session
import models
from database import SessionLocal
import json

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Adaptiv Reports Viewer</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
        h1 { color: #1890ff; }
        h2 { color: #1890ff; margin-top: 30px; }
        .report { border: 1px solid #d9d9d9; border-radius: 4px; padding: 15px; margin-bottom: 20px; }
        .report-header { display: flex; justify-content: space-between; margin-bottom: 10px; }
        .report-id { font-weight: bold; }
        .report-date { color: #8c8c8c; }
        .report-summary { margin-bottom: 15px; }
        .report-data { background-color: #f5f5f5; padding: 10px; border-radius: 4px; overflow: auto; }
        .tabs { display: flex; border-bottom: 1px solid #d9d9d9; margin-bottom: 20px; }
        .tab { padding: 10px 15px; cursor: pointer; }
        .tab.active { border-bottom: 2px solid #1890ff; color: #1890ff; }
        pre { white-space: pre-wrap; }
    </style>
</head>
<body>
    <h1>Adaptiv Reports Viewer</h1>
    <p>This is a simple viewer to debug and display all reports for User ID: {{ user_id }}</p>
    
    <div class="tabs">
        <div class="tab active" onclick="showTab('competitor')">Competitor Reports</div>
        <div class="tab" onclick="showTab('customer')">Customer Reports</div>
        <div class="tab" onclick="showTab('market')">Market Reports</div>
        <div class="tab" onclick="showTab('pricing')">Pricing Reports</div>
        <div class="tab" onclick="showTab('experiment')">Experiment Recommendations</div>
    </div>
    
    <div id="competitor" class="tab-content">
        <h2>Competitor Reports</h2>
        {% for report in competitor_reports %}
        <div class="report">
            <div class="report-header">
                <div class="report-id">ID: {{ report.id }}</div>
                <div class="report-date">{{ report.created_at }}</div>
            </div>
            <div class="report-summary">{{ report.summary }}</div>
            {% if report.insights %}
            <div class="report-data">
                <h4>Insights:</h4>
                <pre>{{ report.insights_pretty }}</pre>
            </div>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    
    <div id="customer" class="tab-content" style="display:none;">
        <h2>Customer Reports</h2>
        {% for report in customer_reports %}
        <div class="report">
            <div class="report-header">
                <div class="report-id">ID: {{ report.id }}</div>
                <div class="report-date">{{ report.created_at }}</div>
            </div>
            <div class="report-summary">{{ report.summary }}</div>
            {% if report.demographics %}
            <div class="report-data">
                <h4>Demographics:</h4>
                <pre>{{ report.demographics_pretty }}</pre>
            </div>
            {% endif %}
            {% if report.events %}
            <div class="report-data">
                <h4>Events:</h4>
                <pre>{{ report.events_pretty }}</pre>
            </div>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    
    <div id="market" class="tab-content" style="display:none;">
        <h2>Market Reports</h2>
        {% for report in market_reports %}
        <div class="report">
            <div class="report-header">
                <div class="report-id">ID: {{ report.id }}</div>
                <div class="report-date">{{ report.created_at }}</div>
            </div>
            <div class="report-summary">{{ report.summary }}</div>
            {% if report.market_trends %}
            <div class="report-data">
                <h4>Market Trends:</h4>
                <pre>{{ report.market_trends_pretty }}</pre>
            </div>
            {% endif %}
            {% if report.supply_chain %}
            <div class="report-data">
                <h4>Supply Chain:</h4>
                <pre>{{ report.supply_chain_pretty }}</pre>
            </div>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    
    <div id="pricing" class="tab-content" style="display:none;">
        <h2>Pricing Reports</h2>
        {% for report in pricing_reports %}
        <div class="report">
            <div class="report-header">
                <div class="report-id">ID: {{ report.id }}</div>
                <div class="report-date">{{ report.created_at }}</div>
            </div>
            <div class="report-summary">{{ report.summary }}</div>
            {% if report.recommended_changes %}
            <div class="report-data">
                <h4>Recommended Changes:</h4>
                <pre>{{ report.recommended_changes_pretty }}</pre>
            </div>
            {% endif %}
            {% if report.rationale %}
            <div class="report-data">
                <h4>Rationale:</h4>
                <pre>{{ report.rationale_pretty }}</pre>
            </div>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    
    <div id="experiment" class="tab-content" style="display:none;">
        <h2>Experiment Recommendations</h2>
        {% for report in experiment_reports %}
        <div class="report">
            <div class="report-header">
                <div class="report-id">ID: {{ report.id }}</div>
                <div class="report-date">{{ report.created_at }}</div>
            </div>
            <div class="report-summary">{{ report.summary }}</div>
            <div>Start Date: {{ report.start_date }}</div>
            <div>Evaluation Date: {{ report.evaluation_date }}</div>
            <div>Status: {{ report.status }}</div>
            {% if report.recommendations %}
            <div class="report-data">
                <h4>Recommendations:</h4>
                <pre>{{ report.recommendations_pretty }}</pre>
            </div>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    
    <script>
        function showTab(tabName) {
            // Hide all tab contents
            var tabContents = document.getElementsByClassName('tab-content');
            for (var i = 0; i < tabContents.length; i++) {
                tabContents[i].style.display = 'none';
            }
            
            // Remove active class from all tabs
            var tabs = document.getElementsByClassName('tab');
            for (var i = 0; i < tabs.length; i++) {
                tabs[i].classList.remove('active');
            }
            
            // Show the selected tab content and set tab as active
            document.getElementById(tabName).style.display = 'block';
            
            // Find the tab that was clicked and add active class
            var allTabs = document.getElementsByClassName('tab');
            for (var i = 0; i < allTabs.length; i++) {
                if (allTabs[i].innerText.toLowerCase().includes(tabName.toLowerCase())) {
                    allTabs[i].classList.add('active');
                    break;
                }
            }
        }
    </script>
</body>
</html>
"""

def prettify_json(json_str):
    """Format JSON string for display."""
    if not json_str:
        return "No data"
    try:
        parsed = json.loads(json_str)
        return json.dumps(parsed, indent=2)
    except:
        return json_str

@app.route('/')
def index():
    db = SessionLocal()
    try:
        user_id = 1  # Default to user ID 1
        
        # Get all reports, including those with errors
        competitor_reports = db.query(models.CompetitorReport).filter(
            models.CompetitorReport.user_id == user_id
        ).order_by(models.CompetitorReport.created_at.desc()).all()
        
        customer_reports = db.query(models.CustomerReport).filter(
            models.CustomerReport.user_id == user_id
        ).order_by(models.CustomerReport.created_at.desc()).all()
        
        market_reports = db.query(models.MarketReport).filter(
            models.MarketReport.user_id == user_id
        ).order_by(models.MarketReport.created_at.desc()).all()
        
        pricing_reports = db.query(models.PricingReport).filter(
            models.PricingReport.user_id == user_id
        ).order_by(models.PricingReport.created_at.desc()).all()
        
        experiment_reports = db.query(models.ExperimentRecommendation).filter(
            models.ExperimentRecommendation.user_id == user_id
        ).order_by(models.ExperimentRecommendation.created_at.desc()).all()
        
        # Format JSON fields
        for report in competitor_reports:
            report.insights_pretty = prettify_json(report.insights)
            
        for report in customer_reports:
            report.demographics_pretty = prettify_json(report.demographics)
            report.events_pretty = prettify_json(report.events)
            
        for report in market_reports:
            report.market_trends_pretty = prettify_json(report.market_trends)
            report.supply_chain_pretty = prettify_json(report.supply_chain)
            
        for report in pricing_reports:
            report.recommended_changes_pretty = prettify_json(report.recommended_changes)
            report.rationale_pretty = prettify_json(report.rationale)
            
        for report in experiment_reports:
            report.recommendations_pretty = prettify_json(report.recommendations)
        
        return render_template_string(
            HTML_TEMPLATE,
            user_id=user_id,
            competitor_reports=competitor_reports,
            customer_reports=customer_reports,
            market_reports=market_reports,
            pricing_reports=pricing_reports,
            experiment_reports=experiment_reports
        )
    finally:
        db.close()

@app.route('/api/reports')
def get_reports():
    """API endpoint to get all reports as JSON."""
    db = SessionLocal()
    try:
        user_id = 1  # Default to user ID 1
        
        # Get the latest non-error report of each type
        competitor_report = db.query(models.CompetitorReport).filter(
            models.CompetitorReport.user_id == user_id,
            ~models.CompetitorReport.summary.like("Error%")
        ).order_by(models.CompetitorReport.created_at.desc()).first()
        
        customer_report = db.query(models.CustomerReport).filter(
            models.CustomerReport.user_id == user_id,
            ~models.CustomerReport.summary.like("Error%")
        ).order_by(models.CustomerReport.created_at.desc()).first()
        
        market_report = db.query(models.MarketReport).filter(
            models.MarketReport.user_id == user_id,
            ~models.MarketReport.summary.like("Error%")
        ).order_by(models.MarketReport.created_at.desc()).first()
        
        pricing_report = db.query(models.PricingReport).filter(
            models.PricingReport.user_id == user_id,
            ~models.PricingReport.summary.like("Error%")
        ).order_by(models.PricingReport.created_at.desc()).first()
        
        experiment_recommendation = db.query(models.ExperimentRecommendation).filter(
            models.ExperimentRecommendation.user_id == user_id,
            ~models.ExperimentRecommendation.summary.like("Error%")
        ).order_by(models.ExperimentRecommendation.created_at.desc()).first()
        
        # Create response object
        response = {
            "competitor_report": {
                "id": competitor_report.id if competitor_report else None,
                "summary": competitor_report.summary if competitor_report else None,
                "insights": json.loads(competitor_report.insights) if competitor_report and competitor_report.insights else None,
                "created_at": competitor_report.created_at.isoformat() if competitor_report else None
            },
            "customer_report": {
                "id": customer_report.id if customer_report else None,
                "summary": customer_report.summary if customer_report else None,
                "demographics": json.loads(customer_report.demographics) if customer_report and customer_report.demographics else None,
                "events": json.loads(customer_report.events) if customer_report and customer_report.events else None,
                "created_at": customer_report.created_at.isoformat() if customer_report else None
            },
            "market_report": {
                "id": market_report.id if market_report else None,
                "summary": market_report.summary if market_report else None,
                "market_trends": json.loads(market_report.market_trends) if market_report and market_report.market_trends else None,
                "supply_chain": json.loads(market_report.supply_chain) if market_report and market_report.supply_chain else None,
                "created_at": market_report.created_at.isoformat() if market_report else None
            },
            "pricing_report": {
                "id": pricing_report.id if pricing_report else None,
                "summary": pricing_report.summary if pricing_report else None,
                "recommended_changes": json.loads(pricing_report.recommended_changes) if pricing_report and pricing_report.recommended_changes else None,
                "rationale": json.loads(pricing_report.rationale) if pricing_report and pricing_report.rationale else None,
                "created_at": pricing_report.created_at.isoformat() if pricing_report else None
            },
            "experiment_recommendation": {
                "id": experiment_recommendation.id if experiment_recommendation else None,
                "summary": experiment_recommendation.summary if experiment_recommendation else None,
                "start_date": experiment_recommendation.start_date.isoformat() if experiment_recommendation else None,
                "evaluation_date": experiment_recommendation.evaluation_date.isoformat() if experiment_recommendation else None,
                "recommendations": json.loads(experiment_recommendation.recommendations) if experiment_recommendation and experiment_recommendation.recommendations else None,
                "status": experiment_recommendation.status if experiment_recommendation else None,
                "created_at": experiment_recommendation.created_at.isoformat() if experiment_recommendation else None
            }
        }
        
        # Print report data to console for debugging
        print("\n==== REPORT DATA ====")
        print("Competitor Report ID:", competitor_report.id if competitor_report else None)
        print("Customer Report ID:", customer_report.id if customer_report else None)
        print("Market Report ID:", market_report.id if market_report else None)
        print("Pricing Report ID:", pricing_report.id if pricing_report else None)
        print("Experiment Recommendation ID:", experiment_recommendation.id if experiment_recommendation else None)
        print("\nReport Structure:", json.dumps(response, indent=2))
        print("==== END REPORT DATA ====\n")
        
        return jsonify(response)
    finally:
        db.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
