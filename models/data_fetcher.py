"""
Data Fetcher Module

This module provides functionality to fetch data from various sources and save it to CSV format.
It supports multiple data sources including:
- NewsAPI (news articles)
- OpenWeatherMap (weather data)
- Alpha Vantage (stock market data)
- FRED (Federal Reserve Economic Data)
- GitHub (repository data)
- COVID-19 data
- World Bank data

The module uses environment variables for API keys, which should be stored in a .env file.
"""

import os
import json
import logging
import time
from typing import Dict, List, Any, Union, Optional, Tuple
from datetime import datetime
import pandas as pd
import requests
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data_fetcher.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DataFetcher")

# Load environment variables
load_dotenv()

# API Keys from environment variables
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")
OPENWEATHER_KEY = os.getenv("OPENWEATHER_KEY")
ALPHAVANTAGE_KEY = os.getenv("ALPHAVANTAGE_KEY")
FRED_KEY = os.getenv("FRED_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
# World Bank API doesn't require an API key
WORLDBANK_KEY = "not_required"

class DataFetcher:
    """
    DataFetcher class for retrieving data from various sources and saving to CSV.
    """
    
    def __init__(self):
        """Initialize the DataFetcher with API keys from environment variables."""
        self.api_keys = {
            "newsapi": NEWSAPI_KEY,
            "openweather": OPENWEATHER_KEY,
            "alphavantage": ALPHAVANTAGE_KEY,
            "fred": FRED_KEY,
            "github": GITHUB_TOKEN,
            "worldbank": WORLDBANK_KEY
        }
        
        # Check which APIs are available
        self.available_apis = {api: key is not None for api, key in self.api_keys.items()}
        
        # Log available APIs
        available = [api for api, available in self.available_apis.items() if available]
        logger.info(f"Available APIs: {', '.join(available)}")
        
        # Log missing APIs
        missing = [api for api, available in self.available_apis.items() if not available]
        if missing:
            logger.warning(f"Missing API keys for: {', '.join(missing)}")
    
    def fetch_news(self, query: str = None, sources: str = None, domains: str = None, 
                  from_date: str = None, to_date: str = None, language: str = "en", 
                  sort_by: str = "publishedAt", page_size: int = 20) -> Dict:
        """
        Fetch news articles from NewsAPI.
        
        Args:
            query: Keywords or phrases to search for
            sources: Comma-separated string of news sources
            domains: Comma-separated string of domains
            from_date: Start date in YYYY-MM-DD format
            to_date: End date in YYYY-MM-DD format
            language: Language code (e.g., 'en' for English)
            sort_by: Sort order (relevancy, popularity, publishedAt)
            page_size: Number of results to return (max 100)
            
        Returns:
            Dictionary containing news articles
        """
        if not self.available_apis["newsapi"]:
            logger.warning("NewsAPI key not available")
            return {"error": "NewsAPI key not available"}
        
        url = "https://newsapi.org/v2/everything"
        
        params = {
            "apiKey": self.api_keys["newsapi"],
            "language": language,
            "sortBy": sort_by,
            "pageSize": page_size
        }
        
        # Add optional parameters if provided
        if query:
            params["q"] = query
        if sources:
            params["sources"] = sources
        if domains:
            params["domains"] = domains
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        
        try:
            logger.info(f"Fetching news with params: {params}")
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"NewsAPI error: {str(e)}")
            return {"error": str(e)}
    
    def fetch_weather(self, location: str, units: str = "metric", days: int = 5) -> Dict:
        """
        Fetch weather data from OpenWeatherMap.
        
        Args:
            location: City name or coordinates
            units: Units of measurement (metric, imperial, standard)
            days: Number of forecast days
            
        Returns:
            Dictionary containing weather data
        """
        if not self.available_apis["openweather"]:
            logger.warning("OpenWeatherMap API key not available")
            return {"error": "OpenWeatherMap API key not available"}
        
        # Current weather
        current_url = "https://api.openweathermap.org/data/2.5/weather"
        current_params = {
            "q": location,
            "units": units,
            "appid": self.api_keys["openweather"]
        }
        
        # Forecast
        forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
        forecast_params = {
            "q": location,
            "units": units,
            "cnt": days * 8,  # 8 data points per day (3-hour intervals)
            "appid": self.api_keys["openweather"]
        }
        
        try:
            logger.info(f"Fetching weather for {location}")
            
            # Get current weather
            current_response = requests.get(current_url, params=current_params)
            current_response.raise_for_status()
            current_data = current_response.json()
            
            # Get forecast
            forecast_response = requests.get(forecast_url, params=forecast_params)
            forecast_response.raise_for_status()
            forecast_data = forecast_response.json()
            
            # Combine data
            return {
                "current": current_data,
                "forecast": forecast_data
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenWeatherMap API error: {str(e)}")
            return {"error": str(e)}
    
    def fetch_stock_data(self, symbol: str, function: str = "TIME_SERIES_DAILY", 
                        outputsize: str = "compact") -> Dict:
        """
        Fetch stock market data from Alpha Vantage.
        
        Args:
            symbol: Stock symbol (e.g., AAPL for Apple)
            function: Data function (TIME_SERIES_INTRADAY, TIME_SERIES_DAILY, etc.)
            outputsize: Output size (compact or full)
            
        Returns:
            Dictionary containing stock data
        """
        if not self.available_apis["alphavantage"]:
            logger.warning("Alpha Vantage API key not available")
            return {"error": "Alpha Vantage API key not available"}
        
        url = "https://www.alphavantage.co/query"
        params = {
            "function": function,
            "symbol": symbol,
            "outputsize": outputsize,
            "apikey": self.api_keys["alphavantage"]
        }
        
        try:
            logger.info(f"Fetching stock data for {symbol}")
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Alpha Vantage API error: {str(e)}")
            return {"error": str(e)}
    
    def fetch_fred_data(self, series_id: str, observation_start: str = None, 
                       observation_end: str = None, units: str = "lin") -> Dict:
        """
        Fetch economic data from FRED (Federal Reserve Economic Data).
        
        Args:
            series_id: FRED series ID (e.g., GDP, UNRATE)
            observation_start: Start date in YYYY-MM-DD format
            observation_end: End date in YYYY-MM-DD format
            units: Units transformation (lin, chg, ch1, pch, pc1, pca, cch, cca)
            
        Returns:
            Dictionary containing economic data
        """
        if not self.available_apis["fred"]:
            logger.warning("FRED API key not available")
            return {"error": "FRED API key not available"}
        
        url = f"https://api.stlouisfed.org/fred/series/observations"
        params = {
            "series_id": series_id,
            "api_key": self.api_keys["fred"],
            "file_type": "json",
            "units": units
        }
        
        # Add optional parameters if provided
        if observation_start:
            params["observation_start"] = observation_start
        if observation_end:
            params["observation_end"] = observation_end
        
        try:
            logger.info(f"Fetching FRED data for series {series_id}")
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"FRED API error: {str(e)}")
            return {"error": str(e)}
    
    def fetch_github_data(self, repo_owner: str, repo_name: str, data_type: str = "repo") -> Dict:
        """
        Fetch data from GitHub API.
        
        Args:
            repo_owner: Repository owner/organization
            repo_name: Repository name
            data_type: Type of data to fetch (repo, issues, commits, pulls)
            
        Returns:
            Dictionary containing GitHub data
        """
        if not self.available_apis["github"]:
            logger.warning("GitHub token not available")
            return {"error": "GitHub token not available"}
        
        headers = {
            "Authorization": f"token {self.api_keys['github']}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        base_url = "https://api.github.com"
        
        # Determine endpoint based on data_type
        if data_type == "repo":
            url = f"{base_url}/repos/{repo_owner}/{repo_name}"
        elif data_type == "issues":
            url = f"{base_url}/repos/{repo_owner}/{repo_name}/issues"
        elif data_type == "commits":
            url = f"{base_url}/repos/{repo_owner}/{repo_name}/commits"
        elif data_type == "pulls":
            url = f"{base_url}/repos/{repo_owner}/{repo_name}/pulls"
        else:
            return {"error": f"Invalid data_type: {data_type}"}
        
        try:
            logger.info(f"Fetching GitHub {data_type} data for {repo_owner}/{repo_name}")
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"GitHub API error: {str(e)}")
            return {"error": str(e)}
    
    def fetch_covid_data(self, country: str = None) -> Dict:
        """
        Fetch COVID-19 data from disease.sh API.
        
        Args:
            country: Country name (optional, if None returns global data)
            
        Returns:
            Dictionary containing COVID-19 data
        """
        base_url = "https://disease.sh/v3/covid-19"
        
        if country:
            url = f"{base_url}/countries/{country}"
        else:
            url = f"{base_url}/all"
        
        try:
            logger.info(f"Fetching COVID-19 data for {'global' if not country else country}")
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"COVID-19 API error: {str(e)}")
            return {"error": str(e)}
    
    def fetch_worldbank_data(self, indicator: str, country: str = "all", 
                            start_year: int = 2010, end_year: int = 2022) -> Dict:
        """
        Fetch data from World Bank API (no API key required).
        
        Args:
            indicator: World Bank indicator code (e.g., NY.GDP.MKTP.CD for GDP)
            country: Country code or 'all' for all countries
            start_year: Start year for data
            end_year: End year for data
            
        Returns:
            Dictionary containing World Bank data
        """
        """
        Fetch data from World Bank API.
        
        Args:
            indicator: World Bank indicator code (e.g., NY.GDP.MKTP.CD for GDP)
            country: Country code or 'all' for all countries
            start_year: Start year for data
            end_year: End year for data
            
        Returns:
            Dictionary containing World Bank data
        """
        url = f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"
        params = {
            "date": f"{start_year}:{end_year}",
            "format": "json",
            "per_page": 1000
        }
        
        try:
            logger.info(f"Fetching World Bank data for indicator {indicator}")
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"World Bank API error: {str(e)}")
            return {"error": str(e)}
    
    def save_to_csv(self, data: Union[Dict, List], filepath: str, flatten: bool = True) -> str:
        """
        Save data to CSV file.
        
        Args:
            data: Data to save (dictionary or list)
            filepath: Path to save the CSV file
            flatten: Whether to flatten nested dictionaries
            
        Returns:
            Path to the saved CSV file
        """
        try:
            # Convert data to DataFrame
            if isinstance(data, dict):
                if "error" in data:
                    logger.error(f"Cannot save data with error: {data['error']}")
                    return None
                
                # Handle different API responses
                if "articles" in data:  # NewsAPI
                    df = pd.DataFrame(data["articles"])
                elif "observations" in data:  # FRED
                    df = pd.DataFrame(data["observations"])
                elif "current" in data and "forecast" in data:  # Weather
                    # Combine current and forecast data
                    current = pd.json_normalize(data["current"])
                    forecast = pd.json_normalize(data["forecast"]["list"])
                    # Save separately
                    current_path = filepath.replace(".csv", "_current.csv")
                    forecast_path = filepath.replace(".csv", "_forecast.csv")
                    current.to_csv(current_path, index=False)
                    forecast.to_csv(forecast_path, index=False)
                    logger.info(f"Saved weather data to {current_path} and {forecast_path}")
                    return [current_path, forecast_path]
                else:
                    # Try to convert to DataFrame, flattening if needed
                    if flatten:
                        df = pd.json_normalize(data)
                    else:
                        df = pd.DataFrame([data])
            elif isinstance(data, list):
                if flatten:
                    df = pd.json_normalize(data)
                else:
                    df = pd.DataFrame(data)
            else:
                logger.error(f"Unsupported data type: {type(data)}")
                return None
            
            # Save to CSV
            df.to_csv(filepath, index=False)
            logger.info(f"Saved data to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error saving to CSV: {str(e)}")
            return None

