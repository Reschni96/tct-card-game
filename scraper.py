import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime, timedelta
import mysql.connector

# URL of the webpage
url = "https://raw.githubusercontent.com/campaign-trail-showcase/campaign-trail-showcase.github.io/main/static/mods/MODLOADERFILE.html"

# Send a request to fetch the content of the webpage
response = requests.get(url)
response.raise_for_status()  # Raise an error for HTTP errors

# Parse the HTML content using BeautifulSoup
soup = BeautifulSoup(response.text, 'html.parser')

# Find all <option> tags
options = soup.find_all('option')

# List to store the data
data = []

# Extract data from each <option> tag and store it in the list
for option in options:
    value = option['value']
    data_tags = option['data-tags'].split()  # Split data-tags into a list of strings
    name = option.text

    # Send a GET request to retrieve additional data for each mod
    mod_url = f"https://cts-backend-w8is.onrender.com/api/get_mod?modName={value}"
    mod_response = requests.get(mod_url)
    mod_data = mod_response.json()

    favs = mod_data.get('favs', 0)  # Default to 0 if 'favs' is not present
    play_count = mod_data.get('playCount', 0)  # Default to 0 if 'playCount' is not present

    data.append({
        'value': value,
        'data-tags': data_tags,
        'name': name,
        'favs': favs,
        'play-count': play_count
    })

# Ensure the data directory exists
os.makedirs('data', exist_ok=True)

# Get the current date
current_date = datetime.now().strftime('%Y%m%d')

# Save the data to a JSON file with the current date in the filename
with open(f'data_archive/moddata_{current_date}.json', 'w') as json_file:
    json.dump(data, json_file, indent=4)

print(f"Data saved to data_archive/moddata_{current_date}.json")

connection = mysql.connector.connect(
    host='campaigntrailmojo.mysql.eu.pythonanywhere-services.com',
    user='campaigntrailmoj',
    password='PWD4MYSQL!',
    database='campaigntrailmoj$default'
)
cursor = connection.cursor()

# Get the current date
current_date_db = datetime.now().strftime('%Y-%m-%d')

for entry in data:
    # Insert data into Scenarios table
    scenario_query = """
    INSERT INTO Scenarios (value, name, favs, play_count, entry_date)
    VALUES (%s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        name = VALUES(name),
        favs = VALUES(favs),
        play_count = VALUES(play_count),
        entry_date = VALUES(entry_date);
    """
    scenario_values = (entry['value'], entry['name'], entry['favs'], entry['play-count'], current_date_db)
    cursor.execute(scenario_query, scenario_values)

# Commit the transaction
connection.commit()

def calculate_total_plays(delta_days):
    # Calculate the past date
    past_date = (datetime.now() - timedelta(days=delta_days)).date()

    # Create a cursor to execute queries
    cursor = connection.cursor()

    # Query the database to sum up play counts for all mods on the specific date
    query = """
    SELECT SUM(play_count) FROM Scenarios
    WHERE entry_date = %s;
    """
    cursor.execute(query, (past_date,))
    result = cursor.fetchone()

    # Close the cursor
    cursor.close()

    # Extract and return the total play counts, or 165785 if no data is found
    total_plays = result[0] if result[0] is not None else 165785
    return total_plays


def get_most_played_mod(data):
    if not data:
        return None
    most_played_mod = max(data, key=lambda x: x.get('play-count', 0))
    return {
        'name': most_played_mod['name'],
        'play_count': most_played_mod['play-count']
    }


def calculate_total_plays_for_period(start_date, end_date):
    start_date = start_date.date()
    end_date = end_date.date()
    # Create a cursor to execute queries
    cursor = connection.cursor()
    # Helper function to get play counts for a specific date
    def get_play_counts(date):
        query = """
        SELECT value, name, play_count FROM Scenarios
        WHERE entry_date = %s;
        """
        cursor.execute(query, (date,))
        return {value: {'name': name, 'play_count': play_count} for value, name, play_count in cursor.fetchall()}

    # Get play counts for end_date and start_date
    end_date_play_counts = get_play_counts(end_date)
    start_date_play_counts = get_play_counts(start_date)

    # If no data on start_date, find the oldest data on record
    if not start_date_play_counts:
        query_oldest_date = """
        SELECT MIN(entry_date) FROM Scenarios;
        """
        cursor.execute(query_oldest_date)
        oldest_date = cursor.fetchone()[0]
        start_date_play_counts = get_play_counts(oldest_date)

    # Calculate the difference in play counts for each mod
    final_data = []
    for value, end_data in end_date_play_counts.items():
        start_play_count = start_date_play_counts.get(value, {'play_count': 0})['play_count']
        difference = end_data['play_count'] - start_play_count
        final_data.append({'value': value, 'name': end_data['name'], 'play_count': difference})

    total_plays = sum(item['play_count'] for item in final_data)

    most_played_mod_data = max(final_data, key=lambda x: x['play_count'])
    most_played_mod = {
        "name": most_played_mod_data['name'],
        "play_count": most_played_mod_data['play_count']
    }

    # Close the cursor
    cursor.close()

    return total_plays, most_played_mod


