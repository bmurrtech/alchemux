"""Behavior specs for PRD 012 media enrichment.

Seams under test:
- yt-dlp option construction through ``MediaDownloader._build_ydl_opts``;
- Layer-2 mutagen enrichment (sanitizer + Artist/comment/date/SOURCE_URL);
- companion info file writer + config/setup gating (ADR 0008 / FR-9);
- shared rate-limit recovery advice (``get_rate_limit_advice``);
- persistent non-secret config passed into a later distill;
- browser profile probe / auto-pick for cookie opt-in;
- setup video-gate for the cookie prompt (preserve when video is No).

Network extraction and browser cookie stores remain system boundaries and are not
used by these tests. Layer-2 container tests use local ffmpeg to build tiny media.
"""

import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

# Ensure ``app.*`` imports work when running from the repository root.
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.config_manager import ConfigManager, EphemeralConfig  # noqa: E402
from app.core.config_wizard import (  # noqa: E402
    configure_download_settings,
    configure_ytdl_settings,
)
from app.core.downloader import MediaDownloader  # noqa: E402
from app.core.setup_wizard import interactive_setup_refresh  # noqa: E402
from app.core.toml_config import read_toml  # noqa: E402
from app.utils.browser_detect import (  # noqa: E402
    detect_cookie_browsers,
    pick_cookie_browser,
)
from app.utils.info_file import (  # noqa: E402
    maybe_write_companion_info_file,
    resolve_info_file_format,
    write_companion_info_file,
)
from app.utils.rate_limit import RATE_LIMIT_ADVICE, get_rate_limit_advice  # noqa: E402


def _downloader_with_config(tmpdir: Path, toml_text: str) -> MediaDownloader:
    cfg_dir = tmpdir / "cfg"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / ".env").write_text("")
    (cfg_dir / "config.toml").write_text(toml_text.strip())
    return MediaDownloader(ConfigManager(env_path=str(cfg_dir / ".env")))


def test_distill_writes_and_embeds_thumbnails_by_default() -> None:
    """A normal audio distill asks yt-dlp to retain source artwork in the seal."""
    with tempfile.TemporaryDirectory() as tmp:
        downloader = _downloader_with_config(
            Path(tmp),
            """
[paths]
output_dir = "./downloads"
temp_dir = "./tmp"

[media.audio]
format = "mp3"

[media.video]
enabled = false
format = "mp4"
""",
        )

        opts = downloader._build_ydl_opts("artifact", audio_format="mp3")

    assert opts["writethumbnail"] is True
    assert opts["embedthumbnail"] is True


@pytest.mark.parametrize(
    ("container", "expects_chapters"),
    [("mp4", True), ("mkv", True), ("webm", False)],
)
def test_video_chapters_only_embed_in_chapter_capable_containers(
    container: str, expects_chapters: bool
) -> None:
    """Video seals include navigation markers only when their container supports them."""
    with tempfile.TemporaryDirectory() as tmp:
        downloader = _downloader_with_config(
            Path(tmp),
            f"""
[paths]
output_dir = "./downloads"
temp_dir = "./tmp"

[media.audio]
format = "mp3"

[media.video]
enabled = true
format = "{container}"
""",
        )

        opts = downloader._build_ydl_opts("artifact", video_format=container)

    assert opts.get("embedchapters", False) is expects_chapters


def test_audio_only_distill_does_not_request_chapter_embedding() -> None:
    """The default audio-only transmutation stays outside the chapter path."""
    with tempfile.TemporaryDirectory() as tmp:
        downloader = _downloader_with_config(
            Path(tmp),
            """
[paths]
output_dir = "./downloads"
temp_dir = "./tmp"

[media.audio]
format = "mp3"

[media.video]
enabled = false
format = "mp4"
""",
        )

        opts = downloader._build_ydl_opts("artifact", audio_format="mp3")

    assert opts.get("embedchapters", False) is False


