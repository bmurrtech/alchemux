"""
Config command - Manage configuration location and diagnostics.

Provides subcommands for viewing, diagnosing, and relocating configuration.
"""

import os
import sys
import shutil
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from app.cli.output import ArcaneConsole
from app.cli.prompts import confirm, checkbox, filepath
from app.core.config_manager import (
    ConfigManager,
    get_pointer_file_path,
    write_config_pointer,
    get_default_output_dir,
)
from app.core.toml_config import read_toml
from app.core.eula import is_packaged_build

# Create Typer app for config subcommands
app = typer.Typer(
    name="config",
    help="Manage configuration location and diagnostics",
    no_args_is_help=False,  # Allow callback to run wizard when no subcommand
)

console = Console()


def _run_repair_menu(config: ConfigManager, repair_options: list, issues: list) -> None:
    """
    Interactive repair menu for config doctor (PRD7 FR-4).

    Args:
        config: ConfigManager instance
        repair_options: List of (repair_id, description) tuples
        issues: List of (issue_id, message) tuples
    """
    console.print()
    console.print(Panel("[bold]Guided Repair[/bold]", border_style="yellow"))
    console.print()

    # Show available repairs
    repair_choices = [(rid, desc) for rid, desc in repair_options]
    selected_repairs = checkbox(
        message="Select repairs to apply",
        choices=repair_choices,
        default_selected=None,
    )

    if not selected_repairs or len(selected_repairs) == 0:
        console.print("\n[yellow]No repairs selected.[/yellow]")
        return

    # Create backup before any repairs (single-latest policy)
    console.print()
    console.print("[dim]Creating backup before repairs...[/dim]")
    backup_dir = config.create_backup()
    if not backup_dir:
        console.print(
            "[red]✗[/red] Failed to create backup. Aborting repairs for safety."
        )
        return

    console.print(f"[green]✓[/green] Backup created at {backup_dir}")
    console.print()

    # Execute repairs
    repair_success = True
    for repair_id in selected_repairs:
        try:
            if repair_id == "create_config_dir":
                config_dir = config.env_path.parent
                config_dir.mkdir(parents=True, exist_ok=True)
                console.print(
                    f"[green]✓[/green] Created config directory: {config_dir}"
                )

            elif repair_id == "recreate_toml":
                config._create_toml_from_example()
                console.print("[green]✓[/green] Recreated config.toml from example")

            elif repair_id == "restore_toml":
                if config.has_backup():
                    if config.restore_from_backup():
                        console.print(
                            "[green]✓[/green] Restored config.toml from backup"
                        )
                    else:
                        console.print("[red]✗[/red] Failed to restore from backup")
                        repair_success = False
                else:
                    console.print(
                        "[yellow]![/yellow] No backup available, recreating from example"
                    )
                    config._create_toml_from_example()
                    console.print("[green]✓[/green] Recreated config.toml from example")

            elif repair_id == "fix_output_path":
                from app.cli.prompts import filepath as prompt_filepath

                current_output = config.get(
                    "paths.output_dir", str(get_default_output_dir())
                )
                console.print(f"\nCurrent output directory: {current_output}")
                new_path = prompt_filepath(
                    message="Enter new output directory path",
                    default=current_output,
                    only_directories=True,
                    mandatory=False,
                )
                if new_path and new_path.strip():
                    from app.core.config_wizard import validate_path

                    is_valid, error = validate_path(new_path)
                    if is_valid:
                        expanded = os.path.abspath(os.path.expanduser(new_path))
                        Path(expanded).mkdir(parents=True, exist_ok=True)
                        config.set("paths.output_dir", expanded)
                        console.print(f"[green]✓[/green] Set output_dir = {expanded}")
                    else:
                        console.print(f"[red]✗[/red] {error}")
                        repair_success = False

            elif repair_id == "fix_temp_path":
                from app.cli.prompts import filepath as prompt_filepath

                current_temp = config.get("paths.temp_dir", "./tmp")
                console.print(f"\nCurrent temp directory: {current_temp}")
                new_path = prompt_filepath(
                    message="Enter new temp directory path",
                    default=current_temp,
                    only_directories=True,
                    mandatory=False,
                )
                if new_path and new_path.strip():
                    from app.core.config_wizard import validate_path

                    is_valid, error = validate_path(new_path)
                    if is_valid:
                        expanded = os.path.abspath(os.path.expanduser(new_path))
                        Path(expanded).mkdir(parents=True, exist_ok=True)
                        config.set("paths.temp_dir", expanded)
                        console.print(f"[green]✓[/green] Set temp_dir = {expanded}")
                    else:
                        console.print(f"[red]✗[/red] {error}")
                        repair_success = False

            elif repair_id == "fix_pointer":
                config_dir = config.env_path.parent
                write_config_pointer(config_dir)
                console.print(
                    "[green]✓[/green] Updated pointer to current config directory"
                )

        except Exception as e:
            console.print(f"[red]✗[/red] Repair '{repair_id}' failed: {e}")
            repair_success = False

    # If any repair failed, offer restore
    if not repair_success:
        console.print()
        console.print("[bold yellow]Some repairs failed.[/bold yellow]")
        restore = confirm("Restore from backup?", default=True)
        if restore:
            if config.restore_from_backup():
                console.print("[green]✓[/green] Restored from backup")
            else:
                console.print("[red]✗[/red] Failed to restore from backup")
    else:
        console.print()
        console.print(
            "[bold green]All selected repairs completed successfully![/bold green]"
        )


