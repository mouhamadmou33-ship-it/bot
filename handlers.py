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
            "مرحبًا بك في بوت تحميل الفيديوهات! 🎥\n\n"
            "أرسل لي رابط فيديو من يوتيوب أو إنستغرام أو فيسبوك لتحميله.\n\n"
            "✨ الميزات:\n"
            "• خيارات جودة متعددة (720p، 480p، 360p)\n"
            "• إمكانية تحميل الصوت فقط\n"
            "• تحميل سريع بإعدادات محسنة\n\n"
            "ملاحظة: الملفات الأكبر من 50 ميجابايت سيتم إرسالها كرابط تحميل مباشر."
        )

    async def handle_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming URLs and ask for quality/audio preference."""
        user = update.effective_user
        url = update.message.text.strip()

        # Log user message for admin panel
        from utils import log_user_message

        log_user_message(user.id, url)

        # Send user message to admin
        if user.id != self.admin_id:
            try:
                admin_text = (
                    f"📩 رسالة جديدة من مستخدم:\n" f"👤 ID: {user.id}\n" f"💬: {url}"
                )
                await context.bot.send_message(chat_id=self.admin_id, text=admin_text)
            except Exception as e:
                logger.error(f"Failed to send user message to admin: {e}")

        # Check rate limiting
        if is_rate_limited(user.id):
            await update.message.reply_text(
                "⏳ يرجى الانتظار بضع ثوانٍ قبل إرسال طلب آخر."
            )
            return

        # Validate URL
        if not is_valid_url(url):
            await update.message.reply_text("❌ يرجى إرسال رابط صحيح.")
            return

        # Detect platform
        platform = detect_platform(url)
        if not platform:
            await update.message.reply_text(
                "❌ عذرًا، البوت يدعم فقط روابط يوتيوب، إنستغرام، وفيسبوك."
            )
            return

        # Store URL for this user
        self.pending_downloads[user.id] = (url, platform)

        # Create quality selection buttons
        keyboard = [
            [
                InlineKeyboardButton(
                    "🎥 ٧٢٠p (الأفضل)", callback_data="format_best720"
                ),
                InlineKeyboardButton("🎬 ٤٨٠p", callback_data="format_best480"),
            ],
            [
                InlineKeyboardButton("📺 ٣٦٠p", callback_data="format_best360"),
                InlineKeyboardButton("🎵 صوت فقط", callback_data="format_audio"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"📱 اختر الجودة لفيديو {platform.capitalize()}:\n\n"
            "⏱️ ملاحظة: قد تستغرق الجودات الأعلى وقتًا أطول في التحميل",
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
            answer_result = query.answer(
                "❌ انتهت صلاحية الرابط. يرجى إرسال الرابط مرة أخرى."
            )
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
            "best720": "٧٢٠p",
            "best480": "٤٨٠p",
            "best360": "٣٦٠p",
            "audio": "صوت فقط",
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
                    caption = f"✅ تم التحميل من {platform.capitalize()} ({format_label})\n📦 الحجم: {file_size:.2f} م.ب"

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
                        f"❌ حدث خطأ أثناء إرسال ملف الفيديو: {str(e)}\n"
                        "قد يكون الملف كبيرًا جدًا أو الاتصال بطيء. "
                        "يرجى المحاولة مرة أخرى أو استخدام فيديو أصغر."
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
                    f"📥 الفيديو كبير جدًا (>٥٠ ميجابايت). رابط التحميل المباشر:\n\n{direct_link}"
                )
            else:
                await status_message.edit_text("❌ فشل تحميل الفيديو.")

        except ValueError as e:
            await status_message.edit_text(f"⚠️ {str(e)}")
        except Exception as e:
            logger.error(f"Error processing URL {url}: {e}")
            await status_message.edit_text(
                f"❌ حدث خطأ غير متوقع: {str(e)}\n" "يرجى المحاولة مرة أخرى."
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
