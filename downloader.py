import yt_dlp
import os
import tempfile
from typing import Optional, Tuple, Callable
import logging

logger = logging.getLogger(__name__)


class VideoDownloader:
    def __init__(
        self,
        max_file_size_mb: int = 200,
        cookies_file: Optional[str] = None,
        cookies_from_browser: Optional[str] = None,
    ):
        self.max_file_size_mb = max_file_size_mb
        self.cookies_file = cookies_file
        self.cookies_from_browser = cookies_from_browser
        self.temp_dir = tempfile.mkdtemp()

    def get_ydl_opts(self, format_type: str = "best720", playlist: bool = False) -> dict:
        """Get yt-dlp options based on requested format.

        Args:
            format_type: 'best720', 'best480', 'best360', 'audio'
        """


        format_specs = {
            "best1080": "best[height<=1080]/best[height<=720]/best",
            "best720": "best[height<=720]/best[height<=480]/best",
            "best480": "best[height<=480]/best[height<=360]/best",
            "best360": "best[height<=360]/best[height<=240]/best",
            "audio": "bestaudio[ext=m4a]/bestaudio",
            "mp3": "bestaudio/best",
        }

        format_choice = format_specs.get(format_type, format_specs["best1080"])

        options = {
            "format": format_choice,
            "outtmpl": os.path.join(self.temp_dir, "% (title)s.%(ext)s"),
            "noplaylist": not playlist,  # Allow playlist download if requested
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [self._progress_hook],
            "socket_timeout": 30,  # 30 seconds timeout
            "postprocessors": [],
            "keepvideo": True,  # Keep source file
        }

        # دعم التحويل إلى mp3
        if format_type == "mp3":
            options["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ]

        if self.cookies_file:
            if os.path.isfile(self.cookies_file):
                options["cookiefile"] = self.cookies_file
            else:
                logger.warning(
                    "YouTube cookies file configured but not found: %s",
                    self.cookies_file,
                )
        elif self.cookies_from_browser:
            options["cookiesfrombrowser"] = (self.cookies_from_browser,)

        return options

    def _progress_hook(self, d):
        """Progress hook for yt-dlp."""
        if d["status"] == "downloading":
            try:
                percent = float(d.get("_percent_str", "0%").strip("%"))
                if hasattr(self, "_progress_callback") and self._progress_callback:
                    import asyncio

                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(self._progress_callback(percent))
                    except:
                        pass
            except (ValueError, KeyError):
                pass

    async def download_video(
        self,
        url: str,
        progress_callback: Optional[Callable[[float], None]] = None,
        format_type: str = "best720",
        playlist: bool = False,
    ) -> Tuple[Optional[str], Optional[str], Optional[int]]:
        """
        Download video or playlist from URL.
        Returns: (file_path, direct_link_if_large, playlist_count)
        If file_path is None and direct_link is provided, file is too large.
        If playlist_count > 1, it is a playlist.
        """
        try:
            self._progress_callback = progress_callback

            # Probe info to check if playlist
            with yt_dlp.YoutubeDL(self.get_ydl_opts(format_type, playlist=playlist)) as ydl:
                info = ydl.extract_info(url, download=False)
                playlist_count = 1
                if info.get('_type') == 'playlist' and 'entries' in info:
                    playlist_count = len(info['entries'])
                    if not playlist:
                        return None, None, playlist_count

                # Download
                ydl.download([url])

                # Find the downloaded file(s)
                files = os.listdir(self.temp_dir)
                if files:
                    file_path = os.path.join(self.temp_dir, files[0])
                    return file_path, None, playlist_count

        except yt_dlp.DownloadError as e:
            err_message = str(e)
            logger.error(f"Download error: {err_message}")
            # أسباب شائعة للفشل
            if (
                "Sign in to confirm you’re not a bot" in err_message
                or "cookies" in err_message.lower()
                or "Use --cookies-from-browser" in err_message
            ):
                raise ValueError("الفيديو يتطلب تسجيل الدخول أو محمي (خاص أو بعمر محدد). جرب فيديو آخر أو زود البوت بملف الكوكيز.")
            if "This video is unavailable" in err_message or "private" in err_message:
                raise ValueError("الفيديو غير متاح أو خاص.")
            if "Unsupported URL" in err_message:
                raise ValueError("الرابط غير مدعوم. يرجى التأكد من صحة الرابط والمنصة.")
            if "File is larger than" in err_message or "too large" in err_message:
                raise ValueError("الفيديو يتجاوز الحد الأقصى للحجم المسموح (200 ميغابايت).")
            raise ValueError(f"فشل التحميل: {err_message}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise ValueError(f"حدث خطأ غير متوقع: {str(e)}")

        return None, None, None

    def cleanup(self):
        """Clean up temporary files."""
        import shutil

        try:
            shutil.rmtree(self.temp_dir)
        except:
            pass