def test_distill_seals_into_a_title_named_folder() -> None:
    """Sealed media lands in a folder named after the title stem."""
    with tempfile.TemporaryDirectory() as tmp:
        downloader = _downloader_with_config(
            Path(tmp),
            """
[paths]
output_dir = "./downloads"
temp_dir = "./tmp"

[media.audio]
format = "mp3"

[media.video]
enabled = false
format = "mp4"
""",
        )

        opts = downloader._build_ydl_opts("My_Song", audio_format="mp3")

    assert opts["outtmpl"] == "My_Song/My_Song.%(ext)s"
    assert opts["writeinfojson"] is False
    assert opts["writedescription"] is False


def test_ytdlp_sidecars_off_by_default_and_on_when_configured() -> None:
    """yt-dlp machine sidecars stay off unless download.ytdlp_sidecars is enabled."""
    with tempfile.TemporaryDirectory() as tmp:
        off = _downloader_with_config(
            Path(tmp),
            """
[paths]
output_dir = "./downloads"
temp_dir = "./tmp"
""",
        )
        assert off._build_ydl_opts("a", audio_format="mp3")["writeinfojson"] is False

        on = _downloader_with_config(
            Path(tmp) / "on",
            """
[paths]
output_dir = "./downloads"
temp_dir = "./tmp"

[download]
ytdlp_sidecars = true
""",
        )
        opts = on._build_ydl_opts("a", audio_format="mp3")
        assert opts["writeinfojson"] is True
        assert opts["writedescription"] is True


def test_legacy_sidecar_artifacts_key_is_ignored() -> None:
    """Unreleased sidecar_artifacts does not enable yt-dlp machine sidecars."""
    with tempfile.TemporaryDirectory() as tmp:
        downloader = _downloader_with_config(
            Path(tmp),
            """
[paths]
output_dir = "./downloads"
temp_dir = "./tmp"

[download]
sidecar_artifacts = true
""",
        )
        opts = downloader._build_ydl_opts("a", audio_format="mp3")
        assert opts["writeinfojson"] is False
        assert opts["writedescription"] is False


def test_info_file_defaults_on_for_missing_key_and_ephemeral() -> None:
    """Absent download.info_file and ephemeral mode both default the companion on."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = Path(tmp) / "cfg"
        cfg_dir.mkdir()
        (cfg_dir / ".env").write_text("")
        (cfg_dir / "config.toml").write_text(
            '[paths]\noutput_dir = "./downloads"\ntemp_dir = "./tmp"\n'
        )
        config = ConfigManager(env_path=str(cfg_dir / ".env"))
        assert config.get_bool("download.info_file", default=True) is True
        assert (config.get("download.info_file_format") or "md") == "md"
        assert config.get_bool("download.ytdlp_sidecars", default=False) is False

    ephemeral = EphemeralConfig("/tmp/out")
    assert ephemeral.get_bool("download.info_file", default=True) is True
    assert ephemeral.get("download.info_file_format") == "md"
    assert ephemeral.get_bool("download.ytdlp_sidecars", default=False) is False


def test_companion_info_file_writes_markdown_beside_seal() -> None:
    """Enabled companion writer produces .info.md with source URL, title, and creator."""
    with tempfile.TemporaryDirectory() as tmp:
        media = Path(tmp) / "Why_Humanity.flac"
        media.write_bytes(b"flac-stub")
        info = {
            "title": "Why Humanity Will Never Leave The Solar System",
            "channel": "Cool Worlds",
            "description": "A talk about space.\n\nMore detail.",
            "upload_date": "20240115",
            "duration": 372,
            "chapters": [
                {"start_time": 0, "title": "Intro"},
                {"start_time": 60, "title": "Physics"},
            ],
        }
        path = write_companion_info_file(
            media,
            "https://youtu.be/Cyl3X88KEgg",
            info=info,
            fmt="md",
        )
        assert path is not None
        assert path.name == "Why_Humanity.info.md"
        text = path.read_text(encoding="utf-8")
        assert "Why Humanity Will Never Leave The Solar System" in text
        assert "Cool Worlds" in text
        assert "https://youtu.be/Cyl3X88KEgg" in text
        assert "A talk about space." in text
        assert "00:00:00 — Intro" in text or "00:00 — Intro" in text
        assert "Downloaded with Alchemux" in text


def test_companion_info_file_respects_txt_format_and_disabled_gate() -> None:
    """txt format writes .info.txt; info_file=false means no companion file."""
    with tempfile.TemporaryDirectory() as tmp:
        media = Path(tmp) / "clip.mp3"
        media.write_bytes(b"mp3-stub")
        info = {"title": "Clip", "uploader": "Channel X"}
        txt_path = write_companion_info_file(
            media,
            "https://example.com/v",
            info=info,
            fmt="txt",
        )
        assert txt_path is not None
        assert txt_path.name == "clip.info.txt"
        body = txt_path.read_text(encoding="utf-8")
        assert "Title: Clip" in body
        assert "Creator / Channel: Channel X" in body
        assert "Source URL: https://example.com/v" in body

        assert resolve_info_file_format("nfo") == "md"
        assert resolve_info_file_format("TXT") == "txt"

        disabled = _downloader_with_config(
            Path(tmp) / "off",
            """
