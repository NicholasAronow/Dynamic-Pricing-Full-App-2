"""
Script to run database migrations
"""
import os
import sys
import importlib.util

def run_migration(migration_file):
    """Run a specific migration file"""
    if not os.path.exists(migration_file):
        print(f"Error: Migration file {migration_file} not found")
        return False

    # Import the migration file as a module
    module_name = os.path.basename(migration_file).replace(".py", "")
    spec = importlib.util.spec_from_file_location(module_name, migration_file)
    migration_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration_module)

    # Run the upgrade function
    try:
        if hasattr(migration_module, "upgrade"):
            print(f"Running migration: {module_name}")
            migration_module.upgrade()
            print(f"Migration {module_name} completed successfully")
            return True
        else:
            print(f"Error: No upgrade function found in {migration_file}")
            return False
    except Exception as e:
        print(f"Error running migration {module_name}: {str(e)}")
        return False

def main():
    """Run all migrations or a specific one if specified"""
    migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
    
    # Check if migrations directory exists
    if not os.path.isdir(migrations_dir):
        print(f"Creating migrations directory: {migrations_dir}")
        os.makedirs(migrations_dir)

    # If a specific migration is specified, run it
    if len(sys.argv) > 1:
        migration_file = sys.argv[1]
        if not os.path.isabs(migration_file):
            migration_file = os.path.join(migrations_dir, migration_file)
        if run_migration(migration_file):
            print("Migration completed successfully")
        else:
            print("Migration failed")
            sys.exit(1)
    else:
        # Find and run all migration files in order
        migrations = []
        for f in os.listdir(migrations_dir):
            if f.endswith(".py") and not f.startswith("__"):
                migrations.append(os.path.join(migrations_dir, f))
        
        # Sort migrations to ensure consistent order
        migrations.sort()
        
        if not migrations:
            print("No migrations found")
            return
        
        # Run each migration
        success_count = 0
        for migration in migrations:
            if run_migration(migration):
                success_count += 1
        
        print(f"Ran {success_count} of {len(migrations)} migrations successfully")

if __name__ == "__main__":
    main()
