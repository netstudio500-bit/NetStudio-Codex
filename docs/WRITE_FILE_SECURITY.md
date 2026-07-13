# write_file security controls

`write_file` is an application-level workspace write control, not an operating-system sandbox.

WRITE is deny-by-default and independent from READ. The CLI grants WRITE only through `--allow-write`; the registry view remains the capability boundary.

Targets and their existing parents are canonically resolved and must remain inside the authorized workspace. External traversal and absolute external paths are rejected. Symlink targets are not writable. `.netstudio` is a reserved internal area: model-facing read, list, search, and write tools reject or omit it.

Creation and overwrite are separate intentions. A missing file requires `create=true`; an existing file requires `overwrite=true`. Parent directory trees are never created implicitly.

Content is encoded as strict UTF-8 and bounded by `DEFAULT_MAX_WRITE_SIZE_BYTES = 1 MiB` using encoded byte length. Content is never truncated.

Before overwrite, exact prior bytes are copied to a uniquely identified checkpoint under `.netstudio/checkpoints` with relative original-path metadata. Creation does not invent a checkpoint. Automatic restore is not implemented.

Writes use a temporary file in the target directory, flush and `fsync`, then `os.replace`. The temporary name is host-generated and cleanup is attempted after failure. A replace failure leaves the original target intact.

Successful writes return relative paths, operation, encoded bytes written, checkpoint evidence, and a unified textual diff. Diff output is bounded by `DEFAULT_MAX_DIFF_CHARS = 64 KiB`; truncation is explicit and does not revert a successful write.