# Convenience functions for direct use

def fetch_news_to_csv(query: str = None, sources: str = None, filepath: str = "news_data.csv", **kwargs) -> str:
    """
    Fetch news data and save directly to CSV.
    
    Args:
        query: Search query
        sources: News sources
        filepath: Output CSV path
        **kwargs: Additional parameters for fetch_news
        
    Returns:
        Path to saved CSV file
    """
    fetcher = DataFetcher()
    data = fetcher.fetch_news(query=query, sources=sources, **kwargs)
    return fetcher.save_to_csv(data, filepath)

def fetch_weather_to_csv(location: str, filepath: str = "weather_data.csv", **kwargs) -> str:
    """
    Fetch weather data and save directly to CSV.
    
    Args:
        location: Location name
        filepath: Output CSV path
        **kwargs: Additional parameters for fetch_weather
        
    Returns:
        Path to saved CSV file
    """
    fetcher = DataFetcher()
    data = fetcher.fetch_weather(location=location, **kwargs)
    return fetcher.save_to_csv(data, filepath)

def fetch_stock_to_csv(symbol: str, filepath: str = "stock_data.csv", **kwargs) -> str:
    """
    Fetch stock data and save directly to CSV.
    
    Args:
        symbol: Stock symbol
        filepath: Output CSV path
        **kwargs: Additional parameters for fetch_stock_data
        
    Returns:
        Path to saved CSV file
    """
    fetcher = DataFetcher()
    data = fetcher.fetch_stock_data(symbol=symbol, **kwargs)
    return fetcher.save_to_csv(data, filepath)

