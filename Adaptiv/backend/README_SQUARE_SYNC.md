# Square Orders Sync Script

This script allows you to sync Square orders for a specific user ID from the command line, replicating the functionality of the "re-sync" button in the PriceRecommendations component.

## Usage

```bash
# Sync orders for a specific user ID
python3 sync_square_orders.py --user-id <USER_ID>

# Sync orders for a user by email
python3 sync_square_orders.py --email <EMAIL>

# Force re-sync all data (not just incremental)
python3 sync_square_orders.py --user-id <USER_ID> --force

# List all users with Square integration
python3 sync_square_orders.py --list-users

# Show help
python3 sync_square_orders.py --help
```

## Examples

```bash
# Sync orders for user ID 123
python3 sync_square_orders.py --user-id 123

# Sync orders for a specific email with force sync
python3 sync_square_orders.py --email testprofessional@test.com --force

# List all users who have Square integration set up
python3 sync_square_orders.py --list-users
```

## What the Script Does

1. **Validates the user**: Checks if the user exists and has an active Square integration
2. **Calls the sync function**: Uses the same `sync_initial_data` function that the frontend "re-sync" button uses
3. **Provides detailed feedback**: Shows progress and results of the sync operation
4. **Handles errors gracefully**: Provides clear error messages if something goes wrong

## Output

The script provides detailed output including:
- ✅ Success/failure status
- 📦 Number of items created/updated
- 📋 Number of orders synced
- 💬 Any messages from the sync process
- ❌ Clear error messages if issues occur

## Requirements

- The script must be run from the backend directory
- The database must be accessible
- The user must have an active Square integration set up

## Force Sync vs Regular Sync

- **Regular sync** (default): Incremental sync that only processes new/changed data
- **Force sync** (`--force` flag): Re-syncs all data from Square, useful for troubleshooting or data recovery

## Troubleshooting

If you encounter issues:

1. **"User not found"**: Verify the user ID or email is correct
2. **"No active Square integration"**: The user needs to connect their Square account first
3. **"Failed to get locations/catalog"**: Check the Square API credentials and network connectivity
4. **Database errors**: Ensure the database is running and accessible

## Security Note

This script requires access to the database and Square API credentials. Only run it in secure environments with proper access controls.
