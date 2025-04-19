#!/usr/bin/env python3

import requests
import re
import bs4
import concurrent.futures
import time
import json
import os
import logging
from typing import List, Dict, Tuple, Set

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('PROXY_FINDER')

# Test URL (YTS API)
TEST_URL = "https://yts.mx/api/v2/list_movies.json?limit=1"

# Free proxy list sources
PROXY_SOURCES = [
    "https://www.sslproxies.org/",
    "https://free-proxy-list.net/",
    "https://www.us-proxy.org/",
    "https://hidemy.name/en/proxy-list/?type=s&anon=4#list",
]

def fetch_proxies_from_url(url: str) -> Set[str]:
    """
    Fetch proxies from a URL source
    
    Args:
        url: URL of the proxy list website
        
    Returns:
        Set of proxy URLs in format http://host:port
    """
    proxies = set()
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
        }
        
        logger.info(f"Fetching proxies from {url}")
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            logger.warning(f"Failed to fetch from {url}: {response.status_code}")
            return proxies
        
        # Parse HTML response
        soup = bs4.BeautifulSoup(response.text, 'html.parser')
        
        # Extract IP addresses and ports - this is a simple pattern, may need adjustment
        # for each specific site's layout
        ip_pattern = r'\d+\.\d+\.\d+\.\d+'
        port_pattern = r'\b\d{2,5}\b'
        
        # Look for table rows that might contain proxy info
        for table in soup.find_all('table'):
            for tr in table.find_all('tr'):
                row_text = tr.get_text()
                
                # Find IP and port in the row
                ip_match = re.search(ip_pattern, row_text)
                if not ip_match:
                    continue
                    
                ip = ip_match.group(0)
                port_match = re.search(port_pattern, row_text[ip_match.end():])
                
                if port_match:
                    port = port_match.group(0)
                    proxy = f"http://{ip}:{port}"
                    proxies.add(proxy)
        
        logger.info(f"Found {len(proxies)} proxies from {url}")
        
    except Exception as e:
        logger.error(f"Error fetching from {url}: {str(e)}")
    
    return proxies

def test_proxy(proxy: str, timeout: int = 5) -> Tuple[str, bool, float]:
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
            logger.info(f"✅ Working: {proxy} - {response.status_code} - {response_time:.2f}s")
            return proxy, True, response_time
        else:
            logger.debug(f"❌ Failed: {proxy} - Status: {response.status_code}")
            return proxy, False, 0
    except Exception as e:
        logger.debug(f"❌ Error: {proxy} - {str(e)[:100]}")
        return proxy, False, 0

def main():
    """Find and test free proxies"""
    # Collect proxies from multiple sources
    all_proxies = set()
    
    for url in PROXY_SOURCES:
        try:
            proxies = fetch_proxies_from_url(url)
            all_proxies.update(proxies)
        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
    
    logger.info(f"Found total of {len(all_proxies)} unique proxies from all sources")
    
    if not all_proxies:
        logger.error("No proxies found. Try again later or add more sources.")
        return
    
    # Test proxies in parallel
    working_proxies = []
    
    logger.info(f"Testing {len(all_proxies)} proxies against {TEST_URL}")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        proxies_list = list(all_proxies)
        results = list(executor.map(test_proxy, proxies_list))
        
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
    
    logger.info(f"\nResults:")
    logger.info(f"Found {len(working_proxies)} working proxies out of {len(all_proxies)}")
    logger.info(f"Working proxies saved to {output_file}")
    
    if working_proxies:
        print("\nTop 5 fastest proxies:")
        for i, proxy_data in enumerate(working_proxies[:5]):
            print(f"{i+1}. {proxy_data['proxy']} - {proxy_data['response_time']:.2f}s")
        
        # Create a Python list format for easy copy-paste
        print("\nCopy-paste ready list for your code:")
        print("default_proxies = [")
        for proxy_data in working_proxies[:10]:  # Use top 10 fastest
            print(f'    "{proxy_data["proxy"]}",')
        print("]")

if __name__ == "__main__":
    main() 