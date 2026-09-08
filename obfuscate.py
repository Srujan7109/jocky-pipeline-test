import re
import random
import string
import sys
import hashlib
import os

# ============================================================
# JOCKY Polymorphic Obfuscation Engine
# Runs as part of the CI/CD pipeline
# Input:  mission.cpp
# Output: mission_obfuscated.cpp (different every run)
# ============================================================

# ----------------------------------------------------------
# CONFIG
# ----------------------------------------------------------
INPUT_FILE  = "mission.cpp"
OUTPUT_FILE = "mission_obfuscated.cpp"

# Variables to rename — add any new variable names here
VARIABLES_TO_RENAME = [
    "target_host",
    "mission_name",
    "process_count",
    "connection_count",
    "process_list",
    "connection_list",
    "proc",
    "conn",
]

# Junk lines to randomly insert between real lines
JUNK_TEMPLATES = [
    "int {var} = {val};",
    "float {var} = {val}.0f;",
    "bool {var} = false;",
    "int {var} = {val} * 0;",
    "long {var} = {val}L;",
    "unsigned int {var} = {val}u;",
]


# ----------------------------------------------------------
# HELPERS
# ----------------------------------------------------------

def random_name(length=10):
    """Generate a random variable name that looks plausible."""
    prefix = random.choice(["_jk", "_fw", "_nt", "_op", "_rx"])
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    return prefix + suffix


def random_int():
    return random.randint(1, 9999)


def build_rename_map(variables):
    """Create a fresh random mapping for every run."""
    return {v: random_name() for v in variables}


def apply_renames(source, rename_map):
    """
    Replace each original variable name with its random counterpart.
    Uses word-boundary matching so 'conn' does not replace inside 'connection'.
    """
    for original, replacement in rename_map.items():
        source = re.sub(r'\b' + re.escape(original) + r'\b', replacement, source)
    return source


def insert_junk(lines, density=0.25):
    """
    Walk through the lines and randomly insert junk statements.
    density = probability of inserting a junk line after each real line.
    Only inserts inside function bodies (after lines ending with ; or {).
    """
    result = []
    inside_function = False

    for line in lines:
        result.append(line)

        stripped = line.strip()

        # Track whether we are inside a function body
        if stripped.endswith('{'):
            inside_function = True
        if stripped == '}' or stripped == '};':
            inside_function = False

        # Only insert junk inside functions, not at top level declarations
        if inside_function and stripped.endswith(';') and random.random() < density:
            junk_var  = random_name(8)
            junk_val  = random_int()
            template  = random.choice(JUNK_TEMPLATES)
            junk_line = "    " + template.format(var=junk_var, val=junk_val)
            result.append(junk_line)

    return result


def encrypt_strings(source):
    """
    Find string literals inside function bodies and add
    a comment showing the encrypted form beside them.
    Keeps the string valid C++ while showing obfuscation intent.
    Uses simple Caesar shift annotation as a demonstration.
    """
    pattern = re.compile(r'("([^"\\]{4,})")')

    def replacer(match):
        original  = match.group(1)
        text      = match.group(2)
        key       = random.randint(1, 25)
        encrypted = ''.join(chr((ord(c) + key) % 128) for c in text)
        # Keep original string valid, annotate with encrypted form
        return f'{original} /* enc:{key}:{repr(encrypted)} */'

    return pattern.sub(replacer, source)


def compute_hash(filepath):
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


# ----------------------------------------------------------
# MAIN
# ----------------------------------------------------------

def main():
    print("=" * 55)
    print("  JOCKY Polymorphic Obfuscation Engine")
    print("=" * 55)

    # Read input
    if not os.path.exists(INPUT_FILE):
        print(f"[ERROR] Input file not found: {INPUT_FILE}")
        sys.exit(1)

    with open(INPUT_FILE, "r") as f:
        source = f.read()

    print(f"[1/4] Read {INPUT_FILE} ({len(source)} bytes)")

    # Step 1 — Rename variables
    rename_map = build_rename_map(VARIABLES_TO_RENAME)
    source = apply_renames(source, rename_map)
    print(f"[2/4] Renamed {len(rename_map)} variables")
    for original, replacement in rename_map.items():
        print(f"      {original:20s} -> {replacement}")

    # Step 2 — Insert junk lines
    lines  = source.splitlines()
    lines  = insert_junk(lines, density=0.3)
    source = "\n".join(lines)
    print(f"[3/4] Inserted junk lines  (total lines: {len(lines)})")

    # Step 3 — Encrypt string literals
    source = encrypt_strings(source)
    print(f"[4/4] String literals encrypted")

    # Write output
    with open(OUTPUT_FILE, "w") as f:
        f.write(source)

    # Hash comparison
    original_hash = compute_hash(INPUT_FILE)
    output_hash   = compute_hash(OUTPUT_FILE)

    print()
    print("-" * 55)
    print(f"  Original hash  : {original_hash[:32]}...")
    print(f"  Obfuscated hash: {output_hash[:32]}...")
    print(f"  Hashes match   : {original_hash == output_hash}")
    print("-" * 55)
    print(f"  Output written : {OUTPUT_FILE}")
    print("=" * 55)


if __name__ == "__main__":
    main()