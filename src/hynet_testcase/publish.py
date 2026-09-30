# SPDX-License-Identifier: MIT
"""Publication of the distribution branch from the development branch.

The distribution branch (`main`) is what users see first: the test case, its user
documentation and the presentation notebook with its Binder configuration. It is
generated, never edited: `hynet-testcase publish` rewrites its whole content from the
current commit of the development branch (`dev`), which keeps the source models, the
inputs and the build code.
"""

import logging
import posixpath
import re
import shutil
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from string import Template

from hynet_testcase.errors import PublishError
from hynet_testcase.paths import RepoPaths

logger = logging.getLogger(__name__)

DEVELOPMENT_BRANCH = "dev"
"""Only branch the distribution branch is published from."""

PUBLISHED_PATHS: tuple[str, ...] = (
    ".gitattributes",
    "CHANGELOG.md",
    "CITATION.cff",
    "LICENSE",
    "LICENSE-DATA",
    "binder/requirements.txt",
    "binder/runtime.txt",
    "docs/assets",
    "docs/data-dictionary.md",
    "docs/scenarios_presentation.pptx",
    "docs/test-case.md",
    "notebooks/presentation.ipynb",
    "testcase",
)
"""Tracked files and directories copied to the distribution branch."""

TEMPLATES_DIR = "publish"
"""Files of the distribution branch only, with `${repository}`, `${commit}` and
`${short_commit}` placeholders, relative to the repository root."""

EXECUTABLES: tuple[str, ...] = ("binder/postBuild",)
"""Published files that git must record as executable."""

# Inline Markdown links and images, `](target)` or `](target#anchor)`.
_LINK = re.compile(r"\]\((?P<target>[^)\s#]*)(?P<anchor>#[^)\s]*)?\)")
_URL_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)


@dataclass(frozen=True)
class Publication:
    """A development commit and the files published from it.

    Attributes:
        repository: URL of the GitHub repository, without a trailing slash.
        commit: Full hash of the development commit.
        tracked: Files tracked at that commit, as repository-relative POSIX paths.
        published: Files of the distribution branch, as repository-relative POSIX paths.
    """

    repository: str
    commit: str
    tracked: frozenset[str]
    published: frozenset[str]

    @property
    def short_commit(self) -> str:
        """Abbreviated hash of the development commit."""
        return self.commit[:7]

    def is_published(self, path: str) -> bool:
        """Whether a file, or a directory holding one, is on the distribution branch."""
        return _covers(self.published, path)

    def is_tracked(self, path: str) -> bool:
        """Whether a file, or a directory holding one, is tracked on the development branch."""
        return _covers(self.tracked, path)

    def source_url(self, path: str) -> str:
        """URL of a tracked file or directory at the development commit."""
        kind = "blob" if path in self.tracked else "tree"
        return f"{self.repository}/{kind}/{self.commit}/{path}"


def _covers(files: frozenset[str], path: str) -> bool:
    return path in files or any(file.startswith(f"{path}/") for file in files)


def rewrite_links(text: str, document: str, publication: Publication) -> str:
    """Points relative Markdown links to unpublished files at the development commit.

    Links to published files stay relative, so they keep working in a download of the
    distribution branch.

    Args:
        text: Markdown content.
        document: Repository-relative path of the Markdown file.
        publication: The publication the file belongs to.

    Returns:
        The content with every relative link resolving on the distribution branch.

    Raises:
        PublishError: If a relative link resolves to no tracked file or directory.
    """
    def replace(match: re.Match[str]) -> str:
        target = match["target"]
        if not target or target.startswith("/") or _URL_SCHEME.match(target):
            return match[0]
        path = posixpath.normpath(posixpath.join(posixpath.dirname(document), target))
        if publication.is_published(path):
            return match[0]
        if path.startswith("..") or not publication.is_tracked(path):
            raise PublishError(f"{document}: link to {target} resolves to no tracked file")
        return f"]({publication.source_url(path)}{match['anchor'] or ''})"

    return _LINK.sub(replace, text)


def _git(directory: Path, *args: str) -> str:
    """Runs a git command and returns its standard output.

    Raises:
        PublishError: If git is missing or the command fails.
    """
    try:
        result = subprocess.run(["git", "-C", str(directory), *args], check=True,
                                capture_output=True, text=True, encoding="utf-8")
    except FileNotFoundError as exc:
        raise PublishError("git is not available") from exc
    except subprocess.CalledProcessError as exc:
        raise PublishError(f"git {' '.join(args)} failed: {exc.stderr.strip()}") from exc
    return result.stdout