def fetch_fred_to_csv(series_id: str, filepath: str = "fred_data.csv", **kwargs) -> str:
    """
    Fetch FRED economic data and save directly to CSV.
    
    Args:
        series_id: FRED series ID
        filepath: Output CSV path
        **kwargs: Additional parameters for fetch_fred_data
        
    Returns:
        Path to saved CSV file
    """
    fetcher = DataFetcher()
    data = fetcher.fetch_fred_data(series_id=series_id, **kwargs)
    return fetcher.save_to_csv(data, filepath)

def fetch_github_to_csv(repo_owner: str, repo_name: str, filepath: str = "github_data.csv", **kwargs) -> str:
    """
    Fetch GitHub data and save directly to CSV.
    
    Args:
        repo_owner: Repository owner
        repo_name: Repository name
        filepath: Output CSV path
        **kwargs: Additional parameters for fetch_github_data
        
    Returns:
        Path to saved CSV file
    """
    fetcher = DataFetcher()
    data = fetcher.fetch_github_data(repo_owner=repo_owner, repo_name=repo_name, **kwargs)
    return fetcher.save_to_csv(data, filepath)

def fetch_covid_to_csv(country: str = None, filepath: str = "covid_data.csv") -> str:
    """
    Fetch COVID-19 data and save directly to CSV.
    
    Args:
        country: Country name (optional)
        filepath: Output CSV path
        
    Returns:
        Path to saved CSV file
    """
    fetcher = DataFetcher()
    data = fetcher.fetch_covid_data(country=country)
    return fetcher.save_to_csv(data, filepath)

