#!/usr/bin/env python3
"""Build and validate the skills-only ZIP for the OpenAI plugin directory.

The OpenAI submission portal (platform.openai.com/plugins) takes a ZIP upload on
its Skills tab. There is no CLI packer, and the portal's validation rules are
documented only as error codes, so this script does the packaging and runs the
same checks locally, before an upload burns a review cycle.

What it does:

1. Exports a clean tree from git (``git archive``), so only committed files are
   packaged and nothing from a dirty checkout leaks in.
2. Strips paths that must not ship to directory users (see ``EXCLUDE``).
3. Validates the staged tree against the documented portal rules
   (https://developers.openai.com/plugins/deploy/submission-errors). Errors exit
   non-zero; warnings print and let the build continue.
4. Writes a deterministic ZIP: sorted entries, fixed timestamps. The same ref
   always produces the same bytes and the same SHA-256.

Usage:

    internal/release/build_openai_bundle.py                    # HEAD
    internal/release/build_openai_bundle.py --ref v1.1.0       # a release tag
    internal/release/build_openai_bundle.py --check-only       # validate, no ZIP
    internal/release/build_openai_bundle.py --out dist --keep-tree

Requires only Python 3.11+ and git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unicodedata
import zipfile
from pathlib import Path

# Paths removed from the submitted bundle, relative to the plugin root.
# Anything matched here is deleted from the staged tree before validation.
EXCLUDE_DIRS = [
    "internal",          # skill-auditor tooling; sources.yaml names private Scandit repos
    "evals",             # the eval harness after #85 moved it out of skills/; see EXCLUDE_SKILL_DIRS
    ".claude-plugin",    # other hosts' manifests: noise in a reviewed bundle
    ".cursor-plugin",
    ".github",
    ".agents",
]
EXCLUDE_FILES = [
    "skills.sh.json",    # third-party marketplace page-grouping config
    "README.md",         # repo-oriented, and advertises the other install channels
    ".gitignore",
]
# Removed from every skill: the eval harness ships competitor migration fixtures
# and is not one of OpenAI's documented skill conventions. #85 relocated these to a
# top-level evals/ tree, which is why "evals" is also in EXCLUDE_DIRS. Both entries
# stay so the builder produces the same bundle before and after that move lands.
EXCLUDE_SKILL_DIRS = ["evals"]

MANIFEST = ".codex-plugin/plugin.json"

CATEGORIES = {
    "Productivity", "Creativity", "Developer Tools", "Business & Operations",
    "Data & Analytics", "Communication", "Education & Research", "Security",
    "Finance", "Healthcare", "Travel", "Entertainment", "Other",
}

# Archive limits (submission-errors.md, "ZIP structure and limit errors").
MAX_ENTRIES = 5_000
MAX_ZIP_BYTES = 100 * 1000 * 1000
MAX_MEMBER_BYTES = 100 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 512 * 1024 * 1024
MAX_PATH_SEGMENTS = 20

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
MENTION_RE = re.compile(r"(?:^|\s)@[A-Za-z0-9_-]")
BLOCK_HEADER_RE = re.compile(r"[|>][+-]?\d*")

errors: list[str] = []
warnings: list[str] = []


def error(code: str, msg: str) -> None:
    errors.append(f"{code}: {msg}")


def warn(code: str, msg: str) -> None:
    warnings.append(f"{code}: {msg}")


# --------------------------------------------------------------------------- #
# staging
# --------------------------------------------------------------------------- #

def export_tree(repo: Path, ref: str, dest: Path) -> None:
    """Materialise `ref` into `dest` using git archive (committed files only)."""
    dest.mkdir(parents=True, exist_ok=True)
    archive = subprocess.run(
        ["git", "-C", str(repo), "archive", "--format=tar", ref],
        stdout=subprocess.PIPE, check=True,
    ).stdout
    tar = subprocess.run(["tar", "-x", "-C", str(dest)], input=archive, check=False)
    if tar.returncode != 0:
        sys.exit(f"failed to extract git archive of {ref}")


def strip_tree(root: Path) -> list[str]:
    removed = []
    for rel in EXCLUDE_DIRS:
        p = root / rel
        if p.is_dir():
            shutil.rmtree(p)
            removed.append(f"{rel}/")
    for rel in EXCLUDE_FILES:
        p = root / rel
        if p.exists():
            p.unlink()
            removed.append(rel)
    skills = root / "skills"
    if skills.is_dir():
        for skill in sorted(skills.iterdir()):
            for name in EXCLUDE_SKILL_DIRS:
                p = skill / name
                if p.is_dir():
                    shutil.rmtree(p)
                    removed.append(f"skills/{skill.name}/{name}/")
    for junk in list(root.rglob(".DS_Store")):
        junk.unlink()
        removed.append(str(junk.relative_to(root)))
    return removed


# --------------------------------------------------------------------------- #
# frontmatter
# --------------------------------------------------------------------------- #

def frontmatter(path: Path) -> dict[str, str] | None:
    """Parse SKILL.md YAML frontmatter into a flat dict of scalars.

    Deliberately minimal (no PyYAML dependency): handles quoted scalars, block
    scalars, and plain multi-line values folded onto one line, which is all the
    portal reads from a SKILL.md. Returns None when frontmatter is absent.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        error("skill_manifest_invalid_utf8", f"{path}: not valid UTF-8")
        return {}
    if not text.startswith("---"):
        return None
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        error("skill_frontmatter_unclosed", f"{path}: front matter never closes with ---")
        return {}
    fm: dict[str, str] = {}
    lines = m.group(1).splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if ":" not in line:
            continue
        indent = len(line) - len(line.lstrip())
        key, _, value = line.strip().partition(":")
        value = value.strip()
        if BLOCK_HEADER_RE.fullmatch(value) or value == "":
            block: list[str] = []
            while i < len(lines):
                nxt = lines[i]
                if nxt.strip() and (len(nxt) - len(nxt.lstrip())) <= indent:
                    break
                block.append(nxt.strip())
                i += 1
            fm[key.strip()] = " ".join(b for b in block if b)
        else:
            cont = [value]
            while i < len(lines):
                nxt = lines[i]
                if not nxt.strip() or (len(nxt) - len(nxt.lstrip())) <= indent:
                    break
                cont.append(nxt.strip())
                i += 1
            fm[key.strip()] = " ".join(cont).strip("\"'")
    return fm


