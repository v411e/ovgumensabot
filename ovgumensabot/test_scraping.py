import asyncio
import urllib.request

from parser import get_menus_from_page
from mensabot import URLS


async def test_menu_scraping():
    # Go through all urls, get html
    for url in URLS:
        html = urllib.request.urlopen(url).read().decode('utf-8')
        # Get menus from html
        menus = get_menus_from_page(html)
        # Print menus
        for menu in menus:
            print(str(menu) + '\n')

if __name__ == '__main__':
    asyncio.run(test_menu_scraping())
