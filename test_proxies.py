#!/usr/bin/env python3

import requests
import concurrent.futures
import time
import os
import json
from typing import List, Dict, Tuple

# Test URL (YTS API)
TEST_URL = "https://yts.mx/api/v2/list_movies.json?limit=1"

def test_proxy(proxy: str, timeout: int = 10) -> Tuple[str, bool, float]:
    """
    Test if a proxy works with the YTS API
    
    Args:
        proxy: Proxy URL in format http://host:port
        timeout: Request timeout in seconds
        
    Returns:
        Tuple of (proxy, is_working, response_time)
    """
    proxies = {'http': proxy, 'https': proxy}
    start_time = time.time()
    try:
        response = requests.get(
            TEST_URL,
            proxies=proxies,
            timeout=timeout,
            verify=False
        )
        response_time = time.time() - start_time
        
        if response.status_code < 400:
            print(f"✅ Working: {proxy} - {response.status_code} - {response_time:.2f}s")
            return proxy, True, response_time
        else:
            print(f"❌ Failed: {proxy} - Status: {response.status_code}")
            return proxy, False, 0
    except Exception as e:
        print(f"❌ Error: {proxy} - {str(e)[:100]}")
        return proxy, False, 0

def get_proxy_list() -> List[str]:
    """Get a list of proxies to test"""
    # You can add more proxy sources here
    proxy_list = [
        # Default proxies from your code
        "http://8.219.74.58:443",
        "http://37.32.20.32:5566", 
        "http://198.27.74.6:9300",
        "http://91.92.209.67:8085",
        "http://203.30.189.29:80",
        "http://64.225.8.132:10000",
        "http://37.32.9.32:3835",
        "http://46.101.13.77:80",
        "http://95.216.194.46:1080",
        "http://153.92.209.71:80",
        # Additional proxies to try
        "http://172.104.146.131:80",
        "http://103.117.192.14:80",
        "http://216.137.184.253:80",
        "http://74.208.177.198:80",
        "http://51.79.152.70:80",
        "http://51.15.242.202:3128",
        "http://20.210.113.32:8123",
        "http://116.173.62.53:8080",
        "http://34.23.45.223:80",
        "http://68.183.185.62:80",
        "http://162.223.94.164:80",
        "http://190.61.88.147:999",
        "http://138.68.60.8:3128",
        "http://47.88.3.19:8080",
        "http://47.74.152.29:8888",
        "http://47.91.95.174:3128"
    ]
    return proxy_list

def main():
    """Test multiple proxies and save working ones"""
    print(f"Testing proxies against {TEST_URL}")
    proxies = get_proxy_list()
    print(f"Testing {len(proxies)} proxies...")
    
    working_proxies = []
    
    # Test proxies in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(test_proxy, proxies)
        
        for proxy, is_working, response_time in results:
            if is_working:
                working_proxies.append({
                    'proxy': proxy,
                    'response_time': response_time
                })
    
    # Sort working proxies by response time
    working_proxies.sort(key=lambda x: x['response_time'])
    
    # Save working proxies to file
    output_file = os.path.join(os.path.dirname(__file__), 'working_proxies.json')
    with open(output_file, 'w') as f:
        json.dump(working_proxies, f, indent=2)
    
    print(f"\nResults:")
    print(f"Found {len(working_proxies)} working proxies out of {len(proxies)}")
    print(f"Working proxies saved to {output_file}")
    
    if working_proxies:
        print("\nTop 5 fastest proxies:")
        for i, proxy_data in enumerate(working_proxies[:5]):
            print(f"{i+1}. {proxy_data['proxy']} - {proxy_data['response_time']:.2f}s")
        
        # Create a Python list format for easy copy-paste
        print("\nCopy-paste ready list for your code:")
        print("default_proxies = [")
        for proxy_data in working_proxies:
            print(f'    "{proxy_data["proxy"]}",')
        print("]")

if __name__ == "__main__":
    main() 