from playwright.sync_api import sync_playwright
import time

def scrape_youtube_search(query):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        search_url = f"https://www.youtube.com/results?search_query={query}"

        page.goto(search_url, timeout=60000)
        page.wait_for_selector("ytd-video-renderer", timeout=10000)

        # ✅ Scroll down to trigger lazy loading of thumbnails
        for _ in range(3):
            page.mouse.wheel(0, 1000)
            time.sleep(2)  # wait for images to load

        # ✅ Give additional wait to ensure thumbnails load
        time.sleep(2)

        video_elements = page.query_selector_all("ytd-video-renderer")[:20]
        for video in video_elements:
            
            title_el = video.query_selector("#video-title")
            channel_el = video.query_selector("ytd-channel-name")
            thumbnail_el = video.query_selector("img")

            title = title_el.get_attribute("title")
            link = "https://www.youtube.com" + title_el.get_attribute("href")
            channel = channel_el.inner_text() if channel_el else "Unknown"

            # ✅ Check both src and data-thumb, and filter placeholders
            thumbnail = ""
            if thumbnail_el:
                src = thumbnail_el.get_attribute("src")
                data_thumb = thumbnail_el.get_attribute("data-thumb")
                thumbnail = src or data_thumb or ""
                if thumbnail.startswith("data:image"):  # skip base64 placeholders
                    thumbnail = ""

            results.append({
                "title": title,
                "link": link,
                "channel": channel,
                "thumbnail": thumbnail
            })

        browser.close()
    return results








