# Letterboxd Watchlist Torrent Manager

This script helps you automatically download torrents for movies in your Letterboxd watchlist that you haven't already downloaded.

## Features

- Fetches your Letterboxd watchlist
- Checks against a Google Sheet to avoid downloading duplicates
- Searches YTS for matching torrents
- Downloads the best quality available (prioritizing 2160p > 1080p bluray > 1080p web)
- Updates your Google Sheet with newly downloaded movies

## Setup

1. Install required dependencies:
   ```
   pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib requests selenium beautifulsoup4 rich
   ```

2. Configure proxy settings (optional but recommended):
   - Edit `working_yts_proxies.json` with a list of working HTTP proxies

3. Set up Google Sheets API credentials:
   - Create a Google Cloud project
   - Enable the Google Sheets API and Google Drive API
   - Create a service account and download the credentials JSON file
   - Share your tracking spreadsheet with the service account email

## Usage

1. Edit `watchlist_torrent_manager.py` and set your preferences:
   - Letterboxd username
   - Google credentials file path
   - Google Sheet ID
   - Your email address

2. Run the script:
   ```
   python watchlist_torrent_manager.py
   ```

## How It Works

1. The script uses the Letterboxd watchlist scraper from `movies.py` to get your watchlist
2. It checks which movies are not already in your Google Sheet
3. For each new movie, it searches YTS for available torrents
4. It downloads the best quality torrent file for each movie
5. It updates your Google Sheet with the newly downloaded movies

## Troubleshooting

- If the proxy requests fail, the script will attempt direct requests
- Check the console output for detailed error messages
- Ensure your Google Sheet has a column named "Film ID"

# letterboxd

![Redlettermedia example](./geta-all-example.gif)

python3 movies.py

Arguments

  `--user USER` `-u USER`   letterboxd.com user

  `--reviews` `-r`          Gets reviews

  `--testing` `-t`          Testing flag - for development only

  `--save-json` `-j`        Saves a JSON file of the reviews dictionary

  `--save-html` `-w`          Saves an HTML document for easily viewing reviews

  `--browser-open` `-b`        Opens saved HTML document in the browser

  `--search SEARCH [SEARCH ...]` `-s SEARCH [SEARCH ...]`
