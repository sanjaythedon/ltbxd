import json
import os
import requests
from proxy_utility import ProxyUtility

def download_2160p_torrents(json_file='yts_movie_data.json', output_folder='torrents'):
    """
    Downloads 2160p torrents for movies in the YTS movie data file.
    
    Args:
        json_file: Path to the YTS movie data JSON file
        output_folder: Folder to save the torrent files
    """
    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Created output folder: {output_folder}")
    
    # Initialize proxy utility
    proxy_util = ProxyUtility()
    
    # Load the JSON data
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # Count variables for stats
    total_entries = len(data)
    processed_entries = 0
    movies_with_2160p = 0
    successful_downloads = 0
    
    print(f"Processing {total_entries} entries from {json_file}...")
    
    # Process each entry in the JSON
    for movie_key, movie_data in data.items():
        processed_entries += 1
        
        # Check if the entry has movies data
        if 'data' in movie_data and 'movies' in movie_data['data'] and movie_data['data']['movies']:
            # Loop through each movie in the array
            for movie in movie_data['data']['movies']:
                movie_title = movie.get('title', 'Unknown')
                movie_year = movie.get('year', 'Unknown')
                
                # Check if the movie has torrents
                if 'torrents' in movie and movie['torrents']:
                    # Filter for 2160p quality
                    torrents_2160p = [t for t in movie['torrents'] if t.get('quality') == '2160p']
                    
                    if torrents_2160p:
                        movies_with_2160p += 1
                        torrent_url = torrents_2160p[0]['url']
                        
                        print(f"Found 2160p torrent for '{movie_title} ({movie_year})': {torrent_url}")
                        
                        # Create a safe filename
                        safe_title = "".join([c if c.isalnum() or c in ' ._-' else '_' for c in movie_title])
                        filename = f"{safe_title}_{movie_year}_2160p.torrent"
                        file_path = os.path.join(output_folder, filename)
                        
                        # Download the torrent file using proxy
                        try:
                            response = proxy_util.request(torrent_url)
                            
                            if response:
                                # Save the binary content
                                with open(file_path, 'wb') as torrent_file:
                                    torrent_file.write(response.content)
                                
                                successful_downloads += 1
                                print(f"Successfully downloaded to {file_path}")
                            else:
                                print(f"Failed to download torrent for {movie_title}")
                        except Exception as e:
                            print(f"Error downloading {movie_title} torrent: {e}")
        
        # Print progress every 10 entries
        if processed_entries % 10 == 0:
            print(f"Progress: {processed_entries}/{total_entries} entries processed")
    
    # Print summary
    print("\n--- Download Summary ---")
    print(f"Total entries processed: {processed_entries}")
    print(f"Movies with 2160p quality found: {movies_with_2160p}")
    print(f"Successfully downloaded torrents: {successful_downloads}")
    print(f"Torrents saved to: {os.path.abspath(output_folder)}")

if __name__ == "__main__":
    download_2160p_torrents() 