def update_tracker(file_path, period_key, total_plays, most_played_mod):
    if os.path.exists(file_path):
        with open(file_path, 'r') as json_file_tracker:
            tracker_data = json.load(json_file_tracker)
    else:
        tracker_data = {}
    tracker_data[period_key] = {
        'total_plays': total_plays,
        'most_played_mod': most_played_mod
    }
    with open(file_path, 'w') as json_file_tracker:
        json.dump(tracker_data, json_file_tracker, indent=4)

# Calculate total plays for specific periods
total_plays_1d = calculate_total_plays(1)
total_plays_3d = calculate_total_plays(3)
total_plays_7d = calculate_total_plays(7)
total_plays_30d = calculate_total_plays(30)

# Get the current total plays across all mods
current_total_plays = sum(mod.get('play-count', 0) for mod in data)

# Calculate changes
change_1d = current_total_plays - total_plays_1d
change_3d = current_total_plays - total_plays_3d
change_7d = current_total_plays - total_plays_7d
change_30d = current_total_plays - total_plays_30d

_, most_played_mod_1d = calculate_total_plays_for_period(datetime.now() - timedelta(days=1), datetime.now())
_, most_played_mod_3d = calculate_total_plays_for_period(datetime.now() - timedelta(days=3), datetime.now())
_, most_played_mod_7d = calculate_total_plays_for_period(datetime.now() - timedelta(days=7), datetime.now())
_, most_played_mod_30d = calculate_total_plays_for_period(datetime.now() - timedelta(days=30), datetime.now())

# Update daily stats
daily_stats = {
    'date': current_date,
    'total_plays': {
        'last_day': {'change': int(change_1d), 'most_played_mod': most_played_mod_1d},
        'last_three_days': {'change': int(change_3d), 'most_played_mod': most_played_mod_3d},
        'last_week': {'change': int(change_7d), 'most_played_mod': most_played_mod_7d},
        'last_month': {'change': int(change_30d), 'most_played_mod': most_played_mod_30d},
    }
}
# Save the daily stats to a JSON file
with open(f'data_archive/dailyStats_{current_date}.json', 'w') as json_file:
    json.dump(daily_stats, json_file, indent=4)

print(f"Daily stats saved to data_archive/dailyStats_{current_date}.json")

time_periods = [
    ('last_day', change_1d, most_played_mod_1d),
    ('last_three_days', change_3d, most_played_mod_3d),
    ('last_week', change_7d, most_played_mod_7d),
    ('last_month', change_30d, most_played_mod_30d),
]

# Insert data into PlayStatistics table
for period, change, most_played_mod in time_periods:
    play_stats_query = """
    INSERT INTO PlayStatistics (date, time_period, play_change, most_played_mod, play_count)
    VALUES (%s, %s, %s, %s, %s);
    """
    play_stats_values = (current_date_db, period, change, most_played_mod['name'], most_played_mod['play_count'])
    cursor.execute(play_stats_query, play_stats_values)

# Commit the transaction
connection.commit()

# Get the current date and time
now = datetime.now()

# Calculate the start of the current week, month, and year
start_of_week = now - timedelta(days=now.weekday()) - timedelta(days=1)
start_of_month = now.replace(day=1) - timedelta(days=1)
start_of_year = now.replace(month=1, day=1) - timedelta(days=1)


# After calculating total plays for week, month, and year:
total_plays_week, most_played_mod_week = calculate_total_plays_for_period(start_of_week, now)
total_plays_month, most_played_mod_month = calculate_total_plays_for_period(start_of_month, now)
total_plays_year, most_played_mod_year = calculate_total_plays_for_period(start_of_year, now)
total_plays_year += 165785

# Update trackers
update_tracker('data_archive/weekTracker.json', now.strftime('%Y-%W'), total_plays_week, most_played_mod_week)
update_tracker('data_archive/monthTracker.json', now.strftime('%Y-%m'), total_plays_month, most_played_mod_month)
update_tracker('data_archive/yearTracker.json', now.strftime('%Y'), total_plays_year, most_played_mod_year)

def update_tracker_db(connection, period_type, period_value, total_plays, most_played_mod):
    cursor = connection.cursor()

    # Check if a record for the period already exists
    check_query = """
    SELECT * FROM PlayTracker
    WHERE period_type = %s AND period_value = %s;
    """
    cursor.execute(check_query, (period_type, period_value))
    existing_record = cursor.fetchone()

    # If record exists, update it; otherwise, insert a new record
    if existing_record:
        update_query = """
        UPDATE PlayTracker
        SET total_plays = %s, most_played_mod = %s, play_count = %s
        WHERE period_type = %s AND period_value = %s;
        """
        cursor.execute(update_query, (total_plays, most_played_mod['name'], most_played_mod['play_count'], period_type, period_value))
    else:
        insert_query = """
        INSERT INTO PlayTracker (period_type, period_value, total_plays, most_played_mod, play_count)
        VALUES (%s, %s, %s, %s, %s);
        """
        cursor.execute(insert_query, (period_type, period_value, total_plays, most_played_mod['name'], most_played_mod['play_count']))

    connection.commit()
    cursor.close()


update_tracker_db(connection, 'week', now.strftime('%Y-%W'), total_plays_week, most_played_mod_week)
update_tracker_db(connection, 'month', now.strftime('%Y-%m'), total_plays_month, most_played_mod_month)
update_tracker_db(connection, 'year', now.strftime('%Y'), total_plays_year, most_played_mod_year)

if connection.is_connected():
    connection.close()