@app.command("show")
def config_show(
    plain: bool = typer.Option(False, "--plain", help="Disable colors"),
) -> None:
    """
    Show current configuration paths and values.

    Displays the active configuration directory, file paths, and key settings.
    """
    config = ConfigManager()

    # Create table
    table = Table(title="Configuration", show_header=True, header_style="bold cyan")
    table.add_column("Setting", style="dim")
    table.add_column("Value")

    # Active config directory
    config_dir = config.env_path.parent
    table.add_row("Config directory", str(config_dir))
    table.add_row("config.toml", str(config.toml_path))
    table.add_row(".env", str(config.env_path))

    # Pointer file status
    pointer_file = get_pointer_file_path()
    if pointer_file.exists():
        table.add_row("Pointer file", str(pointer_file))
    else:
        table.add_row("Pointer file", "[dim](not set)[/dim]")

    # Output and temp directories
    output_dir = config.get("paths.output_dir", str(get_default_output_dir()))
    temp_dir = config.get("paths.temp_dir", "./tmp")
    table.add_row("Output directory", output_dir)
    table.add_row("Temp directory", temp_dir)

    # Storage settings
    storage_dest = config.get("storage.destination", "local")
    storage_fallback = config.get("storage.fallback", "local")
    table.add_row("Storage destination", storage_dest)
    table.add_row("Storage fallback", storage_fallback)

    # UI settings
    arcane_terms = config.get("product.arcane_terms", "true")
    plain_mode = config.get("ui.plain", "false")
    table.add_row("Arcane terminology", arcane_terms)
    table.add_row("Plain mode", plain_mode)

    console.print(table)


