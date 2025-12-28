# Alchemux Legend

**Arcane Terminology Reference**

This document explains the arcane terminology used in Alchemux's output.  
For the complete visual legend with sigils and formatting.

---

## Stage Terminology

Alchemux uses arcane-themed terminology throughout its interface.  
Each stage has both an arcane name and a technical equivalent:

| Arcane Term | Technical Term | Description |
|------------|---------------|-------------|
| **scribe** | validate | URL validation and format checking |
| **scry** | detect source | Source platform detection (YouTube, Facebook, etc.) |
| **profile** | extract metadata | Metadata extraction (title, duration, etc.) |
| **vessel** | prepare file | File preparation and path setup |
| **distill** | download | Media download and conversion |
| **attune** | locate | Output file resolution and final path determination |
| **mux** | embed metadata | Metadata embedding into media files |
| **evaporate** | upload | Cloud storage upload (if enabled) |
| **purge** | cleanup | Temporary file cleanup |
| **seal** | save | Final completion and persistence |

---

## Stage Sigils

Each stage has a unique visual sigil (symbol) for easy identification:

- ⊢ — scribe (validate)
- ⟁ — scry (detect source)
- ⌬ — profile (extract metadata)
- ⧈ — vessel (prepare file)
- ⚗ — distill (download)
- ◇ — attune (locate)
- ⌘ — mux (embed metadata)
- ⇮ — evaporate (upload)
- ⌿ — purge (cleanup)
- ■ — seal (save)

---

## Message Mappings

When using technical mode (`ARCANE_TERMS=false`), messages are translated:

| Arcane Message | Technical Message |
|----------------|-------------------|
| "scribing input" | "validating input" |
| "source scryed" | "source detected" |
| "inscribing metadata" | "embedding metadata" |
| "inscription complete" | "metadata embedded" |
| "charging vessel" | "preparing file" |
| "distilling stream" | "downloading" |
| "distillation complete" | "download complete" |
| "attunement complete" | "file located" |
| "evaporating artifact" | "uploading" |
| "purging residues" | "cleaning up" |
| "chamber clear" | "cleanup complete" |
| "bottled" | "saved" |

---

## Phase Headers

Major phases use bracketed headers with consistent tense:

- ⟦⟁ SCRYING⟧ → ⟦⟁ DETECTING⟧  
- ⟦⚗ DISTILLING⟧ → ⟦⚗ DOWNLOADING⟧  
- ⟦◇ ATTUNING⟧ → ⟦◇ LOCATING⟧  
- ⟦⌘ MUXING⟧ → ⟦⌘ EMBEDDING⟧  
- ╔═ SEAL COMPLETE ═╗ → ╔═ SAVE COMPLETE ═╗  

(when `ARCANE_TERMS=false`)

---

## Progress Indicators

Progress bars use pulse marks (◐ ◓ ◑ ◒) that rotate during active operations.

Arcane mode:
+++
>> distill | [=====>........] 45% | charging vessel ◐
+++

Technical mode:
+++
>> download | [=====>........] 45% | preparing file ◐
+++

---

## Glyph Dividers

Soft separators appear between major phases:

+++
~∿~∿~∿~∿~∿~∿~
+++

They help visually reset attention between rites.

---

## Completion States

Successful completion uses an elevated seal box.

Arcane mode:
+++
╔═ SEAL COMPLETE ═╗
[■] bottled → /path/to/file.mp3
╚════════════════╝
+++

Technical mode:
+++
╔═ SAVE COMPLETE ═╗
[■] saved → /path/to/file.mp3
╚════════════════╝
+++

---

## Error Format

Errors use the “fracture detected” pattern:

+++
⟬×⟭ distill | fracture detected
    └─ cause: network instability
+++

---

## Configuration

Control terminology via the `ARCANE_TERMS` environment variable:

- `ARCANE_TERMS=true` (default) — Use arcane terminology
- `ARCANE_TERMS=false` — Use technical terminology

Set via `.env` or directly in the environment.
