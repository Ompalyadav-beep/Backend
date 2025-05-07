from flask import Flask, request, jsonify, session, redirect, url_for # Removed render_template_string, send_from_directory
import pandas as pd
import asyncio
import csv
import threading
from search_scraper import scrape_youtube_search # Ensure this path is correct
from trending import scrape_trending # Ensure this path is correct
from flask_cors import CORS # Import CORS

app = Flask(__name__)
app.secret_key = 'e3a1bba8b50e463fa53a1d0d3ffbd1b2'
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

# --- CORS Configuration ---
# Allow requests from your frontend's origin.
# If your frontend runs on http://localhost:3000 (common for React dev server)
# or if you open HTML files directly (origin is "null")
# For development, you can be permissive, but be more specific in production.
CORS(app, supports_credentials=True, origins=["http://127.0.0.1:5500", "http://localhost:5500", "null"]) # Example: for VS Code Live Server on port 5500 and file:// protocol

def load_trending_data():
    data = []
    try:
        with open('./data/trending_IN.csv', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
    except FileNotFoundError:
        print("Error: trending_IN.csv not found. Make sure it's in the 'data' directory.")
        # Optionally, return an empty list or raise an error that can be caught by the routes
    return data

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '').lower()
    data = load_trending_data()
    if not data:
         return jsonify({"error": "Trending data not available or file not found", "results": [], "not_found": True, "query": query}), 500
    matches = [video for video in data if query in video['title'].lower()]
    if matches:
        return jsonify({"results": matches, "not_found": False})
    else:
        return jsonify({"results": [], "not_found": True, "query": query})

@app.route('/scrape_youtube', methods=['GET'])
def scrape_youtube():
    query = request.args.get('query')
    if not query:
        return jsonify({"error": "Query is required"}), 400
    try:
        scraped_results = scrape_youtube_search(query) # Ensure this function exists and works
        return jsonify({"results": scraped_results})
    except Exception as e:
        return jsonify({"error": f"Scraping failed: {str(e)}"}), 500


@app.route('/refresh', methods=['POST'])
def refresh_trending():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized. Please log in."}), 401 # Return 401

    def run_scraper():
        # Ensure your asyncio event loop is handled correctly if Flask runs in a different thread context
        # For simplicity, if scrape_trending is complex, consider a task queue like Celery.
        # For now, this creates a new loop for the thread.
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(scrape_trending("IN", 100)) # Ensure this function exists
        finally:
            loop.close()


    threading.Thread(target=run_scraper).start()
    return jsonify({'message': 'Trending data refresh initiated!'})


@app.route('/login', methods=['POST']) # Only POST for API login
def login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        if username == 'admin' and password == 'admin123':
            session['user'] = username
            return jsonify({"message": "Login successful", "user": username}), 200
        return jsonify({"error": "Invalid credentials"}), 401 # Return 401 for failed login
    # GET request for /login is removed, frontend will have its own login page

@app.route('/logout', methods=['POST']) # Changed to POST as it changes server state
def logout():
    user = session.pop('user', None)
    if user:
        return jsonify({"message": "Logout successful"}), 200
    return jsonify({"message": "No active session to log out from"}), 200 # Or 400 if you prefer


@app.route('/api/check-session', methods=['GET'])
def check_session():
    if 'user' in session:
        return jsonify({"isLoggedIn": True, "user": session['user']}), 200
    return jsonify({"isLoggedIn": False}), 200


@app.route('/api/videos', methods=['GET'])
def get_videos():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized. Please log in."}), 401 # Return 401

    try:
        df = pd.read_csv('./data/trending_IN.csv')
    except FileNotFoundError:
        return jsonify({"error": "Trending data file not found."}), 500

    df = df.rename(columns={
        'title': 'title',
        'channelTitle': 'channel',
        'viewCount': 'views',
        'publishedAt': 'published',
        'videoUrl': 'url',
        'videoId': 'videoId'
    })
    videos = df[['title', 'channel', 'views', 'published', 'url']].to_dict(orient='records')
    return jsonify(videos)


@app.route('/api/graph-data', methods=['GET'])
def graph_data():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized. Please log in."}), 401 # Return 401

    try:
        df = pd.read_csv('./data/trending_IN.csv')
    except FileNotFoundError:
        return jsonify({"error": "Trending data file not found."}), 500

    def parse_views(view_str):
        try:
            if pd.isna(view_str): return 0 # Handle NaN values
            view_str = str(view_str).replace(' views', '').strip()
            if 'K' in view_str:
                return int(float(view_str.replace('K', '')) * 1_000)
            elif 'M' in view_str:
                return int(float(view_str.replace('M', '')) * 1_000_000)
            elif 'B' in view_str:
                return int(float(view_str.replace('B', '')) * 1_000_000_000)
            else:
                return int(str(view_str).replace(',', ''))
        except:
            return 0

    df['viewCount'] = df['viewCount'].apply(parse_views)
    top20 = df.sort_values(by='viewCount', ascending=False).head(20)
    labels = top20['title'].tolist()
    data = top20['viewCount'].tolist()
    return jsonify({'labels': labels, 'data': data})

# Removed routes that served HTML files directly:
# @app.route('/')
# @app.route('/<path:path>')
# @app.route('/graph') (GET for graph.html)
# /login GET method

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000) # Explicitly set host and port