[paths]
output_dir = "./downloads"
temp_dir = "./tmp"

[download]
info_file = false
""",
        ).config
        other = Path(tmp) / "other.flac"
        other.write_bytes(b"flac-stub")
        assert (
            maybe_write_companion_info_file(
                disabled, other, "https://example.com/v", info=info
            )
            is None
        )
        assert list(other.parent.glob("other.info.*")) == []


def test_companion_info_file_skips_chapters_without_parseable_start() -> None:
    """Chapters missing or with bad start_time are omitted; never invent 00:00."""
    from app.utils.info_file import format_chapter_lines

    lines = format_chapter_lines(
        [
            {"title": "Intro", "start_time": 0},
            {"title": "No start"},
            {"title": "Bad", "start_time": "nope"},
            {"title": "Physics", "start_time": 60},
        ]
    )
    assert lines == ["00:00:00 — Intro", "00:01:00 — Physics"]


def test_companion_info_file_formats_duration_and_downloaded_iso() -> None:
    """Duration uses MM:SS / HH:MM:SS; Downloaded is ISO-8601 with offset."""
    from datetime import datetime, timezone, timedelta

    from app.utils.info_file import format_duration, write_companion_info_file

    assert format_duration(372) == "06:12"
    assert format_duration(3720) == "01:02:00"

    with tempfile.TemporaryDirectory() as tmp:
        media = Path(tmp) / "clip.flac"
        media.write_bytes(b"flac-stub")
        when = datetime(2026, 8, 5, 18, 40, 0, tzinfo=timezone(timedelta(hours=-4)))
        path = write_companion_info_file(
            media,
            "https://example.com/v",
            info={"title": "Clip", "duration": 372},
            fmt="md",
            downloaded_at=when,
        )
        assert path is not None
        text = path.read_text(encoding="utf-8")
        assert "06:12" in text
        assert "2026-08-05T18:40:00-04:00" in text

        long_media = Path(tmp) / "long.flac"
        long_media.write_bytes(b"flac-stub")
        huge = "x" * 3000
        path2 = write_companion_info_file(
            long_media,
            "https://example.com/v",
            info={"title": "Long", "description": huge},
            fmt="txt",
            downloaded_at=when,
        )
        assert path2 is not None
        assert huge in path2.read_text(encoding="utf-8")


def test_setup_companion_info_file_defaults_yes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Setup's companion-info confirm defaults to Yes and persists info_file=true."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = Path(tmp) / "cfg"
        output_dir = Path(tmp) / "output"
        cfg_dir.mkdir()
        output_dir.mkdir()
        env_path = cfg_dir / ".env"
        toml_path = cfg_dir / "config.toml"
        env_path.write_text("")
        toml_path.write_text(
            '[paths]\noutput_dir = "./downloads"\ntemp_dir = "./tmp"\n\n'
            '[eula]\naccepted = "true"\n'
        )
        config = ConfigManager(env_path=str(env_path))
        companion_defaults: list[bool] = []

        def confirm(message: str, default: bool = False) -> bool:
            if "companion information file" in message.lower():
                companion_defaults.append(default)
                return default
            return False

        def select(message: str, choices: object, default: object = None) -> object:
            if message == "Output directory":
                return "custom"
            return default

        monkeypatch.setattr("app.core.setup_wizard.confirm", confirm)
        monkeypatch.setattr("app.core.setup_wizard.select", select)
        monkeypatch.setattr(
            "app.core.setup_wizard.filepath", lambda **_kwargs: str(output_dir)
        )
        monkeypatch.setattr("app.core.setup_wizard.is_packaged_build", lambda: False)
        monkeypatch.setattr(
            "app.core.setup_wizard.check_media_deps",
            lambda: (SimpleNamespace(found=True), SimpleNamespace(found=True)),
        )

        assert interactive_setup_refresh(config) is True
        stored = read_toml(toml_path)

    assert companion_defaults == [True]
    assert stored["download"]["info_file"] is True
    assert stored["download"].get("info_file_format", "md") == "md"
    assert stored["download"]["ytdlp_sidecars"] is False


def test_config_download_settings_persist_info_file_and_ytdlp_sidecars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Download Settings wizard can disable the companion file and enable yt-dlp sidecars."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = Path(tmp) / "cfg"
        cfg_dir.mkdir()
        env_path = cfg_dir / ".env"
        toml_path = cfg_dir / "config.toml"
        env_path.write_text("")
        toml_path.write_text(
            '[paths]\noutput_dir = "./downloads"\ntemp_dir = "./tmp"\n\n'
            "[download]\n"
            "info_file = true\n"
            'info_file_format = "md"\n'
            "ytdlp_sidecars = false\n"
        )
        config = ConfigManager(env_path=str(env_path))

        # Change info_file? Y → Enable? N; Change format? N; Change ytdlp? Y → Enable? Y
        confirms = iter([True, False, False, True, True])

        def confirm(_message: str, default: bool = False) -> bool:
            return next(confirms)

        monkeypatch.setattr("app.core.config_wizard.confirm", confirm)
        configure_download_settings(config)
        stored = read_toml(toml_path)

    assert stored["download"]["info_file"] is False
    assert stored["download"]["ytdlp_sidecars"] is True


def test_distill_does_not_enable_artist_title_parse_metadata_by_default() -> None:
    """Always-on Artist-Title parse-metadata is disabled; Layer-2 owns Artist."""
    with tempfile.TemporaryDirectory() as tmp:
        downloader = _downloader_with_config(
            Path(tmp),
            """
