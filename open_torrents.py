import os
import subprocess

def open_torrent_files():
    """
    Opens all files in the 'torrents/' folder using the default application.
    This function is designed to be triggered on a Windows PC.
    """
    # Get the absolute path of the torrents folder
    torrents_folder = os.path.abspath('torrents/')
    
    # Check if the folder exists
    if not os.path.exists(torrents_folder):
        print(f"Error: The folder '{torrents_folder}' does not exist.")
        return
    
    # Get a list of all files in the torrents folder
    files = [f for f in os.listdir(torrents_folder) if os.path.isfile(os.path.join(torrents_folder, f))]
    
    if not files:
        print(f"No files found in '{torrents_folder}'.")
        return
    
    # Open each file using the default application
    for file in files:
        file_path = os.path.join(torrents_folder, file)
        try:
            # Using os.startfile which is Windows-specific
            os.startfile(file_path)
            print(f"Opened: {file}")
        except Exception as e:
            print(f"Error opening {file}: {e}")

if __name__ == "__main__":
    open_torrent_files() 