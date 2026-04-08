# translations.py
# Simple translation dictionary and helpers

def get_translations():
    return {
        "start": {
            "ar": "مرحبًا بك في بوت تحميل الفيديوهات! 🎥\n\nMHD\n\nتحميل دون علامة مائيه\nأرسل لي رابط فيديو من يوتيوب أو إنستغرام أو فيسبوك لتحميله.\n\n✨ الميزات:\n• خيارات جودة متعددة (1080p، 720p، 480p، 360p)\n• إمكانية تحميل الصوت فقط\n• تحميل سريع\n\n💡 ملاحظة: يُرجى عدم إرسال روابط غير مرتبطة بفيديوهات.",
            "en": "Welcome to the video downloader bot! 🎥\n\nMHD\n\nDownload without watermark.\nSend me a YouTube, Instagram, or Facebook video link to download.\n\n✨ Features:\n• Multiple quality options (1080p, 720p, 480p, 360p)\n• Audio-only download\n• Fast download\n\n💡 Note: Please do not send non-video links."
        },
        "choose_quality": {
            "ar": "📱 اختر الجودة:",
            "en": "📱 Choose quality:"
        },
        "lang_button": {
            "ar": "🇬🇧 English",
            "en": "🇸🇦 العربية"
        },
        "lang_changed": {
            "ar": "تم تغيير اللغة إلى العربية.",
            "en": "Language changed to English."
        },
        # ... أضف المزيد حسب الحاجة ...
    }

def translate(key, lang="ar"):
    t = get_translations()
    return t.get(key, {}).get(lang, t.get(key, {}).get("ar", key))
