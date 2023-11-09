from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar
from cardgame.card_app import card_app # Import the Blueprint
from db_handler import get_connection

app = Flask(__name__)
app.config['SECRET_KEY'] = "2687313dbbbee0d2266518971aba5f1e"
app.register_blueprint(card_app, url_prefix='/games')

clients = {}

def get_latest_data():
    # Define a query to get all entries with the newest date from the Scenarios table
    query = """
        SELECT * FROM Scenarios
        WHERE entry_date = (SELECT MAX(entry_date) FROM Scenarios);
    """

    # Use the get_data_from_db function to execute the query and get the data
    latest_data = get_data_from_db(query)

    # Format the data for compatibility with existing code
    formatted_data = []
    for entry in latest_data:
        formatted_data.append({
            'value': entry['value'],
            'name': entry['name'],
            'favs': entry['favs'],
            'play_count': entry['play_count'],
            'entry_date': entry['entry_date']
        })

    return formatted_data


def last_day_of_month(year, month):
    _, last_day = calendar.monthrange(year, month)
    return f"{year}-{month:02d}-{last_day:02d}"

def get_data_from_db(query):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return data

def get_mod_data(mod_name):
    # Initialize mod data and time periods
    mod_data = {}
    time_periods = ['1', '3', '7', '30']
    fallback_date = datetime(2023, 11, 1).strftime('%Y-%m-%d')

    # Extract current data
    query = f"SELECT * FROM Scenarios WHERE value = '{mod_name}' ORDER BY entry_date DESC LIMIT 1;"
    current_data = get_data_from_db(query)
    if current_data:
        mod_data['current'] = current_data[0]
        current_date = mod_data['current']['entry_date']

    # Extract historical data
    for days in time_periods:
        # Set target date to the max of the calculated date and the fallback date
        target_date = max((current_date - timedelta(days=int(days))).strftime('%Y-%m-%d'), fallback_date)

        query = f"SELECT * FROM Scenarios WHERE value = '{mod_name}' AND entry_date <= '{target_date}' ORDER BY entry_date DESC LIMIT 1;"
        historical_data = get_data_from_db(query)

        if historical_data:
            mod_data[str(days)] = {
                'play_count_change': mod_data['current']['play_count'] - historical_data[0]['play_count'],
                'favs_change': mod_data['current']['favs'] - historical_data[0]['favs']
            }
        else:
            # If no historical data found, assume both favs and play_count were 0 at the historical date
            mod_data[str(days)] = {
                'play_count_change': mod_data['current']['play_count'],
                'favs_change': mod_data['current']['favs']
            }
    return mod_data


@app.route('/')
def index():
    data = get_latest_data()
    sort_by = request.args.get('sort_by', 'value')
    if sort_by in ['play_count', 'favs']:
        data.sort(key=lambda x: x[sort_by], reverse=True)
    else:
        data.sort(key=lambda x: x[sort_by])
    return render_template('index.html', data=data)

@app.route('/mod/<mod_name>')
def mod_detail(mod_name):
    mod_data = get_mod_data(mod_name)
    return render_template('mod_detail.html', mod_data=mod_data, mod_name=mod_name)

@app.route('/recent')
def recent():
    # Get current date and previous day in the format YYYY-MM-DD
    current_date = datetime.now().strftime('%Y-%m-%d')
    previous_day = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    # Define a query to get data from today
    query_today = f"""
        SELECT * FROM PlayStatistics
        WHERE date = '{current_date}';
    """

    # Define a query to get data from yesterday
    query_yesterday = f"""
        SELECT * FROM PlayStatistics
        WHERE date = '{previous_day}';
    """

    # Get data from the database
    data_db = get_data_from_db(query_today)
    if not data_db:
        data_db = get_data_from_db(query_yesterday)
        current_date = previous_day

    # Reformat data to match the desired JSON structure
    data = {
        "date": current_date.replace('-', ''),
        "total_plays": {}
    }

    for entry in data_db:
        time_period = entry['time_period'].lower().replace(' ', '_')
        data['total_plays'][time_period] = {
            "change": entry['play_change'],
            "most_played_mod": {
                "name": entry['most_played_mod'],
                "play_count": entry['play_count']
            }
        }

    return render_template('recent.html', data=data)


@app.route('/get_top_mods/<int:days>')
def get_top_mods(days):
    # Initialize end_date and start_date
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Define query templates
    query_template = """
        SELECT * FROM Scenarios
        WHERE entry_date = '{}';
    """

    # Loop until data is found for end_date
    while True:
        end_data = get_data_from_db(query_template.format(end_date.strftime('%Y-%m-%d')))
        if end_data:
            break
        end_date -= timedelta(days=1)
        start_date -= timedelta(days=1)

    # Fetch data for start_date
    start_data = get_data_from_db(query_template.format(start_date.strftime('%Y-%m-%d')))

    # Handle missing data files
    if not start_data:
        return {'error': "Sorry, data doesn't reach back far enough!"}

    # Calculate play count changes
    mod_changes = []
    for mod in end_data:
        start_mod = next((m for m in start_data if m['value'] == mod['value']), None)
        start_plays = start_mod['play_count'] if start_mod else 0
        play_count_change = mod['play_count'] - start_plays
        mod_changes.append({'mod_name': mod['name'], 'play_count_change': play_count_change})

    # Sort mods by play count change and get top 10
    top_mods = sorted(mod_changes, key=lambda x: x['play_count_change'], reverse=True)[:10]

    return jsonify({'top_mods': top_mods})

