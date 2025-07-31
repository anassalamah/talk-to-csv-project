import pandas as pd
import io
import contextlib
import json
import re
import time
import requests

class AnalysisAgent:
    """
    Encapsulates the entire data analysis workflow, from routing to synthesis.
    The agent's logic is decoupled from the web communication layer (e.g., SocketIO)
    by using a progress_callback function to report its state.
    """
    def __init__(self, dataframe: pd.DataFrame, config: object, progress_callback=None):
        """
        Initializes the agent with data, configuration, and a callback.

        Args:
            dataframe (pd.DataFrame): The pre-processed data for analysis.
            config (object): A configuration object with model names, URLs, etc.
            progress_callback (function, optional): A function to call with stage updates.
                                                    It should accept a dictionary. Defaults to None.
        """
        self.df = dataframe
        self.df_summary = self._get_dataframe_summary(dataframe)
        self.config = config
        self.conversation_history = []
        # If no callback is provided, use a simple print statement for debugging
        self.callback = progress_callback if callable(progress_callback) else lambda data: print(data)

    def _get_dataframe_summary(self, df: pd.DataFrame) -> str:
        buffer = io.StringIO()
        df.info(buf=buffer)
        return f"The DataFrame `df` has {len(df)} rows and these columns:\n{buffer.getvalue()}"

    def _call_llm_api(self, messages, model_name, temperature):
        data = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "stream": False
        }
        try:
            response = requests.post(self.config.LLM_API_URL, headers={"Content-Type": "application/json"}, json=data)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            print(f"❌ API Request Error: {e}")
            self.callback({'stage': 'error', 'error': f"API Request Error: Could not connect to the LLM API."})
            return f"Error calling LLM API: {str(e)}"

    def _build_chat_messages(self, system_prompt: str, history: list, query: str) -> list:
        messages = [{"role": "system", "content": system_prompt}]
        for turn in history:
            messages.append({"role": "user", "content": turn["user"]})
            messages.append({"role": "assistant", "content": turn["assistant"]})
        messages.append({"role": "user", "content": query})
        return messages

    def _python_executor(self, code_string: str) -> str:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        global_scope = {'df': self.df.copy(), 'pd': pd}
        try:
            with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
                # THE FIX: Set pandas options before executing the agent's code.
                # This ensures that any printed DataFrame will show the full content.
                pd.set_option('display.max_colwidth', None)
                pd.set_option('display.width', 1000) # Also increase total width to prevent line wrapping
                exec(code_string, global_scope)
            stderr_result = stderr_buffer.getvalue()
            if stderr_result: return f"ERROR: {stderr_result}"
            stdout_result = stdout_buffer.getvalue()
            return stdout_result if stdout_result.strip() else ""
        except Exception as e:
            return f"ERROR: {type(e).__name__}: {e}"

    def _router_agent(self, query: str, history: list) -> dict:
        self.callback({'stage': 'router', 'status': 'running'})
        system_prompt = """You are a router agent. Classify the user's query into `analysis` or `direct_answer`. Consider the conversation history for context.
Respond with ONLY a JSON object like `{"decision": "analysis"}` or `{"decision": "direct_answer", "answer": "Your **Markdown-formatted** response in Arabic."}`."""
        messages = self._build_chat_messages(system_prompt, history, f"Query: {query}")
        response_text = self._call_llm_api(messages, self.config.ROUTER_MODEL, 0.2)
        try:
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                decision = json.loads(json_match.group(0))
                self.callback({'stage': 'router', 'status': 'complete', 'decision': decision['decision']})
                return decision
        except (json.JSONDecodeError, AttributeError):
            pass # Fall through to default
        self.callback({'stage': 'router', 'status': 'complete', 'decision': 'analysis'})
        return {"decision": "analysis"}

    def _planner_agent(self, query: str, history: list, failed_code: str = None, feedback: str = None) -> str:
        stage_name = 'reflection' if failed_code else 'planner'
        self.callback({'stage': stage_name, 'status': 'running'})
        
        if failed_code:
            system_prompt = """You are an expert data analyst. Your previous script FAILED.
**CRITICAL ANALYSIS:** Your script likely failed because you IGNORED a core rule. The most common error is trying to load data (e.g., using `pd.read_csv`), but the DataFrame `df` is ALREADY in memory.
Analyze the user query, history, your broken code, and the error. Create a NEW, correct script.
**ABSOLUTE RULES:**
1.  The DataFrame `df` is ALREADY LOADED. Use it directly.
2.  **DO NOT** use `pd.read_csv` or any file-reading functions. This will cause an error.
3.  The script must be directly executable.
4.  The final line MUST be a `print()` statement.
Respond ONLY with the Python code, wrapped in ```python ... ```."""
            user_prompt_content = f"**Data Schema:**\n{self.df_summary}\n\n**Your Failed Code:**\n```python\n{failed_code}\n```\n\n**Feedback / Error Message:**\n{feedback}"
            messages = self._build_chat_messages(system_prompt, history, user_prompt_content)
        else:
            system_prompt = """You are an expert data scientist. Your task is to write a Python script to answer the user's query.

**ENVIRONMENT & TOOLS:**
- The DataFrame `df` is ALREADY LOADED in memory. DO NOT use `pd.read_csv`.
- Usually, the data is made up of Arabic and English text.
- You have a rich environment with the following key libraries pre-installed:
  - `pandas` (as pd): For data manipulation.
  - `numpy` (as np): For numerical operations.
  - `textblob`: For straightforward sentiment analysis and NLP.
  - `nltk.sentiment.SentimentIntensityAnalyzer`: For more nuanced sentiment analysis.
  - `sklearn`: For machine learning tasks (classification, clustering, etc.).
  - `matplotlib.pyplot` (as plt), `seaborn` (as sns): For creating data visualizations.

**RULES:**
1.  Choose the best tool for the job from the libraries provided.
2.  The script must be directly executable.
3.  The final line of your script MUST be a `print()` statement that displays the final answer or result.
4.  If the user asks for a plot, save it to a file (e.g., `plt.savefig('plot.png')`) and print the path to the file.

Respond ONLY with the Python code, wrapped in ```python ... ```."""
            messages = self._build_chat_messages(system_prompt, history, f"Data Schema:\n{self.df_summary}\n\nQuery:\n{query}")
        
        response_text = self._call_llm_api(messages, self.config.PLANNER_MODEL, 0.3)
        code_match = re.search(r'```python\n(.*?)\n```', response_text, re.DOTALL)
        script = code_match.group(1).strip() if code_match else ""
        
        if script:
            self.callback({'stage': stage_name, 'status': 'complete', 'code': script})
        else:
            self.callback({'stage': stage_name, 'status': 'failed', 'error': 'Agent failed to generate a valid script.'})
        return script

    def _synthesizer_agent(self, query: str, observation: str) -> str:
        self.callback({'stage': 'synthesis', 'status': 'running'})
        system_prompt = "You are an expert data analyst. Synthesize the results of a data analysis into a clear, comprehensive answer for the user in Arabic. **Use Markdown for formatting**, such as using `**bold**` for emphasis and numbered lists for ranking."
        messages = self._build_chat_messages(system_prompt, [], f"Query:\n{query}\n\nData Analysis Output:\n{observation}")
        final_answer = self._call_llm_api(messages, self.config.SYNTHESIZER_MODEL, 0.7)
        self.callback({'stage': 'synthesis', 'status': 'complete', 'answer': final_answer})
        return final_answer

    def _run_agent_workflow(self, query: str, history: list, timings: dict) -> str:
        script = self._planner_agent(query, history)
        if not script:
            return "Agent failed to create a script."

        for i in range(self.config.MAX_RETRIES):
            attempt = i + 1
            self.callback({'stage': 'execution', 'status': 'running', 'attempt': attempt, 'max_retries': self.config.MAX_RETRIES})
            observation = self._python_executor(script)
            
            if "ERROR:" in observation.upper():
                feedback = observation
                self.callback({'stage': 'execution', 'status': 'failed', 'attempt': attempt, 'output': feedback})
            elif not observation.strip():
                feedback = "CRITICAL: The script ran without errors but produced no output. Create a new script."
                self.callback({'stage': 'execution', 'status': 'failed', 'attempt': attempt, 'output': feedback})
            else:
                self.callback({'stage': 'execution', 'status': 'complete', 'attempt': attempt, 'output': observation})
                final_answer = self._synthesizer_agent(query, observation)
                return final_answer
            
            if i < self.config.MAX_RETRIES - 1:
                script = self._planner_agent(query, history, failed_code=script, feedback=feedback)
                if not script:
                    return "Agent failed to recover from error."
        
        return "Agent failed to recover after multiple attempts."

    def process_query(self, query: str) -> str:
        """The main entry point for processing a user query."""
        short_history = self.conversation_history[-self.config.HISTORY_LENGTH:]
        
        router_decision_obj = self._router_agent(query, short_history)
        decision = router_decision_obj.get("decision")
        final_answer = ""

        if decision == "analysis":
            final_answer = self._run_agent_workflow(query, short_history, {})
        elif decision == "direct_answer":
            final_answer = router_decision_obj.get("answer", "I can answer that directly, but there was an issue.")
            self.callback({'stage': 'synthesis', 'status': 'complete', 'answer': final_answer})
        else:
            final_answer = self._run_agent_workflow(query, short_history, {})

        self.conversation_history.append({"user": query, "assistant": final_answer})
        return final_answer