import requests
import json
import random
import os

class ProxyUtility:
    def __init__(self, proxy_file='working_yts_proxies.json'):
        """Initialize the proxy utility"""
        self.proxy_file = proxy_file
        self.proxies = self._load_proxies()
        self.current_proxy = None
    
    def _load_proxies(self):
        """Load proxies from file"""
        if not os.path.exists(self.proxy_file):
            print(f"WARNING: Proxy file {self.proxy_file} not found!")
            return []
        
        try:
            with open(self.proxy_file, 'r') as f:
                proxies = json.load(f)
                print(f"Loaded {len(proxies)} proxies from {self.proxy_file}")
                return proxies
        except Exception as e:
            print(f"ERROR: Failed to load proxies: {e}")
            return []
    
    def get_random_proxy(self):
        """Get a random proxy from the loaded proxies"""
        if not self.proxies:
            return None
        
        self.current_proxy = random.choice(self.proxies)
        return self.current_proxy
    
    def remove_current_proxy(self):
        """Remove the current proxy from the list and update the file"""
        if self.current_proxy and self.current_proxy in self.proxies:
            self.proxies.remove(self.current_proxy)
            
            # Update the file
            with open(self.proxy_file, 'w') as f:
                json.dump(self.proxies, f)
            
            print(f"Removed proxy {self.current_proxy}. {len(self.proxies)} proxies remaining.")
            self.current_proxy = None
    
    def request(self, url, method='get', max_retries=3, timeout=10, **kwargs):
        """Make a request through a proxy with automatic retry and rotation"""
        retries = 0
        
        while retries < max_retries:
            proxy = self.get_random_proxy()
            
            if not proxy:
                print("No proxies available!")
                return None
            
            proxies = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
            
            try:
                print(f"Trying request with proxy {proxy}...")
                
                if method.lower() == 'get':
                    response = requests.get(url, proxies=proxies, timeout=timeout, **kwargs)
                elif method.lower() == 'post':
                    response = requests.post(url, proxies=proxies, timeout=timeout, **kwargs)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                if response.status_code == 200:
                    print(f"Request successful with proxy {proxy}")
                    return response
                else:
                    print(f"Request failed with status code {response.status_code}")
            except Exception as e:
                print(f"Error with proxy {proxy}: {e}")
                # self.remove_current_proxy()
            
            retries += 1
        
        print(f"Failed after {max_retries} retries")
        return None

# Example usage
if __name__ == "__main__":
    # Test the utility
    proxy_util = ProxyUtility()
    
    response = proxy_util.request('https://yts.mx/api/v2/list_movies.json?query_term=the%20beast%202023')
    
    if response:
        data = response.json()
        if data.get('status') == 'ok':
            movie_count = data.get('data', {}).get('movie_count', 0)
            print(f"Successfully accessed YTS API. Found {movie_count} movies.")
            
            # Sample of movies
            if movie_count > 0:
                movies = data.get('data', {}).get('movies', [])[:5]
                for movie in movies:
                    print(f"- {movie['title']} ({movie['year']}) - Rating: {movie['rating']}")
        else:
            print(f"API returned non-ok status: {data}")
    else:
        print("Failed to access YTS API through proxies") 