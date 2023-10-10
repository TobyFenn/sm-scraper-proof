import requests
from bs4 import BeautifulSoup
import sqlite3
import re

# Set up the SQLite database connection and table
conn = sqlite3.connect('celebrity_data.db')
cursor = conn.cursor()

# Update the 'celebrities' table to include 'career_summary'
cursor.execute('''
CREATE TABLE IF NOT EXISTS celebrities (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    birthdate TEXT,
    birthplace TEXT,
    occupations TEXT,
    career_summary TEXT
)
''')
conn.commit()

# Clear the celebrities table for debugging
cursor.execute("DELETE FROM celebrities")
conn.commit()

# List of artists to scrape
artists = [
    "Shawn Mendes",
    "Taylor Swift",
    "Ariana Grande",
    "Ed Sheeran",
    "Billie Eilish",
    "Post Malone",
    "Beyonce",
    "Rihanna",
    "Bruno Mars",
    "Justin Bieber"
]


def extract_second_sentence(content):
    """Extract the second sentence from the Wikipedia content."""

    # Remove reference tags
    content_cleaned = re.sub(r'\[\d+\]', '', content)

    # Extract the second sentence
    sentences = re.split(r'(?<=[.!?])\s+', content_cleaned, 2)
    return sentences[1] if len(sentences) > 1 else None


for artist in artists:
    # Scrape the data
    URL = f"https://en.wikipedia.org/wiki/{artist.replace(' ', '_')}"
    response = requests.get(URL)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, 'html.parser')

    # Extract the second sentence
    content_paragraph = soup.select_one('div.mw-parser-output > p:not(:empty)')
    career_summary = extract_second_sentence(content_paragraph.text) if content_paragraph else None

    # Find the infobox table
    infobox = soup.find('table', class_='infobox')
    if infobox:
        # Extract birthdate
        birth_date = infobox.find('span', class_='bday')
        birth_date = birth_date.text if birth_date else None

        # Extract birthplace
        birth_place = infobox.find('div', class_='birthplace')
        birth_place = birth_place.text.strip() if birth_place else None

        # Extract occupations
        occupation_row = infobox.find('th', string=lambda x: x in ['Occupation', 'Occupations'])
        occupations = None
        if occupation_row and occupation_row.next_sibling:
            # Check if occupations are in list items
            occupation_items = getattr(occupation_row.next_sibling, 'find_all', lambda x: [])('li')
            if occupation_items:
                occupations = ', '.join([item.get_text(strip=True) for item in occupation_items])
            else:
                occupations = occupation_row.next_sibling.get_text(', ', strip=True).replace('\n', ', ')

        # Insert or replace the scraped data in the database, including career_summary
        cursor.execute("""
        INSERT OR REPLACE INTO celebrities (name, birthdate, birthplace, occupations, career_summary) 
        VALUES (?, ?, ?, ?, ?)""",
                       (artist, birth_date, birth_place, occupations, career_summary))
        conn.commit()

        print(f"Stored data for {artist}!")
        print("Birth Date:", birth_date)
        print("Birth Place:", birth_place)
        print("Occupations:", occupations)
        print("Career Summary:", career_summary)
        print('-' * 50)  # Print a separator for clarity

    else:
        print(f"Infobox not found for {artist}!")

# Close the database connection
conn.close()
