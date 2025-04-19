import json
import os
import requests
import time
from proxy_utility import ProxyUtility
from google_sheets_utility import GoogleSheetsUtility

def download_best_quality_torrents(json_file='yts_movie_data.json', output_folder='torrents', request_delay=1.0, 
                                 credentials_file=None, sheet_id=None, share_with_email=None):
    """
    Downloads best quality torrents for movies in the YTS movie data file.
    Priority: 2160p > 1080p bluray > 1080p web
    
    Args:
        json_file: Path to the YTS movie data JSON file
        output_folder: Folder to save the torrent files
        request_delay: Delay in seconds between torrent download requests
        credentials_file: Path to Google API credentials file
        sheet_id: Google Sheet ID to track downloads (if None, a new sheet will be created)
        share_with_email: Email address to share the created sheet with
    """
    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Created output folder: {output_folder}")
    
    # Initialize proxy utility
    proxy_util = ProxyUtility()
    
    # Initialize Google Sheets tracking (if credentials provided)
    sheets_util = None
    if credentials_file:
        try:
            sheets_util = GoogleSheetsUtility(credentials_file)
            if not sheet_id:
                sheet_id = sheets_util.create_movie_tracking_sheet(share_with=share_with_email)
                print(f"Created a new tracking sheet with ID: {sheet_id}")
            elif share_with_email and sheets_util:
                # Share existing sheet if email is provided
                sheets_util.share_sheet(sheet_id, share_with_email)
                
            print(f"Using Google Sheet ID: {sheet_id} for tracking downloads")
        except Exception as e:
            print(f"WARNING: Could not initialize Google Sheets tracking: {e}")
            sheets_util = None
    
    # Load the JSON data
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # Count variables for stats
    total_entries = len(data)
    processed_entries = 0
    movies_with_torrents = 0
    quality_stats = {'2160p': 0, '1080p_bluray': 0, '1080p_web': 0}
    successful_downloads = 0
    
    print(f"Processing {total_entries} entries from {json_file}...")
    print(f"Using {request_delay} second delay between requests")
    
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
                    selected_torrent = None
                    quality_type = None
                    
                    # 1. Check for 2160p quality
                    torrents_2160p = [t for t in movie['torrents'] if t.get('quality') == '2160p']
                    if torrents_2160p:
                        selected_torrent = torrents_2160p[0]
                        quality_type = '2160p'
                        quality_stats['2160p'] += 1
                    else:
                        # 2. Check for 1080p bluray
                        torrents_1080p_bluray = [t for t in movie['torrents'] 
                                               if t.get('quality') == '1080p' and t.get('type', '').lower() == 'bluray']
                        if torrents_1080p_bluray:
                            selected_torrent = torrents_1080p_bluray[0]
                            quality_type = '1080p_bluray'
                            quality_stats['1080p_bluray'] += 1
                        else:
                            # 3. Check for 1080p web
                            torrents_1080p_web = [t for t in movie['torrents'] 
                                                if t.get('quality') == '1080p' and t.get('type', '').lower() == 'web']
                            if torrents_1080p_web:
                                selected_torrent = torrents_1080p_web[0]
                                quality_type = '1080p_web'
                                quality_stats['1080p_web'] += 1
                    
                    # If we found a torrent matching our criteria
                    if selected_torrent:
                        movies_with_torrents += 1
                        torrent_url = selected_torrent['url']
                        
                        print(f"Found {quality_type} torrent for '{movie_title} ({movie_year})': {torrent_url}")
                        
                        # Create a safe filename
                        safe_title = "".join([c if c.isalnum() or c in ' ._-' else '_' for c in movie_title])
                        filename = f"{safe_title}_{movie_year}_{quality_type}.torrent"
                        file_path = os.path.join(output_folder, filename)
                        
                        # Download the torrent file using proxy
                        download_success = False
                        try:
                            response = proxy_util.request(torrent_url)
                            
                            if response:
                                # Save the binary content
                                with open(file_path, 'wb') as torrent_file:
                                    torrent_file.write(response.content)
                                
                                download_success = True
                                successful_downloads += 1
                                print(f"Successfully downloaded to {file_path}")
                                
                                # Add to Google Sheet if tracking is enabled
                                if sheets_util and sheet_id:
                                    sheets_util.add_movie_entry(
                                        sheet_id=sheet_id,
                                        movie_name=movie_title,
                                        year=movie_year,
                                        is_downloaded=True
                                    )
                            else:
                                print(f"Failed to download torrent for {movie_title}")
                        except Exception as e:
                            print(f"Error downloading {movie_title} torrent: {e}")
                        
                        # Sleep to avoid overwhelming the proxy server
                        print(f"Waiting {request_delay} seconds before next request...")
                        time.sleep(request_delay)
        
        # Print progress every 10 entries
        if processed_entries % 10 == 0:
            print(f"Progress: {processed_entries}/{total_entries} entries processed")
    
    # Print summary
    print("\n--- Download Summary ---")
    print(f"Total entries processed: {processed_entries}")
    print(f"Movies with matching torrents found: {movies_with_torrents}")
    print(f"Quality breakdown:")
    print(f"  - 2160p: {quality_stats['2160p']}")
    print(f"  - 1080p Bluray: {quality_stats['1080p_bluray']}")
    print(f"  - 1080p Web: {quality_stats['1080p_web']}")
    print(f"Successfully downloaded torrents: {successful_downloads}")
    print(f"Torrents saved to: {os.path.abspath(output_folder)}")
    if sheets_util and sheet_id:
        print(f"Download tracking available at: https://docs.google.com/spreadsheets/d/{sheet_id}")

if __name__ == "__main__":
    # You can provide Google credentials file path and optionally an existing sheet ID
    # If sheet_id is None, a new sheet will be created
    download_best_quality_torrents(
        request_delay=2.0,  # Default 2 second delay
        credentials_file='/Users/aaa/projects/lb/letterboxd/ltbxd-457319-fb2679bd42ac.json',
        sheet_id=os.environ.get('GOOGLE_SHEET_ID'),
        share_with_email='shanjairajan54@gmail.com'  # Set this environment variable with your email
    ) 