[paths]
output_dir = "./downloads"
temp_dir = "./tmp"

[media.audio]
format = "mp3"
""",
        )

        opts = downloader._build_ydl_opts("artifact", audio_format="mp3")

    parsers = [
        pp for pp in opts.get("postprocessors", []) if pp.get("key") == "MetadataParser"
    ]
    assert parsers == []


def test_compact_comment_sanitizes_preserves_emoji_and_appends_source() -> None:
    """Compact comments keep emoji, strip controls, and always carry Source footer."""
    from app.utils.metadata import (
        COMPACT_DESCRIPTION_MAX_BYTES,
        build_compact_comment,
        sanitize_description_text,
    )

    dirty = "👉 hello\x00\r\n\nworld"
    clean = sanitize_description_text(dirty)
    assert "\x00" not in clean
    assert "👉" in clean
    assert "\r" not in clean

    comment = build_compact_comment(dirty, "https://example.com/v")
    assert "Source: https://example.com/v" in comment
    assert "👉" in comment

    huge = "x" * (COMPACT_DESCRIPTION_MAX_BYTES + 500)
    truncated = build_compact_comment(huge, "https://example.com/v")
    assert (
        truncated.encode("utf-8").endswith(b"Source: https://example.com/v")
        or "Source: https://example.com/v" in truncated
    )
    assert "…" in truncated or len(truncated.encode("utf-8")) <= (
        COMPACT_DESCRIPTION_MAX_BYTES + 80
    )


def _ffmpeg_tiny_media(path: Path, fmt: str) -> None:
    """Create a tiny media file for mutagen tests (requires local ffmpeg)."""
    import shutil
    import subprocess

    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg required for Layer-2 mutagen container tests")
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=r=44100:cl=mono",
        "-t",
        "0.1",
    ]
    if fmt == "mp3":
        cmd += ["-q:a", "9", str(path)]
    elif fmt == "flac":
        cmd += ["-c:a", "flac", str(path)]
    else:
        raise AssertionError(fmt)
    subprocess.run(cmd, check=True)


@pytest.mark.parametrize("fmt", ["mp3", "flac"])
def test_layer2_enrich_writes_artist_comment_date_and_source_url(fmt: str) -> None:
    """Layer-2 writes the lean field set into sealed audio containers."""
    from mutagen.flac import FLAC
    from mutagen.mp3 import MP3

    from app.utils.metadata import (
        enrich_sealed_metadata,
        read_source_url_from_metadata,
    )

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"seal.{fmt}"
        _ffmpeg_tiny_media(path, fmt)
        info = {
            "channel": "The AI Automators",
            "description": "👉 Access our course\n\n#AI",
            "upload_date": "20260710",
        }
        url = "https://www.youtube.com/watch?v=tjRkSyfac1A"
        assert enrich_sealed_metadata(str(path), url, info=info) is True
        assert read_source_url_from_metadata(str(path)) == url

        if fmt == "mp3":
            tags = MP3(path).tags
            assert tags is not None
            assert tags.get("TPE1").text[0] == "The AI Automators"
            assert "👉" in tags.getall("COMM")[0].text[0]
            assert "Source:" in tags.getall("COMM")[0].text[0]
            assert "2026-07-10" in str(tags.get("TDRC"))
        else:
            audio = FLAC(path)
            assert audio["ARTIST"][0] == "The AI Automators"
            assert "👉" in audio["DESCRIPTION"][0]
            assert "Source:" in audio["DESCRIPTION"][0]
            assert audio["DATE"][0] == "2026-07-10"
            assert audio["SOURCE_URL"][0] == url


@pytest.mark.parametrize(
    "error_text",
    [
        "ERROR: HTTP Error 429: Too Many Requests",
        "HTTP Error 402: Payment Required",
        "the source reported Too Many Requests",
    ],
)
def test_rate_limited_fractures_use_one_shared_recovery_message(
    error_text: str,
) -> None:
    """Shared recovery wording covers every rate-limit form distill may surface."""
    assert get_rate_limit_advice(error_text) == RATE_LIMIT_ADVICE
    assert "alchemux config" in RATE_LIMIT_ADVICE
    assert "after enabling video" in RATE_LIMIT_ADVICE


def test_non_rate_limited_errors_do_not_get_rate_limit_advice() -> None:
    """Unrelated HTTP failures do not receive cookie/rate-limit recovery copy."""
    assert get_rate_limit_advice("HTTP Error 404: Not Found") is None


def test_browser_probe_reports_only_existing_profile_roots() -> None:
    """Cookie browser detection lists names whose fake profile roots exist."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "Chrome").mkdir()
        (root / "Firefox").mkdir()
        roots = {
            "chrome": (root / "Chrome",),
            "firefox": (root / "Firefox",),
            "brave": (root / "Brave",),
        }
        assert detect_cookie_browsers(roots=roots) == ["chrome", "firefox"]


