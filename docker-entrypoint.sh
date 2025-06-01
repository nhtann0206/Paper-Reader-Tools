#!/bin/bash
set -e

# Debug information
echo "Running as user: $(id)"

# Ensure directories exist and have proper permissions
mkdir -p /app/data /app/uploads /app/output
chmod 777 /app/data /app/uploads /app/output

# Show directory permissions
echo "Directory permissions:"
ls -la /app/data

# Check for existing database
if [ -f /app/data/papers.db ]; then
    echo "Existing database found"
    # Make sure it has correct permissions
    chmod 666 /app/data/papers.db
    echo "Set permissions on existing database"
    ls -la /app/data/papers.db
else
    echo "No existing database found, will initialize"
fi

# Initialize database with verbose output
echo "Initializing database..."
python -u /app/init_db.py

# Make sure database file has proper permissions
if [ -f /app/data/papers.db ]; then
    chmod 666 /app/data/papers.db
    echo "Database file permissions:"
    ls -la /app/data/papers.db
else
    echo "WARNING: Database file not created!"
fi

# Start the API server
echo "Starting API server..."
exec "$@"
