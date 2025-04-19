import json
import time
from proxy_utility import ProxyUtility

def main():
    # Load the watchlist
    with open('kokkithedon_watchlist.json', 'r') as f:
        watchlist_data = json.load(f)
    
    # Initialize the proxy utility
    proxy_util = ProxyUtility()
    
    # Dictionary to store all responses
    all_responses = {}
    
    # Process each movie in the watchlist
    for movie in watchlist_data.get('watchlist', []):
        movie_id = movie.get('id')
        if not movie_id:
            continue
        
        print(f"Fetching data for movie: {movie.get('title')} (ID: {movie_id})")
        
        # Build API URL with query parameter
        url = f'https://yts.mx/api/v2/list_movies.json?query_term={movie_id}'
        
        # Make request through proxy
        response = proxy_util.request(url)
        
        if response:
            try:
                # Store the JSON response
                movie_data = response.json()
                all_responses[movie_id] = movie_data
                print(f"Successfully fetched data for {movie_id}")
            except Exception as e:
                print(f"Error parsing response for {movie_id}: {e}")
        else:
            print(f"Failed to get data for {movie_id}")
        
        # Add a small delay to avoid overwhelming the API
        time.sleep(1)
    
    # Save all responses to a file
    output_file = 'yts_movie_data.json'
    with open(output_file, 'w') as f:
        json.dump(all_responses, f, indent=4)
    
    print(f"All movie data saved to {output_file}")

if __name__ == "__main__":
    main() 