@app.route('/by_day')
def by_day():
    # Query to fetch data for 'last_day' time period
    query = "SELECT * FROM PlayStatistics WHERE time_period = 'last_day' ORDER BY date DESC;"
    result = get_data_from_db(query)

    # Initialize daily stats list
    daily_stats = []

    # Loop through the results and format data
    for row in result:
        formatted_date = row['date'].strftime('%Y-%m-%d')
        last_day_plays = row['play_change']
        most_played_mod = {'name': row['most_played_mod'], 'play_count': row['play_count']}
        daily_stats.append({'date': formatted_date, 'last_day': last_day_plays, 'most_played_mod': most_played_mod})

    # Render the by_day.html template and pass the data
    return render_template('by_day.html', daily_stats=daily_stats)

@app.route('/by_week')
def by_week():
    # Query to fetch weekly data
    query = "SELECT * FROM PlayTracker WHERE period_type = 'week' ORDER BY period_value DESC;"
    result = get_data_from_db(query)

    # Format and sort weekly stats
    weekly_stats = [{
        'week': row['period_value'],
        'total_plays': row['total_plays'],
        'most_played_mod': {'name': row['most_played_mod'], 'play_count': row['play_count']}
    } for row in result]

    # Render the by_week.html template and pass the data
    return render_template('by_week.html', weekly_stats=weekly_stats, datetime=datetime, timedelta=timedelta)

@app.route('/by_month')
def by_month():
    # Query to fetch monthly data
    query = "SELECT * FROM PlayTracker WHERE period_type = 'month' ORDER BY period_value DESC;"
    result = get_data_from_db(query)

    # Format and sort monthly stats
    monthly_stats = [{
        'month': row['period_value'],
        'total_plays': row['total_plays'],
        'most_played_mod': {'name': row['most_played_mod'], 'play_count': row['play_count']}
    } for row in result]

    # Render the by_month.html template and pass the data
    return render_template('by_month.html', monthly_stats=monthly_stats, last_day_of_month=last_day_of_month)




@app.route('/mod_plays/<period>/<date>')
def mod_plays_by_period(period, date):
    # Validate period
    if period not in ['day', 'week', 'month']:
        return "Invalid period"

    # Calculate timedelta based on period
    if period == 'day':
        delta = timedelta(days=1)
    elif period == 'week':
        delta = timedelta(weeks=1)
    elif period == 'month':
        delta = relativedelta(months=1)

    # Parse date and calculate previous and next dates
    current_date = datetime.strptime(date, '%Y-%m-%d')
    previous_date = current_date - delta
    next_date = current_date + delta

    # Load current data
    current_query = f"SELECT * FROM Scenarios WHERE entry_date='{current_date.strftime('%Y-%m-%d')}'"
    current_data = get_data_from_db(current_query)

    # Load previous data
    previous_query = f"SELECT * FROM Scenarios WHERE entry_date='{previous_date.strftime('%Y-%m-%d')}'"
    previous_data = get_data_from_db(previous_query)

    if not current_data:
        if not previous_data:
            return render_template('mod_plays_by_period.html', date=date, error="Sorry, no data available", period=period)
        else:
            return render_template('mod_plays_by_period.html', date=date, error="Sorry, no data available", previous_date=previous_date.strftime('%Y-%m-%d'), period=period)

    # Fallback to the earliest available data for week and month
    if not previous_data and period != 'day':
        earliest_date_query = "SELECT MIN(entry_date) as earliest_date FROM Scenarios"
        earliest_date_result = get_data_from_db(earliest_date_query)
        earliest_date = earliest_date_result[0]['earliest_date']
        earliest_data_query = f"SELECT * FROM Scenarios WHERE entry_date='{earliest_date}'"
        previous_data = get_data_from_db(earliest_data_query)


    if not previous_data:
        return render_template('mod_plays_by_period.html', date=date, error="Sorry, no data available", period=period, current_date=next_date.strftime('%Y-%m-%d'))

    mod_plays = []
    for mod in current_data:
        # Calculate play count change
        play_count_change = mod['play_count']
        prev_mod = next((item for item in previous_data if item['value'] == mod['value']), None)
        if prev_mod:
            play_count_change -= prev_mod['play_count']
        else:
            play_count_change = max(0, play_count_change)  # Fallback to 0 if no previous data

        mod_plays.append({'name': mod['name'], 'play_count_change': play_count_change})

    # Sort by plays descending
    mod_plays.sort(key=lambda x: x['play_count_change'], reverse=True)

    return render_template('mod_plays_by_period.html', date=date, mod_plays=mod_plays, previous_date=previous_date.strftime('%Y-%m-%d'), current_date=next_date.strftime('%Y-%m-%d'), period=period)

if __name__ == '__main__':
    app.run()