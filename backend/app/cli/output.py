"""
Arcane output console using Rich for stylized ritual output.
"""
import os
import sys
from typing import Optional
from rich.console import Console
from rich.progress import (
    Progress, SpinnerColumn, TextColumn, BarColumn, 
    TimeRemainingColumn, TimeElapsedColumn, TaskProgressColumn
)
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text


class ArcaneConsole:
    """
    Centralized console for arcane ritual output.
    
    Provides methods for stage messages, progress bars, seal boxes,
    fracture runes, and dividers while respecting --plain mode and NO_COLOR.
    """
    
    # Stage sigils mapping
    SIGILS = {
        "scribe": "⊢",
        "scry": "⟁",
        "profile": "⌬",
        "vessel": "⧈",
        "distill": "⚗",
        "attune": "◇",
        "mux": "⌘",
        "evaporate": "⇮",
        "purge": "⌿",
        "seal": "■",
        # Legacy support (map old names to new)
        "validate": "⊢",
        "scan": "⟁",
        "condense": "◇",
        "upload": "⇮",
        "clean": "⌿",
    }
    
    # Stage name mapping: arcane → technical
    STAGE_MAPPING = {
        "scribe": "validate",
        "scry": "detect source",
        "distill": "download",
        "mux": "embed",
        "seal": "save",
        "vessel": "prepare",
        "attune": "locate",
        "profile": "extract metadata",
        "evaporate": "upload",
        "purge": "cleanup",
        # Legacy support
        "validate": "validate",
        "scan": "detect source",
        "condense": "locate",
        "upload": "upload",
        "clean": "cleanup",
    }
    
    # Message mapping: arcane → technical
    MESSAGE_MAPPING = {
        "scribing input": "validating input",
        "checking URL...": "checking URL...",
        "source scryed": "source detected",
        "detecting source...": "detecting source...",
        "inscribing metadata": "embedding metadata",
        "inscribing metadata...": "embedding metadata...",
        "inscription complete": "metadata embedded",
        "bottled": "saved",
        "charging vessel": "preparing file",
        "distilling stream": "downloading",
        "transmuting stream": "downloading",  # Legacy support
        "distillation complete": "download complete",
        "saturation complete": "download complete",  # Legacy support
        "attunement complete": "file located",
        "file bound": "file located",  # Legacy support
        "evaporating artifact": "uploading",
        "uploading to cloud...": "uploading to cloud...",
        "evaporating artifact...": "uploading...",
        "purging residues": "cleaning up",
        "purging residues...": "cleaning up...",
        "chamber clear": "cleanup complete",
        "ready": "ready",
        "accepted": "accepted",
        "transfer complete": "transfer complete",
        "initializing...": "initializing...",
        "partial metadata recovered": "partial metadata recovered",
    }
    
    def _translate_message_partial(self, message: str) -> str:
        """
        Translate message with partial matching for dynamic messages.
        Handles messages like "source: youtube" by translating the prefix.
        
        Args:
            message: Message text that may contain dynamic content
            
        Returns:
            Translated message
        """
        if self.arcane_terms:
            return message
        
        # Check for partial matches in dynamic messages
        if message.startswith("source: "):
            return message.replace("source: ", "source detected: ", 1)
        elif message.startswith('title="'):
            # Keep title messages as-is, they're already technical
            return message
        
        return message
    
    # Phase header mapping: arcane → technical
    PHASE_HEADER_MAPPING = {
        "⟁ SCRYING": "⟁ DETECTING",
        "⚗ DISTILLING": "⚗ DOWNLOADING",
        "◇ ATTUNING": "◇ LOCATING",
        "⌘ MUXING": "⌘ EMBEDDING",
        "⇮ EVAPORATING": "⇮ UPLOADING",
        "SEAL COMPLETE": "SAVE COMPLETE",
    }
    
    # Pulse marks for progress animation
    PULSE_MARKS = ["◐", "◓", "◑", "◒"]
    
    # Stage-to-spinner mapping (non-emoji spinners only)
    # Reference: python -m rich.spinner
    # Forbidden: christmas, arrow2, earth, hearts, monkey, moon, runner, smiley, weather
    SPINNER_MAP = {
        "scribe": "dots",      # Inscribing dots
        "scry": "dots3",       # Divination pulses
        "profile": "dots2",    # Data extraction matrix
        "vessel": "toggle11",  # Matches vessel sigil ⧈
        "distill": "arc",      # Distillation rotation
        "attune": "dots4",     # Frequency alignment
        "mux": "dots",         # Stream weaving
        "evaporate": "arrow3", # Ascending upload
        "purge": "dots5",      # Cleaning residue
        "seal": "toggle3",     # Final seal stamp
        # Technical aliases
        "validate": "dots",
        "detect": "dots3",
        "download": "arc",
        "embed": "dots",
        "upload": "arrow3",
        "cleanup": "dots5",
        "save": "toggle3",
    }
    
    def __init__(self, plain: bool = False, arcane_terms: Optional[bool] = None):
        """
        Initialize ArcaneConsole.
        
        Args:
            plain: If True, disable colors and animations (for CI/logs)
            arcane_terms: If False, use technical terms instead of arcane. 
                         If None, reads from ARCANE_TERMS env var (default: True)
        """
        self.plain = plain or os.getenv("NO_COLOR", "").lower() in ("1", "true", "yes")
        
        # Determine arcane_terms setting
        if arcane_terms is None:
            arcane_terms_str = os.getenv("ARCANE_TERMS", "true").lower()
            self.arcane_terms = arcane_terms_str in ("1", "true", "yes")
        else:
            self.arcane_terms = arcane_terms
        
        # Create console instances
        self.console = Console(force_terminal=not self.plain, no_color=self.plain)
        self.err_console = Console(stderr=True, force_terminal=not self.plain, no_color=self.plain)
        
        # Color styles
        self.colors = {
            "success": "green" if not self.plain else None,
            "processing": "cyan" if not self.plain else None,
            "warning": "yellow" if not self.plain else None,
            "error": "bold red" if not self.plain else None,
        }
    
    def _translate_stage(self, stage: str) -> str:
        """Translate stage name from arcane to technical if needed."""
        if self.arcane_terms:
            return stage
        return self.STAGE_MAPPING.get(stage, stage)
    
    def _translate_message(self, message: str) -> str:
        """Translate message from arcane to technical if needed."""
        if self.arcane_terms:
            return message
        # Try full match first
        if message in self.MESSAGE_MAPPING:
            return self.MESSAGE_MAPPING[message]
        # Try partial matching for dynamic messages
        return self._translate_message_partial(message)
    
    def translate_message(self, message: str) -> str:
        """Public method to translate message from arcane to technical if needed."""
        return self._translate_message(message)
    
    def _translate_phase_header(self, phase: str) -> str:
        """Translate phase header from arcane to technical if needed."""
        if self.arcane_terms:
            return phase
        # Check if phase contains any arcane terms
        for arcane, technical in self.PHASE_HEADER_MAPPING.items():
            if arcane in phase:
                return phase.replace(arcane, technical)
        return phase
    
    def print_stage(
        self,
        stage: str,
        message: str,
        status: Optional[str] = None,
        style: Optional[str] = None
    ) -> None:
        """
        Print stage message with sigil.
        
        Args:
            stage: Stage name (e.g., "scribe", "distill")
            message: Message text
            status: Optional status text
            style: Optional style (success, processing, warning, error)
        """
        # Translate stage and message if needed
        display_stage = self._translate_stage(stage)
        display_message = self._translate_message(message)
        display_status = self._translate_message(status) if status else None
        
        sigil = self.SIGILS.get(stage, "")
        if display_status:
            text = f"{sigil} {display_message} | {display_status}"
        else:
            text = f"{sigil} {display_message}"
        
        # Apply style if provided
        if style and style in self.colors:
            style_val = self.colors[style]
            if style_val:
                self.console.print(text, style=style_val)
            else:
                self.console.print(text)
        else:
            self.console.print(text)
    
    def stage_status(self, stage: str, message: str):
        """
        Show a status spinner for a stage (e.g., "checking URL...").
        Use with context manager for automatic spinner.
        
        Uses stage-consistent non-emoji spinners from SPINNER_MAP.
        
        Args:
            stage: Stage name
            message: Status message
            
        Returns:
            Console status context manager
        """
        sigil = self.SIGILS.get(stage, "")
        display_stage = self._translate_stage(stage)
        display_message = self._translate_message(message)
        
        # Get stage-specific spinner (non-emoji only)
        spinner = self.SPINNER_MAP.get(stage, "dots")
        
        return self.console.status(
            f"[bold]{sigil}[/bold] {display_message}",
            spinner=spinner,
            spinner_style="cyan" if not self.plain else None,
        )
    
    def stage_ok(self, stage: str, message: str, duration: Optional[str] = None) -> None:
        """
        Print a consistent stage success line with uniform formatting.
        
        Args:
            stage: Stage name
            message: Success message
            duration: Optional duration (e.g., "10:23")
        """
        sigil = self.SIGILS.get(stage, "")
        display_stage = self._translate_stage(stage)
        display_message = self._translate_message(message)
        
        # Use Table.grid for consistent alignment
        t = Table.grid(padding=(0, 1))
        t.add_column(width=2, style="bold")
        t.add_column(width=12, style="bold")
        t.add_column()
        
        if duration:
            t.add_row(f"{sigil}", display_stage, f"[green]✓[/green] {display_message} [dim]{duration}[/dim]")
        else:
            t.add_row(f"{sigil}", display_stage, f"[green]✓[/green] {display_message}")
        
        self.console.print(t)
    
    def print_success(self, stage: str, message: str, status: Optional[str] = None) -> None:
        """Print success message with checkmark."""
        # Translate stage and message if needed
        display_stage = self._translate_stage(stage)
        display_message = self._translate_message(message)
        display_status = self._translate_message(status) if status else None
        
        sigil = "[✓]"
        if display_status:
            text = f"{sigil} {display_stage} | {display_status}"
        else:
            text = f"{sigil} {display_stage} | {display_message}"
        self.console.print(text, style=self.colors["success"])
    
    def print_divider(self) -> None:
        """Print glyph divider between major phases using Rich Rule."""
        self.console.print(Rule(characters="~∿", style="dim"))
    
    def print_phase_header(self, phase: str) -> None:
        """
        Print phase header using arcane glyph pattern.
        
        Args:
            phase: Phase name (e.g., "⚗ DISTILL", "⌘ MUX")
        """
        # Translate phase header if needed
        display_phase = self._translate_phase_header(phase)
        # Use arcane glyph pattern with phase name
        self.console.print(f"~∿~∿~∿~∿~∿~∿~ [dim]⟦{display_phase}⟧[/dim] ~∿~∿~∿~∿~∿~∿~")
    
    def print_progress(
        self,
        stage: str,
        percent: int,
        status: str,
        pulse: Optional[str] = None
    ) -> None:
        """
        Print progress bar with pulse mark.
        
        DEPRECATED: Use create_progress_context() for Rich-based progress instead.
        This ASCII-based method is kept for backward compatibility only.
        
        Args:
            stage: Stage name
            percent: Progress percentage (0-100)
            status: Status description
            pulse: Optional pulse mark (◐ ◓ ◑ ◒)
        """
        # Translate stage and status if needed
        display_stage = self._translate_stage(stage)
        display_status = self._translate_message(status)
        
        percent = max(0, min(100, percent))
        bar_length = 20
        filled = int(bar_length * percent / 100)
        unfilled = bar_length - filled
        
        # Build progress bar
        if filled == bar_length:
            bar = "=" * filled
            pulse_text = ""
        else:
            bar = "=" * filled + ">" + "." * (unfilled - 1) if unfilled > 0 else "=" * filled
            pulse_text = f" {pulse}" if pulse else ""
        
        sigil = self.SIGILS.get(stage, ">>")
        text = f"{sigil} {display_stage} | [{bar}] {percent}% | {display_status}{pulse_text}"
        self.console.print(text, end="\r")
    
    def create_progress_context(
        self,
        stage: str,
        total: Optional[int] = None,
        description: Optional[str] = None
    ) -> Progress:
        """
        Create Rich Progress context manager for progress bars.
        
        Uses spinner for unknown totals, bar for known totals.
        Reference: https://rich.readthedocs.io/en/stable/progress.html
        
        Args:
            stage: Stage name
            total: Total progress (None for indeterminate/pulsing)
            description: Initial description
            
        Returns:
            Rich Progress instance configured with Alchemux styling
        """
        display_stage = self._translate_stage(stage)
        sigil = self.SIGILS.get(stage, "")
        spinner = self.SPINNER_MAP.get(stage, "dots")
        
        # Build columns based on whether total is known
        if total is None:
            # Indeterminate progress - use spinner (will switch to bar when total is set)
            columns = [
                SpinnerColumn(spinner_name=spinner),
                TextColumn(f"[bold]{sigil}[/bold]"),
                TextColumn("[bold]{task.fields[stage]}[/bold]"),
                TextColumn("[progress.description]{task.description}"),
                TextColumn("|"),
                TextColumn("{task.fields[status]}"),
                TimeElapsedColumn(),
            ]
        else:
            # Determinate progress - use bar
            columns = [
                TextColumn(f"[bold]{sigil}[/bold]"),
                TextColumn("[bold]{task.fields[stage]}[/bold]"),
                BarColumn(bar_width=None, complete_style="green", finished_style="green"),
                TaskProgressColumn(),
                TextColumn("|"),
                TextColumn("[progress.description]{task.description}"),
                TextColumn("{task.fields[status]}"),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
            ]
        
        progress = Progress(
            *columns,
            console=self.console,
            transient=False,
            expand=True,
            disable=self.plain,
        )
        
        return progress
    
    def create_spinner_status(self, stage: str, message: str):
        """
        Create Rich Status spinner for unknown-duration tasks.
        
        Alias for stage_status() for API consistency with PRD.
        
        Reference: https://rich.readthedocs.io/en/stable/console.html#status
        
        Args:
            stage: Stage name
            message: Status message
            
        Returns:
            Console status context manager
        """
        return self.stage_status(stage, message)
    
    def add_progress_task(
        self,
        progress: Progress,
        stage: str,
        total: Optional[int] = None,
        status: str = "",
        description: str = "",
        pulse: Optional[str] = None
    ) -> int:
        """
        Add a task to a progress context.
        
        Args:
            progress: Progress instance
            stage: Stage name
            total: Total progress (None for unknown)
            status: Status description
            pulse: Initial pulse mark (not used in new format, kept for compatibility)
            
        Returns:
            Task ID
        """
        # Translate stage and status if needed
        display_stage = self._translate_stage(stage)
        display_status = self._translate_message(status) if status else ""
        
        if total is None:
            return progress.add_task(
                description=description or display_stage,
                total=None,
                stage=display_stage,
                status=display_status
            )
        else:
            return progress.add_task(
                description=description or "initializing",
                total=total,
                stage=display_stage,
                status=display_status
            )
    
    def rotate_pulse(self, iteration: int) -> str:
        """
        Rotate pulse marks: ◐ → ◓ → ◑ → ◒ → ◐
        
        Args:
            iteration: Current iteration number
            
        Returns:
            Pulse mark character
        """
        return self.PULSE_MARKS[iteration % len(self.PULSE_MARKS)]
    
    def print_seal(
        self,
        title_base: Optional[str] = None,
        items: Optional[list] = None,
        location: Optional[str] = None,
        locations: Optional[list] = None,
    ) -> None:
        """
        Print seal box: title (no ext) in header when provided; one line per output.
        items = [(ext, path_or_url), ...] — when len > 1, show ".ext bottled → path_or_URL".
        Legacy: location / locations as plain strings still supported.
        """
        # Normalize to (title_base, list of (ext, path_or_url))
        if items:
            display_pairs = [(str(e).strip(), str(v).strip()) for e, v in items if v]
        elif locations:
            display_pairs = [("", str(s).strip()) for s in locations if s]
        elif location:
            display_pairs = [("", str(location).strip())]
        else:
            display_pairs = []

        if not display_pairs:
            return

        if self.arcane_terms:
            action = "bottled"
            box_title = "SEAL COMPLETE"
        else:
            action = "saved"
            box_title = "SAVE COMPLETE"
        if title_base:
            box_title = f"{box_title} — {title_base}"

        show_ext = len(display_pairs) > 1
        content_lines = []
        for ext, path_or_url in display_pairs:
            if show_ext and ext:
                prefix = f"[bold][■][/bold] .{ext} {action} → "
            else:
                prefix = f"[bold][■][/bold] {action} → "
            content_lines.append(prefix + f"[dim]{path_or_url}[/dim]")
        content = "\n".join(content_lines)

        panel_style = self.colors["success"] if self.colors["success"] else "default"
        self.console.print(
            Panel.fit(
                content,
                title=box_title,
                border_style=panel_style,
                padding=(0, 1),
            )
        )

    def print_fractured_box(self, entries: list) -> None:
        """
        Print FRACTURED box (red outline) for failed saves.
        entries = [(ext_or_type, cause), ...]
        Arcane: "⟬⌿⟭ [.ext] fractured | cause: cause"
        Tech: "[×] [.ext] save failed | cause: cause"
        """
        if not entries:
            return
        if self.arcane_terms:
            sigil, label = "⟬⌿⟭", "fractured"
        else:
            sigil, label = "[×]", "save failed"
        content_lines = [
            f"{sigil} [.{ext}] {label} | cause: {cause}"
            for ext, cause in entries
        ]
        content = "\n".join(content_lines)
        style = self.colors["error"] or "red"
        self.err_console.print(
            Panel.fit(
                content,
                title="FRACTURED",
                border_style=style,
                padding=(0, 1),
            )
        )
    
    def print_fracture(self, stage: str, cause: str) -> None:
        """
        Print fracture rune error message.
        
        Args:
            stage: Stage name where error occurred
            cause: Error cause/message
        """
        # Translate stage if needed
        display_stage = self._translate_stage(stage)
        self.err_console.print(f"⟬×⟭ {display_stage} | fracture detected", style=self.colors["error"])
        self.err_console.print(f"    └─ cause: {cause}", style=self.colors["error"])
    
    def print_banner(self) -> None:
        """
        Print ALCHEMUX banner using hardcoded gothic-style ASCII art.
        
        Uses text-based representation for reliability and experimentation.
        Applies gold color (yellow) via Rich if not in plain mode.
        Uses raw strings to preserve exact backslash formatting.
        
        The exact spacing, backslashes, and characters are critical for proper rendering.
        Any changes will break the logo display.
        """
        # DO NOT CHANGE banner_lines - Exact format required for logo rendering
        # Hardcoded gothic-style ASCII art
        # In markdown, \\ in code blocks represents a single backslash
        # Using raw strings (r"...") preserves backslashes literally
        # Each \\ in the raw string will print as a single backslash
        banner_lines = [
            "  ___                                             ",
            " -   -_  ,,      ,,                               ",
            "(  ~/||  ||      ||                         ,     ",
            r"(  / ||  ||  _-_ ||/\\  _-_  \\/\\/\\ \\ \\ \\ /` ",
            r" \/==||  || ||   || || || \\ || || || || ||  \\   ",
            r" /_ _||  || ||   || || ||/   || || || || ||  /\\  ",
            r"(  - \\, \\ \\,/ \\ |/  \\,/ \\ \\ \\ \\/\\ /  \; ",
            "                   _/                             ",
        ]
        
        # Apply gold color via Rich if not in plain mode
        if not self.plain:
            for line in banner_lines:
                self.console.print(line, style="yellow", highlight=False)
        else:
            # Plain mode - no color, print exactly as-is
            for line in banner_lines:
                print(line)
        
        print()

