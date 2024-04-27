from alembic import environment, command


# Define connection details (replace with your actual settings)

def run_migration(db_url, script_location, revision_id):
    config = environment.EnvironmentContext(
        script_location=script_location,  # Path to your migration scripts directory
        url=db_url,
        echo=True  # Set to True for logging output
    )

    command.upgrade(config, revision_id)
