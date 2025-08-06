# Database Table Deletion Scripts

This directory contains scripts to delete old database tables from the Dynamic Pricing application.

## Scripts

### 1. `preview_table_deletion.py` (Safe Preview)
- **Purpose**: Shows what tables exist and would be deleted WITHOUT actually deleting them
- **Usage**: `python3 preview_table_deletion.py`
- **Safe**: ✅ Read-only, no data is modified

### 2. `delete_tables_script.py` (Actual Deletion)
- **Purpose**: Actually deletes the specified tables and all their data
- **Usage**: `python3 delete_tables_script.py`
- **Destructive**: ⚠️ Permanently deletes data, requires confirmation

## Tables to be Deleted

The following tables will be deleted:

### Agent Memory & Analysis Tables
- `strategy_evolutions` - Strategy evolution tracking
- `pricing_decisions` - Pricing decision history
- `experiment_learnings` - Experiment insights
- `experiment_price_changes` - Price changes from experiments
- `price_recommendation_actions` - Price recommendation actions
- `experiment_recommendations` - Experiment recommendations
- `pricing_reports` - Pricing analysis reports
- `performance_anomalies` - Performance anomaly detection
- `performance_baselines` - Performance baseline metrics
- `bundle_recommendations` - Product bundle recommendations
- `customer_reports` - Customer analysis reports
- `competitor_reports` - Competitor analysis reports
- `market_reports` - Market analysis reports

### Core Business Tables
- `cogs` - Cost of Goods Sold data

### Agent Memory Tables
- `pricing_recommendations` - Individual pricing recommendations
- `pricing_experiments` - A/B test experiments
- `data_collection_snapshots` - Data quality snapshots
- `market_analysis_snapshots` - Market analysis snapshots
- `competitor_price_histories` - Historical competitor pricing
- `agent_memories` - Generic agent memory storage

## Usage Instructions

### Step 1: Preview (Recommended)
```bash
python3 preview_table_deletion.py
```
This will show you:
- Which tables exist
- How many rows each table contains
- Total rows that would be deleted
- No data is actually deleted

### Step 2: Delete (If Confirmed)
```bash
python3 delete_tables_script.py
```
This will:
- Ask for confirmation (type 'DELETE' to proceed)
- Delete all specified tables
- Show progress and summary
- Handle foreign key constraints automatically

## Safety Features

- **Confirmation Required**: The deletion script requires typing 'DELETE' to proceed
- **Preview Mode**: Always run the preview first to see what will be deleted
- **Progress Reporting**: Shows which tables are being processed
- **Error Handling**: Gracefully handles missing tables and errors
- **Foreign Key Management**: Temporarily disables foreign key constraints during deletion

## Current Status (Last Check)

- **Tables Found**: 20/20
- **Total Rows**: 2,994
- **Largest Table**: `competitor_price_histories` (1,956 rows)

## Backup Recommendation

Before running the deletion script, consider backing up your database:
```bash
# For SQLite databases
cp adaptiv.db adaptiv_backup_$(date +%Y%m%d_%H%M%S).db
```

## Recovery

Once tables are deleted, they cannot be recovered unless you have a backup. Make sure you really want to delete this data before proceeding.
