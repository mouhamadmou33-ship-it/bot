import inspect
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)
from downloader import VideoDownloader
from utils import is_valid_url, detect_platform, is_rate_limited
import asyncio

logger = logging.getLogger(__name__)


class BotHandlers:
    def __init__(
        self,
        admin_id: int,
        cookies_file: str | None = None,
        cookies_from_browser: str | None = None,
    ):
        self.admin_id = admin_id
        self.downloader = VideoDownloader(
            cookies_file=cookies_file, cookies_from_browser=cookies_from_browser
        )
        # Store pending downloads: {user_id: (url, platform)}
        self.pending_downloads = {}

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        await update.message.reply_text(
            "Welcome to the Video Downloader Bot! 🎥\n\n"
            "Send me a YouTube, Instagram, or Facebook video URL to download it.\n\n"
            "✨ Features:\n"
            "• Multiple quality options (720p, 480p, 360p)\n"
            "• Audio-only download option\n"
            "• Fast downloads with optimized settings\n\n"
            "Note: Files larger than 50MB will be sent as direct download links."
        )

    async def handle_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming URLs and ask for quality/audio preference."""
        user = update.effective_user
        url = update.message.text.strip()

        # Check rate limiting
        if is_rate_limited(user.id):
            await update.message.reply_text(
                "⏳ Please wait a few seconds before making another request."
            )
            return

        # Validate URL
        if not is_valid_url(url):
            await update.message.reply_text("❌ Please send a valid URL.")
            return

        # Detect platform
        platform = detect_platform(url)
        if not platform:
            await update.message.reply_text(
                "❌ Sorry, I only support YouTube, Instagram, and Facebook URLs."
            )
            return

        # Store URL for this user
        self.pending_downloads[user.id] = (url, platform)

        # Create quality selection buttons
        keyboard = [
            [
                InlineKeyboardButton("🎥 720p (Best)", callback_data="format_best720"),
                InlineKeyboardButton("🎬 480p", callback_data="format_best480"),
            ],
            [
                InlineKeyboardButton("📺 360p", callback_data="format_best360"),
                InlineKeyboardButton("🎵 Audio Only", callback_data="format_audio"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"📱 Choose quality for {platform.capitalize()} video:\n\n"
            "⏱️ Note: Larger qualities may take longer to download",
            reply_markup=reply_markup,
        )

    async def handle_quality_selection(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle quality selection callback."""
        query = update.callback_query
        user = query.from_user

        # Get format type from callback data
        format_type = query.data.replace("format_", "")

        # Get stored URL
        if user.id not in self.pending_downloads:
            answer_result = query.answer("❌ URL expired. Please send the URL again.")
            if inspect.isawaitable(answer_result):
                await answer_result
            return

        url, platform = self.pending_downloads[user.id]

        # Acknowledge button press
        answer_result = query.answer()
        if inspect.isawaitable(answer_result):
            await answer_result

        status_message = await query.edit_message_text("⏳ Downloading... Please wait.")

        format_labels = {
            "best720": "720p",
            "best480": "480p",
            "best360": "360p",
            "audio": "Audio Only",
        }

        try:
            logger.info(f"User {user.id} requested {format_type} for {platform}")

            # Download video with selected format
            file_path, direct_link = await self.downloader.download_video(
                url, format_type=format_type
            )

            if file_path:
                # Send the video file
                try:
                    file_size = os.path.getsize(file_path) / (1024 * 1024)  # Size in MB
                    logger.info(f"Sending file: {file_size:.2f} MB")

                    format_label = format_labels.get(format_type, format_type)
                    caption = f"✅ Downloaded from {platform.capitalize()} ({format_label})\n📦 Size: {file_size:.2f} MB"

                    with open(file_path, "rb") as video_file:
                        await query.message.reply_document(
                            document=video_file,
                            caption=caption,
                            read_timeout=30,
                            write_timeout=30,
                            connect_timeout=30,
                        )
                except Exception as e:
                    logger.error(f"Error sending file: {e}")
                    await status_message.edit_text(
                        f"❌ Error sending the video file: {str(e)}\n"
                        "The file might be too large or the connection is slow. "
                        "Please try again or use a smaller video."
                    )
                finally:
                    try:
                        os.remove(file_path)  # Clean up temp file
                    except:
                        pass

                try:
                    await status_message.delete()
                except:
                    pass
            elif direct_link:
                # Send direct link
                await status_message.edit_text(
                    f"📥 Video is too large (>50MB). Direct download link:\n\n{direct_link}"
                )
            else:
                await status_message.edit_text("❌ Failed to download the video.")

        except ValueError as e:
            await status_message.edit_text(f"⚠️ {str(e)}")
        except Exception as e:
            logger.error(f"Error processing URL {url}: {e}")
            await status_message.edit_text(
                f"❌ An unexpected error occurred: {str(e)}\n" "Please try again."
            )
        finally:
            # Clean up pending download
            if user.id in self.pending_downloads:
                del self.pending_downloads[user.id]

    def get_handlers(self):
        """Return list of handlers."""
        return [
            CommandHandler("start", self.start_command),
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_url),
            CallbackQueryHandler(self.handle_quality_selection, pattern="^format_"),
        ]