# --------------------------------------------------------------------------- #
# manifest checks
# --------------------------------------------------------------------------- #

def one_line(value: str) -> bool:
    return "\n" not in value and "\r" not in value


def check_len(value: str, limit: int, code: str, label: str) -> None:
    if len(value) > limit:
        error(code, f"{label} is {len(value)} characters, limit {limit}")


def srgb_luminance(hex_color: str) -> float:
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast(hex_color: str, other_luminance: float) -> float:
    a, b = srgb_luminance(hex_color), other_luminance
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def png_size(data: bytes) -> tuple[int, int] | None:
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", data[16:24])


def svg_size(text: str) -> tuple[float, float] | None:
    head = text[:4000]
    vb = re.search(r'viewBox\s*=\s*"([^"]+)"', head)
    if vb:
        parts = vb.group(1).replace(",", " ").split()
        if len(parts) == 4:
            try:
                return float(parts[2]), float(parts[3])
            except ValueError:
                return None
    w = re.search(r'\bwidth\s*=\s*"([\d.]+)"', head)
    h = re.search(r'\bheight\s*=\s*"([\d.]+)"', head)
    if w and h:
        return float(w.group(1)), float(h.group(1))
    return None


def check_image(root: Path, field: str, value: str) -> None:
    if not value.startswith("./"):
        error("branding_asset_path_missing_root_prefix", f"interface.{field} must start with ./")
    if ".." in Path(value).parts:
        error("declared_asset_path_unsafe", f"interface.{field} must not traverse with ..")
    path = (root / value.lstrip("./")).resolve()
    if not path.is_file():
        error("declared_asset_file_missing", f"interface.{field} -> {value} does not exist in the bundle")
        return
    ext = path.suffix.lower()
    if ext not in IMAGE_EXTS:
        error("image_file_format_unsupported", f"{value}: {ext} is not png/jpg/jpeg/webp/svg")
        return
    size = path.stat().st_size
    if size > 5 * 1024 * 1024:
        error("image_file_too_large", f"{value} is {size} bytes, limit 5 MiB")
    if ext == ".svg":
        dims = svg_size(path.read_text(encoding="utf-8", errors="replace"))
        if dims is None:
            error("svg_dimensions_missing", f"{value}: no numeric viewBox or width/height")
            return
        w, h = dims
        if w != h:
            error("svg_dimensions_not_square", f"{value} is {w}x{h}")
        if min(w, h) < 48:
            error("svg_dimensions_too_small", f"{value} is {w}x{h}, minimum 48x48")
    elif ext == ".png":
        dims = png_size(path.read_bytes())
        if dims is None:
            error("raster_image_extension_content_mismatch", f"{value} is not a real PNG")
            return
        w, h = dims
        if w != h:
            error("raster_image_not_square", f"{value} is {w}x{h}")
        if min(w, h) < 48:
            error("raster_image_dimensions_too_small", f"{value} is {w}x{h}, minimum 48x48")
        if max(w, h) > 4096:
            error("raster_image_dimensions_too_large", f"{value} is {w}x{h}, maximum 4096x4096")


