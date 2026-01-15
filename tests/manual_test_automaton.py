import os
import sys

# Ensure project root is on sys.path so `gamer` can be imported when running this file directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gamer.utils.automaton_url_parser import AutomatonUrlParser


if __name__ == '__main__':
    url = 'https://automaton-media.com/pc-steam-epic-games-store-gog/?query-19d0b21f=1'
    items = AutomatonUrlParser.extract_dynamic_media_links(url)
    print('Found', len(items), 'items')
    for i, it in enumerate(items[:10], start=1):
        title = it['title'] or '(no title)'
        print(f"{i}. {title}")
        print('   ' + it['url'])