def fetch_worldbank_to_csv(indicator: str, filepath: str = "worldbank_data.csv", **kwargs) -> str:
    """
    Fetch World Bank data and save directly to CSV.
    
    Args:
        indicator: World Bank indicator code
        filepath: Output CSV path
        **kwargs: Additional parameters for fetch_worldbank_data
        
    Returns:
        Path to saved CSV file
    """
    fetcher = DataFetcher()
    data = fetcher.fetch_worldbank_data(indicator=indicator, **kwargs)
    return fetcher.save_to_csv(data, filepath)

# Example usage
if __name__ == "__main__":
    # Create a DataFetcher instance
    fetcher = DataFetcher()
    
    # Example: Fetch news about technology and save to CSV
    news_data = fetcher.fetch_news(query="technology", page_size=10)
    fetcher.save_to_csv(news_data, "technology_news.csv")
    
    # Example: Fetch weather for New York
    weather_data = fetcher.fetch_weather(location="New York")
    fetcher.save_to_csv(weather_data, "new_york_weather.csv")
    
    # Example: Fetch stock data for Apple
    stock_data = fetcher.fetch_stock_data(symbol="AAPL")
    fetcher.save_to_csv(stock_data, "apple_stock.csv")
    
    # Example: Fetch GDP data from FRED
    fred_data = fetcher.fetch_fred_data(series_id="GDP")
    fetcher.save_to_csv(fred_data, "gdp_data.csv")
    
    # Example: Fetch GitHub data for a repository
    github_data = fetcher.fetch_github_data(repo_owner="microsoft", repo_name="vscode")
    fetcher.save_to_csv(github_data, "vscode_github.csv")
    
    # Example: Fetch COVID-19 data for the US
    covid_data = fetcher.fetch_covid_data(country="usa")
    fetcher.save_to_csv(covid_data, "usa_covid.csv")
    
    # Example: Fetch World Bank GDP data
    worldbank_data = fetcher.fetch_worldbank_data(indicator="NY.GDP.MKTP.CD")
    fetcher.save_to_csv(worldbank_data, "worldbank_gdp.csv")