def check_manifest(root: Path) -> dict:
    path = root / MANIFEST
    if not path.is_file():
        error("plugin_manifest_missing", f"{MANIFEST} not found in the bundle")
        return {}
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        error("plugin_manifest_json_malformed", f"{MANIFEST}: {exc}")
        return {}
    if not isinstance(manifest, dict):
        error("plugin_manifest_root_not_object", f"{MANIFEST} must be a JSON object")
        return {}

    name = manifest.get("name", "")
    if not name:
        error("plugin_name_missing", "name is required")
    else:
        check_len(name, 64, "plugin_name_too_long", "name")
        if not NAME_RE.match(name):
            error("plugin_name_format", f"name {name!r} must be ASCII letters, digits, _ or -")

    version = manifest.get("version", "")
    if not version:
        error("plugin_version_missing", "version is required")
    elif not SEMVER_RE.match(str(version)):
        error("plugin_version_not_semver", f"version {version!r} is not semantic")

    description = manifest.get("description", "")
    if not description:
        error("plugin_description_missing", "description is required")
    else:
        check_len(description, 1024, "plugin_description_too_long", "description")

    author = manifest.get("author") or {}
    author_name = author.get("name", "") if isinstance(author, dict) else ""
    if not author_name:
        error("plugin_developer_missing", "author.name is required")
    else:
        check_len(author_name, 120, "plugin_author_name_too_long", "author.name")
    for field, limit in (("email", 320), ("url", 2048)):
        value = author.get(field) if isinstance(author, dict) else None
        if value:
            check_len(value, limit, f"plugin_author_{field}_too_long", f"author.{field}")
            if field == "url" and not value.startswith("https://"):
                error("plugin_author_url_not_https", "author.url must be HTTPS")
    homepage = manifest.get("homepage")
    if homepage and not homepage.startswith("https://"):
        error("plugin_homepage_format", "homepage must be HTTPS")

    # Skills-only uploads must not carry MCP or app wiring.
    if "mcpServers" in manifest or (root / ".mcp.json").exists():
        error("mcp_configuration_excluded", "skills-only bundle must not include mcpServers or .mcp.json")
    if "apps" in manifest or (root / ".app.json").exists():
        error("app_configuration_excluded", "skills-only bundle must not include apps or .app.json")

    interface = manifest.get("interface")
    if not isinstance(interface, dict):
        error("plugin_interface_wrong_type", "interface must be an object")
        return manifest

    display = interface.get("displayName", "")
    if not display:
        error("plugin_display_name_empty", "interface.displayName is required")
    else:
        # 80 for package validation, 30 for final directory submission.
        check_len(display, 30, "plugin_display_name_too_long", "interface.displayName")
        if not one_line(display):
            error("plugin_display_name_character_unsupported", "interface.displayName must fit on one line")

    short = interface.get("shortDescription", "")
    if not short:
        error("plugin_short_description_missing", "interface.shortDescription is required")
    else:
        # 240 for package validation, 30 for final directory submission.
        check_len(short, 30, "plugin_short_description_too_long", "interface.shortDescription")
        if not one_line(short):
            error("plugin_short_description_character_unsupported", "interface.shortDescription must fit on one line")

    long_desc = interface.get("longDescription", "")
    if not long_desc:
        error("plugin_long_description_empty", "interface.longDescription is required")
    else:
        check_len(long_desc, 4000, "plugin_long_description_too_long", "interface.longDescription")

    developer = interface.get("developerName", "")
    if not developer:
        error("plugin_developer_name_empty", "interface.developerName is required")
    else:
        check_len(developer, 80, "plugin_developer_name_too_long", "interface.developerName")
        if author_name and developer != author_name:
            warn("developer_name_defaulted",
                 f"author.name {author_name!r} != interface.developerName {developer!r}; "
                 "the portal substitutes the verified identity after confirmation")

    category = interface.get("category")
    if category is not None and category not in CATEGORIES:
        error("plugin_category_unknown", f"category {category!r} is not a supported value")

    capabilities = interface.get("capabilities") or []
    if len(capabilities) > 20:
        error("plugin_capabilities_too_many", f"{len(capabilities)} capabilities, limit 20")
    for cap in capabilities:
        if not isinstance(cap, str) or not cap:
            error("plugin_capability_empty", "each capability must be a non-empty string")
        elif len(cap) > 120 or not one_line(cap):
            error("plugin_capability_too_long", f"capability {cap!r} must be one line of 120 characters or fewer")

    prompts = interface.get("defaultPrompt") or []
    if isinstance(prompts, str):
        prompts = [prompts]
    if len(prompts) > 3:
        error("plugin_default_prompt_too_many", f"{len(prompts)} starter prompts, limit 3")
    seen_prompts: set[str] = set()
    for prompt in prompts:
        if not isinstance(prompt, str) or not prompt.strip():
            error("plugin_default_prompt_empty", "each starter prompt must be non-empty")
            continue
        # 512 for package validation, 128 for final directory submission.
        if len(prompt) > 128:
            error("plugin_default_prompt_too_long", f"prompt is {len(prompt)} characters, limit 128: {prompt!r}")
        if not one_line(prompt):
            error("plugin_default_prompt_character_unsupported", f"prompt must fit on one line: {prompt!r}")
        if MENTION_RE.search(prompt):
            error("plugin_default_prompt_mention", f"prompt must not contain an @mention: {prompt!r}")
        key = unicodedata.normalize("NFKC", " ".join(prompt.split())).casefold()
        if key in seen_prompts:
            error("plugin_default_prompt_duplicate", f"duplicate starter prompt: {prompt!r}")
        seen_prompts.add(key)

    if "screenshots" in interface:
        error("screenshot_configuration_excluded",
              "skills-only bundle must not include interface.screenshots (even an empty list); "
              "screenshots require an MCP-backed submission with custom UI")

    for field in ("websiteURL", "privacyPolicyURL", "termsOfServiceURL", "supportURL"):
        value = interface.get(field)
        if value is None:
            continue
        if not value:
            error(f"plugin_{field.lower()}_empty", f"interface.{field} must be non-empty when present")
        elif not value.startswith("https://"):
            error(f"plugin_{field.lower()}_format", f"interface.{field} must be HTTPS")
        elif len(value) > 1024:
            error(f"plugin_{field.lower()}_too_long", f"interface.{field} is {len(value)} characters, limit 1024")

    for field, reference in (("brandColor", 1.0), ("brandColorDark", srgb_luminance("#212121"))):
        value = interface.get(field)
        if not value:
            continue
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
            error("plugin_brand_color_format", f"interface.{field} must be a six-digit hex colour")
            continue
        ratio = contrast(value, reference)
        against = "white" if field == "brandColor" else "#212121"
        if ratio < 2.0:
            error("plugin_brand_color_contrast",
                  f"interface.{field} {value} has {ratio:.2f}:1 contrast against {against}, minimum 2:1")
        elif ratio < 2.3:
            warn("plugin_brand_color_contrast",
                 f"interface.{field} {value} clears 2:1 against {against} by a thin margin ({ratio:.2f}:1)")

    for field in ("logo", "composerIcon"):
        value = interface.get(field)
        if not value:
            error(f"plugin_{'logo' if field == 'logo' else 'composer_icon'}_path_missing",
                  f"interface.{field} is required and must reference a square image")
        else:
            check_image(root, field, value)

    skills_path = manifest.get("skills")
    if skills_path is not None:
        if not isinstance(skills_path, str) or not skills_path:
            error("plugin_skills_path_empty", "skills must be a non-empty path string")
        elif skills_path.strip("./").rstrip("/") != "skills":
            error("plugin_skills_path_unsupported", f"skills must resolve to the root skills/ directory, got {skills_path!r}")
        elif not (root / "skills").is_dir():
            error("plugin_skills_directory_missing", "declared skills/ directory does not exist")

    return manifest


