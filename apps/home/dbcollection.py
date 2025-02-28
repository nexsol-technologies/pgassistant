import json
import os

# Define the path to the DBeaver connections JSON file
DBEAVER_CONFIG_PATH = os.path.expanduser("~/Library/DBeaverData/workspace6/General/.dbeaver/data-sources.json")

# Function to read and extract PostgreSQL connections
# Function to extract PostgreSQL connections
def extract_postgresql_connections(config_path):
    try:
        with open(config_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        # Ensure we have a dictionary of connections
        connections = data.get("connections", {})

        # Filter PostgreSQL connections
        pg_connections = [
            {
                "name": conn_data.get("name"),
                "host": conn_data.get("configuration", {}).get("host"),
                "port": conn_data.get("configuration", {}).get("port", "5432"),
                "database": conn_data.get("configuration", {}).get("database"),
                "username": conn_data.get("configuration", {}).get("auth-model", "native"),  # No username field in provided data
                "provider": conn_data.get("provider"),
            }
            for conn_id, conn_data in connections.items() if conn_data.get("provider") == "postgresql"
        ]

        return pg_connections

    except FileNotFoundError:
        print(f"Error: Configuration file not found at {config_path}")
        return []
    except json.JSONDecodeError:
        print("Error: Failed to parse JSON file. Check the file format.")
        return []


# Get PostgreSQL connections
pg_connections = extract_postgresql_connections(DBEAVER_CONFIG_PATH)

# Display results
if pg_connections:
    for conn in pg_connections:
        print(f"Name: {conn['name']}, Host: {conn['host']}, Port: {conn['port']}, Database: {conn['database']}, User: {conn['username']}")
else:
    print("No PostgreSQL connections found.")