def test_browser_auto_pick_prefers_os_default_when_multiple_detected() -> None:
    """When several browsers exist, auto-pick follows the preferred OS order."""
    assert (
        pick_cookie_browser(["firefox", "chrome"], preferred=("chrome", "firefox"))
        == "chrome"
    )
    assert pick_cookie_browser(["firefox"]) == "firefox"
    assert pick_cookie_browser([]) is None


def test_browser_auto_pick_falls_back_to_fixed_priority_not_os_extra() -> None:
    """Without an OS default present, pick chrome→firefox→brave before chromium."""
    assert pick_cookie_browser(
        ["chromium", "brave"], preferred=("firefox", "chrome")
    ) == ("brave")
    assert (
        pick_cookie_browser(
            ["chromium", "brave", "opera"], preferred=("firefox", "chrome")
        )
        == "brave"
    )


def test_config_reliability_defaults_browser_cookie_access_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Declining the reliability prompt keeps browser-cookie access absent from a seal."""
    monkeypatch.delenv("YTDL_COOKIES_FROM_BROWSER", raising=False)
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = Path(tmp) / "cfg"
        cfg_dir.mkdir()
        (cfg_dir / ".env").write_text("")
        (cfg_dir / "config.toml").write_text(
            '[paths]\noutput_dir = "./downloads"\ntemp_dir = "./tmp"\n'
        )
        config = ConfigManager(env_path=str(cfg_dir / ".env"))
        prompt_defaults: list[bool] = []
        responses = iter([True, False])

        def confirm(_message: str, default: bool = False) -> bool:
            prompt_defaults.append(default)
            return next(responses)

        monkeypatch.setattr("app.core.config_wizard.confirm", confirm)
        configure_ytdl_settings(config)

        opts = MediaDownloader(config)._build_ydl_opts("artifact", audio_format="mp3")

    assert prompt_defaults == [False, False]
    assert "cookiesfrombrowser" not in opts


def test_config_reliability_auto_picks_a_detected_browser(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Opting in saves an auto-detected browser name in TOML, never a cookie export."""
    monkeypatch.delenv("YTDL_COOKIES_FROM_BROWSER", raising=False)
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = Path(tmp) / "cfg"
        cfg_dir.mkdir()
        env_path = cfg_dir / ".env"
        toml_path = cfg_dir / "config.toml"
        env_path.write_text("")
        toml_path.write_text(
            '[paths]\noutput_dir = "./downloads"\ntemp_dir = "./tmp"\n'
        )
        config = ConfigManager(env_path=str(env_path))
        responses = iter([True, True])
        monkeypatch.setattr(
            "app.core.config_wizard.confirm",
            lambda _message, default=False: next(responses),
        )
        monkeypatch.setattr(
            "app.utils.browser_detect.detect_cookie_browsers",
            lambda: ["firefox", "chrome"],
        )
        monkeypatch.setattr(
            "app.utils.browser_detect.pick_cookie_browser",
            lambda detected, preferred=None: "firefox",
        )

        configure_ytdl_settings(config)
        stored = read_toml(toml_path)
        opts = MediaDownloader(config)._build_ydl_opts("artifact", audio_format="mp3")

        assert env_path.read_text() == ""

    assert stored["ytdl"]["cookies_from_browser"] == "firefox"
    assert opts["cookiesfrombrowser"] == ("firefox",)


