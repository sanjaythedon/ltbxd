import requests
from bs4 import BeautifulSoup
import json
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_free_proxies():
    """Scrape free proxies from free-proxy-list.net"""
    print("Fetching free proxies...")
    url = "https://free-proxy-list.net/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    proxies = []
    
    # Extract proxies from the table
    proxy_table = soup.find('table', attrs={'class': 'table table-striped table-bordered'})
    if not proxy_table or not proxy_table.tbody:
        print("Failed to find proxy table on the website.")
        return []
    
    for row in proxy_table.tbody.find_all('tr'):
        columns = row.find_all('td')
        if len(columns) >= 7:  # Make sure we have enough columns
            if columns[6].text.strip() == 'yes':  # Only get HTTPS proxies
                ip = columns[0].text.strip()
                port = columns[1].text.strip()
                proxy = f"{ip}:{port}"
                proxies.append(proxy)
    
    print(f"Found {len(proxies)} potential HTTPS proxies")
    return proxies

def test_proxy(proxy, timeout=7):
    """Test if a proxy works"""
    proxies = {
        'http': f'http://{proxy}',
        'https': f'http://{proxy}'
    }
    
    try:
        start = time.time()
        response = requests.get('https://httpbin.org/ip', proxies=proxies, timeout=timeout)
        response_time = time.time() - start
        
        if response.status_code == 200:
            return {
                'proxy': proxy,
                'working': True,
                'response_time': response_time,
                'ip': response.json().get('origin', 'Unknown')
            }
    except Exception as e:
        pass
    
    return {'proxy': proxy, 'working': False}

def test_yts_api_with_proxy(proxy, timeout=10):
    """Test accessing YTS API with a proxy"""
    proxies = {
        'http': f'http://{proxy}',
        'https': f'http://{proxy}'
    }
    
    try:
        response = requests.get('https://yts.mx/api/v2/list_movies.json', proxies=proxies, timeout=timeout)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'ok':
                movie_count = data.get('data', {}).get('movie_count', 0)
                return {
                    'proxy': proxy,
                    'success': True,
                    'movie_count': movie_count,
                    'sample_movies': [m['title'] for m in data.get('data', {}).get('movies', [])[:3]] if movie_count > 0 else []
                }
    except Exception as e:
        pass
    
    return {'proxy': proxy, 'success': False}

def main():
    # First test our real IP
    print("Testing connection without proxy...")
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=5)
        print(f"Current IP: {response.json().get('ip')}")
    except Exception as e:
        print(f"Error checking IP: {e}")
    
    # Try accessing YTS API directly
    print("\nTrying to access YTS API without proxy...")
    try:
        response = requests.get('https://yts.mx/api/v2/list_movies.json', timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'ok':
                movie_count = data.get('data', {}).get('movie_count', 0)
                print(f"Successfully accessed YTS API. Found {movie_count} movies.")
                if movie_count > 0:
                    sample_movies = [m['title'] for m in data.get('data', {}).get('movies', [])[:3]]
                    print(f"Sample movies: {json.dumps(sample_movies, indent=2)}")
            else:
                print(f"API returned non-ok status: {data}")
        else:
            print(f"Failed to access YTS API. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error accessing YTS API: {e}")
        print("This suggests we need to use a proxy/VPN to access the site.")
    
    # Get and test proxies
    proxies = get_free_proxies()
    
    if not proxies:
        print("No proxies found. Exiting.")
        return
    
    # Test proxies concurrently to find working ones faster
    print(f"\nTesting {len(proxies)} proxies for basic connectivity...")
    working_proxies = []
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_proxy = {executor.submit(test_proxy, proxy): proxy for proxy in proxies}
        for future in as_completed(future_to_proxy):
            result = future.result()
            if result['working']:
                print(f"Found working proxy: {result['proxy']} (Response time: {result['response_time']:.2f}s, IP: {result['ip']})")
                working_proxies.append(result['proxy'])
    
    if not working_proxies:
        print("No working proxies found. Try again later.")
        return
    
    print(f"\nFound {len(working_proxies)} working proxies. Testing them with YTS API...")
    
    # Test working proxies with YTS API
    successful_proxies = []
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_proxy = {executor.submit(test_yts_api_with_proxy, proxy): proxy for proxy in working_proxies}
        for future in as_completed(future_to_proxy):
            result = future.result()
            if result['success']:
                print(f"Proxy {result['proxy']} successfully accessed YTS API!")
                print(f"  Found {result['movie_count']} movies")
                if result['sample_movies']:
                    print(f"  Sample movies: {json.dumps(result['sample_movies'], indent=2)}")
                successful_proxies.append(result['proxy'])
    
    # Save working proxies
    if successful_proxies:
        print(f"\nSuccessfully accessed YTS API through {len(successful_proxies)} proxies.")
        with open('working_yts_proxies.json', 'w') as f:
            json.dump(successful_proxies, f)
        print(f"Saved working proxies to working_yts_proxies.json")
    else:
        print("\nCould not access YTS API through any of the tested proxies.")

if __name__ == "__main__":
    main() 