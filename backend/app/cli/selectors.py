"""
Enhanced interactive selectors using Rich.

Provides modern CLI patterns with radio-button visual indicators,
section headers, status panels, and inline yes/no prompts.

Inspired by modern CLI UX patterns adapted to Alchemux's arcane theme.
"""

from typing import List, Optional, Tuple, Dict
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()

# Alchemux-themed selection indicators (arcane variant)
SELECTED_INDICATOR = "◉"  # Filled circle for selected
UNSELECTED_INDICATOR = "○"  # Empty circle for unselected
SECTION_MARKER = "◇"  # Diamond for section headers (matches attune sigil)
SECTION_MARKER_ACTIVE = "◆"  # Filled diamond for active sections

# Phase state indicators
PHASE_COMPLETE = "◆"  # Filled diamond
PHASE_CURRENT = "◇"  # Empty diamond (active)
PHASE_PENDING = "○"  # Empty circle (not started)


def render_selection_list(
    options: List[Tuple[str, str]],  # (value, display_label)
    selected_index: int,
    context_info: Optional[Dict[int, str]] = None,  # {index: "additional context"}
) -> str:
    """
    Render a selection list with radio-button indicators.

    Args:
        options: List of (value, display_label) tuples
        selected_index: Currently selected index
        context_info: Optional dict mapping index to contextual info

    Returns:
        Formatted string for display
    """
    lines = []
    for i, (value, label) in enumerate(options):
        if i == selected_index:
            indicator = f"[green]{SELECTED_INDICATOR}[/green]"
            label_style = "[bold]"
            label_end = "[/bold]"
            # Add context if available
            if context_info and i in context_info:
                context = f" [cyan]({context_info[i]})[/cyan]"
            else:
                context = ""
        else:
            indicator = f"[dim]{UNSELECTED_INDICATOR}[/dim]"
            label_style = ""
            label_end = ""
            context = ""

        lines.append(f"  {indicator} {label_style}{label}{label_end}{context}")

    return "\n".join(lines)


def interactive_select(
    title: str,
    options: List[Tuple[str, str]],
    default_index: int = 0,
    context_info: Optional[Dict[int, str]] = None,
    show_panel: bool = True,
) -> Tuple[str, int]:
    """
    Interactive single-select with numbered input fallback.

    Uses numbered selection for maximum terminal compatibility
    (works in CI, non-interactive terminals, piped input).

    Args:
        title: Selection prompt title
        options: List of (value, display_label) tuples
        default_index: Default selected index
        context_info: Optional contextual info per option
        show_panel: Wrap in panel (unused, kept for API compatibility)

    Returns:
        Tuple of (selected_value, selected_index)
    """
    console.print()
    console.print(f"[bold]{SECTION_MARKER} {title}[/bold]")

    for i, (value, label) in enumerate(options):
        marker = SELECTED_INDICATOR if i == default_index else UNSELECTED_INDICATOR
        style = "[green]" if i == default_index else "[dim]"
        end_style = "[/green]" if i == default_index else "[/dim]"
        context = ""
        if context_info and i in context_info:
            context = f" [cyan]({context_info[i]})[/cyan]"
        console.print(
            f"  {style}{marker}[/{end_style.strip('[/')}] [{i+1}] {label}{context}"
        )

    # Get selection
    try:
        choice = Prompt.ask(
            f"\n  Enter number [1-{len(options)}]", default=str(default_index + 1)
        )

        idx = int(choice) - 1
        if 0 <= idx < len(options):
            return options[idx][0], idx
    except (ValueError, EOFError, KeyboardInterrupt):
        pass

    return options[default_index][0], default_index


