#!/bin/env python3

'''
Letterboxd does not really have an API.
Test account:
    testfitzy1293
'''



import requests
import sys
import re
from bs4 import BeautifulSoup
from pprint import pprint
import json
from time import time
from time import sleep, time

# =======================================================================================================================================================================
# Global stuff (argparse stuff and rich console constructor).
# CL args and the console object from rich should be globals.
# Don't bother constructing console objects in every function.

import argparse
parser = argparse.ArgumentParser(description='letterboxd args')
parser.add_argument('--user', '-u', dest='user', help='letterboxd.com user')
parser.add_argument('--reviews', '-r', dest='reviews', action="store_true", default=False, help='Gets reviews')
parser.add_argument('--watchlist', '-l', dest='watchlist', action="store_true", default=False, help='Gets watchlist')
parser.add_argument('--testing', '-t', dest='testing', action='store_true', default=False, help='Testing flag - for development only')
parser.add_argument('--save-json', '-j', dest='json', action="store_true", default=False, help='Saves a JSON file of the reviews dictionary')
parser.add_argument('--save-html', '-w', dest='html', action="store_true", default=False, help='Saves an HTML document for easily viewing reviews')
parser.add_argument('--browser-open', '-b', dest='browserOpen', action="store_true", default=False, help='Opens saved HTML document in the browser')
parser.add_argument('--search', '-s', nargs='+', dest='search', default=())
args = parser.parse_args()


from rich.console import Console
from rich import print as rprint
console = Console()
# =======================================================================================================================================================================

# Make a list of the pages of reviews. (Ex. /user/films/reviews/page/1 ... /user/films/reviews/page/5)
# Can use the previews of the reviews (before clicking more) to get review text for multiple movies, if the review is short enough.
# Doing it like this is faster than requesting each review individually .

def getReviewUrls(user):
    reviewsBaseUrl = f'https://letterboxd.com/{user}/films/reviews/'
    html_text = requests.get(reviewsBaseUrl).text
    soup = BeautifulSoup(html_text, 'html.parser')
    pageDiv = str(soup.find("div", {'class': "pagination"}))
    sleep(.05)
    try:
        lastValidPage = int(pageDiv.split('/films/reviews/page/')[-1].split('/')[0])
        return [f'{reviewsBaseUrl}page/{str(i)}' for i in range(1, lastValidPage + 1)]
    except ValueError:
        return [reviewsBaseUrl]


def getSingleReview(url=''):
    for possibleUrl in (url, url + '/1/'): # super-8 review had a an extra /1/ on the end
        soup = BeautifulSoup(requests.get(possibleUrl).text, 'html.parser')
        reviewDivHtmlStr = str(soup.find("div", {'class': "review body-text -prose -hero -loose"}))
        sleep(.05)
        if not reviewDivHtmlStr  == 'None':
            return '<p>' + reviewDivHtmlStr.split('<p>')[-1].replace('</div>', '')
    return None


def getWatchlistUrls(user):
    watchlistBaseUrl = f'https://letterboxd.com/{user}/watchlist/'
    
    # Use headers to mimic a browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://letterboxd.com/',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    html_text = requests.get(watchlistBaseUrl, headers=headers).text
    soup = BeautifulSoup(html_text, 'html.parser')
    pageDiv = str(soup.find("div", {'class': "pagination"}))
    sleep(.05)
    try:
        lastValidPage = int(pageDiv.split('/watchlist/page/')[-1].split('/')[0])
        return [f'{watchlistBaseUrl}page/{str(i)}' for i in range(1, lastValidPage + 1)]
    except (ValueError, IndexError):
        # If no pagination is found or there's an error parsing it, return just the base URL
        console.print("[yellow]No pagination found or only one page exists.")
        return [watchlistBaseUrl]


