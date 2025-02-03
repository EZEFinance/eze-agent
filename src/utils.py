import os

def get_env_variable(env_key):
    if env_key in os.environ and os.environ[env_key]:
        return os.environ[env_key]