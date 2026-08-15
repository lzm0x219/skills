"""Atomic output helpers with an explicit no-clobber contract."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile


class OutputExistsError(FileExistsError):
    """Raised when a no-clobber commit loses a destination race."""


def commit_staged_file(staged_path: Path, destination: Path, *, overwrite: bool) -> None:
    """Publish a completed same-filesystem file atomically."""
    if overwrite:
        os.replace(staged_path, destination)
        return
    try:
        os.link(staged_path, destination, follow_symlinks=False)
    except FileExistsError as error:
        raise OutputExistsError(f"output file already exists: {destination}") from error
    staged_path.unlink()


def _file_identity(path: Path) -> tuple[int, int]:
    state = path.stat(follow_symlinks=False)
    return state.st_dev, state.st_ino


def commit_staged_files(
    staged_files: list[tuple[Path, Path]],
    *,
    overwrite: bool,
) -> None:
    """Publish a same-directory batch and roll back a failed commit."""
    if not staged_files:
        return
    destination_parents = {destination.parent.resolve() for _, destination in staged_files}
    if len(destination_parents) != 1:
        raise ValueError("atomic batches must share one destination directory")
    destination_parent = next(iter(destination_parents))
    published: list[tuple[Path, tuple[int, int]]] = []
    backups: dict[Path, Path] = {}
    with tempfile.TemporaryDirectory(
        prefix=".atomic-output-backup-",
        dir=destination_parent,
    ) as backup_directory:
        backup_root = Path(backup_directory)
        if overwrite:
            for index, (_, destination) in enumerate(staged_files):
                if destination.exists():
                    backup = backup_root / str(index)
                    os.link(destination, backup, follow_symlinks=False)
                    backups[destination] = backup
        try:
            for staged_path, destination in staged_files:
                commit_staged_file(staged_path, destination, overwrite=overwrite)
                published.append((destination, _file_identity(destination)))
        except BaseException:
            for destination, identity in reversed(published):
                backup = backups.get(destination)
                if backup is not None:
                    os.replace(backup, destination)
                    continue
                try:
                    if _file_identity(destination) == identity:
                        destination.unlink()
                except FileNotFoundError:
                    pass
            raise
