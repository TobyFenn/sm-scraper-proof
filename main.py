import requests
from bs4 import BeautifulSoup
import sqlite3
import re

# Set up the SQLite database connection and table
conn = sqlite3.connect('celebrity_data.db')
cursor = conn.cursor()

# Update the 'celebrities' table to include 'career_summary'
cursor.execute('''
CREATE TABLE IF NOT EXISTS relevant_sentences (
    id INTEGER PRIMARY KEY,
    celebrity_id INTEGER,
    context TEXT,  -- Added a column for context/type of the sentence
    sentence TEXT,
    FOREIGN KEY(celebrity_id) REFERENCES celebrities(id)
)
''')
conn.commit()

# Clear the celebrities and relevant_sentences tables for debugging
cursor.execute("DELETE FROM celebrities")
cursor.execute("DELETE FROM relevant_sentences")
conn.commit()

# List of artists to scrape
artists = [
    "Ed Sheeran",
    "Post Malone",
    "Bruno Mars",
]


def extract_section_sentences(soup, section_name):
    """Extract concise sentences from a specific section like 'Early Life' or 'Personal Life'."""
    section = None
    search_patterns = [
        section_name,
        section_name.lower(),
        section_name.split()[0].lower(),
        section_name.replace(" ", "-").lower(),
        section_name.replace(" ", "").lower()
    ]

    for pattern in search_patterns:
        section = soup.find(lambda tag: tag.name in ["h2", "h3", "h4"] and pattern in tag.get_text(strip=True).lower())
        if section:
            break

    if not section:
        return []

    # Determine the depth of our main section (h2, h3, h4, etc.)
    section_depth = int(section.name[1])

    siblings = list(section.find_all_next())
    relevant_sentences = []

    for tag in siblings:
        # Stop when reaching another section header of the same or greater depth
        if tag.name and tag.name.startswith("h") and int(tag.name[1]) <= section_depth:
            break

        if tag.name == "p":
            content_cleaned = re.sub(r'\[\d+\]', '', tag.text)
            sentences = re.split(r'(?<=[.!?])\s+', content_cleaned)

            for sentence in sentences:
                if 20 <= len(sentence) <= 150:
                    relevant_sentences.append(sentence.strip())

    return relevant_sentences


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

    early_life_sentences = extract_section_sentences(soup, "Early Life")
    personal_life_sentences = extract_section_sentences(soup, "Personal Life")

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

        # Updated the INSERT command to accommodate 'early_life_content' instead of 'career_summary'
        cursor.execute("""
        INSERT OR REPLACE INTO celebrities (name, birthdate, birthplace, occupations) 
        VALUES (?, ?, ?, ?)""",
                       (artist, birth_date, birth_place, occupations))
        conn.commit()

        # Retrieve the id of the artist (either it's newly inserted or replaced)
        cursor.execute("SELECT id FROM celebrities WHERE name = ?", (artist,))
        artist_id = cursor.fetchone()[0]

        # Insert sentences associated with this artist ID
        for context, sentences in [("Early Life", early_life_sentences), ("Personal Life", personal_life_sentences)]:
            if sentences:
                for sentence in sentences:
                    cursor.execute("INSERT INTO relevant_sentences (celebrity_id, context, sentence) VALUES (?, ?, ?)",
                                   (artist_id, context, sentence))
                    conn.commit()

                print(f"{context} Sentences:", ', '.join(sentences))
            else:
                print(f"No {context} sentences found for", artist)

        # print('-' * 50)

        print(f"Stored data for {artist}!")
        print("Birth Date:", birth_date)
        print("Birth Place:", birth_place)
        print("Occupations:", occupations)
        # print("Early Life Sentences:", early_life_sentences)
        print('-' * 50)

    else:
        print(f"Infobox not found for {artist}!")

# Close the database connection
conn.close()