# --------------------------------------------------------------------------- #
# skill checks
# --------------------------------------------------------------------------- #

def check_skills(root: Path, plugin_name: str, plugin_license: str = "") -> int:
    skills = root / "skills"
    if not skills.is_dir():
        error("plugin_runtime_surface_missing", "bundle must contain skills/<skill>/SKILL.md")
        return 0

    count = 0
    seen_names: dict[str, str] = {}
    metadata_skills: list[str] = []
    license_mismatches: list[tuple[str, str]] = []
    for entry in sorted(skills.iterdir()):
        if entry.is_symlink():
            warn("skill_symlink_ignored", f"skills/{entry.name} is a symlink and will not be imported")
            continue
        if entry.is_file():
            warn("skill_file_ignored", f"skills/{entry.name} is a file and will not be imported")
            continue
        if entry.name.startswith("."):
            error("skill_directory_hidden", f"skills/{entry.name} must not start with .")
            continue

        manifest = entry / "SKILL.md"
        if not manifest.is_file():
            nested = list(entry.rglob("SKILL.md"))
            if nested:
                error("skill_manifest_nested",
                      f"skills/{entry.name} has SKILL.md only at {nested[0].relative_to(skills)}; "
                      "each skill directory must be an immediate child of skills/")
            else:
                error("skill_manifest_missing", f"skills/{entry.name} has no SKILL.md")
            continue

        count += 1
        fm = frontmatter(manifest)
        if fm is None:
            error("skill_frontmatter_missing", f"skills/{entry.name}/SKILL.md has no YAML front matter")
            continue

        name = fm.get("name", "")
        if not name:
            error("skill_name_missing", f"skills/{entry.name}/SKILL.md front matter has no name")
        else:
            if name in seen_names:
                error("skill_identity_duplicate",
                      f"skill name {name!r} used by both skills/{seen_names[name]} and skills/{entry.name}")
            seen_names[name] = entry.name
            identity = f"{plugin_name}:{name}"
            if len(identity) > 64:
                error("skill_identity_too_long", f"{identity} is {len(identity)} characters, limit 64")

        desc = fm.get("description", "")
        if not desc:
            error("skill_description_missing", f"skills/{entry.name}/SKILL.md front matter has no description")
        elif len(desc) > 1024:
            error("skill_description_too_long",
                  f"skills/{entry.name} description is {len(desc)} characters, limit 1024")

        # The portal ignores `metadata` in SKILL.md and says so, once per skill. Surfacing it
        # here keeps the upload free of 74 identical warnings nobody can act on at review time.
        if "metadata" in fm:
            metadata_skills.append(entry.name)

        # Not an OpenAI rule. A skill that declares a licence contradicting the plugin manifest
        # is a licence misstatement in a reviewed artifact, and it has now happened twice.
        skill_license = fm.get("license")
        if skill_license and plugin_license and skill_license != plugin_license:
            license_mismatches.append((entry.name, skill_license))

        body = re.sub(r"^---\n.*?\n---", "", manifest.read_text(encoding="utf-8"), flags=re.S).strip()
        if not body:
            error("skill_body_empty", f"skills/{entry.name}/SKILL.md has no instructions after front matter")

    if count == 0:
        error("archive_plugin_files_missing", "bundle must contain at least one valid skills/<skill>/SKILL.md")

    if metadata_skills:
        warn("skill_metadata_ignored",
             f"{len(metadata_skills)} skill(s) carry `metadata` in SKILL.md front matter. The portal ignores it "
             "and warns once per skill; interface settings belong in agents/openai.yaml. Harmless, but every "
             "one of these becomes a warning on upload.")
    for name, value in license_mismatches:
        warn("skill_license_mismatch",
             f"skills/{name} declares license {value!r} but the plugin manifest declares {plugin_license!r}")
    return count