def getWatchlist(user):
    watchlistUrls = getWatchlistUrls(user)
    console.print('[cyan] Watchlist pages')
    rprint(watchlistUrls)
    print()
    
    movieDelim = f'[red]{"=" * 80}'
    console.print(movieDelim)
    
    watchlist = []
    
    # Use headers to mimic a browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://letterboxd.com/',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    # List of known non-movie titles/UI elements to filter out
    non_movie_items = [
        'Start a new list…', 'Add all films to a list…', 'Add all films to watchlist',
        'Remove filters', 'Fade watched films', 'Show custom posters', 'Custom posters',
        'Any decade', 'Any genre', 'Apple TV+ US', 'Apple TV US', 'Newer', 'Older',
        'About', 'Pro', 'News', 'Apps', 'Podcast', 'Year in Review', 'Gifts', 'Help', 'Terms', 'API', 'Contact',
        'Powered by JustWatch', 'Film Name', 'Film Popularity', 'Shuffle', 'When Added'
    ]
    
    # Create a set for faster lookups
    non_movie_set = set(non_movie_items)
    non_movie_set.update([str(i) for i in range(1, 10)])  # Add page numbers
    
    for url in watchlistUrls:
        console.print(f'[cyan]Requesting: [bold blue]{url}')
        start = time()
        response = requests.get(url, headers=headers)
        rprint(f'responseTime={time() - start}')
        console.print(movieDelim)
        htmlText = response.text
        
        soup = BeautifulSoup(htmlText, 'html.parser')
        
        # APPROACH 1: Target the exact movie divs based on HTML structure analysis
        # Looking at the HTML, actual movies are in a specific section after the watchlist count header
        watchlist_header = soup.find('h1', string=lambda text: text and "wants to see" in text)
        
        console.print(f'[magenta]Watchlist header found: {watchlist_header is not None}')
        
        # If we can't find the standard header, try an alternative approach
        if not watchlist_header:
            # Try to find the poster grid directly - this is the main container for films
            poster_grid = soup.find('ul', class_='poster-list')
            if poster_grid:
                console.print(f'[green]Found poster list directly')
                film_posters = poster_grid.find_all('li', class_='poster-container')
                console.print(f'[green]Found {len(film_posters)} film posters')
                
                for poster in film_posters:
                    # Find div.film-poster which contains all the movie data
                    film_poster = poster.find('div', class_='film-poster')
                    if film_poster:
                        # Get the film slug (contains the title)
                        film_slug = film_poster.get('data-film-slug', '')
                        
                        # Get the title from img alt attribute since frame-title is empty
                        film_title = ''
                        img = film_poster.find('img')
                        if img and img.get('alt'):
                            film_title = img['alt'].strip()
                        
                        # If we couldn't get the title from img alt, try to parse from the slug
                        if not film_title and film_slug:
                            # Convert slug to title (replace hyphens with spaces and capitalize)
                            film_title = film_slug.replace('-', ' ').title()
                            # Remove year from slug if it exists
                            if film_title.endswith(tuple(str(year) for year in range(1900, 2030))):
                                film_title = ' '.join(film_title.split()[:-1])
                        
                        # Try to get the year from film-poster data
                        film_year = film_poster.get('data-film-release-year', '')
                        
                        # If we couldn't get the year from data attributes, try to extract from slug
                        if not film_year and film_slug and film_slug[-4:].isdigit():
                            film_year = film_slug[-4:]
                        
                        # If we still don't have a year but the title has a year in parentheses, extract it
                        if not film_year and '(' in film_title and ')' in film_title:
                            year_match = re.search(r'\((\d{4})\)', film_title)
                            if year_match:
                                film_year = year_match.group(1)
                                # Remove the year from the title
                                film_title = film_title.split('(')[0].strip()
                        
                        if film_title:
                            # Create a full title with year if available
                            full_title = film_title
                            if film_year:
                                full_title = f"{film_title} ({film_year})"
                            
                            # Create the ID from just the title (no year)
                            movie_id = film_slug if film_slug else film_title.lower().replace(' ', '-').replace(':', '').replace('&', 'and')
                            
                            movie_info = {
                                "title": full_title,
                                "id": movie_id
                            }
                            watchlist.append(movie_info)
                            console.print(f'[cyan]Added film: [bold blue]{full_title}')
                            continue
            
        elif watchlist_header:
            console.print(f'[green]Found watchlist header: {watchlist_header.text}')
            
            # Find films between the header and the pagination section
            current_element = watchlist_header.find_next_sibling()
            
            # Find the exact list of movies
            while current_element and not (current_element.name == 'div' and current_element.find('a', string='Newer')):
                if current_element.name == 'ul' and 'poster-list' in current_element.get('class', []):
                    console.print(f'[green]Found poster list')
                    
                    # Now extract the movies from this list - they should be direct children of this ul
                    film_posters = current_element.find_all('li', class_='poster-container')
                    console.print(f'[green]Found {len(film_posters)} film posters')
                    
                    for poster in film_posters:
                        # Look for the frame element that contains the title with year
                        frame_element = poster.find('a', class_='frame')
                        if frame_element:
                            # Find the span with class 'frame-title' which has the format "Title (Year)"
                            title_span = frame_element.find('span', class_=['frame-title', 'film-title', 'title'])
                            if title_span and title_span.text.strip():
                                full_title = title_span.text.strip()
                                
                                # Extract the base title without year for the ID
                                # If the title has format "Title (Year)", extract just "Title"
                                if '(' in full_title and ')' in full_title:
                                    basic_title = full_title.split('(')[0].strip()
                                else:
                                    basic_title = full_title
                                
                                # Double check it's not a UI element
                                if basic_title and basic_title not in non_movie_set:
                                    movie_id = basic_title.lower().replace(' ', '-').replace(':', '').replace('&', 'and')
                                    movie_info = {
                                        "title": full_title,
                                        "id": movie_id
                                    }
                                    watchlist.append(movie_info)
                                    console.print(f'[cyan]Added film: [bold blue]{full_title}')
                
                current_element = current_element.find_next_sibling()
        
        sleep(0.5)  # Be polite to the server
    
    # Show result summary
    if watchlist:
        console.print(f'[green]Successfully extracted {len(watchlist)} films from watchlist')
    else:
        console.print('[red]Could not extract films from watchlist')
        # Save HTML for debugging
        with open(f"{user}_watchlist_debug.html", "w") as f:
            f.write(htmlText)
        console.print(f'[yellow]Saved HTML to {user}_watchlist_debug.html for inspection')
    
    return watchlist


