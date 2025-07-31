# --- Centralized Configuration ---

# File Paths
DATA_FILE_PATH = "tweets.csv"

# LLM API Settings
LLM_API_URL = "http://localhost:1234/v1/chat/completions"

# Model Names
ROUTER_MODEL = "google/gemma-3-12b"
# ROUTER_MODEL = "google/gemma-3n-e4b"
PLANNER_MODEL = "mistralai/codestral-22b-v0.1"
# PLANNER_MODEL = "google/gemma-3-12b"
SYNTHESIZER_MODEL = "google/gemma-3-12b"
# SYNTHESIZER_MODEL = "google/gemma-3n-e4b"

# Agent Settings
MAX_RETRIES = 3
HISTORY_LENGTH = 3 # Number of past conversations to consider