@app.command("doctor")
def config_doctor(
    plain: bool = typer.Option(False, "--plain", help="Disable colors"),
) -> None:
    """
    Run diagnostics on configuration and offer guided repairs.

    Checks for common issues like missing files, invalid TOML, and missing credentials.
    If issues are found, offers interactive repair options with automatic backup.
    """
    config = ConfigManager()
    issues = []
    repair_options = []

    console.print(Panel("[bold]Configuration Diagnostics[/bold]", border_style="cyan"))
    console.print()

    # Check config directory
    config_dir = config.env_path.parent
    if config_dir.exists():
        console.print(f"[green]>[/green] Config directory exists: {config_dir}")
    else:
        console.print(f"[red]x[/red] Config directory missing: {config_dir}")
        issues.append(("config_dir_missing", "Config directory does not exist"))
        repair_options.append(("create_config_dir", "Create config directory"))

    # Check config.toml
    _toml_valid = False
    _toml_corrupted = False
    if config.toml_path.exists():
        try:
            toml_data = read_toml(config.toml_path)
            if toml_data:
                console.print("[green]>[/green] config.toml exists and valid")
                _toml_valid = True
            else:
                console.print("[yellow]![/yellow] config.toml is empty")
                issues.append(("toml_empty", "config.toml is empty"))
                repair_options.append(
                    ("recreate_toml", "Recreate config.toml from example")
                )
        except Exception as e:
            console.print(f"[red]x[/red] config.toml parse error: {e}")
            issues.append(("toml_invalid", f"config.toml invalid: {e}"))
            repair_options.append(
                ("recreate_toml", "Recreate config.toml from example")
            )
            repair_options.append(("restore_toml", "Restore config.toml from backup"))
            _toml_corrupted = True
    else:
        console.print(f"[red]x[/red] config.toml missing: {config.toml_path}")
        issues.append(("toml_missing", "config.toml does not exist"))
        repair_options.append(("recreate_toml", "Create config.toml from example"))

    # Check .env
    if config.env_path.exists():
        console.print("[green]>[/green] .env exists")
    else:
        console.print("[yellow]![/yellow] .env missing (may be created on first use)")

    # Check output directory
    output_dir = config.get("paths.output_dir", str(get_default_output_dir()))
    output_path = Path(output_dir)
    _output_writable = False
    if output_path.exists():
        if os.access(output_path, os.W_OK):
            console.print(f"[green]>[/green] Output directory writable: {output_dir}")
            _output_writable = True
        else:
            console.print(f"[red]x[/red] Output directory not writable: {output_dir}")
            issues.append(
                ("output_not_writable", f"Output directory not writable: {output_dir}")
            )
            repair_options.append(("fix_output_path", "Set new output directory path"))
    else:
        # Check if parent is writable (can create)
        parent = output_path.parent
        if parent.exists() and os.access(parent, os.W_OK):
            console.print(
                f"[yellow]![/yellow] Output directory will be created: {output_dir}"
            )
            _output_writable = True
        else:
            console.print(f"[red]x[/red] Cannot create output directory: {output_dir}")
            issues.append(
                (
                    "output_cannot_create",
                    f"Cannot create output directory: {output_dir}",
                )
            )
            repair_options.append(("fix_output_path", "Set new output directory path"))

    # Check temp directory
    temp_dir = config.get("paths.temp_dir", "./tmp")
    temp_path = Path(temp_dir)
    _temp_writable = False
    if temp_path.exists():
        if os.access(temp_path, os.W_OK):
            console.print(f"[green]>[/green] Temp directory writable: {temp_dir}")
            _temp_writable = True
        else:
            console.print(f"[red]x[/red] Temp directory not writable: {temp_dir}")
            issues.append(
                ("temp_not_writable", f"Temp directory not writable: {temp_dir}")
            )
            repair_options.append(("fix_temp_path", "Set new temp directory path"))
    else:
        parent = temp_path.parent
        if parent.exists() and os.access(parent, os.W_OK):
            console.print(
                f"[yellow]![/yellow] Temp directory will be created: {temp_dir}"
            )
            _temp_writable = True
        else:
            console.print(f"[red]x[/red] Cannot create temp directory: {temp_dir}")
            issues.append(
                ("temp_cannot_create", f"Cannot create temp directory: {temp_dir}")
            )
            repair_options.append(("fix_temp_path", "Set new temp directory path"))

    # Check storage credentials if configured
    storage_dest = config.get("storage.destination", "local")
    if storage_dest == "s3":
        if config.is_s3_configured():
            console.print("[green]>[/green] S3 credentials configured")
        else:
            console.print("[red]x[/red] S3 selected but credentials missing")
            issues.append(("s3_credentials_missing", "S3 credentials missing"))
            # Note: Not adding repair option here - user should run setup s3
    elif storage_dest == "gcp":
        if config.is_gcp_configured():
            console.print("[green]>[/green] GCP credentials configured")
        else:
            console.print("[red]x[/red] GCP selected but credentials missing")
            issues.append(("gcp_credentials_missing", "GCP credentials missing"))
            # Note: Not adding repair option here - user should run setup gcp

    # Check pointer file
    pointer_file = get_pointer_file_path()
    if pointer_file.exists():
        pointer_target = pointer_file.read_text().strip()
        if Path(pointer_target).exists():
            console.print(f"[green]>[/green] Pointer file valid: {pointer_target}")
        else:
            console.print(
                f"[yellow]![/yellow] Pointer file target missing: {pointer_target}"
            )
            issues.append(
                (
                    "pointer_invalid",
                    f"Pointer file points to non-existent directory: {pointer_target}",
                )
            )
            repair_options.append(
                ("fix_pointer", "Update pointer to current config directory")
            )
    else:
        console.print("[dim]-[/dim] No pointer file (using default config location)")

    # Summary
    console.print()
    if issues:
        console.print(f"[bold yellow]Found {len(issues)} issue(s):[/bold yellow]")
        for issue_id, issue_msg in issues:
            console.print(f"  [yellow]-[/yellow] {issue_msg}")

        # Offer repair menu (PRD7 FR-4)
        console.print()
        if repair_options:
            repair_now = confirm("Repair issues now?", default=True)
            if repair_now:
                _run_repair_menu(config, repair_options, issues)
        else:
            console.print(
                "[dim]No automatic repairs available. Please fix issues manually.[/dim]"
            )
    else:
        console.print("[bold green]All checks passed![/bold green]")