def _ls_files(root: Path, *paths: str) -> frozenset[str]:
    return frozenset(filter(None, _git(root, "ls-files", "-z", "--", *paths).split("\0")))


def _check_source(root: Path) -> str:
    """Checks that the development branch is clean and returns its commit.

    Raises:
        PublishError: If the working tree is not a clean checkout of the development
            branch.
    """
    branch = _git(root, "branch", "--show-current").strip()
    if branch != DEVELOPMENT_BRANCH:
        raise PublishError(f"publish from the {DEVELOPMENT_BRANCH} branch, not from "
                           f"{branch or 'a detached HEAD'}")
    if _git(root, "status", "--porcelain").strip():
        raise PublishError("the working tree has uncommitted changes; the distribution "
                           "branch must come from a commit")
    return _git(root, "rev-parse", "HEAD").strip()


def _check_target(target: Path, root: Path) -> None:
    """Checks that the target is a separate git worktree, which publishing empties.

    Raises:
        PublishError: If the target overlaps the repository or is not a git worktree.
    """
    if target.is_relative_to(root) or root.is_relative_to(target):
        raise PublishError(f"{target} overlaps the repository; use a separate worktree")
    if not (target / ".git").exists():
        raise PublishError(f"{target} is not a git worktree; create it with "
                           f"`git worktree add --orphan -b main {target}`")


def _repository_url(root: Path) -> str:
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    try:
        return str(project["project"]["urls"]["Repository"]).rstrip("/")
    except KeyError as exc:
        raise PublishError("pyproject.toml has no [project.urls] Repository") from exc


def _render(template: Path, publication: Publication) -> str:
    try:
        return Template(template.read_text(encoding="utf-8")).substitute(
            repository=publication.repository, commit=publication.commit,
            short_commit=publication.short_commit)
    except (KeyError, ValueError) as exc:
        raise PublishError(f"{template.name}: invalid placeholder {exc}") from exc


def _clear(target: Path) -> None:
    for child in target.iterdir():
        if child.name == ".git":
            continue
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def publish(paths: RepoPaths, target: Path) -> Publication:
    """Rewrites the content of the distribution branch from the development commit.

    Args:
        paths: Repository on the development branch.
        target: Worktree of the distribution branch. Everything in it but `.git` is
            replaced.

    Returns:
        The publication written to the target.

    Raises:
        PublishError: If the repository or the target is not in a state to publish, a
            published path or template is missing, or a link cannot be resolved.
    """
    root = paths.root.resolve()
    target = target.resolve()
    commit = _check_source(root)
    _check_target(target, root)

    tracked = _ls_files(root)
    copies = _ls_files(root, *PUBLISHED_PATHS)
    for path in PUBLISHED_PATHS:
        if not _covers(copies, path):
            raise PublishError(f"published path {path} is not tracked")
    templates = {path.removeprefix(f"{TEMPLATES_DIR}/"): path
                 for path in tracked if path.startswith(f"{TEMPLATES_DIR}/")}
    if not templates:
        raise PublishError(f"no template in {TEMPLATES_DIR}/")
    if clashes := copies & templates.keys():
        raise PublishError(f"templates overwrite published files: {sorted(clashes)}")
    for path in EXECUTABLES:
        if path not in templates.keys() | copies:
            raise PublishError(f"executable {path} is not published")

    publication = Publication(repository=_repository_url(root), commit=commit,
                              tracked=tracked, published=copies | templates.keys())
    _clear(target)
    for path in sorted(copies):
        destination = target / path
        if path.endswith(".md"):
            text = (root / path).read_text(encoding="utf-8")
            _write_text(destination, rewrite_links(text, path, publication))
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / path, destination)
    for path, template in sorted(templates.items()):
        text = _render(root / template, publication)
        if path.endswith(".md"):
            text = rewrite_links(text, path, publication)
        _write_text(target / path, text)

    logger.info("published %d files from %s@%s to %s", len(publication.published),
                DEVELOPMENT_BRANCH, publication.short_commit, target)
    if not _git(root, "branch", "--remotes", "--contains", commit).strip():
        logger.warning("%s@%s is not pushed: push it before the distribution branch, whose "
                       "Binder installs the package from it", DEVELOPMENT_BRANCH,
                       publication.short_commit)
    # Windows checkouts do not record the executable bit, so it is set in the index.
    logger.info("next, in %s: git add --all && git update-index --chmod=+x %s", target,
                " ".join(EXECUTABLES))
    return publication
