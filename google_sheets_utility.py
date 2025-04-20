import os
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.errors import HttpError

class GoogleSheetsUtility:
    def __init__(self, credentials_file=None):
        """
        Initialize the Google Sheets utility.
        
        Args:
            credentials_file: Path to the Google service account credentials JSON file
        """
        self.credentials_file = credentials_file or os.environ.get('GOOGLE_CREDENTIALS_FILE')
        self.sheet_id = None
        self.service = None
        self.drive_service = None
        
        if not self.credentials_file:
            raise ValueError("Google credentials file path must be provided")
            
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Sheets API and Drive API"""
        try:
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'  # Required for sharing sheets
            ]
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_file, scopes=scopes)
            self.service = build('sheets', 'v4', credentials=credentials)
            self.drive_service = build('drive', 'v3', credentials=credentials)
            print("Successfully authenticated with Google APIs")
        except Exception as e:
            print(f"Error authenticating with Google APIs: {e}")
            raise
    
    def create_movie_tracking_sheet(self, title="YTS Movie Downloads Tracker", share_with=None):
        """
        Create a new Google Sheet for tracking movie downloads.
        
        Args:
            title: Title of the sheet
            share_with: Email address to share the sheet with (e.g., your personal gmail)
            
        Returns:
            sheet_id: ID of the created sheet
        """
        try:
            # Create the spreadsheet
            spreadsheet = {
                'properties': {
                    'title': title
                },
                'sheets': [
                    {
                        'properties': {
                            'title': 'Movies',
                            'gridProperties': {
                                'rowCount': 1000,
                                'columnCount': 3
                            }
                        }
                    }
                ]
            }
            
            spreadsheet = self.service.spreadsheets().create(body=spreadsheet).execute()
            self.sheet_id = spreadsheet['spreadsheetId']
            
            # Add headers
            values = [['Movie name', 'Year', 'Film ID', 'Is downloaded']]
            body = {
                'values': values
            }
            
            self.service.spreadsheets().values().update(
                spreadsheetId=self.sheet_id, 
                range='Movies!A1:D1',
                valueInputOption='RAW',
                body=body
            ).execute()
            
            # Share the sheet if an email is provided
            if share_with:
                self.share_sheet(self.sheet_id, share_with)
            
            print(f"Created new tracking sheet: {title}")
            print(f"Sheet ID: {self.sheet_id}")
            print(f"View your sheet at: https://docs.google.com/spreadsheets/d/{self.sheet_id}")
            
            return self.sheet_id
            
        except HttpError as error:
            print(f"An error occurred while creating sheet: {error}")
            return None
    
    def share_sheet(self, sheet_id, email, role='writer'):
        """
        Share a spreadsheet with a specific user
        
        Args:
            sheet_id: The ID of the spreadsheet to share
            email: The email address to share with
            role: The permission role (reader, writer, or owner)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create the permission
            user_permission = {
                'type': 'user',
                'role': role,
                'emailAddress': email
            }
            
            # Share the file
            self.drive_service.permissions().create(
                fileId=sheet_id,
                body=user_permission,
                sendNotificationEmail=False
            ).execute()
            
            print(f"Successfully shared spreadsheet with {email}")
            return True
            
        except HttpError as error:
            print(f"An error occurred while sharing the sheet: {error}")
            return False
    
    def add_movie_entry(self, sheet_id, movie_name, year, film_id=None, is_downloaded=True):
        """
        Add a movie entry to the tracking sheet.
        
        Args:
            sheet_id: ID of the Google Sheet
            movie_name: Name of the movie
            year: Release year of the movie
            film_id: Unique identifier of the film
            is_downloaded: Whether the torrent was downloaded successfully
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the next empty row
            result = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range='Movies!A:A'
            ).execute()
            
            values = result.get('values', [])
            next_row = len(values) + 1
            
            # Add the new entry
            body = {
                'values': [[movie_name, year, film_id, str(is_downloaded)]]
            }
            
            self.service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=f'Movies!A{next_row}:D{next_row}',
                valueInputOption='RAW',
                body=body
            ).execute()
            
            print(f"Added entry for '{movie_name} ({year})' to tracking sheet")
            return True
            
        except HttpError as error:
            print(f"An error occurred while adding movie entry: {error}")
            return False
            
    def get_sheet_id(self):
        """Return the current sheet ID"""
        return self.sheet_id 
        
    def get_sheet_data(self, sheet_id, range_name='Movies!A:Z'):
        """
        Get data from a Google Sheet.
        
        Args:
            sheet_id: ID of the Google Sheet
            range_name: Range to get data from (default: all columns in 'Movies' sheet)
            
        Returns:
            List of rows with values
        """
        try:
            # If range_name contains sheet name with spaces not already in quotes, handle it
            if '!' in range_name and "'" not in range_name.split('!')[0] and ' ' in range_name.split('!')[0]:
                sheet_part = range_name.split('!')[0]
                range_part = range_name.split('!')[1]
                range_name = f"'{sheet_part}'!{range_part}"
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                print(f"No data found in sheet {sheet_id}")
                return []
                
            return values
            
        except HttpError as error:
            print(f"An error occurred while getting sheet data: {error}")
            return []
    
    def create_new_sheet(self, spreadsheet_id, sheet_title, headers=None):
        """
        Creates a new sheet in an existing spreadsheet.
        
        Args:
            spreadsheet_id: ID of the existing spreadsheet
            sheet_title: Name of the new sheet to create
            headers: List of column headers to add to the first row
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create a new sheet in the spreadsheet
            body = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': sheet_title,
                            'gridProperties': {
                                'rowCount': 1000,
                                'columnCount': len(headers) if headers else 5
                            }
                        }
                    }
                }]
            }
            
            response = self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
            print(f"Created new sheet '{sheet_title}' in spreadsheet")
            
            # Add headers if provided
            if headers:
                # Handle sheet titles with spaces by enclosing in single quotes
                formatted_sheet_title = f"'{sheet_title}'" if ' ' in sheet_title else sheet_title
                
                body = {
                    'values': [headers]
                }
                
                self.service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=f'{formatted_sheet_title}!A1:{chr(65 + len(headers) - 1)}1',
                    valueInputOption='RAW',
                    body=body
                ).execute()
                
                print(f"Added headers to sheet '{sheet_title}'")
            
            return True
            
        except HttpError as error:
            print(f"An error occurred while creating new sheet: {error}")
            return False
    
    def add_movie_entry_to_sheet(self, sheet_id, sheet_name, movie_name, year, film_id=None):
        """
        Add a movie entry to a specific sheet in the tracking spreadsheet.
        
        Args:
            sheet_id: ID of the Google Sheet
            sheet_name: Name of the sheet to add the entry to
            movie_name: Name of the movie
            year: Release year of the movie
            film_id: Unique identifier of the film
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Handle sheet names with spaces by enclosing in single quotes if needed
            formatted_sheet_name = f"'{sheet_name}'" if ' ' in sheet_name else sheet_name
            
            # Get the next empty row
            result = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=f'{formatted_sheet_name}!A:A'
            ).execute()
            
            values = result.get('values', [])
            next_row = len(values) + 1
            
            # Add the new entry
            body = {
                'values': [[movie_name, year, film_id]]
            }
            
            self.service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=f'{formatted_sheet_name}!A{next_row}:C{next_row}',
                valueInputOption='RAW',
                body=body
            ).execute()
            
            print(f"Added entry for '{movie_name} ({year})' to '{sheet_name}' sheet")
            return True
            
        except HttpError as error:
            print(f"An error occurred while adding movie entry to sheet '{sheet_name}': {error}")
            return False
    
    def get_all_sheet_names(self, spreadsheet_id):
        """
        Get a list of all sheet names in a spreadsheet.
        
        Args:
            spreadsheet_id: ID of the Google Sheet
            
        Returns:
            List of sheet names
        """
        try:
            # Get spreadsheet information including sheets
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            # Extract sheet names
            sheet_names = [sheet['properties']['title'] for sheet in spreadsheet.get('sheets', [])]
            
            return sheet_names
            
        except HttpError as error:
            print(f"An error occurred while getting sheet names: {error}")
            return [] 