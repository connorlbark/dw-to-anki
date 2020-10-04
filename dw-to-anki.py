import requests
import bs4
import genanki
import random


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
    answer = answer_entry.p.text
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

def get_module_name(url):
    return url.split('/')[-3]


vocab = {}
decks = {}

for link in get_links():
    soup = get_soup_for(link)
    for (word, answer) in extract_all_vocab(soup):
        vocab[word] = answer

    module_name = get_module_name(link)
    deck = generate_anki_deck(module_name, vocab)

    decks[module_name] = deck

for (name, deck) in decks.items():
    genanki.Package(deck).write_to_file('out/' + name + ".apkg")

#    vocab_soups = soup.find_all("div", class_="vocabulary")
#    for vocab in vocab_soups:
#        entries = vocab.find_all("div", class_="vocabulary-entry")
#        print(len(entries))
