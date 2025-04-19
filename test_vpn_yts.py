import requests
import time
import json
from pyvpn import PyVpn

def test_ip_before_vpn():
    """Check IP address before connecting to VPN"""
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=10)
        print("Current IP (before VPN):", response.json()['ip'])
    except Exception as e:
        print(f"Error checking IP before VPN: {e}")

def test_ip_with_vpn(country_code):
    """Check IP address with VPN connected"""
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=10)
        print(f"IP with VPN ({country_code}):", response.json()['ip'])
    except Exception as e:
        print(f"Error checking IP with VPN: {e}")

def test_yts_api():
    """Test accessing the YTS API"""
    try:
        response = requests.get('https://yts.mx/api/v2/list_movies.json', timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'ok':
                movie_count = data['data']['movie_count']
                print(f"Successfully accessed YTS API. Found {movie_count} movies.")
                # Save first few movie details for verification
                if movie_count > 0:
                    movies = data['data']['movies'][:3]  # First 3 movies
                    print(f"Sample movies: {json.dumps([m['title'] for m in movies], indent=2)}")
            else:
                print(f"API error: {data}")
        else:
            print(f"Failed to access YTS API. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error accessing YTS API: {e}")

def main():
    # Test current IP
    print("Testing connection before VPN...")
    test_ip_before_vpn()
    
    # Try to access YTS API without VPN
    print("\nTrying to access YTS API without VPN...")
    test_yts_api()
    
    # Test with VPN
    country_code = "US"  # You can change this to any country code
    print(f"\nConnecting to VPN ({country_code})...")
    
    try:
        vpn = PyVpn(country=country_code)
        vpn.connect()
        
        if vpn.connected:
            print(f"Successfully connected to VPN in {country_code}")
            
            # Wait a moment for connection to stabilize
            time.sleep(5)
            
            # Check IP with VPN
            test_ip_with_vpn(country_code)
            
            # Try to access YTS API with VPN
            print("\nTrying to access YTS API with VPN...")
            test_yts_api()
            
            # Disconnect VPN
            vpn.disconnect()
            print("VPN disconnected")
        else:
            print(f"Failed to connect to VPN in {country_code}")
    except Exception as e:
        print(f"Error with VPN connection: {e}")

if __name__ == "__main__":
    main() 