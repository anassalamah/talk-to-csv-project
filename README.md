# Talk to CSV Project - Intelligent Data Analysis System

An AI-powered data analysis agent that provides interactive data insights through a web interface. The system uses multiple specialized AI models to analyze data, execute Python code, and generate comprehensive reports in Arabic.

## Features

- **Multi-Agent Architecture**: Router, Planner, and Synthesizer agents working together
- **Real-time Web Interface**: Flask-SocketIO powered interface with live updates
- **Intelligent Query Routing**: Automatically determines whether queries need analysis or direct answers
- **Code Generation & Execution**: Generates and executes Python scripts for data analysis
- **Arabic Language Support**: Provides responses and synthesis in Arabic
- **Error Recovery**: Automatic retry mechanism with reflection for failed code execution
- **Interactive Progress Tracking**: Real-time status updates during analysis

## Architecture

The system consists of three main components:

### Core Components

1. **AnalysisAgent** (`agent.py`) - Main agent orchestrating the analysis workflow
2. **Flask Web App** (`app.py`) - Web server and SocketIO event handling
3. **Configuration** (`config.py`) - Centralized settings and model configurations

### Agent Workflow

1. **Router Agent**: Classifies queries as requiring analysis or direct answers
2. **Planner Agent**: Generates Python code for data analysis tasks
3. **Executor**: Runs generated code in a sandboxed environment
4. **Synthesizer Agent**: Creates comprehensive Arabic responses from analysis results

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd talk-to-csv-project
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Prepare your data**:
   - Place your CSV data file in the project root
   - Update `DATA_FILE_PATH` in `config.py` to point to your data file
   - Default expects `tweets.csv` with columns for text analysis

## Configuration

### LLM Setup

The system requires a local LLM API server. Configure in `config.py`:

```python
LLM_API_URL = "http://localhost:1234/v1/chat/completions"
ROUTER_MODEL = "google/gemma-3-12b"
PLANNER_MODEL = "mistralai/codestral-22b-v0.1"
SYNTHESIZER_MODEL = "google/gemma-3-12b"
```

### Data Format

Expected CSV columns (automatically mapped):
- `post.text` → `text`
- `post.posted_time` → `timestamp`
- `post.username` → `username`
- `user.followers_count` → `followers`
- `post_metrics.retweet_count` → `retweets`
- `post_metrics.like_count` → `likes`
- `post_metrics.reply_count` → `replies`

## Usage

1. **Start the application**:
   ```bash
   python app.py
   ```

2. **Access the web interface**:
   - Open http://127.0.0.1:5000 in your browser
   - The interface supports Arabic queries and responses

3. **Example queries**:
   - "ما هي المشاعر السائدة في البيانات؟" (What are the prevailing sentiments in the data?)
   - "أظهر لي توزيع المتابعين" (Show me the distribution of followers)
   - "ما هي أكثر المنشورات تفاعلاً؟" (What are the most engaging posts?)

## Dependencies

- **pandas**: Data manipulation and analysis
- **nltk**: Natural language processing
- **flask**: Web framework
- **flask-socketio**: Real-time communication
- **python-eventlet**: Async support
- **requests**: HTTP client for LLM API calls

## File Structure

```
talk-to-csv-project/
├── agent.py              # Core analysis agent
├── app.py               # Flask web application
├── config.py            # Configuration settings
├── requirements.txt     # Python dependencies
├── templates/
│   └── index.html      # Web interface template
├── static/
│   ├── css/
│   │   └── style.css   # Styling
│   └── js/
│       └── script.js   # Frontend JavaScript
└── tweets_sample.xlsx   # Sample data file
```

## Error Handling

- **Automatic Retry**: Failed code execution triggers reflection and retry (up to 3 attempts)
- **Progress Tracking**: Real-time status updates for each analysis stage
- **Graceful Fallbacks**: System continues operation even if individual components fail

## Contributing

1. Follow the existing code structure and conventions
2. Test with sample data before submitting changes
3. Ensure Arabic language support is maintained
4. Update documentation for new features

## License

This project is provided as-is for educational and research purposes.