def test_setup_without_video_preserves_existing_cookie_preference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Declining video in setup skips the cookie prompt and keeps the stored browser."""
    monkeypatch.delenv("YTDL_COOKIES_FROM_BROWSER", raising=False)
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = Path(tmp) / "cfg"
        output_dir = Path(tmp) / "output"
        cfg_dir.mkdir()
        output_dir.mkdir()
        env_path = cfg_dir / ".env"
        toml_path = cfg_dir / "config.toml"
        env_path.write_text("")
        toml_path.write_text(
            '[paths]\noutput_dir = "./downloads"\ntemp_dir = "./tmp"\n\n'
            '[eula]\naccepted = "true"\n\n'
            '[ytdl]\ncookies_from_browser = "chrome"\n'
        )
        config = ConfigManager(env_path=str(env_path))
        cookie_prompts = 0

        def confirm(message: str, default: bool = False) -> bool:
            nonlocal cookie_prompts
            if message.startswith("Pass cookies for YouTube downloads?"):
                cookie_prompts += 1
                return False
            return False

        def select(message: str, choices: object, default: object = None) -> object:
            if message == "Output directory":
                return "custom"
            return default

        monkeypatch.setattr("app.core.setup_wizard.confirm", confirm)
        monkeypatch.setattr("app.core.setup_wizard.select", select)
        monkeypatch.setattr(
            "app.core.setup_wizard.filepath", lambda **_kwargs: str(output_dir)
        )
        monkeypatch.setattr("app.core.setup_wizard.is_packaged_build", lambda: False)
        monkeypatch.setattr(
            "app.core.setup_wizard.check_media_deps",
            lambda: (SimpleNamespace(found=True), SimpleNamespace(found=True)),
        )

        assert interactive_setup_refresh(config) is True
        stored = read_toml(toml_path)

    assert cookie_prompts == 0
    assert stored["ytdl"]["cookies_from_browser"] == "chrome"


@pytest.mark.parametrize(
    ("opt_in", "detected", "expected_browser"),
    [
        (False, ["firefox"], ""),
        (True, ["firefox"], "firefox"),
        (True, [], ""),
    ],
)
def test_setup_with_video_cookie_opt_in_auto_picks_browser(
    monkeypatch: pytest.MonkeyPatch,
    opt_in: bool,
    detected: list[str],
    expected_browser: str,
) -> None:
    """With video enabled, setup cookie Y auto-picks a detected browser; N clears."""
    monkeypatch.delenv("YTDL_COOKIES_FROM_BROWSER", raising=False)
    monkeypatch.delenv("media.video.enabled", raising=False)
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = Path(tmp) / "cfg"
        output_dir = Path(tmp) / "output"
        cfg_dir.mkdir()
        output_dir.mkdir()
        env_path = cfg_dir / ".env"
        toml_path = cfg_dir / "config.toml"
        env_path.write_text("")
        toml_path.write_text(
            '[paths]\noutput_dir = "./downloads"\ntemp_dir = "./tmp"\n\n'
            '[eula]\naccepted = "true"\n\n'
            '[ytdl]\ncookies_from_browser = "chrome"\n'
        )
        config = ConfigManager(env_path=str(env_path))
        cookie_prompt_defaults: list[bool] = []

        def confirm(message: str, default: bool = False) -> bool:
            if message.startswith("Enable video download?"):
                return True
            if message.startswith("Pass cookies for YouTube downloads?"):
                cookie_prompt_defaults.append(default)
                return opt_in
            return False

        def select(message: str, choices: object, default: object = None) -> object:
            if message == "Output directory":
                return "custom"
            return default

        monkeypatch.setattr("app.core.setup_wizard.confirm", confirm)
        monkeypatch.setattr("app.core.setup_wizard.select", select)
        monkeypatch.setattr(
            "app.core.setup_wizard.filepath", lambda **_kwargs: str(output_dir)
        )
        monkeypatch.setattr("app.core.setup_wizard.is_packaged_build", lambda: False)
        monkeypatch.setattr(
            "app.core.setup_wizard.check_media_deps",
            lambda: (SimpleNamespace(found=True), SimpleNamespace(found=True)),
        )
        monkeypatch.setattr(
            "app.utils.browser_detect.detect_cookie_browsers",
            lambda: detected,
        )
        monkeypatch.setattr(
            "app.utils.browser_detect.pick_cookie_browser",
            lambda browsers, preferred=None: (browsers[0] if browsers else None),
        )

        assert interactive_setup_refresh(config) is True
        stored = read_toml(toml_path)

        assert env_path.read_text() == ""

    assert cookie_prompt_defaults == [False]
    assert stored.get("ytdl", {}).get("cookies_from_browser", "") == expected_browser