def inline_yes_no(prompt: str, default: bool = True, show_marker: bool = True) -> bool:
    """
    Compact inline Yes/No with visual indicators.

    Pattern: ◆ Enable auto-open after download?
             ● Yes / ○ No

    Args:
        prompt: Question text
        default: Default selection
        show_marker: Show section diamond marker

    Returns:
        True for Yes, False for No
    """
    marker = f"{SECTION_MARKER_ACTIVE} " if show_marker else ""

    if default:
        options_display = f"[green]{SELECTED_INDICATOR} Yes[/green] / [dim]{UNSELECTED_INDICATOR} No[/dim]"
    else:
        options_display = f"[dim]{UNSELECTED_INDICATOR} Yes[/dim] / [green]{SELECTED_INDICATOR} No[/green]"

    console.print(f"\n{marker}[bold]{prompt}[/bold]")
    console.print(f"  {options_display}")

    try:
        choice = Prompt.ask("  ", default="y" if default else "n").lower().strip()
        return choice in ("y", "yes", "1", "true")
    except (EOFError, KeyboardInterrupt):
        return default


def print_section_header(
    title: str, subtitle: Optional[str] = None, marker: str = SECTION_MARKER
) -> None:
    """
    Print section header with optional subtitle and hierarchy bar.

    Pattern:
    ◇ Audio Format (Setup)
    │ MP3 (default)
    │
    ◇ Storage Configuration ───────────────

    Args:
        title: Section title
        subtitle: Optional subtitle/context
        marker: Marker character (default: ◇)
    """
    console.print(f"\n[cyan]{marker}[/cyan] [bold]{title}[/bold]")
    if subtitle:
        console.print(f"[dim]│[/dim] {subtitle}")


def print_status_panel(
    title: str, content_lines: List[str], border_style: str = "dim"
) -> None:
    """
    Print a status panel with key-value pairs.

    Pattern:
    ╭─ Current Settings ────────────────────╮
    │ Output: ~/Downloads/Alchemux          │
    │ Audio format: flac                    │
    │ Storage: local                        │
    │ Arcane mode: enabled                  │
    ╰───────────────────────────────────────╯

    Args:
        title: Panel title
        content_lines: List of content lines
        border_style: Border color/style
    """
    content = "\n".join(content_lines)
    console.print(
        Panel(
            content,
            title=f"[bold]{title}[/bold]",
            title_align="left",
            border_style=border_style,
            padding=(0, 1),
        )
    )


def print_hierarchy_item(text: str, is_last: bool = False, indent: int = 0) -> None:
    """
    Print item with hierarchy indicator.

    Args:
        text: Item text
        is_last: If True, use └─ instead of │
        indent: Indentation level
    """
    prefix = "  " * indent
    connector = "└─" if is_last else "│"
    console.print(f"{prefix}[dim]{connector}[/dim] {text}")


def print_phase_indicator(
    phases: List[str], current_phase: int, phase_status: Optional[List[str]] = None
) -> None:
    """
    Print multi-phase progress indicator.

    Arcane Mode Pattern:
    ◆ scribe >
    ◆ scry >
    ◇ distill <- current
    ○ mux
    ○ seal

    Args:
        phases: List of phase names
        current_phase: Index of current phase (0-based)
        phase_status: Optional list of status strings per phase
    """
    for i, phase in enumerate(phases):
        if i < current_phase:
            marker = f"[green]{PHASE_COMPLETE}[/green]"
            status = "[green]>[/green]" if not phase_status else phase_status[i]
        elif i == current_phase:
            marker = f"[cyan]{PHASE_CURRENT}[/cyan]"
            status = "[cyan]<-[/cyan]"
        else:
            marker = f"[dim]{PHASE_PENDING}[/dim]"
            status = ""

        console.print(f"  {marker} {phase} {status}")


def print_info_panel(
    title: str, instructions: List[str], docs_link: Optional[str] = None
) -> None:
    """
    Print informational panel with instructions.

    Pattern:
    ◇ S3 Storage Setup ───────────────────

    You'll need:
      - S3 endpoint URL
      - Access key and secret key
      - Bucket name

    Credentials are stored securely in .env

    Docs: docs/commands.md#storage

    Args:
        title: Panel title
        instructions: List of instruction lines
        docs_link: Optional documentation link
    """
    console.print(
        f"\n[cyan]{SECTION_MARKER}[/cyan] [bold]{title}[/bold] [dim]{'─' * 30}[/dim]"
    )
    console.print()
    for instruction in instructions:
        console.print(f"  {instruction}")
    if docs_link:
        console.print(f"\n  [dim]Docs: {docs_link}[/dim]")
    console.print()
