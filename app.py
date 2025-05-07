from flask import Flask, request, jsonify
import pandas as pd
import asyncio
import csv
import threading
from search_scraper import scrape_youtube_search
from trending import scrape_trending
from flask_cors import CORS

app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
CORS(app, supports_credentials=True, origins=["http://127.0.0.1:5500", "http://localhost:5500", "null"])

def load_trending_data():
    data = []
    try:
        with open('./data/trending_IN.csv', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
    except FileNotFoundError:
        print("Error: trending_IN.csv not found.")
    return data

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '').lower()
    data = load_trending_data()
    if not data:
        return jsonify({"error": "Trending data not available", "results": [], "not_found": True, "query": query}), 500
    matches = [video for video in data if query in video['title'].lower()]
    return jsonify({"results": matches, "not_found": not matches, "query": query})

@app.route('/scrape_youtube', methods=['GET'])
def scrape_youtube():
    query = request.args.get('query')
    if not query:
        return jsonify({"error": "Query is required"}), 400
    try:
        scraped_results = scrape_youtube_search(query)
        return jsonify({"results": scraped_results})
    except Exception as e:
        return jsonify({"error": f"Scraping failed: {str(e)}"}), 500

@app.route('/refresh', methods=['POST'])
def refresh_trending():
    def run_scraper():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(scrape_trending("IN", 100))
        finally:
            loop.close()
    threading.Thread(target=run_scraper).start()
    return jsonify({'message': 'Trending data refresh initiated!'})

@app.route('/api/videos', methods=['GET'])
def get_videos():
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
    try:
        df = pd.read_csv('./data/trending_IN.csv')
    except FileNotFoundError:
        return jsonify({"error": "Trending data file not found."}), 500

    def parse_views(view_str):
        try:
            if pd.isna(view_str): return 0
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

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)

# Explicitly set host and port
