"""
Arcane output console using Rich for stylized ritual output.
"""
import os
import sys
from typing import Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

try:
    from termcolor import colored
    HAS_TERMCOLOR = True
except ImportError:
    HAS_TERMCOLOR = False


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
        "SEAL COMPLETE": "SAVE COMPLETE",
    }
    
    # Pulse marks for progress animation
    PULSE_MARKS = ["◐", "◓", "◑", "◒"]
    
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
    
    def stage_status(self, stage: str, message: str) -> None:
        """
        Show a status spinner for a stage (e.g., "checking URL...").
        Use with context manager for automatic spinner.
        
        Args:
            stage: Stage name
            message: Status message
        """
        sigil = self.SIGILS.get(stage, "")
        display_stage = self._translate_stage(stage)
        display_message = self._translate_message(message)
        return self.console.status(f"[bold]{sigil}[/bold] {display_message}")
    
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
        Uses proper Rich Progress that handles log line collisions.
        
        Args:
            stage: Stage name
            total: Total progress (None for unknown duration)
            description: Initial description
            
        Returns:
            Rich Progress instance
        """
        # Translate stage if needed
        display_stage = self._translate_stage(stage)
        sigil = self.SIGILS.get(stage, "")
        
        if total is None:
            # Spinner for unknown duration (transient, overwrites line)
            progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
                console=self.console,
            )
        else:
            # Clean progress bar with stage name, bar, percentage, and status
            # Format: >> distill | [=====>........] 45% | charging vessel
            progress = Progress(
                TextColumn(f"[bold]>> {{task.fields[stage]}}[/bold] | {{task.description}}"),
                BarColumn(bar_width=None),
                TextColumn("{{task.percentage:>3.0f}}%"),
                TextColumn("|"),
                TextColumn("{{task.fields[status]}}"),
                TimeElapsedColumn(),
                console=self.console,
                transient=False,  # Keep progress bar visible
            )
        
        return progress
    
    def add_progress_task(
        self,
        progress: Progress,
        stage: str,
        total: Optional[int] = None,
        status: str = "",
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
            return progress.add_task(description=f"{display_stage}", total=None)
        else:
            return progress.add_task(
                description="initializing",
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
    
    def print_seal(self, file_path: str) -> None:
        """
        Print seal box completion message using Rich Panel with enhanced details.
        
        Args:
            file_path: Path to completed file
        """
        from pathlib import Path
        
        path_obj = Path(file_path)
        basename = path_obj.name
        dir_path = path_obj.parent
        
        # Translate seal message if needed
        if self.arcane_terms:
            action = "bottled"
            title = "SEAL COMPLETE"
        else:
            action = "saved"
            title = "SAVE COMPLETE"
        
        # Build panel content with basename emphasized and path dimmed
        content_lines = [
            f"[bold][■][/bold] {action} → [bold]{basename}[/bold]",
            f"[dim]path: {dir_path}/...[/dim]"
        ]
        
        content = "\n".join(content_lines)
        
        # Use Rich Panel for clean, terminal-aware display
        panel_style = self.colors["success"] if self.colors["success"] else "default"
        self.console.print(
            Panel.fit(
                content,
                title=title,
                border_style=panel_style,
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
        Applies gold color (yellow) if termcolor is available and not in plain mode.
        Uses raw strings to preserve exact backslash formatting.
        
        ⚠️  CRITICAL: DO NOT MODIFY THE BANNER_LINES BELOW (lines 277-285)
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
            r" /_ _||  || ||   || || ||/   || || || || ||  /\  ",
            r"(  - \\, \\ \\,/ \\ |/  \\,/ \\ \\ \\ \\/\\ /  \; ",
            "                   _/                             ",
        ]
        
        # Apply color if not in plain mode and termcolor is available
        if not self.plain and HAS_TERMCOLOR:
            try:
                # Use termcolor for yellow (gold-like) color
                for line in banner_lines:
                    print(colored(line, "yellow"))
            except Exception:
                # Fallback to plain if coloring fails
                for line in banner_lines:
                    print(line)
        else:
            # Plain mode or no termcolor - no color, print exactly as-is
            for line in banner_lines:
                print(line)
        
        print()

