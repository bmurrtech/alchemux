"""
Thin wrapper around InquirerPy with TTY detection and Rich fallback.

When stdin/stdout are not a TTY (e.g. CI, pipes) or InquirerPy is unavailable,
falls back to Rich Prompt/Confirm so wizards still behave or use safe defaults.
Centralizes KeyboardInterrupt handling for consistent cancel behavior.
"""
import sys
from typing import Any, Callable, List, Optional, Sequence, Union

# TTY check: prefer InquirerPy only when interactive
def _is_interactive() -> bool:
    return hasattr(sys.stdin, "isatty") and sys.stdin.isatty() and hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def _inquirer_available() -> bool:
    try:
        from InquirerPy import inquirer  # noqa: F401
        return True
    except Exception:
        return False


def _use_inquirer() -> bool:
    return _is_interactive() and _inquirer_available()


def confirm(
    message: str,
    default: bool = False,
) -> Optional[bool]:
    """
    Yes/no prompt. Returns True/False, or None on cancel/interrupt when using fallback.
    """
    if _use_inquirer():
        try:
            from InquirerPy import inquirer
            return inquirer.confirm(message=message, default=default).execute()
        except KeyboardInterrupt:
            return None
        except EOFError:
            return default if default is not None else None
    # Rich fallback
    try:
        from rich.prompt import Confirm
        return Confirm.ask(message, default=default)
    except (KeyboardInterrupt, EOFError):
        return default


def select(
    message: str,
    choices: Sequence[Union[str, Any]],
    default: Any = None,
) -> Any:
    """
    Single-select from a list. choices can be strings or (value, name) pairs.
    default should match one of the choice values.
    """
    if _use_inquirer():
        try:
            from InquirerPy import inquirer
            return inquirer.select(message=message, choices=list(choices), default=default).execute()
        except KeyboardInterrupt:
            return default
        except EOFError:
            return default
    # Rich fallback: simple numbered prompt
    from rich.prompt import Prompt
    opts = []
    for i, c in enumerate(choices):
        if isinstance(c, (list, tuple)) and len(c) >= 2:
            opts.append((c[0], str(c[1])))
        else:
            v = c if not isinstance(c, dict) else c.get("value", c.get("name", c))
            opts.append((v, str(v)))
    try:
        for i, (val, label) in enumerate(opts):
            sys.stdout.write(f"  {i + 1}. {label}\n")
        sys.stdout.flush()
        rep = Prompt.ask(f"\n{message}", default="1")
        idx = int(rep) - 1
        if 0 <= idx < len(opts):
            return opts[idx][0]
    except (ValueError, KeyboardInterrupt, EOFError):
        pass
    return default if default is not None and any(o[0] == default for o in opts) else (opts[0][0] if opts else None)


def checkbox(
    message: str,
    choices: Sequence[Union[str, Any]],
    default_selected: Optional[Sequence[Any]] = None,
) -> Optional[List[Any]]:
    """
    Multi-select checklist. Returns list of selected values, or None on cancel.
    default_selected: optional list of values to be pre-selected.
    """
    if _use_inquirer():
        try:
            from InquirerPy import inquirer
            from InquirerPy.base.control import Choice
            out_choices = []
            for c in choices:
                if isinstance(c, (list, tuple)) and len(c) >= 2:
                    val, name = c[0], c[1]
                    enabled = default_selected is not None and val in default_selected
                    out_choices.append(Choice(val, name=name, enabled=enabled))
                elif isinstance(c, dict):
                    val = c.get("value", c.get("name", c))
                    enabled = default_selected is not None and val in default_selected
                    out_choices.append(Choice(val, name=c.get("name", str(val)), enabled=enabled))
                else:
                    enabled = default_selected is not None and c in default_selected
                    out_choices.append(Choice(c, enabled=enabled))
            return inquirer.checkbox(
                message=message,
                choices=out_choices,
            ).execute()
        except KeyboardInterrupt:
            return None
        except EOFError:
            return list(default_selected) if default_selected else []
    # Rich fallback: return default or empty
    return list(default_selected) if default_selected else []


def text(
    message: str,
    default: str = "",
    validate: Optional[Callable[[str], bool]] = None,
    invalid_message: str = "Invalid input",
) -> Optional[str]:
    """
    Free-text input. validate(result) should return True if valid.
    """
    if _use_inquirer():
        try:
            from InquirerPy import inquirer
            kwargs = {"message": message, "default": default}
            if validate is not None:
                kwargs["validate"] = validate
                kwargs["invalid_message"] = invalid_message
            return inquirer.text(**kwargs).execute()
        except KeyboardInterrupt:
            return None
        except EOFError:
            return default or ""
    try:
        from rich.prompt import Prompt
        while True:
            ans = Prompt.ask(message, default=default or "")
            if validate is None or validate(ans):
                return ans
            sys.stderr.write(f"{invalid_message}\n")
            sys.stderr.flush()
    except (KeyboardInterrupt, EOFError):
        return default or ""


def secret(
    message: str,
    default: str = "",
) -> Optional[str]:
    """Masked input (e.g. passwords). Falls back to getpass when not TTY."""
    if _use_inquirer():
        try:
            from InquirerPy import inquirer
            return inquirer.secret(message=message, default=default).execute()
        except KeyboardInterrupt:
            return None
        except EOFError:
            return default or ""
    try:
        import getpass
        return getpass.getpass(f"{message}: ").strip() or default or ""
    except (KeyboardInterrupt, EOFError):
        return default or ""


def filepath(
    message: str,
    default: str = "",
    validate: Optional[Callable[[str], bool]] = None,
    invalid_message: str = "Invalid path",
    only_directories: bool = False,
    only_files: bool = False,
    mandatory: bool = True,
) -> Optional[str]:
    """
    Path input with tab/autocomplete when InquirerPy is used (TTY).
    Uses InquirerPy PathValidator when validate is None so only_directories/only_files
    enable proper path completion per PRD6. validate(path) can override.
    """
    if _use_inquirer():
        try:
            from InquirerPy import inquirer
            kwargs = {
                "message": message,
                "default": default,
                "only_directories": only_directories,
                "only_files": only_files,
                "mandatory": mandatory,
            }
            if validate is not None:
                kwargs["validate"] = validate
                kwargs["invalid_message"] = invalid_message
            else:
                # Use PathValidator so tab/autocomplete works (PRD6)
                try:
                    from InquirerPy.validator import PathValidator
                    if only_directories:
                        kwargs["validate"] = PathValidator(is_dir=True, message=invalid_message)
                    elif only_files:
                        kwargs["validate"] = PathValidator(is_file=True, message=invalid_message)
                except Exception:
                    pass
            return inquirer.filepath(**kwargs).execute()
        except KeyboardInterrupt:
            return None
        except EOFError:
            return default or ""
    # Rich fallback: plain text with optional validate
    return text(message=message, default=default, validate=validate, invalid_message=invalid_message)