# Should probably make different functions for batch getting all movies and searching.
# Because args.search should only be checked once, not every time there's another movie review.
# But it was too easy to just throw that in and add a continue

def getReviews(user):
    movieDelim = f'[red]{"=" * 80}'
    look = f'/{user}/film/'
    reviewsText = {}

    if args.search:
        console.print(movieDelim)
        for url in [f'https://letterboxd.com/{user}/film/{movie}/' for movie in args.search]:
            movie = url.split('/film/')[-1][:-1]
            console.print(f'[cyan]movie: [bold blue]{movie}')
            console.print(f'\t[green]Searching')
            console.print(f'\t[green]Requesting: {url}')
            console.print(movieDelim)

            reviewsText[movie] = getSingleReview(url=url)
        return reviewsText

    reviewUrls = getReviewUrls(user)
    console.print('[cyan] Urls with multiple reviews')
    rprint(reviewUrls)
    print()

    console.print(movieDelim)
    for url in reviewUrls:
        console.print(f'[cyan]Requesting: [bold blue]{url}')
        start = time()
        response = requests.get(url)
        rprint(f'reponseTime={time() - start}')
        console.print(movieDelim)
        htmlText = response.text

        soup = BeautifulSoup(htmlText, 'html.parser')
        review_items = soup.select('li.film-detail')
        
        for item in review_items:
            movie_link = item.select_one('h2.headline-2 a')
            if not movie_link:
                continue
                
            movie = movie_link['href'].split('/film/')[-1].rstrip('/')
            console.print(f'[cyan]movie: [bold blue]{movie}')
            
            review_text = item.select_one('.js-review-body')
            if not review_text:
                continue
                
            # Check if this is a partial review (has ellipsis)
            review_preview = review_text.text.strip()
            
            if review_preview.endswith('…'):  # NOT THREE PERIODS - DIFFERENT UNICODE CHAR
                movieReviewUrl = f'https://letterboxd.com/{user}/film/{movie}/'
                console.print('\t[magenta]Preview contains partial review')
                console.print(f'\t[magenta]Requesting: {movieReviewUrl}')
                console.print(movieDelim)

                full_review = getSingleReview(url=movieReviewUrl)
                if full_review:
                    reviewsText[movie] = full_review
                else:
                    # If we can't get the full review, use what we have
                    reviewsText[movie] = str(review_text)
            else:
                console.print('\t[blue]Preview contains full review')
                console.print('\t[blue]No need to request individual page')
                console.print(movieDelim)
                
                # Get the actual review HTML
                p_tag = review_text.find('p')
                if p_tag:
                    reviewsText[movie] = str(p_tag)
                else:
                    reviewsText[movie] = str(review_text)

            sleep(.05)

    return reviewsText


def writeReviews(reviewsDict={}):
    user = reviewsDict['user']
    if not args.search:
        fname = f'{user}_all_reviews.html'

    else:
        fname = f'{user}_searched_reviews.html'
    rprint(f'html={fname}')

    with open(fname, 'w+') as f:
        f.write('<!DOCTYPE html>\n')
        f.write('<html>\n')
        f.write('<head>\n')
        f.write('</head>\n')
        f.write('<body>\n')

        f.write(f'<h1>{user} - letterboxd.com reviews </h1>\n<br>')

        for i, (movie, review) in enumerate(reviewsDict['reviews'].items()):
            htmlMovieTitle = movie.replace('-', ' ').title()
            f.write(f'<b>{i + 1}: {htmlMovieTitle}</b>\n<br>')
            f.write(f'{review}\n<br>')

        f.write('</body>\n')
        f.write('</html>\n')

    if args.browserOpen:
        from webbrowser import open_new_tab
        open_new_tab(fname)


def letterboxdRun():
    user = args.user
    baseUrl = f'https://letterboxd.com/{user}/films/'

    if args.reviews:
        fname = f'{user}_reviews.json'
        reviewsText = getReviews(user)

        outputDict = {'user': user, 'reviews': reviewsText}

        if args.html:
            writeReviews(outputDict)

        if args.json:
            rprint(f'json={fname}')
            jsonStr = json.dumps(outputDict, indent=3)
            with open(fname, 'w+') as f:
                f.write(jsonStr)
    
    if args.watchlist:
        fname = f'{user}_watchlist.json'
        watchlist = getWatchlist(user)
        
        outputDict = {'user': user, 'watchlist': watchlist}
        
        if args.json:
            rprint(f'json={fname}')
            jsonStr = json.dumps(outputDict, indent=3)
            with open(fname, 'w+') as f:
                f.write(jsonStr)
            console.print(f'[green]Saved watchlist with {len(watchlist)} films to {fname}')


if __name__ == '__main__':
    console.print('[cyan]*Command line arguments* ')
    for k,v in vars(args).items():
        rprint(f'\t{k}={v}')
    print()

    console.print('[cyan]--Making requests to letterboxd.com--\n[red]This may take some time depending on how many reviews there are.\n')
    letterboxdRun()