@app.command("mv")
def config_mv(
    destination: Optional[str] = typer.Argument(
        None, help="Destination directory (prompted with path completion if omitted)"
    ),
    move: bool = typer.Option(False, "--move", help="Move files instead of copy"),
    plain: bool = typer.Option(False, "--plain", help="Disable colors"),
) -> None:
    """
    Copy or move configuration to a new directory.

    With no path, prompts interactively with directory autocomplete.
    By default, copies config files. Use --move to move instead.
    Updates the pointer file so the new location is used on next run.
    """
    config = ConfigManager()
    src_dir = config.env_path.parent
    if destination is None or (
        isinstance(destination, str) and not destination.strip()
    ):
        default_dir = (
            str(Path(sys.executable).resolve().parent)
            if is_packaged_build()
            else str(src_dir)
        )
        destination = filepath(
            message="Enter path to save configs (directory):",
            default=default_dir,
            only_directories=True,
            mandatory=False,
        )
        if not destination or not str(destination).strip():
            console.print("[yellow]Cancelled. Config location unchanged.[/yellow]")
            raise typer.Exit(0)
        destination = str(destination).strip()
    dest_dir = Path(destination).expanduser().resolve()

    console.print(f"[dim]Source:[/dim] {src_dir}")
    console.print(f"[dim]Destination:[/dim] {dest_dir}")
    console.print()

    # Check if source and destination are the same
    if src_dir.resolve() == dest_dir:
        console.print(
            "[yellow]![/yellow] Source and destination are the same. Nothing to do."
        )
        raise typer.Exit(code=0)

    # Create destination if needed (with confirmation)
    if not dest_dir.exists():
        if (
            confirm(f"Create destination directory {dest_dir}?", default=True)
            is not True
        ):
            console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit(code=0)
        console.print(f"[dim]Creating directory: {dest_dir}[/dim]")
        dest_dir.mkdir(parents=True, exist_ok=True)

    operation = "Moving" if move else "Copying"
    if (
        confirm(f"Proceed with {operation.lower()} to {dest_dir}?", default=True)
        is not True
    ):
        console.print("[yellow]Cancelled.[/yellow]")
        raise typer.Exit(code=0)

    # Copy/move files
    files_to_transfer = ["config.toml", ".env"]

    for filename in files_to_transfer:
        src_file = src_dir / filename
        dest_file = dest_dir / filename

        if src_file.exists():
            if move:
                shutil.move(str(src_file), str(dest_file))
            else:
                shutil.copy2(str(src_file), str(dest_file))
            console.print(f"[green]>[/green] {operation} {filename}")
        else:
            console.print(f"[yellow]![/yellow] {filename} not found, skipping")

    # Verify destination config.toml is valid
    dest_toml = dest_dir / "config.toml"
    if dest_toml.exists():
        try:
            read_toml(dest_toml)
            console.print("[green]>[/green] config.toml validated")
        except Exception as e:
            console.print(f"[red]x[/red] config.toml validation failed: {e}")
            raise typer.Exit(code=1)

    # Update pointer file (with confirmation)
    if confirm("Update config pointer to new location?", default=True) is not True:
        console.print(
            "[yellow]Pointer not updated. Config relocated but pointer still points to old location.[/yellow]"
        )
    else:
        write_config_pointer(dest_dir)
        console.print("[green]>[/green] Updated config pointer")

    # Summary
    console.print()
    console.print(
        Panel(
            f"[bold green]Configuration relocated![/bold green]\n\n"
            f"New location: {dest_dir}\n"
            f"Pointer file: {get_pointer_file_path()}",
            title="Success",
            border_style="green",
        )
    )


