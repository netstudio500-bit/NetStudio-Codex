# search_text security controls

`search_text` is an application-level workspace search control. It is not an operating-system sandbox.

The tool declares only the `READ` capability and remains hidden by the deny-by-default policy until READ is explicitly granted. The CLI grants the capability through `--allow-read`; it does not authorize tool names individually.

The configured workspace root is resolved canonically. Every requested search root is resolved against that root and must remain contained by real path semantics. Traversal and absolute paths that resolve outside the workspace are rejected.

Directory traversal is explicit and deterministic. Directory symlinks are not followed. File symlinks are not searched. A symlink root that resolves outside the workspace is rejected, so external content is not searched through symlink indirection.

Search is literal, not regular-expression based. Case-insensitive search uses Unicode `casefold()`. Input files are decoded with strict UTF-8. Invalid UTF-8 files are skipped and counted in `skipped_invalid_utf8`; there is no system-encoding or byte-search fallback.

Search is bounded by `DEFAULT_MAX_FILES = 1000`, `DEFAULT_MAX_RESULTS = 200`, and `DEFAULT_MAX_SEARCH_FILE_SIZE_BYTES = 1 MiB`. Oversized files are skipped before text loading and counted in `skipped_too_large`. File or result limit exhaustion sets `truncated` explicitly.

Matches contain workspace-relative POSIX paths only and 1-based line and column positions. Enumeration order is deterministic by normalized workspace-relative path; matches are emitted in path, line, then column order.

An isolated per-file `OSError` during stat or read skips that file so one inaccessible file does not fail the whole search. A root resolution or non-recoverable enumeration error fails the operation with `search_failed`.
