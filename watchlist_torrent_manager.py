import sys
import importlib.util
import os
from google_sheets_utility import GoogleSheetsUtility
from proxy_utility import ProxyUtility
import time
import requests
from logfire_definition import logfire

# Get the directory where the script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

def import_module_from_file(file_path, module_name):
    """Dynamically import a module from a file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Import necessary modules from the other script files with absolute paths
movies_module = import_module_from_file(os.path.join(script_dir, "movies.py"), "movies_module")
fetch_movie_data_module = import_module_from_file(os.path.join(script_dir, "fetch_movie_data.py"), "fetch_movie_data_module")
yts_torrent_downloader_module = import_module_from_file(os.path.join(script_dir, "yts_torrent_downloader.py"), "yts_torrent_downloader_module")

def get_film_ids_from_sheet(credentials_file, sheet_id):
    """Get all film IDs already in the Google Sheet."""
    sheets_util = GoogleSheetsUtility(credentials_file)
    
    # Get the data from the sheet
    sheet_data = sheets_util.get_sheet_data(sheet_id)
    
    # Extract film IDs (assuming they're in a column called 'Film ID')
    film_ids = set()
    headers = None
    film_id_index = None
    
    for i, row in enumerate(sheet_data):
        if i == 0:  # Headers row
            headers = row
            for j, header in enumerate(headers):
                if header == "Film ID":
                    film_id_index = j
                    break
            if film_id_index is None:
                logfire.warn("'Film ID' column not found in Google Sheet")
                return film_ids
        else:
            if film_id_index < len(row) and row[film_id_index]:
                film_ids.add(row[film_id_index])
    
    logfire.info(f"Found {len(film_ids)} existing film IDs in Google Sheet")
    return film_ids

def get_film_ids_from_not_available_sheet(credentials_file, sheet_id):
    """Get all film IDs from the NotAvailable sheet in the Google Sheet."""
    sheets_util = GoogleSheetsUtility(credentials_file)
    
    # Get the data from the NotAvailable sheet
    sheet_data = sheets_util.get_sheet_data(sheet_id, range_name="NotAvailable!A:Z")
    
    # Extract film IDs (assuming they're in a column called 'Film ID')
    film_ids = set()
    headers = None
    film_id_index = None
    
    for i, row in enumerate(sheet_data):
        if i == 0:  # Headers row
            headers = row
            for j, header in enumerate(headers):
                if header == "Film ID":
                    film_id_index = j
                    break
            if film_id_index is None:
                logfire.warn("'Film ID' column not found in NotAvailable sheet")
                return film_ids
        else:
            if film_id_index < len(row) and row[film_id_index]:
                film_ids.add(row[film_id_index])
    
    logfire.info(f"Found {len(film_ids)} existing film IDs in NotAvailable sheet")
    return film_ids

def process_watchlist_and_download_torrents(
    letterboxd_username, 
    output_folder='torrents',
    request_delay=2.0,
    credentials_file=None,
    sheet_id=None,
    share_with_email=None
):
    """
    Main function to process watchlist and download torrents for new movies.
    
    Args:
        letterboxd_username: Letterboxd username to fetch watchlist from
        output_folder: Folder to save torrent files
        request_delay: Delay between API requests
        credentials_file: Path to Google API credentials file
        sheet_id: Google Sheet ID for tracking
        share_with_email: Email to share the sheet with
    """
    logfire.info(f"Fetching watchlist for user: {letterboxd_username}")
    # Get watchlist using the getWatchlist function from movies.py
    watchlist = movies_module.getWatchlist(letterboxd_username)
    
    if not watchlist:
        logfire.warn("No movies found in watchlist. Exiting.")
        return
    
    logfire.info(f"Found {len(watchlist)} movies in watchlist")
    
    # If we have a Google Sheet, filter out movies already in it
    filtered_watchlist = watchlist
    if credentials_file and sheet_id:
        logfire.info("Checking Google Sheet for existing films")
        existing_film_ids = get_film_ids_from_sheet(credentials_file, sheet_id)
        not_available_film_ids = get_film_ids_from_not_available_sheet(credentials_file, sheet_id)
        
        # Combine both sets of film IDs to exclude
        all_excluded_film_ids = existing_film_ids.union(not_available_film_ids)
        
        # Filter out movies already in either sheet
        filtered_watchlist = [
            movie for movie in watchlist 
            if not (movie.get("film_id") and movie.get("film_id") in all_excluded_film_ids)
        ]
        
        logfire.info(f"Filtered out {len(watchlist) - len(filtered_watchlist)} already tracked or unavailable movies")
        logfire.info(f"Processing {len(filtered_watchlist)} new movies")
    
    if not filtered_watchlist:
        logfire.info("No new movies to process. Exiting.")
        return
    
    # Initialize the proxy utility
    proxy_util = ProxyUtility()
    
    # Dictionary to store all responses from YTS API
    logfire.info(f"Fetching YTS movie data for {len(filtered_watchlist)} movies")
    movie_data_dict = {}
    
    # Process each movie in the filtered watchlist
    for movie in filtered_watchlist:
        movie_id = movie.get('id')
        letterboxd_id = movie.get('film_id')
        
        if not movie_id:
            continue
        
        logfire.info(f"Fetching data for movie: {movie.get('title')} (ID: {movie_id})")
        
        # Replace minus signs with %20 in the movie ID
        formatted_id = movie_id.replace('-', '%20')
        
        # Build API URL with query parameter
        url = f'https://yts.mx/api/v2/list_movies.json?query_term={formatted_id}'
        
        # Make request through proxy
        response = proxy_util.request(url)
        
        # If proxy request failed, try a direct request
        if not response:
            logfire.warn(f"Proxy request failed, attempting direct request for {movie_id}")
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    logfire.info(f"Direct request successful for {movie_id}")
                else:
                    logfire.error(f"Direct request failed with status code {response.status_code}")
                    response = None
            except Exception as e:
                logfire.error(f"Error with direct request: {e}")
                response = None
        
        if response:
            try:
                # Get the JSON response
                movie_data = response.json()
                # movie_data['film_id'] = letterboxd_id
                movie_data_dict[letterboxd_id] = movie_data
                logfire.info(f"Successfully fetched data for {movie_id}")
            except Exception as e:
                logfire.error(f"Error parsing response for {movie_id}: {e}")
        else:
            logfire.error(f"Failed to get data for {movie_id}")
        
        # Add a small delay to avoid overwhelming the API
        time.sleep(request_delay)
    
    # Download torrents using the movie data we just fetched
    if movie_data_dict:
        logfire.info(f"Downloading torrents for {len(movie_data_dict)} movies")
        
        # Initialize the downloader by importing the required function from yts_torrent_downloader.py
        yts_torrent_downloader = yts_torrent_downloader_module.download_best_quality_torrents
        
        # We'll modify the downloader function to accept our movie_data_dict directly
        # First, save the existing function implementation
        original_download_function = yts_torrent_downloader_module.download_best_quality_torrents
        
        # Create a wrapper function to use our in-memory data instead of reading from a file
        def download_from_dict(movie_data_dict, output_folder, request_delay, credentials_file, sheet_id, share_with_email):
            """Modified version of download_best_quality_torrents that uses an in-memory dict."""
            import os
            
            # Create output folder if it doesn't exist
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)
                logfire.info(f"Created output folder: {output_folder}")
            
            # Initialize proxy utility
            proxy_util = ProxyUtility()
            
            # Initialize Google Sheets tracking (if credentials provided)
            sheets_util = None
            if credentials_file:
                try:
                    sheets_util = GoogleSheetsUtility(credentials_file)
                    if not sheet_id:
                        sheet_id = sheets_util.create_movie_tracking_sheet(share_with=share_with_email)
                        logfire.info(f"Created a new tracking sheet with ID: {sheet_id}")
                    elif share_with_email and sheets_util:
                        # Share existing sheet if email is provided
                        sheets_util.share_sheet(sheet_id, share_with_email)
                        
                    logfire.info(f"Using Google Sheet ID: {sheet_id} for tracking downloads")
                except Exception as e:
                    logfire.error(f"WARNING: Could not initialize Google Sheets tracking: {e}")
                    sheets_util = None
            
            # Count variables for stats
            total_entries = len(movie_data_dict)
            processed_entries = 0
            movies_with_torrents = 0
            quality_stats = {'2160p': 0, '1080p_bluray': 0, '1080p_web': 0}
            successful_downloads = 0
            
            logfire.info(f"Processing {total_entries} entries...")
            logfire.info(f"Using {request_delay} second delay between requests")
            
            # Process each entry in the dictionary
            for letterboxd_id, movie_data in movie_data_dict.items():
                processed_entries += 1
                # letterboxd_id = movie_data.get('film_id')
                
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
                                film_id = movie.get('id', None)  # Get the unique film ID
                                
                                logfire.info(f"Found {quality_type} torrent for '{movie_title} ({movie_year})': {torrent_url}")
                                
                                # Create a safe filename
                                safe_title = "".join([c if c.isalnum() or c in ' ._-' else '_' for c in movie_title])
                                filename = f"{safe_title}_{movie_year}_{quality_type}.torrent"
                                file_path = os.path.join(output_folder, filename)
                                
                                # Download the torrent file using proxy
                                download_success = False
                                try:
                                    response = proxy_util.request(torrent_url)
                                    
                                    # If proxy request failed, try a direct request
                                    if not response:
                                        logfire.warn(f"Proxy request failed, attempting direct request for torrent")
                                        try:
                                            headers = {
                                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                                            }
                                            response = requests.get(torrent_url, headers=headers, timeout=10)
                                            if response.status_code == 200:
                                                logfire.info(f"Direct torrent request successful")
                                            else:
                                                logfire.error(f"Direct torrent request failed with status code {response.status_code}")
                                                response = None
                                        except Exception as e:
                                            logfire.error(f"Error with direct torrent request: {e}")
                                            response = None
                                    
                                    if response:
                                        # Save the binary content
                                        with open(file_path, 'wb') as torrent_file:
                                            torrent_file.write(response.content)
                                        
                                        download_success = True
                                        successful_downloads += 1
                                        logfire.info(f"Successfully downloaded to {file_path}")
                                        
                                        # Add to Google Sheet if tracking is enabled
                                        if sheets_util and sheet_id:
                                            sheets_util.add_movie_entry(
                                                sheet_id=sheet_id,
                                                movie_name=movie_title,
                                                year=movie_year,
                                                film_id=letterboxd_id,
                                                is_downloaded=True
                                            )
                                    else:
                                        logfire.error(f"Failed to download torrent for {movie_title}")
                                except Exception as e:
                                    logfire.error(f"Error downloading {movie_title} torrent: {e}")
                                
                                # Sleep to avoid overwhelming the proxy server
                                logfire.debug(f"Waiting {request_delay} seconds before next request...")
                                time.sleep(request_delay)
                else:
                    # Handle cases where movie data is not available
                    logfire.warn(f"Movie data not available for Letterboxd ID: {letterboxd_id}")
                    
                    # Get movie title and year from letterboxd data
                    movie_title = "Unknown"
                    movie_year = "Unknown"
                    
                    # Try to extract info from watchlist item
                    for watchlist_item in filtered_watchlist:
                        if watchlist_item.get('film_id') == letterboxd_id:
                            movie_title = watchlist_item.get('title', 'Unknown')
                            movie_year = watchlist_item.get('year', 'Unknown')
                            break
                    
                    # Add to a "not available" sheet in Google Sheets if tracking is enabled
                    if sheets_util and sheet_id:
                        # Get all sheet names and check if NotAvailable exists
                        all_sheet_names = sheets_util.get_all_sheet_names(sheet_id)
                        not_available_sheet_exists = "NotAvailable" in all_sheet_names
                        
                        # Create the sheet if it doesn't exist
                        if not not_available_sheet_exists:
                            logfire.info("Creating 'NotAvailable' sheet in the spreadsheet...")
                            headers = ['Movie Name', 'Year', 'Film ID']
                            sheets_util.create_new_sheet(sheet_id, "NotAvailable", headers)
                        
                        # Add the movie to the "not available" sheet
                        sheets_util.add_movie_entry_to_sheet(
                            sheet_id=sheet_id,
                            sheet_name="NotAvailable",
                            movie_name=movie_title,
                            year=movie_year,
                            film_id=letterboxd_id
                        )
                
                # Print progress every 5 entries
                if processed_entries % 5 == 0 or processed_entries == total_entries:
                    logfire.info(f"Progress: {processed_entries}/{total_entries} entries processed")
            
            # Print summary
            logfire.info("\n--- Download Summary ---")
            logfire.info(f"Total entries processed: {processed_entries}")
            logfire.info(f"Movies with matching torrents found: {movies_with_torrents}")
            logfire.info(f"Quality breakdown:")
            logfire.info(f"  - 2160p: {quality_stats['2160p']}")
            logfire.info(f"  - 1080p Bluray: {quality_stats['1080p_bluray']}")
            logfire.info(f"  - 1080p Web: {quality_stats['1080p_web']}")
            logfire.info(f"Successfully downloaded torrents: {successful_downloads}")
            logfire.info(f"Torrents saved to: {os.path.abspath(output_folder)}")
            if sheets_util and sheet_id:
                logfire.info(f"Download tracking available at: https://docs.google.com/spreadsheets/d/{sheet_id}")
            
            return successful_downloads
        
        # Update the quality_stats dictionary to have zero counts
        download_from_dict.__globals__['quality_stats'] = {'2160p': 0, '1080p_bluray': 0, '1080p_web': 0}
        
        # Call our modified download function with the in-memory movie data
        download_from_dict(
            movie_data_dict=movie_data_dict,
            output_folder=output_folder,
            request_delay=request_delay,
            credentials_file=credentials_file,
            sheet_id=sheet_id,
            share_with_email=share_with_email
        )
    else:
        logfire.warn("No movie data found to download torrents for")

if __name__ == "__main__":
    # Set your preferences here
    logfire.info("Starting watchlist torrent manager")
    process_watchlist_and_download_torrents(
        letterboxd_username="kokkithedon",  # Replace with your Letterboxd username
        output_folder=os.path.join(script_dir, "torrents"),
        request_delay=2.0,
        credentials_file=os.path.join(script_dir, 'ltbxd-457319-b911c40746e0.json'),
        sheet_id='1S6yZ5osVGhfmqwFKQbKfPg5B2j0CqKTAmUHnJIhB6pA',
        share_with_email='shanjairajan54@gmail.com'
    ) 
    logfire.info("Finished processing watchlist") 