import requests
import bs4
import genanki
import random
import re
import os
from concurrent import futures
from django.utils.text import slugify

levels = {
    "a1": "https://learngerman.dw.com/en/beginners/c-36519789",
    "a2": "https://learngerman.dw.com/en/beginners-with-prior-knowledge/c-36519797",
    "b1-1": "https://learngerman.dw.com/en/fortgeschrittene/c-36519718",
    "b1-2": "https://learngerman.dw.com/en/deutsch-im-job-profis-gesucht/c-39902336",
}

model = genanki.Model(
    random.randrange(1 << 30, 1 << 31),
    'German Model',
    fields=[
        {'name': 'Question'},
        {'name': 'Answer'},
    ],
    templates=[
        {
            'name': 'Card 1',
            'qfmt': '{{Question}}',
            'afmt': '{{FrontSide}}<hr id="answer">{{Answer}}',
        },
])

def get_links():
    with open('modules') as module_file:
        return map(lambda x: x + "/lv", module_file.readlines())

def get_soup_for(link):
    resp = requests.get(link)
    resp.raise_for_status()
    return bs4.BeautifulSoup(resp.text, 'html.parser')

def extract_all_vocab(soup):
    # extract all vocabulary blocks, then, for each, extract the indivual entries
    vocab_soups = [x.find_all("div", "vocabulary-entry") for x in soup.find_all("div", class_="vocabulary")]
    # there are three html elements w/ the vocabulary-entry tag in each vocabulary block. the first and last
    # are the only ones with content.
    return [extract_vocab(vocab_soup[0], vocab_soup[2]) for vocab_soup in vocab_soups if len(vocab_soup) == 3]


def extract_vocab(word_entry, answer_entry):
    word = word_entry.strong.text
    answer_html = answer_entry.p
    if answer_html == None:
        answer_html = answer_entry.td
        if answer_html == None:
            print("WARNING: Answer cannot be found in <p> nor <td>, trying outer entry html... Will render as", answer_entry.text.strip())
            answer_html = answer_entry
    answer = answer_html.text.strip()
    return (word, answer)

def generate_anki_deck(module_name, vocab_map):

    deck = genanki.Deck(
        random.randrange(1 << 30, 1 << 31),
        module_name
    )

    for (word, ans) in vocab_map.items():
        note = genanki.Note(
            model=model,
            fields=[word, ans]
        )

        deck.add_note(note)
    return deck

def get_module_compact_name(url):
    return url.split('/')[-2]

def get_module_full_name(soup):
    title = soup.find('div', class_='excercise-nav-title')
    return title.h1.text



def generate_deck_from_module(link):
    module_soup = get_soup_for(link)
    vocab_soup = get_soup_for(link + "/lv")
    vocab = {}
    for (word, answer) in extract_all_vocab(vocab_soup):
        vocab[word] = answer

    module_name = get_module_full_name(module_soup)
    if len(vocab) == 0:
        print ("WARNING:", link, "produced an empty vocab list.")
    return module_name, generate_anki_deck(module_name, vocab)

def is_module_href(href):
    if '-test-' in href:
        return None

    return re.match(r"^\/en\/(?:(?![×Þ÷þø])[-ß'0-9a-zÀ-ÿ])+\/l-[0-9]+$", href)

def extract_all_module_links(soup):
    module_links = [link_soup['href'] for link_soup in soup.find_all("a", href=True) if is_module_href(link_soup['href'])]
    
    return ["https://learngerman.dw.com" + stub for stub in module_links]

def generate_decks_for_level(link):
    soup = get_soup_for(link)

    decks = {}

    with futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_compact_name = {}
        for link in extract_all_module_links(soup):
            future = executor.submit(generate_deck_from_module, link)
            future_to_compact_name[future] = get_module_compact_name(link)

        for future in futures.as_completed(future_to_compact_name):

            compact_name = future_to_compact_name[future]
            print("done loading deck for", compact_name, "...")
            full_name, deck = future.result()
            decks[full_name] = deck

    return decks



for (level, link) in levels.items():
    print("Generating decks for", level)

    decks = generate_decks_for_level(link)

    print("Writing decks at out/" + level + " for level", level)
    for (name, deck) in decks.items():
        if not os.path.isdir('out/' + level):
            os.makedirs('out/' + level)
        genanki.Package(deck).write_to_file('out/' + level + "/" + slugify(name, allow_unicode=True) + ".apkg")
