#!/usr/bin/env python3

import requests
import json
import os
import urllib3
import logging
import sys
from proxy_api import ProxyRotator

# Disable SSL warnings - Note: Only for testing purposes
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('YTS_FETCHER')

# YTS API base URL
YTS_API_URL = "https://yts.mx/api/v2/list_movies.json"

# Parameters for the API request (customize as needed)
DEFAULT_PARAMS = {
    'limit': 20,            # Number of movies to return
    'page': 1,              # Page number
    'quality': '1080p',     # Filter by quality (720p, 1080p, 2160p, 3D)
    'minimum_rating': 7.0,  # Filter by minimum rating
    'sort_by': 'download_count', # Sort by (title, year, rating, peers, seeds, download_count, etc.)
    'order_by': 'desc'      # Order by (desc, asc)
}

def load_working_proxies():
    """Load working proxies from the JSON file if it exists."""
    proxy_file = os.path.join(os.path.dirname(__file__), 'working_proxies.json')
    
    if os.path.exists(proxy_file):
        try:
            with open(proxy_file, 'r') as f:
                proxies_data = json.load(f)
            
            # Extract proxy URLs from the data
            proxy_list = [item['proxy'] for item in proxies_data]
            
            if proxy_list:
                logger.info(f"Loaded {len(proxy_list)} working proxies from {proxy_file}")
                return proxy_list
        except Exception as e:
            logger.warning(f"Failed to load proxies from {proxy_file}: {e}")
    
    logger.info("No working proxies file found, using defaults")
    return None

def fetch_movies(params=None, max_retries=5, retry_delay=3):
    """
    Fetch movies from YTS API using a rotating proxy with SSL verification disabled.
    
    Args:
        params: API parameters (dict)
        max_retries: Number of retry attempts for each request
        retry_delay: Delay between retries in seconds
        
    Returns:
        API response data (dict) or None if failed
    """
    # Use provided params or defaults
    params = params or DEFAULT_PARAMS
    
    # Load working proxies if available
    proxy_list = load_working_proxies()
    
    # Initialize the proxy rotator with potentially custom proxies
    proxy_rotator = ProxyRotator(
        proxy_list=proxy_list,
        verify_ssl=False,
        max_retries=max_retries,
        retry_delay=retry_delay
    )
    
    logger.info(f"Fetching movies from YTS API using proxy rotation")
    logger.info(f"Parameters: {params}")
    
    # Use the proxy_rotator to make the request
    response = proxy_rotator.request(
        method="GET",
        url=YTS_API_URL,
        params=params
    )
    
    if not response:
        logger.error("Failed to fetch movies after multiple retries")
        return None
    
    try:
        # Parse JSON response
        data = response.json()
        
        # Check if response is successful
        if data.get('status') != 'ok':
            logger.error(f"API error: {data.get('status_message', 'Unknown error')}")
            return None
            
        # Get movie data
        movie_count = data.get('data', {}).get('movie_count', 0)
        movie_list = data.get('data', {}).get('movies', [])
        
        logger.info(f"Successfully fetched {len(movie_list)} movies of {movie_count} total movies")
        
        # Save the response to a JSON file
        output_file = os.path.join(os.path.dirname(__file__), 'yts_movies.json')
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
            
        logger.info(f"Saved response to {output_file}")
        
        # Print a sample of movies
        print("\nSample of fetched movies:")
        for i, movie in enumerate(movie_list[:5]):  # Show first 5 movies
            print(f"{i+1}. {movie.get('title')} ({movie.get('year')}) - Rating: {movie.get('rating')}")
            
        return data
        
    except Exception as e:
        logger.error(f"Error processing response: {e}")
        return None

def main():
    """Main entry point with command-line argument handling."""
    # Allow custom parameters from command line
    try:
        if len(sys.argv) > 1:
            # Check if the argument is a valid JSON string
            custom_params = json.loads(sys.argv[1])
            fetch_movies(params=custom_params)
        else:
            fetch_movies()
    except json.JSONDecodeError:
        logger.error("Invalid JSON parameters. Please provide a valid JSON string.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 