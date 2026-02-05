"""
Doctor command - Run configuration diagnostics and guided repairs.

Standalone command for diagnosing and fixing configuration issues.
"""
import os
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from app.cli.output import ArcaneConsole
from app.cli.prompts import confirm, checkbox
from app.core.config_manager import ConfigManager, get_default_output_dir
from app.core.toml_config import read_toml

console = Console()


def _run_repair_menu(config: ConfigManager, repair_options: list, issues: list) -> None:
    """
    Run interactive repair menu.
    
    Args:
        config: ConfigManager instance
        repair_options: List of (repair_id, description) tuples
        issues: List of (issue_id, message) tuples
    """
    if not repair_options:
        console.print("[dim]No repairs available.[/dim]")
        return
    
    console.print()
    console.print("[bold]Available Repairs:[/bold]")
    
    # Present repair options as checkbox list
    selected_repairs = checkbox(
        message="Select repairs to apply:",
        choices=[(opt_id, desc) for opt_id, desc in repair_options],
        default=[opt_id for opt_id, _ in repair_options],  # Select all by default
    )
    
    if not selected_repairs:
        console.print("[yellow]No repairs selected.[/yellow]")
        return
    
    # Create backup before repairs
    console.print()
    console.print("[dim]Creating backup before repairs...[/dim]")
    backup_path = config.create_backup()
    if backup_path:
        console.print(f"[green]✓[/green] Backup created: {backup_path}")
    else:
        console.print("[yellow]![/yellow]  Could not create backup, proceeding anyway...")
    
    # Apply selected repairs
    repair_success = True
    for repair_id in selected_repairs:
        try:
            if repair_id == "create_config_dir":
                config_dir = config.env_path.parent
                config_dir.mkdir(parents=True, exist_ok=True)
                console.print(f"[green]✓[/green] Created config directory: {config_dir}")
            
            elif repair_id == "recreate_toml":
                config._create_toml_from_example()
                console.print(f"[green]✓[/green] Recreated config.toml from example")
            
            elif repair_id == "restore_toml":
                if config.has_backup():
                    if config.restore_from_backup():
                        console.print(f"[green]✓[/green] Restored config.toml from backup")
                    else:
                        console.print(f"[red]✗[/red] Restore from backup failed")
                        repair_success = False
                else:
                    console.print(f"[yellow]![/yellow]  No backup available for restore")
            
            elif repair_id == "fix_output_path":
                default_path = str(get_default_output_dir())
                config.set("paths.output_dir", default_path)
                console.print(f"[green]✓[/green] Set output directory to default: {default_path}")
            
            elif repair_id == "fix_pointer":
                current_config_dir = config.env_path.parent
                pointer_path = get_config_location()
                if pointer_path.parent.exists():
                    write_config_pointer(str(current_config_dir))
                    console.print(f"[green]✓[/green] Updated pointer file")
                else:
                    console.print(f"[yellow]![/yellow]  Could not update pointer file")
            
            else:
                console.print(f"[yellow]![/yellow]  Unknown repair: {repair_id}")
        
        except Exception as e:
            console.print(f"[red]✗[/red] Repair '{repair_id}' failed: {e}")
            repair_success = False
    
    # If repairs failed, offer restore
    if not repair_success and backup_path:
        console.print()
        restore = confirm("Some repairs failed. Restore from backup?", default=True)
        if restore:
            if config.restore_from_backup():
                console.print("[green]✓[/green] Configuration restored from backup")
            else:
                console.print("[red]✗[/red] Restore failed")


def doctor() -> None:
    """
    Run diagnostics on configuration and offer guided repairs.
    
    Checks for common issues like missing files, invalid TOML, and missing credentials.
    If issues are found, offers interactive repair options with automatic backup.
    """
    config = ConfigManager()
    issues = []
    repair_options = []
    
    # Initialize console
    arcane_terms_str = config.get("product.arcane_terms") or os.getenv("ARCANE_TERMS", "true")
    arcane_terms = arcane_terms_str.lower() in ("1", "true", "yes")
    arcane_console = ArcaneConsole(plain=plain, arcane_terms=arcane_terms)
    
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
    toml_valid = False
    toml_corrupted = False
    if config.toml_path.exists():
        try:
            toml_data = read_toml(config.toml_path)
            if toml_data:
                console.print(f"[green]>[/green] config.toml exists and valid")
                toml_valid = True
            else:
                console.print(f"[yellow]![/yellow] config.toml is empty")
                issues.append(("toml_empty", "config.toml is empty"))
                repair_options.append(("recreate_toml", "Recreate config.toml from example"))
        except Exception as e:
            console.print(f"[red]x[/red] config.toml parse error: {e}")
            issues.append(("toml_invalid", f"config.toml invalid: {e}"))
            repair_options.append(("recreate_toml", "Recreate config.toml from example"))
            repair_options.append(("restore_toml", "Restore config.toml from backup"))
            toml_corrupted = True
    else:
        console.print(f"[red]x[/red] config.toml missing: {config.toml_path}")
        issues.append(("toml_missing", "config.toml does not exist"))
        repair_options.append(("recreate_toml", "Create config.toml from example"))
    
    # Check .env
    if config.env_path.exists():
        console.print(f"[green]>[/green] .env exists")
    else:
        console.print(f"[yellow]![/yellow] .env missing (may be created on first use)")
    
    # Check output directory
    output_dir = config.get("paths.output_dir", str(get_default_output_dir()))
    output_path = Path(output_dir)
    output_writable = False
    if output_path.exists():
        if os.access(output_path, os.W_OK):
            console.print(f"[green]>[/green] Output directory writable: {output_dir}")
            output_writable = True
        else:
            console.print(f"[red]x[/red] Output directory not writable: {output_dir}")
            issues.append(("output_not_writable", f"Output directory not writable: {output_dir}"))
            repair_options.append(("fix_output_path", "Set output directory to default"))
    else:
        try:
            parent = output_path.parent
            if parent.exists() and os.access(parent, os.W_OK):
                console.print(f"[yellow]![/yellow] Output directory does not exist (will be created): {output_dir}")
            else:
                console.print(f"[red]x[/red] Output directory parent not writable: {output_dir}")
                issues.append(("output_parent_not_writable", f"Output directory parent not writable: {output_dir}"))
                repair_options.append(("fix_output_path", "Set output directory to default"))
        except Exception:
            console.print(f"[red]x[/red] Invalid output directory path: {output_dir}")
            issues.append(("output_invalid", f"Invalid output directory path: {output_dir}"))
            repair_options.append(("fix_output_path", "Set output directory to default"))
    
    # Check pointer file
    from app.core.config_manager import get_pointer_file_path
    pointer_file = get_pointer_file_path()
    if pointer_file.exists():
        pointer_target = pointer_file.read_text().strip()
        if Path(pointer_target).exists():
            console.print(f"[green]>[/green] Pointer file valid: {pointer_target}")
        else:
            console.print(f"[yellow]![/yellow] Pointer file target missing: {pointer_target}")
            issues.append(("pointer_invalid", f"Pointer file points to non-existent directory: {pointer_target}"))
            repair_options.append(("fix_pointer", "Update pointer to current config directory"))
    else:
        console.print(f"[dim]-[/dim] No pointer file (using default config location)")
    
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
            console.print("[dim]No automatic repairs available. Please fix issues manually.[/dim]")
    else:
        console.print("[bold green]All checks passed![/bold green]")
    
    console.print()  # Extra spacing
