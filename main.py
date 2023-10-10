import requests
from bs4 import BeautifulSoup
import sqlite3

# Set up the SQLite database connection and table
conn = sqlite3.connect('celebrity_data.db')
cursor = conn.cursor()

# Create the 'celebrities' table
cursor.execute('''
CREATE TABLE IF NOT EXISTS celebrities (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    birthdate TEXT,
    birthplace TEXT,
    occupations TEXT
)
''')
conn.commit()

# Scrape the data
URL = "https://en.wikipedia.org/wiki/Shawn_Mendes"
response = requests.get(URL)
response.raise_for_status()

soup = BeautifulSoup(response.content, 'html.parser')

# Find the infobox table
infobox = soup.find('table', class_='infobox')

if infobox:
    # Extract birthdate
    birth_date = infobox.find('span', class_='bday')
    if birth_date:
        birth_date = birth_date.text

    # Extract birthplace
    birth_place = infobox.find('div', class_='birthplace')
    if birth_place:
        birth_place = birth_place.text.strip()

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

    # Insert the scraped data into the database
    cursor.execute("INSERT INTO celebrities (name, birthdate, birthplace, occupations) VALUES (?, ?, ?, ?)",
                   ("Shawn Mendes", birth_date, birth_place, occupations))
    conn.commit()

    print("Birth Date:", birth_date)
    print("Birth Place:", birth_place)
    print("Occupations:", occupations)

else:
    print("Infobox not found!")

# Close the database connection
conn.close()