# Keep existing wizard as default when no subcommand
@app.callback(invoke_without_command=True)
def config_callback(
    ctx: typer.Context,
    plain: bool = typer.Option(False, "--plain", help="Disable colors and animations"),
) -> None:
    """
    Manage configuration location and diagnostics.

    Without a subcommand, launches the interactive configuration wizard.

    Subcommands:
      show    - Show current configuration paths and values
      doctor  - Run diagnostics on configuration
      mv      - Copy or move configuration to a new directory
    """
    if ctx.invoked_subcommand is None:
        # No subcommand - run wizard
        config_manager = ConfigManager()

        # Use config.toml product.arcane_terms with env fallback (PRD6 regression prevention)
        arcane_terms_str = config_manager.get("product.arcane_terms") or os.getenv(
            "ARCANE_TERMS", "true"
        )
        arcane_terms = arcane_terms_str.lower() in ("1", "true", "yes")
        arcane_console = ArcaneConsole(plain=plain, arcane_terms=arcane_terms)

        if not config_manager.check_toml_file_exists():
            arcane_console.print_fracture(
                "config", "config.toml not found. Run 'alchemux setup' first."
            )
            raise typer.Exit(code=1)

        from app.core.config_wizard import interactive_config_wizard

        try:
            success = interactive_config_wizard(config_manager)
            if not success:
                raise typer.Exit(code=1)
        except KeyboardInterrupt:
            console.print("\n[yellow]Configuration cancelled.[/yellow]")
            raise typer.Exit(code=1)


# Legacy function for backward compatibility (if called directly)
def config_command(
    ctx: typer.Context = None,
    plain: bool = False,
) -> None:
    """
    Legacy wrapper for config command.

    DEPRECATED: Use the config Typer app directly.
    """
    # Just run the wizard
    config_manager = ConfigManager()

    # Use config.toml product.arcane_terms with env fallback (PRD6 regression prevention)
    arcane_terms_str = config_manager.get("product.arcane_terms") or os.getenv(
        "ARCANE_TERMS", "true"
    )
    arcane_terms = arcane_terms_str.lower() in ("1", "true", "yes")
    arcane_console = ArcaneConsole(plain=plain, arcane_terms=arcane_terms)

    if not config_manager.check_toml_file_exists():
        arcane_console.print_fracture(
            "config", "config.toml not found. Run 'alchemux setup' first."
        )
        raise typer.Exit(code=1)

    from app.core.config_wizard import interactive_config_wizard

    try:
        success = interactive_config_wizard(config_manager)
        if not success:
            raise typer.Exit(code=1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Configuration cancelled.[/yellow]")
        raise typer.Exit(code=1)
