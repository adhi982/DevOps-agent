import os
import json
import time
import logging
from typing import Dict, List, Any, Union, Optional, Tuple
from datetime import datetime

import google.generativeai as genai
from dotenv import load_dotenv

# Global instance for convenience functions
_gemini_assistant = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("gemini_assistant.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("GeminiAssistant")

# Load environment variables
load_dotenv()

# Initialize API configuration
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    logger.info("Gemini API configured successfully")
else:
    logger.warning("⚠️ Gemini API key missing. Set GOOGLE_API_KEY in your .env file.")

# Model configuration
MODELS = {
    "default": "gemini-2.0-flash",  # Faster, default model
    "advanced": "gemini-2.0",       # More capable model
    "vision": "gemini-2.0-vision"   # For processing images
}

# -------------------- GEMINI CLIENT CLASS --------------------

class GeminiAssistant:
    """Enhanced Gemini Assistant for data collection, processing, and analysis."""
    
    def __init__(self, model_type: str = "default", temperature: float = 0.2):
        """Initialize the Gemini Assistant.
        
        Args:
            model_type: The type of model to use ("default", "advanced", or "vision")
            temperature: Controls randomness (0.0-1.0)
        """
        self.api_key = api_key
        self.model_type = model_type
        self.model_name = MODELS.get(model_type, MODELS["default"])
        self.temperature = temperature
        
        # Initialize model if API key is available
        if self.api_key:
            self.model = genai.GenerativeModel(
                self.model_name,
                generation_config={"temperature": self.temperature}
            )
            logger.info(f"Using Gemini model: {self.model_name}")
        else:
            self.model = None
            logger.warning("Running in mock mode (no API key)")
        
        # Track conversation history for context
        self.conversation_history = []
        self.max_history_length = 10
    
    def ask(self, prompt: str, include_history: bool = True) -> str:
        """Send a prompt to Gemini and get a response.
        
        Args:
            prompt: The user's query
            include_history: Whether to include conversation history
            
        Returns:
            The model's response text
        """
        if not self.api_key:
            return self._get_mock_response(prompt)
        
        try:
            # Create a conversation with history if requested
            if include_history and self.conversation_history:
                chat = self.model.start_chat(history=self.conversation_history)
                response = chat.send_message(prompt)
            else:
                response = self.model.generate_content(prompt)
            
            # Update conversation history
            self._update_history(prompt, response.text)
            
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            return f"❌ Gemini Error: {str(e)}"
    
    def analyze_data(self, data: Any, analysis_type: str = "general") -> str:
        """Analyze provided data with specific analysis instructions.
        
        Args:
            data: The data to analyze (can be dict, list, string, etc.)
            analysis_type: Type of analysis to perform
                ("general", "trends", "anomalies", "summary", "recommendations")
                
        Returns:
            Analysis results as text
        """
        analysis_prompts = {
            "general": "Analyze this data and provide key insights:",
            "trends": "Identify and explain key trends in this data:",
            "anomalies": "Identify any anomalies or outliers in this data:",
            "summary": "Provide a comprehensive summary of this data:",
            "recommendations": "Based on this data, provide actionable recommendations:"
        }
        
        prompt = f"""{analysis_prompts.get(analysis_type, analysis_prompts["general"])}
        
        DATA:
        {data}
        
        Format your response with clear sections. Include specific numbers and percentages when relevant.
        Use markdown formatting for better readability.
        """
        
        return self.ask(prompt, include_history=False)
    
    def generate_data_schema(self, data_sample: Union[List, Dict]) -> Dict:
        """Generate a schema recommendation for the given data sample.
        
        Args:
            data_sample: Sample data to analyze
            
        Returns:
            Dictionary with schema recommendations
        """
        prompt = f"""
        Analyze this data sample and recommend an optimal schema structure.
        Include field names, data types, and any constraints.
        Format response as valid JSON.
        
        DATA SAMPLE:
        {json.dumps(data_sample, indent=2)}
        """
        
        try:
            schema_text = self.ask(prompt, include_history=False)
            # Extract JSON from the response if needed
            if "```json" in schema_text:
                schema_text = schema_text.split("```json")[1].split("```")[0].strip()
            return json.loads(schema_text)
        except json.JSONDecodeError:
            logger.error("Failed to parse schema JSON")
            return {"error": "Could not generate valid schema"}
    
    def extract_structured_data(self, text: str, schema: Optional[Dict] = None) -> Dict:
        """Extract structured data from unstructured text.
        
        Args:
            text: The text to process
            schema: Optional schema to guide extraction
            
        Returns:
            Dictionary of extracted structured data
        """
        schema_str = json.dumps(schema) if schema else "appropriate fields based on content"
        
        prompt = f"""
        Extract structured data from the following text.
        Return ONLY a valid JSON object with {schema_str}.
        
        TEXT:
        {text}
        """
        
        try:
            extracted_text = self.ask(prompt, include_history=False)
            # Extract JSON from the response if needed
            if "```json" in extracted_text:
                extracted_text = extracted_text.split("```json")[1].split("```")[0].strip()
            return json.loads(extracted_text)
        except json.JSONDecodeError:
            logger.error("Failed to parse extracted JSON")
            return {"error": "Could not extract structured data"}
    
    def generate_data_cleaning_instructions(self, data_sample: Union[List, Dict]) -> List[Dict]:
        """Generate data cleaning recommendations for the sample.
        
        Args:
            data_sample: Sample data to analyze
            
        Returns:
            List of cleaning instructions
        """
        prompt = f"""
        Analyze this data sample and provide specific data cleaning instructions.
        For each issue found, include:
        1. The field or column name
        2. The issue type (missing values, outliers, formatting, etc.)
        3. A recommended cleaning approach
        
        Format your response as a valid JSON array of cleaning instructions.
        
        DATA SAMPLE:
        {json.dumps(data_sample, indent=2)}
        """
        
        try:
            instructions_text = self.ask(prompt, include_history=False)
            # Extract JSON from the response if needed
            if "```json" in instructions_text:
                instructions_text = instructions_text.split("```json")[1].split("```")[0].strip()
            return json.loads(instructions_text)
        except json.JSONDecodeError:
            logger.error("Failed to parse cleaning instructions JSON")
            return [{"error": "Could not generate valid cleaning instructions"}]
    
    def generate_visualization_recommendations(self, data_schema: Dict) -> List[Dict]:
        """Generate visualization recommendations based on data schema.
        
        Args:
            data_schema: Schema describing the data structure
            
        Returns:
            List of visualization recommendations
        """
        prompt = f"""
        Based on this data schema, recommend appropriate visualizations.
        For each visualization, include:
        1. Chart type (bar chart, line chart, scatter plot, etc.)
        2. Fields to use
        3. Why this visualization would be insightful
        
        Format your response as a valid JSON array of visualization recommendations.
        
        DATA SCHEMA:
        {json.dumps(data_schema, indent=2)}
        """
        
        try:
            viz_text = self.ask(prompt, include_history=False)
            # Extract JSON from the response if needed
            if "```json" in viz_text:
                viz_text = viz_text.split("```json")[1].split("```")[0].strip()
            return json.loads(viz_text)
        except json.JSONDecodeError:
            logger.error("Failed to parse visualization JSON")
            return [{"error": "Could not generate valid visualization recommendations"}]
    
    def generate_query(self, description: str, data_source: str) -> str:
        """Generate a query for a given data source based on description.
        
        Args:
            description: Natural language description of the query
            data_source: Type of data source (sql, mongodb, api, etc.)
            
        Returns:
            Generated query string
        """
        query_formats = {
            "sql": "SQL query with proper syntax",
            "mongodb": "MongoDB query using proper syntax",
            "csv": "Python Pandas code to filter/query the data",
            "api": "API request parameters in JSON format",
            "newsapi": "NewsAPI query parameters",
            "github": "GitHub API parameters",
            "fred": "FRED API query parameters"
        }
        
        format_instruction = query_formats.get(data_source.lower(), "appropriate query format")
        
        prompt = f"""
        Generate a {format_instruction} for the following query description:
        
        DESCRIPTION: {description}
        
        Return ONLY the query without explanation.
        """
        
        return self.ask(prompt, include_history=False)
    
    def detect_intent(self, text: str) -> Tuple[str, float]:
        """Detect the intent of a user query with confidence score.
        
        Args:
            text: The user's query text
            
        Returns:
            Tuple of (intent_name, confidence_score)
        """
        intents = [
            "data_fetch",        # Fetch data from a source
            "data_analysis",     # Analyze existing data
            "data_cleaning",     # Clean or preprocess data
            "visualization",     # Create visualizations
            "export",            # Export or save data
            "database",          # Database operations
            "general_question",  # General questions
            "comparison",        # Compare datasets
            "prediction",        # Make predictions
            "newsapi",           # News related queries
            "weather",           # Weather related queries
            "fred",              # Economic data queries
            "github",            # GitHub related queries
            "datahub",           # General data hub queries
            "help"               # Help with the application
        ]
        
        prompt = f"""
        Act as an intent classifier for a data assistant application.
        Classify the user's query into ONE of these intents:
        {', '.join(intents)}
        
        Also provide a confidence score between 0.0 and 1.0.
        
        User query: "{text}"
        
        Respond in this JSON format:
        {{
          "intent": "intent_name",
          "confidence": 0.0
        }}
        """
        
        try:
            response = self.ask(prompt, include_history=False)
            # Extract JSON from the response
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            
            result = json.loads(response)
            return (result["intent"], result["confidence"])
        except (json.JSONDecodeError, KeyError):
            logger.error("Failed to parse intent JSON")
            return ("general_question", 0.5)
    
    def generate_data_transformation_code(self, 
                                         source_data_format: str, 
                                         target_data_format: str,
                                         example_data: str = None) -> str:
        """Generate Python code for data transformation.
        
        Args:
            source_data_format: Format of source data (CSV, JSON, etc.)
            target_data_format: Desired output format
            example_data: Example of the data (optional)
            
        Returns:
            Python code for transformation
        """
        prompt = f"""
        Generate Python code to transform data from {source_data_format} format to {target_data_format} format.
        
        Include proper error handling and comments.
        Use pandas, numpy, and other appropriate libraries.
        """
        
        if example_data:
            prompt += f"\n\nExample of source data:\n{example_data}"
        
        prompt += "\n\nReturn only the Python code without explanations."
        
        response = self.ask(prompt, include_history=False)
        
        # Extract code from the response if needed
        if "```python" in response:
            response = response.split("```python")[1].split("```")[0].strip()
            
        return response
    
    def generate_report_template(self, data_type: str, audience: str) -> str:
        """Generate a report template for specific data and audience.
        
        Args:
            data_type: Type of data being reported on
            audience: Target audience (executives, analysts, etc.)
            
        Returns:
            Markdown report template
        """
        prompt = f"""
        Create a detailed report template for {data_type} data targeted at {audience}.
        
        Structure it with:
        - Executive summary
        - Key findings
        - Detailed analysis sections
        - Recommendations
        - Appendix
        
        Use markdown formatting. Include placeholders for data points and insights.
        """
        
        response = self.ask(prompt, include_history=False)
        return response
    
    def _update_history(self, user_input: str, assistant_response: str) -> None:
        """Update conversation history with the latest exchange.
        
        Args:
            user_input: User's message
            assistant_response: Assistant's response
        """
        # Add the current exchange
        self.conversation_history.append({"role": "user", "parts": [user_input]})
        self.conversation_history.append({"role": "model", "parts": [assistant_response]})
        
        # Trim history if too long
        if len(self.conversation_history) > self.max_history_length * 2:
            # Keep the most recent exchanges
            self.conversation_history = self.conversation_history[-self.max_history_length * 2:]
    
    def _get_mock_response(self, prompt: str) -> str:
        """Generate mock responses when API key is not available.
        
        Args:
            prompt: User query
            
        Returns:
            Mock response based on query
        """
        from datetime import datetime
        import random
        
        prompt_lower = prompt.lower().strip()
        
        mock_responses = {
            "hello": "Hello there! I'm your data assistant. How can I help you today?",
            "what time is it": f"It's currently {datetime.now().strftime('%I:%M %p')} (simulated time in mock mode).",
            "help": "I can help you with data collection, cleaning, analysis, and visualization. What would you like to do?",
            "news": "[MOCK] Here are the latest headlines: 'Tech stocks surge', 'New climate report released', 'Sports team wins championship'",
            "weather": f"[MOCK] Current temperature is {random.randint(15, 30)}°C with {random.choice(['sunny', 'cloudy', 'rainy'])} conditions.",
            "analysis": "[MOCK] After analyzing your data, I found several interesting trends: spending increases on weekends, there are seasonal patterns in Q4, and some outliers in the March data.",
            "default": f"[MOCK RESPONSE] This is a simulated Gemini response since no API key was provided.\n\nI can help you with:\n- Data collection and integration\n- Data cleaning and preprocessing\n- Data analysis and visualization\n- Report generation\n\n(To get real responses, add GOOGLE_API_KEY to .env)"
        }
        
        # Try to match the prompt with predefined responses
        for key, response in mock_responses.items():
            if key in prompt_lower:
                return response
        
        return mock_responses["default"]


# Convenience functions for direct use

def get_gemini_assistant() -> GeminiAssistant:
    """Get or create a global GeminiAssistant instance."""
    global _gemini_assistant
    if _gemini_assistant is None:
        _gemini_assistant = GeminiAssistant()
    return _gemini_assistant

def ask_gemini(prompt: str, include_history: bool = True) -> str:
    """Convenience function to ask Gemini a question.
    
    Args:
        prompt: The user's query
        include_history: Whether to include conversation history
        
    Returns:
        The model's response text
    """
    assistant = get_gemini_assistant()
    return assistant.ask(prompt, include_history)

def detect_intent(text: str) -> str:
    """Detect the intent of a user query.
    
    Args:
        text: The user's query text
        
    Returns:
        The detected intent name
    """
    assistant = get_gemini_assistant()
    intent, confidence = assistant.detect_intent(text)
    return intent


# -------------------- DATA SOURCE HANDLERS --------------------

class DataSourceHandler:
    """Base class for handling different data sources."""
    
    def __init__(self, gemini_assistant: GeminiAssistant):
        self.gemini = gemini_assistant
    
    def handle_query(self, query: str) -> Dict:
        """Handle a natural language query for this data source.
        
        Args:
            query: Natural language query
            
        Returns:
            Results as dictionary
        """
        raise NotImplementedError("Subclasses must implement handle_query")
    
    def fetch_data(self, **params) -> Dict:
        """Fetch data from this source using specific parameters.
        
        Args:
            **params: Source-specific parameters
            
        Returns:
            Data as dictionary
        """
        raise NotImplementedError("Subclasses must implement fetch_data")
    
    def to_csv(self, data: Dict, filepath: str) -> str:
        """Convert data to CSV and save to file.
        
        Args:
            data: Data to convert
            filepath: Path to save CSV file
            
        Returns:
            Path to saved file
        """
        raise NotImplementedError("Subclasses must implement to_csv")


class NewsAPIHandler(DataSourceHandler):
    """Handler for NewsAPI data source."""
    
    def handle_query(self, query: str) -> Dict:
        """Handle natural language news queries.
        
        Args:
            query: Natural language query about news
            
        Returns:
            NewsAPI results
        """
        # Use Gemini to extract parameters from natural language
        prompt = f"""
        Convert this natural language query about news into NewsAPI parameters.
        Return ONLY a JSON object with these fields: q (query), sources, domains, 
        from, to, language, sortBy, pageSize.
        Only include fields that are relevant to the query.
        
        Query: "{query}"
        """
        
        try:
            params_text = self.gemini.ask(prompt, include_history=False)
            if "```json" in params_text:
                params_text = params_text.split("```json")[1].split("```")[0].strip()
            params = json.loads(params_text)
            
            # Call the fetch_data method with extracted parameters
            return self.fetch_data(**params)
        except Exception as e:
            logger.error(f"NewsAPI error: {str(e)}")
            return {"error": str(e)}
    
    def fetch_data(self, **params) -> Dict:
        """Fetch news data from NewsAPI.
        
        Args:
            **params: NewsAPI parameters
            
        Returns:
            News data
        """
        # Placeholder for actual NewsAPI implementation
        # In a real implementation, you would use requests to call the NewsAPI
        logger.info(f"Would fetch NewsAPI with params: {params}")
        return {
            "status": "ok",
            "totalResults": 10,
            "articles": [
                {"title": "Sample Article", "description": "This is a placeholder for NewsAPI integration"}
            ]
        }
    
    def to_csv(self, data: Dict, filepath: str) -> str:
        """Convert news data to CSV and save.
        
        Args:
            data: News data
            filepath: CSV output path
            
        Returns:
            Path to saved file
        """
        # In a real implementation, use pandas to convert to CSV
        logger.info(f"Would save news data to {filepath}")
        return filepath


class WeatherHandler(DataSourceHandler):
    """Handler for weather data."""
    
    def handle_query(self, query: str) -> Dict:
        """Handle natural language weather queries.
        
        Args:
            query: Natural language query about weather
            
        Returns:
            Weather data
        """
        # Extract location and other parameters
        prompt = f"""
        Extract weather query parameters from this text.
        Return ONLY a JSON object with: location, days (forecast days), 
        unit (metric/imperial), and any other relevant parameters.
        
        Query: "{query}"
        """
        
        try:
            params_text = self.gemini.ask(prompt, include_history=False)
            if "```json" in params_text:
                params_text = params_text.split("```json")[1].split("```")[0].strip()
            params = json.loads(params_text)
            
            return self.fetch_data(**params)
        except Exception as e:
            logger.error(f"Weather handling error: {str(e)}")
            return {"error": str(e)}
    
    def fetch_data(self, **params) -> Dict:
        """Fetch weather data.
        
        Args:
            **params: Weather API parameters
            
        Returns:
            Weather data
        """
        # Placeholder for weather API implementation
        logger.info(f"Would fetch weather with params: {params}")
        return {
            "location": params.get("location", "Unknown"),
            "current": {
                "temp": 22,
                "condition": "Partly cloudy",
                "humidity": 65
            },
            "forecast": [
                {"date": "2025-04-11", "max": 24, "min": 18, "condition": "Sunny"}
            ]
        }
    
    def to_csv(self, data: Dict, filepath: str) -> str:
        """Convert weather data to CSV and save.
        
        Args:
            data: Weather data
            filepath: CSV output path
            
        Returns:
            Path to saved file
        """
        logger.info(f"Would save weather data to {filepath}")
        return filepath


# -------------------- DATA PROCESSING --------------------

class DataProcessor:
    """Process and transform data from various sources."""
    
    def __init__(self, gemini_assistant: GeminiAssistant):
        self.gemini = gemini_assistant
    
    def clean_data(self, data: Union[List, Dict], instructions: List[Dict] = None) -> Dict:
        """Clean data based on instructions or auto-generated cleaning rules.
        
        Args:
            data: Data to clean
            instructions: Optional cleaning instructions
            
        Returns:
            Cleaned data and applied rules
        """
        # Generate cleaning instructions if not provided
        if not instructions:
            instructions = self.gemini.generate_data_cleaning_instructions(data)
        
        # In a real implementation, apply cleaning rules
        # This is a placeholder
        logger.info(f"Would clean data with {len(instructions)} rules")
        
        return {
            "cleaned_data": data,  # Replace with actual cleaned data
            "applied_rules": instructions
        }
    
    def transform_data(self, data: Union[List, Dict], output_format: str) -> Dict:
        """Transform data to desired format.
        
        Args:
            data: Input data
            output_format: Desired output format
            
        Returns:
            Transformed data
        """
        # Generate and execute transformation code
        # In a real implementation, this would execute the code
        logger.info(f"Would transform data to {output_format}")
        
        return {
            "transformed_data": data,  # Replace with actual transformed data
            "output_format": output_format
        }
    
    def merge_datasets(self, datasets: List[Dict], merge_key: str = None) -> Dict:
        """Merge multiple datasets.
        
        Args:
            datasets: List of datasets to merge
            merge_key: Key to use for merging
            
        Returns:
            Merged dataset
        """
        # In a real implementation, use pandas or similar to merge
        logger.info(f"Would merge {len(datasets)} datasets on key {merge_key}")
        
        return {
            "merged_data": {"sample": "merged data"},
            "merge_info": {"source_count": len(datasets), "key": merge_key}
        }


# -------------------- DATA ANALYSIS --------------------

class DataAnalyzer:
    """Analyze and extract insights from data."""
    
    def __init__(self, gemini_assistant: GeminiAssistant):
        self.gemini = gemini_assistant
    
    def analyze(self, data: Union[List, Dict], analysis_type: str = "general") -> Dict:
        """Analyze data with specified analysis type.
        
        Args:
            data: Data to analyze
            analysis_type: Type of analysis
            
        Returns:
            Analysis results
        """
        analysis = self.gemini.analyze_data(data, analysis_type)
        
        return {
            "analysis": analysis,
            "type": analysis_type,
            "timestamp": datetime.now().isoformat()
        }
    
    def generate_report(self, data: Union[List, Dict], audience: str = "general") -> str:
        """Generate a comprehensive report from data.
        
        Args:
            data: Data for report
            audience: Target audience
            
        Returns:
            Markdown report
        """
        # Get data type for template
        data_type = "general"
        if isinstance(data, list) and len(data) > 0:
            if all(isinstance(item, dict) for item in data):
                sample_keys = list(data[0].keys())
                data_type = f"tabular data with fields: {', '.join(sample_keys[:5])}"
        
        # Get report template
        template = self.gemini.generate_report_template(data_type, audience)
        
        # Generate report content
        prompt = f"""
        Fill in this report template with insights from the provided data.
        Use markdown formatting for better readability.
        Include charts and visualizations descriptions where appropriate.
        
        TEMPLATE:
        {template}
        
        DATA:
        {json.dumps(data)[:2000] + "..." if len(json.dumps(data)) > 2000 else json.dumps(data)}
        """
        
        report = self.gemini.ask(prompt, include_history=False)
        return report
    
    def compare_datasets(self, dataset1: Union[List, Dict], dataset2: Union[List, Dict]) -> Dict:
        """Compare two datasets and highlight differences.
        
        Args:
            dataset1: First dataset
            dataset2: Second dataset
            
        Returns:
            Comparison results
        """
        # Generate comparison
        prompt = f"""
        Compare these two datasets and identify key differences.
        Focus on structure, values, trends, and statistics.
        
        DATASET 1:
        {json.dumps(dataset1)[:1000] + "..." if len(json.dumps(dataset1)) > 1000 else json.dumps(dataset1)}
        
        DATASET 2:
        {json.dumps(dataset2)[:1000] + "..." if len(json.dumps(dataset2)) > 1000 else json.dumps(dataset2)}
        """
        
        comparison = self.gemini.ask(prompt, include_history=False)
        
        return {
            "comparison": comparison,
            "timestamp": datetime.now().isoformat()
        }


# -------------------- DATABASE INTEGRATION --------------------

class DatabaseHelper:
    """Helper for MongoDB integration."""
    
    def __init__(self, gemini_assistant: GeminiAssistant):
        self.gemini = gemini_assistant
    
    def generate_schema(self, data_sample: Union[List, Dict]) -> Dict:
        """Generate MongoDB schema for data.
        
        Args:
            data_sample: Sample data
            
        Returns:
            MongoDB schema
        """
        return self.gemini.generate_data_schema(data_sample)
    
    def generate_query(self, description: str) -> str:
        """Generate MongoDB query from description.
        
        Args:
            description: Query description
            
        Returns:
            MongoDB query string
        """
        return self.gemini.generate_query(description, "mongodb")


# -------------------- MAIN HELPER FUNCTIONS --------------------

def create_assistant(model_type: str = "default", temperature: float = 0.2) -> GeminiAssistant:
    """Create a new Gemini Assistant instance.
    
    Args:
        model_type: Model type to use
        temperature: Temperature setting
    
    Returns:
        GeminiAssistant instance
    """
    return GeminiAssistant(model_type=model_type, temperature=temperature)

def process_natural_language_query(assistant: GeminiAssistant, query: str) -> Dict:
    """Process a natural language query and route to appropriate handler.
    
    Args:
        assistant: GeminiAssistant instance
        query: Natural language query
    
    Returns:
        Response data
    """
    # Detect intent
    intent, confidence = assistant.detect_intent(query)
    
    # Create handlers based on intent
    handlers = {
        "newsapi": NewsAPIHandler(assistant),
        "weather": WeatherHandler(assistant),
        # Add other handlers here
    }
    
    # Route to appropriate handler or use default response
    if intent in handlers and confidence > 0.6:
        return {
            "intent": intent,
            "confidence": confidence,
            "response": handlers[intent].handle_query(query)
        }
    else:
        # General query handling
        return {
            "intent": intent,
            "confidence": confidence,
            "response": assistant.ask(query)
        }

def analyze_data_file(assistant: GeminiAssistant, file_path: str, analysis_type: str = "general") -> Dict:
    """Analyze a data file.
    
    Args:
        assistant: GeminiAssistant instance
        file_path: Path to data file
        analysis_type: Type of analysis
    
    Returns:
        Analysis results
    """
    # In a real implementation, determine file type and read accordingly
    # This is a placeholder
    file_ext = file_path.split('.')[-1].lower()
    
    if file_ext == 'json':
        with open(file_path, 'r') as f:
            data = json.load(f)
    elif file_ext in ['csv', 'xlsx', 'xls']:
        # In a real implementation, use pandas
        data = {"message": f"Would read {file_ext} file"}
    else:
        return {"error": f"Unsupported file type: {file_ext}"}
    
    analyzer = DataAnalyzer(assistant)
    return analyzer.analyze(data, analysis_type)

def save_to_mongodb(data: Union[List, Dict], collection_name: str) -> Dict:
    """Save data to MongoDB.
    
    Args:
        data: Data to save
        collection_name: MongoDB collection name
    
    Returns:
        Operation result
    """
    # Placeholder for MongoDB integration
    logger.info(f"Would save data to MongoDB collection: {collection_name}")
    
    return {
        "status": "success",
        "collection": collection_name,
        "record_count": len(data) if isinstance(data, list) else 1
    }


# Example usage
if __name__ == "__main__":
    # Create assistant
    assistant = create_assistant()
    
    # Process a query
    result = process_natural_language_query(
        assistant, 
        "Get me the latest news about technology companies"
    )
    
    print(json.dumps(result, indent=2))