# --------------------------------------------------------------------------- #
# archive checks
# --------------------------------------------------------------------------- #

def check_paths(root: Path) -> tuple[int, int]:
    entries = 0
    total = 0
    normalised: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            error("archive_member_type_unsupported", f"{rel} is a symlink; entries must be regular files or directories")
            continue
        if path.is_dir():
            continue
        entries += 1
        size = path.stat().st_size
        total += size
        if size > MAX_MEMBER_BYTES:
            error("archive_member_too_large", f"{rel} is {size} bytes, limit 100 MiB")
        segments = rel.split("/")
        if len(segments) > MAX_PATH_SEGMENTS:
            error("archive_member_path_too_deep", f"{rel} has {len(segments)} segments, limit 20")
        if any(seg != seg.strip() for seg in segments):
            error("archive_member_path_has_outer_whitespace", f"{rel} has a segment with outer whitespace")
        if "\\" in rel:
            error("archive_member_path_has_backslash", f"{rel} contains a backslash")
        key = unicodedata.normalize("NFC", rel).casefold()
        if key in normalised and normalised[key] != rel:
            error("archive_member_path_normalization_collision",
                  f"{rel} collides with {normalised[key]} after case and Unicode normalisation")
        normalised[key] = rel

    if entries == 0:
        error("archive_empty", "bundle is empty")
    if entries > MAX_ENTRIES:
        error("archive_too_many_entries", f"{entries} entries, limit {MAX_ENTRIES}")
    if total > MAX_UNCOMPRESSED_BYTES:
        error("archive_uncompressed_too_large", f"{total} bytes extracted, limit 512 MiB")
    return entries, total


