import inspect
import logging
import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)
from downloader import VideoDownloader
from utils import is_valid_url, detect_platform, is_rate_limited, get_rate_limit_seconds
from translations import translate
USER_LANGS_FILE = "user_langs.json"

def get_user_lang(user_id):
    import json
    try:
        with open(USER_LANGS_FILE, "r", encoding="utf-8") as f:
            langs = json.load(f)
        return langs.get(str(user_id), "ar")
    except Exception:
        return "ar"

def set_user_lang(user_id, lang):
    import json
    try:
        with open(USER_LANGS_FILE, "r", encoding="utf-8") as f:
            langs = json.load(f)
    except Exception:
        langs = {}
    langs[str(user_id)] = lang
    with open(USER_LANGS_FILE, "w", encoding="utf-8") as f:
        json.dump(langs, f, ensure_ascii=False)
from stats import increment_stats, get_user_stats, get_total_stats
import asyncio

logger = logging.getLogger(__name__)

# --- متابعة صفحة فيسبوك ---
FACEBOOK_PAGE_URL = "https://www.facebook.com/share/1BWj4b2vUB/"
ALLOWED_USERS_FILE = "allowed_users.json"


def load_allowed_users():
    try:
        with open(ALLOWED_USERS_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_allowed_users(users_set):
    with open(ALLOWED_USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(users_set), f)


class BotHandlers:
    def __init__(
        self,
        admin_id: int,
        cookies_file: str | None = None,
        cookies_from_browser: str | None = None,
    ):
        self.admin_id = admin_id
        self.downloader = VideoDownloader(
            max_file_size_mb=200,
            cookies_file=cookies_file, cookies_from_browser=cookies_from_browser
        )
        # Store pending downloads: {user_id: (url, platform)}
        self.pending_downloads = {}

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        user_id = update.effective_user.id
        lang = get_user_lang(user_id)
        allowed_users = load_allowed_users()
        keyboard = [
            [InlineKeyboardButton("✅ تمت المتابعة، ابدأ الاستخدام", callback_data="fb_followed")],
            [InlineKeyboardButton("🔗 متابعة الصفحة على فيسبوك", url=FACEBOOK_PAGE_URL)],
            [InlineKeyboardButton(translate("lang_button", lang), callback_data="change_lang")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if user_id not in allowed_users:
            await update.message.reply_text(
                "👋 قبل استخدام البوت يجب متابعة صفحتنا على فيسبوك:\n"
                f"{FACEBOOK_PAGE_URL}\n\n"
                "بعد المتابعة اضغط الزر بالأسفل 'تمت المتابعة' ليتم تفعيل البوت لك.",
                reply_markup=reply_markup,
            )
            return
        await update.message.reply_text(
            translate("start", lang),
            reply_markup=reply_markup,
        )

    async def handle_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming URLs and ask for quality/audio preference."""
        user = update.effective_user
        user_id = user.id
        allowed_users = load_allowed_users()
        if user_id not in allowed_users:
            keyboard = [
                [
                    InlineKeyboardButton(
                        "✅ تمت المتابعة، ابدأ الاستخدام", callback_data="fb_followed"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔗 متابعة الصفحة على فيسبوك", url=FACEBOOK_PAGE_URL
                    )
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "👋 قبل استخدام البوت يجب متابعة صفحتنا على فيسبوك:\n"
                f"{FACEBOOK_PAGE_URL}\n\n"
                "بعد المتابعة اضغط الزر بالأسفل 'تمت المتابعة' ليتم تفعيل البوت لك.",
                reply_markup=reply_markup,
            )
            return

        url = update.message.text.strip()

        # Log user message for admin panel
        from utils import log_user_message

        log_user_message(user.id, url)

        # Send user message to admin
        if user.id != self.admin_id:
            try:
                username = user.username or "(لا يوجد)"
                first_name = user.first_name or ""
                last_name = user.last_name or ""
                full_name = (first_name + " " + last_name).strip()
                admin_text = (
                    f"📩 رسالة جديدة من مستخدم:\n"
                    f"👤 الاسم: {full_name}\n"
                    f"🔗 اسم المستخدم: @{username}\n"
                    f"🆔 المعرف الرقمي: {user.id}\n"
                    f"💬 الرسالة: {url}"
                )
                await context.bot.send_message(chat_id=self.admin_id, text=admin_text)
            except Exception as e:
                logger.error(f"Failed to send user message to admin: {e}")

        # Check rate limiting
        if is_rate_limited(user.id):
            lang = get_user_lang(user.id)
            wait_msg = {
                "ar": f"⏳ يرجى الانتظار {get_rate_limit_seconds()} ثانية قبل إرسال طلب آخر.",
                "en": f"⏳ Please wait {get_rate_limit_seconds()} seconds before sending another request."
            }
            await update.message.reply_text(wait_msg.get(lang, wait_msg["ar"]))
            return

        # Validate URL
        if not is_valid_url(url):
            await update.message.reply_text("❌ يرجى إرسال رابط صحيح.")
            return

        # Detect platform
        platform = detect_platform(url)
        if not platform:
            lang = get_user_lang(user.id)
            msg = {
                "ar": "❌ عذرًا، البوت يدعم فقط روابط يوتيوب، إنستغرام، فيسبوك، تيك توك، وتويتر.",
                "en": "❌ Sorry, the bot only supports YouTube, Instagram, Facebook, TikTok, and Twitter links."
            }
            await update.message.reply_text(msg.get(lang, msg["ar"]))
            return

        # Store URL for this user
        self.pending_downloads[user.id] = (url, platform)

        # Create quality selection buttons
        keyboard = [
            [
                InlineKeyboardButton("🎥 1080p (الأعلى)", callback_data="format_best1080"),
                InlineKeyboardButton("🎥 720p", callback_data="format_best720"),
            ],
            [
                InlineKeyboardButton("🎬 480p", callback_data="format_best480"),
                InlineKeyboardButton("📺 360p", callback_data="format_best360"),
            ],
            [
                InlineKeyboardButton("🎵 صوت فقط (m4a)", callback_data="format_audio"),
                InlineKeyboardButton("🎶 mp3", callback_data="format_mp3"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"📱 اختر الجودة لفيديو {platform.capitalize()}:\n\n",
            reply_markup=reply_markup,
        )

    async def handle_quality_selection(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle quality selection callback and متابعة فيسبوك callback."""
        query = update.callback_query
        user = query.from_user


        # زر تغيير اللغة
        if query.data == "change_lang":
            current_lang = get_user_lang(user.id)
            new_lang = "en" if current_lang == "ar" else "ar"
            set_user_lang(user.id, new_lang)
            await query.answer(translate("lang_changed", new_lang))
            await query.edit_message_text(translate("start", new_lang))
            return

        # زر متابعة فيسبوك
        if query.data == "fb_followed":
            allowed_users = load_allowed_users()
            allowed_users.add(user.id)
            save_allowed_users(allowed_users)
            await query.answer("تم التفعيل! يمكنك الآن استخدام البوت.")
            await query.edit_message_text(
                "✅ تم تفعيل البوت لك! أرسل الآن رابط الفيديو للتحميل."
            )
            return

        # باقي الكول باك (اختيار الجودة)
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
            "best1080": "1080p",
            "best720": "720p",
            "best480": "480p",
            "best360": "360p",
            "audio": "صوت فقط (m4a)",
            "mp3": "mp3 صوت فقط",
        }

        try:
            logger.info(f"User {user.id} requested {format_type} for {platform}")

            # الخطوة الأولى: تحقق هل الرابط قائمة تشغيل
            file_path, direct_link, playlist_count = await self.downloader.download_video(
                url, format_type=format_type, playlist=False
            )

            if playlist_count and playlist_count > 1:
                # تحذير المستخدم إذا كانت القائمة كبيرة
                if playlist_count > 10:
                    await status_message.edit_text(f"⚠️ هذا الرابط يحتوي على قائمة تشغيل بعدد {playlist_count} فيديو. هل تريد المتابعة؟ (سيتم تحميل أول 10 فيديو فقط)")
                else:
                    await status_message.edit_text(f"🔗 هذا الرابط قائمة تشغيل بعدد {playlist_count} فيديو. هل تريد المتابعة؟")

                # زر متابعة التحميل
                keyboard = [[InlineKeyboardButton("تحميل القائمة", callback_data=f"playlist_{format_type}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.message.reply_text("اضغط للمتابعة:", reply_markup=reply_markup)
                return

            # إذا ليس قائمة تشغيل أو فيديو واحد فقط
            if file_path:
                increment_stats(user.id)
                try:
                    file_size = os.path.getsize(file_path) / (1024 * 1024)
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
                    # إشعار خاص للمستخدم
                    await context.bot.send_message(chat_id=user.id, text="🎉 تم التحميل بنجاح! يمكنك الآن مشاهدة أو حفظ الملف.")
                except Exception as e:
                    logger.error(f"Error sending file: {e}")
                    await status_message.edit_text(
                        f"❌ حدث خطأ أثناء إرسال ملف الفيديو: {str(e)}\n"
                        "قد يكون الملف كبيرًا جدًا أو الاتصال بطيء. "
                        "يرجى المحاولة مرة أخرى أو استخدام فيديو أصغر."
                    )
                    # إشعار خاص بفشل الإرسال
                    await context.bot.send_message(chat_id=user.id, text=f"❌ حدث خطأ أثناء إرسال الملف: {str(e)}")
                finally:
                    try:
                        os.remove(file_path)
                    except:
                        pass
                try:
                    await status_message.delete()
                except:
                    pass
            elif direct_link:
                await status_message.edit_text(
                    f"📥 الفيديو كبير جدًا (>200 ميجابايت). رابط التحميل المباشر:\n\n{direct_link}"
                )
                await context.bot.send_message(chat_id=user.id, text="📥 تم تجهيز رابط تحميل مباشر للفيديو الكبير.")
            else:
                await status_message.edit_text("❌ فشل تحميل الفيديو.")
                await context.bot.send_message(chat_id=user.id, text="❌ فشل تحميل الفيديو. تأكد من الرابط أو جرب لاحقًا.")
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_count = get_user_stats(user_id)
        total = get_total_stats()
        await update.message.reply_text(f"📊 إحصائيات التحميل:\n• عدد تحميلاتك: {user_count}\n• إجمالي التحميلات: {total}")

        except ValueError as e:
            # رسائل خطأ واضحة للمستخدم
            await status_message.edit_text(f"❌ {str(e)}")
            await context.bot.send_message(chat_id=user.id, text=f"❌ {str(e)}")
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
            CommandHandler("stats", self.stats_command),
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_url),
            CallbackQueryHandler(self.handle_quality_selection),
        ]
