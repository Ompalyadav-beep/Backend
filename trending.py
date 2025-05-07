import asyncio
import csv
from pathlib import Path
import pandas as pd
from playwright.async_api import async_playwright

def clean_text(text):
    if not text:
        return "N/A"
    return ' '.join(text.replace('\xa0', ' ').split())

def clean_views(views_str):
    if not views_str or 'view' not in views_str.lower():
        return "N/A"
    return clean_text(views_str)

def clean_uploaded(uploaded_str):
    return clean_text(uploaded_str)

async def scrape_trending(country='IN', count=100):
    url = f"https://www.youtube.com/feed/trending?gl={country}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_selector('ytd-video-renderer')

        videos = page.locator('ytd-video-renderer')
        total_videos = await videos.count()
        print(f" Found {total_videos} trending videos in {country}")

        data = []

        for i in range(min(count, total_videos)):
            try:
                video = videos.nth(i)
                title = await video.locator('#video-title').text_content()
                channel = await video.locator('ytd-channel-name').first.text_content()
                views = await video.locator('#metadata-line span').nth(0).text_content()
                uploaded = await video.locator('#metadata-line span').nth(1).text_content()
                href = await video.locator('#video-title').get_attribute('href')

                video_id = href.split('=')[-1] if href and '=' in href else href.split('/')[-1] if href else "N/A"
                video_url = f"https://www.youtube.com/watch?v={video_id}" if video_id != "N/A" else "N/A"

                data.append({
                    "title": clean_text(title),
                    "channelTitle": clean_text(channel),
                    "viewCount": clean_views(views),
                    "publishedAt": clean_uploaded(uploaded),
                    "videoUrl": video_url,
                    "videoId": video_id,
                    "category": "N/A"
                })

            except Exception as e:
                print(f" Error parsing video #{i+1}: {e}")

        await browser.close()

        # Save only the current trending videos
        filename = f"data/trending_{country}.csv"
        df_new = pd.DataFrame(data)

        if Path(filename).exists():
            df_old = pd.read_csv(filename)
            old_ids = set(df_old["videoId"])
            new_ids = set(df_new["videoId"])
            removed_ids = old_ids - new_ids
            added_ids = new_ids - old_ids
            print(f" Removed {len(removed_ids)} videos no longer trending.")
            print(f" Added {len(added_ids)} new trending videos.")

        df_new.to_csv(filename, index=False, encoding="utf-8")
        print(f" Overwrote {filename} with {len(df_new)} current trending videos.")

        clean_csv(filename)

def clean_csv(filepath):
    try:
        df = pd.read_csv(filepath)

        for col in df.columns:
            df[col] = df[col].astype(str).apply(lambda x: ' '.join(x.replace('\xa0', ' ').split()))

        df.drop_duplicates(subset='videoId', inplace=True)
        df.to_csv(filepath, index=False, encoding='utf-8')
        print(f" Cleaned and updated {filepath}")
    except Exception as e:
        print(f" Error cleaning CSV: {e}")

if __name__ == "__main__":
    asyncio.run(scrape_trending("IN", 100))



