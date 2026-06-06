"""
Normalize argv so root flags are accepted before/after URL.
"""

from pathlib import Path

# Root-level CLI command names that should not be reordered.
ROOT_COMMANDS = {
    "setup",
    "config",
    "doctor",
    "update",
    "batch",
    "distill",
    "invoke",
    "mux",
    "seal",
    "inspect",
}

# Boolean root flags accepted by the root callback.
ROOT_BOOLEAN_FLAGS = {
    "--version",
    "-v",
    "--help",
    "-h",
    "--clipboard",
    "-p",
    "--debug",
    "--accept-eula",
    "--flac",
    "--video",
    "--local",
    "--s3",
    "--gcp",
    "--verbose",
    "--plain",
    "--no-config",
}

# Root flags that consume a following value token.
ROOT_VALUE_FLAGS = {
    "--download-dir",
}


def _is_known_root_flag(token: str) -> bool:
    if token in ROOT_BOOLEAN_FLAGS or token in ROOT_VALUE_FLAGS:
        return True
    return any(token.startswith(f"{flag}=") for flag in ROOT_VALUE_FLAGS)


def _split_double_dash(tokens: list[str]) -> tuple[list[str], list[str]]:
    if "--" not in tokens:
        return tokens, []
    delimiter_idx = tokens.index("--")
    return tokens[:delimiter_idx], tokens[delimiter_idx:]


def _first_non_flag_token(tokens: list[str]) -> str | None:
    idx = 0
    while idx < len(tokens):
        token = tokens[idx]
        if _is_known_root_flag(token):
            if token in ROOT_VALUE_FLAGS and "=" not in token and idx + 1 < len(tokens):
                idx += 2
                continue
            idx += 1
            continue
        if token.startswith("-"):
            idx += 1
            continue
        return token
    return None


def normalize_argv(argv: list[str]) -> list[str]:
    """
    Normalize root invocation argv so flags can appear after URL.

    Examples:
      - alchemux URL --no-config --download-dir .
      - alchemux --no-config --download-dir . URL
    """
    if len(argv) <= 1:
        return argv

    program = argv[0]
    tokens = argv[1:]
    prefix_tokens, suffix_tokens = _split_double_dash(tokens)
    if not prefix_tokens:
        return argv

    # Do not reorder command invocations.
    first_non_flag = _first_non_flag_token(prefix_tokens)
    if first_non_flag in ROOT_COMMANDS:
        return argv

    reordered_flags: list[str] = []
    reordered_positionals: list[str] = []
    idx = 0
    while idx < len(prefix_tokens):
        token = prefix_tokens[idx]
        if _is_known_root_flag(token):
            reordered_flags.append(token)
            if (
                token in ROOT_VALUE_FLAGS
                and "=" not in token
                and idx + 1 < len(prefix_tokens)
            ):
                reordered_flags.append(prefix_tokens[idx + 1])
                idx += 2
                continue
        else:
            reordered_positionals.append(token)
        idx += 1

    # Keep executable name unchanged for help branding (`alchemux` / `amx`).
    if Path(program).name:
        return [program, *reordered_flags, *reordered_positionals, *suffix_tokens]
    return argv
