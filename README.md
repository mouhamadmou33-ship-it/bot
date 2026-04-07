# Telegram Video Downloader Bot

A production-ready Telegram bot that downloads videos from YouTube, Instagram, and Facebook using yt-dlp.

## Features

- Download videos from YouTube, Instagram, and Facebook
- Automatic platform detection
- File size limit (50MB) - sends direct download link for larger files
- Rate limiting per user
- Progress updates during download
- Comprehensive error handling
- Logging to console and file
- Async/await implementation

## Setup

1. Clone or download the project files.

2. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your bot token:

   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   ADMIN_ID=your_admin_id
   YOUTUBE_COOKIES_FILE=path/to/youtube_cookies.txt  # Optional, for restricted videos
   COOKIES_FROM_BROWSER=chrome  # Optional, browser name (chrome, firefox, edge, etc.)
   ```

4. (Optional) For YouTube videos that require sign-in:
   - **Option 1: Export cookies to file**
     - Export cookies from your browser (Chrome/Firefox recommended)
     - Save them to a file (e.g., `youtube_cookies.txt`)
     - Set the path in `.env` as `YOUTUBE_COOKIES_FILE`
     - See yt-dlp documentation for cookie export methods
   - **Option 2: Use browser cookies directly**
     - Set `COOKIES_FROM_BROWSER` to your browser name (e.g., `chrome`, `firefox`)
     - Make sure the browser is logged into YouTube
     - Note: This may require additional permissions or browser extensions

5. Run the bot:
   ```
   python main.py
   ```

## Usage

- Start the bot with `/start`
- Send a video URL from YouTube, Instagram, or Facebook
- The bot will download and send the video or a direct link if too large

## Architecture

- `main.py`: Entry point with logging and application setup
- `handlers.py`: Telegram bot message handlers
- `downloader.py`: Video downloading logic with yt-dlp
- `utils.py`: Utility functions for validation, rate limiting, etc.
- `requirements.txt`: Python dependencies
- `.env`: Environment variables

## Security

- URL validation to prevent injection
- Filename sanitization
- Rate limiting to prevent abuse

## Requirements

- Python 3.8+
- Valid Telegram bot token from BotFather
