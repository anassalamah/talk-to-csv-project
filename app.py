import eventlet
eventlet.monkey_patch()

import pandas as pd
import nltk
import time
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

# Import our refactored components
import config
from agent import AnalysisAgent

# --- Flask and SocketIO Setup ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode='eventlet')

# --- Global Agent Instance ---
# In a real-world multi-user app, you would manage instances per session.
# For this single-user demo, a global instance is acceptable.
analysis_agent = None

# --- Helper Functions ---
def load_and_preprocess_data(file_path):
    """Loads and prepares the initial DataFrame."""
    try:
        df = pd.read_csv(file_path, header=0)
        print(f"✅ Raw data loaded successfully from '{file_path}'.")
        
        column_map = {
            'post.text': 'text', 'post.posted_time': 'timestamp', 'post.username': 'username', 
            'user.followers_count': 'followers', 'post_metrics.retweet_count': 'retweets',
            'post_metrics.like_count': 'likes', 'post_metrics.reply_count': 'replies'
        }
        existing_columns = {k: v for k, v in column_map.items() if k in df.columns}
        simplified_df = df[list(existing_columns.keys())].copy()
        simplified_df.rename(columns=existing_columns, inplace=True)
        print(f"✅ Data simplified. Kept {len(simplified_df.columns)} relevant columns.")
        return simplified_df
    except FileNotFoundError:
        print(f"❌ ERROR: Data file not found at '{file_path}'.")
        return None

# --- Flask Routes ---
@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

# --- SocketIO Event Handlers ---
@socketio.on('connect')
def handle_connect():
    print(f"✅ Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    print(f"❌ Client disconnected: {request.sid}")

@socketio.on('run_query')
def handle_run_query(json_data):
    """Handles the user's query by invoking the agent."""
    query = json_data.get('query')
    if not query:
        emit('agent_error', {'error': 'Invalid request: Missing query.'})
        return

    if not analysis_agent:
        emit('agent_error', {'error': 'Server error: Agent not initialized.'})
        return

    print(f"🚀 Processing query from {request.sid}: \"{query}\"")
    
    # The agent's progress callback will emit socket events
    analysis_agent.process_query(query)
    
    # Signal that the entire process is complete
    socketio.emit('query_complete', {'status': 'done'}, to=request.sid)
    print("--- Query Processing Complete ---")

@socketio.on_error_default
def error_handler(e):
    print(f"SocketIO error occurred: {e}")
    emit('agent_error', {'error': f'A socket communication error occurred: {e}'})

# --- Main Application Entry Point ---
if __name__ == "__main__":
    print("--- Initializing Application ---")
    
    # Load data and initialize the agent
    dataframe = load_and_preprocess_data(config.DATA_FILE_PATH)
    if dataframe is not None:
        # Define the callback function that the agent will use
        def agent_progress_callback(data):
            socketio.emit('stage_update', data)

        analysis_agent = AnalysisAgent(
            dataframe=dataframe,
            config=config,
            progress_callback=agent_progress_callback
        )
        print("✅ Analysis Agent initialized successfully.")
        print("-" * 30)
        print("🚀 Starting Flask-SocketIO server.")
        print(f"➡️  Access the application at http://127.0.0.1:5000")
        print("-" * 30)
        socketio.run(app, host='127.0.0.1', port=5000)
    else:
        print("❌ Could not start: Data loading failed.")