# --------------------------------------------------------------------------- #
# zip
# --------------------------------------------------------------------------- #

def write_zip(root: Path, out: Path) -> None:
    """Write a deterministic ZIP with the plugin root at the archive root."""
    files = sorted(p for p in root.rglob("*") if p.is_file() and not p.is_symlink())
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in files:
            info = zipfile.ZipInfo(path.relative_to(root).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, path.read_bytes())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ref", default="HEAD", help="git ref to package (default: HEAD). Use the release tag.")
    parser.add_argument("--repo", default=None, help="repository path (default: the repo containing this script)")
    parser.add_argument("--out", default="dist", help="output directory for the ZIP (default: dist)")
    parser.add_argument("--check-only", action="store_true", help="validate the staged tree without writing a ZIP")
    parser.add_argument("--keep-tree", action="store_true", help="leave the staged tree on disk for inspection")
    args = parser.parse_args()

    repo = Path(args.repo).resolve() if args.repo else Path(__file__).resolve().parents[2]
    if not (repo / ".git").exists():
        print(f"{repo} is not a git repository", file=sys.stderr)
        return 1

    sha = subprocess.run(["git", "-C", str(repo), "rev-parse", args.ref],
                         capture_output=True, text=True, check=True).stdout.strip()

    workdir = Path(tempfile.mkdtemp(prefix="openai-bundle-"))
    stage = workdir / "plugin"
    try:
        export_tree(repo, args.ref, stage)
        removed = strip_tree(stage)

        manifest = check_manifest(stage)
        skill_count = check_skills(stage, manifest.get("name", ""), manifest.get("license", ""))
        entries, uncompressed = check_paths(stage)

        print(f"ref            {args.ref} ({sha[:12]})")
        print(f"plugin         {manifest.get('name', '?')} {manifest.get('version', '?')}")
        print(f"skills         {skill_count}")
        print(f"entries        {entries}")
        print(f"uncompressed   {uncompressed / 1_048_576:.1f} MiB")
        print(f"stripped       {', '.join(removed[:5])}{' ...' if len(removed) > 5 else ''} ({len(removed)} paths)")

        if warnings:
            print(f"\n{len(warnings)} warning(s):")
            for line in warnings:
                print(f"  ! {line}")
        if errors:
            print(f"\n{len(errors)} error(s), submission would be rejected:")
            for line in errors:
                print(f"  x {line}")
            return 1

        if args.check_only:
            print("\nvalidation passed, no ZIP written (--check-only)")
            return 0

        version = manifest.get("version", "0.0.0")
        out = Path(args.out).resolve() / f"{manifest.get('name', 'plugin')}-{version}.zip"
        write_zip(stage, out)
        size = out.stat().st_size
        if size > MAX_ZIP_BYTES:
            print(f"\nx archive_too_large: {size} bytes, limit 100 MB")
            return 1
        digest = hashlib.sha256(out.read_bytes()).hexdigest()
        print(f"\nvalidation passed")
        print(f"zip            {out}")
        print(f"compressed     {size / 1_048_576:.1f} MiB")
        print(f"sha256         {digest}")
        print(f"\nUpload this file on the Skills tab at https://platform.openai.com/plugins")
        return 0
    finally:
        if args.keep_tree:
            print(f"\nstaged tree kept at {stage}")
        else:
            shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
