import re
import random
import string
import sys
import hashlib
import os

# ============================================================
# JOCKY Polymorphic Obfuscation Engine v2
# Runs as part of the CI/CD pipeline
# Input:  mission.cpp
# Output: mission_obfuscated.cpp (different every run)
# ============================================================

INPUT_FILE  = "mission.cpp"
OUTPUT_FILE = "mission_obfuscated.cpp"

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

JUNK_TEMPLATES = [
    "int {var} = {val};",
    "float {var} = {val}.0f;",
    "bool {var} = false;",
    "int {var} = {val} * 0;",
    "long {var} = {val}L;",
    "unsigned int {var} = {val}u;",
]

# Useless comments to flood the code with
USELESS_COMMENTS = [
    "// initializing standard buffer",
    "// checking alignment",
    "// routine memory check",
    "// standard pipeline flush",
    "// verify stack pointer",
    "// cache prefetch hint",
    "// branch prediction optimization",
    "// register allocation hint",
    "// null pointer safety check",
    "// overflow guard",
    "// alignment padding",
    "// standard header sync",
    "// memory fence operation",
    "// pipeline stall avoidance",
    "// speculative execution barrier",
    "// loop unroll candidate",
    "// vectorization hint",
    "// inline expansion marker",
    "// tail call optimization hint",
    "// dead store elimination guard",
    "// constant folding marker",
    "// strength reduction candidate",
    "// alias analysis hint",
    "// escape analysis marker",
    "// devirtualization hint",
    "// inlining boundary marker",
    "// profile guided optimization hint",
    "// basic block marker",
    "// dominator tree node",
    "// live variable boundary",
]

# Dead function templates — never called, just exist
DEAD_FUNCTION_TEMPLATES = [
    """
// {comment}
int {fname}(int {p1}, int {p2}) {{
    // {inner_comment}
    int {lv1} = {p1} * {val1};
    int {lv2} = {p2} + {val2};
    // {inner_comment2}
    if ({lv1} > {lv2}) {{
        return {lv1} - {lv2};
    }}
    return {lv2};
}}
""",
    """
// {comment}
void {fname}(float {p1}) {{
    // {inner_comment}
    float {lv1} = {p1} * {val1}.0f;
    float {lv2} = {lv1} / {val2}.0f;
    // {inner_comment2}
    (void){lv2};
}}
""",
    """
// {comment}
bool {fname}(int {p1}) {{
    // {inner_comment}
    int {lv1} = {p1} & 0xFF;
    int {lv2} = {lv1} ^ {val1};
    // {inner_comment2}
    return ({lv2} > {val2});
}}
""",
]


# ----------------------------------------------------------
# HELPERS
# ----------------------------------------------------------

def random_name(length=10):
    prefix = random.choice(["_jk", "_fw", "_nt", "_op", "_rx"])
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    return prefix + suffix


def random_int():
    return random.randint(1, 9999)


def build_rename_map(variables):
    return {v: random_name() for v in variables}


def apply_renames(source, rename_map):
    for original, replacement in rename_map.items():
        source = re.sub(r'\b' + re.escape(original) + r'\b', replacement, source)
    return source


# ----------------------------------------------------------
# TECHNIQUE 1: Junk Insertion + Useless Comments
# ----------------------------------------------------------

def insert_junk_and_comments(lines, junk_density=0.25, comment_density=0.35):
    result = []
    inside_function = False

    for line in lines:
        result.append(line)
        stripped = line.strip()

        if stripped.endswith('{'):
            inside_function = True
        if stripped == '}' or stripped == '};':
            inside_function = False

        if inside_function and stripped.endswith(';'):
            # Insert useless comment
            if random.random() < comment_density:
                indent = "    "
                comment = random.choice(USELESS_COMMENTS)
                result.append(indent + comment)

            # Insert junk variable declaration
            if random.random() < junk_density:
                junk_var  = random_name(8)
                junk_val  = random_int()
                template  = random.choice(JUNK_TEMPLATES)
                junk_line = "    " + template.format(var=junk_var, val=junk_val)
                result.append(junk_line)

    return result


# ----------------------------------------------------------
# TECHNIQUE 2: String Annotation (Caesar shift marker)
# ----------------------------------------------------------

def annotate_strings(source):
    pattern = re.compile(r'("([^"\\]{4,})")')

    def replacer(match):
        original = match.group(1)
        text     = match.group(2)
        key      = random.randint(1, 25)
        encrypted = ''.join(chr((ord(c) + key) % 128) for c in text)
        return f'{original} /* enc:{key}:{repr(encrypted)} */'

    return pattern.sub(replacer, source)


# ----------------------------------------------------------
# TECHNIQUE 3: Instruction Substitution
# Replaces simple arithmetic with equivalent expressions
# ----------------------------------------------------------

def substitute_instructions(source):
    substitutions = [
        # x + 1  →  x - (-1)
        (r'(\b\w+\b)\s*\+\s*1\b',
         lambda m: f'{m.group(1)} - (-1)'),

        # x - 1  →  x + (-1)
        (r'(\b\w+\b)\s*-\s*1\b',
         lambda m: f'{m.group(1)} + (-1)'),

        # x * 2  →  (x << 1)
        (r'(\b\w+\b)\s*\*\s*2\b',
         lambda m: f'({m.group(1)} << 1)'),

        # x == 0  →  !(x)
        (r'(\b\w+\b)\s*==\s*0\b',
         lambda m: f'(!({m.group(1)}))'),

        # true  →  (1 == 1)
        (r'\btrue\b',
         lambda m: '(1 == 1)'),

        # false  →  (1 == 0)
        (r'\bfalse\b',
         lambda m: '(1 == 0)'),
    ]

    for pattern, replacement in substitutions:
        # Only apply substitution 50% of the time per match
        # to keep variation between builds
        def maybe_replace(m, repl=replacement):
            if random.random() < 0.5:
                return repl(m)
            return m.group(0)

        source = re.sub(pattern, maybe_replace, source)

    return source


# ----------------------------------------------------------
# TECHNIQUE 4: Dead Code Insertion
# Adds entire fake functions that are never called
# ----------------------------------------------------------

def insert_dead_functions(source, count=3):
    dead_functions = []

    for _ in range(count):
        template = random.choice(DEAD_FUNCTION_TEMPLATES)
        dead_fn  = template.format(
            fname         = random_name(8),
            p1            = random_name(5),
            p2            = random_name(5),
            lv1           = random_name(6),
            lv2           = random_name(6),
            val1          = random_int(),
            val2          = random_int(),
            comment       = random.choice(USELESS_COMMENTS).replace("// ", ""),
            inner_comment = random.choice(USELESS_COMMENTS),
            inner_comment2= random.choice(USELESS_COMMENTS),
        )
        dead_functions.append(dead_fn)

    # Insert dead functions just before the main() function
    insertion_point = source.find("int main()")
    if insertion_point == -1:
        return source

    dead_block = "\n".join(dead_functions) + "\n"
    return source[:insertion_point] + dead_block + source[insertion_point:]


# ----------------------------------------------------------
# TECHNIQUE 5: Control Flow Flattening
# Converts simple if/else blocks into switch-based dispatch
# ----------------------------------------------------------

def flatten_control_flow(source):
    # Pattern: if (COND) { BODY_A } else { BODY_B }
    # Replace with switch-based equivalent using state variable
    pattern = re.compile(
        r'if\s*\(([^)]+)\)\s*\{([^{}]*)\}\s*else\s*\{([^{}]*)\}',
        re.DOTALL
    )

    def replacer(match):
        if random.random() < 0.5:
            return match.group(0)  # leave half unchanged for variation

        cond   = match.group(1).strip()
        body_a = match.group(2).strip()
        body_b = match.group(3).strip()
        state  = random_name(6)
        val_a  = random_int()
        val_b  = random_int()

        flattened = f"""
    // {random.choice(USELESS_COMMENTS).replace("// ", "")}
    int {state} = ({cond}) ? {val_a} : {val_b};
    switch ({state}) {{
        case {val_a}:
            {body_a}
            break;
        case {val_b}:
            {body_b}
            break;
        default:
            break;
    }}"""
        return flattened

    return pattern.sub(replacer, source)


# ----------------------------------------------------------
# TECHNIQUE 6: Comment Flooding at File Level
# Adds blocks of useless comments at top of file
# ----------------------------------------------------------

def flood_file_header(source, count=15):
    header_lines = []
    for _ in range(count):
        comment = random.choice(USELESS_COMMENTS)
        header_lines.append(comment)

    header_block = "\n".join(header_lines) + "\n\n"
    return header_block + source


# ----------------------------------------------------------
# HASH UTILITIES
# ----------------------------------------------------------

def compute_hash(filepath):
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
    print("  JOCKY Polymorphic Obfuscation Engine v2")
    print("=" * 55)

    if not os.path.exists(INPUT_FILE):
        print(f"[ERROR] Input file not found: {INPUT_FILE}")
        sys.exit(1)

    with open(INPUT_FILE, "r") as f:
        source = f.read()

    print(f"[1/7] Read {INPUT_FILE} ({len(source)} bytes)")

    # Step 1: Rename variables
    rename_map = build_rename_map(VARIABLES_TO_RENAME)
    source = apply_renames(source, rename_map)
    print(f"[2/7] Renamed {len(rename_map)} variables")
    for original, replacement in rename_map.items():
        print(f"      {original:20s} -> {replacement}")

    # Step 2: Annotate strings
    source = annotate_strings(source)
    print(f"[3/7] String literals annotated with encryption markers")

    # Step 3: Instruction substitution
    source = substitute_instructions(source)
    print(f"[4/7] Arithmetic instructions substituted")

    # Step 4: Control flow flattening
    source = flatten_control_flow(source)
    print(f"[5/7] Control flow flattening applied")

    # Step 5: Insert junk lines and useless comments
    lines  = source.splitlines()
    lines  = insert_junk_and_comments(lines, junk_density=0.3, comment_density=0.4)
    source = "\n".join(lines)
    print(f"[6/7] Junk lines and useless comments inserted (total lines: {len(lines)})")

    # Step 6: Insert dead functions
    source = insert_dead_functions(source, count=3)
    print(f"[7/7] Dead code functions inserted")

    # Step 7: Flood file header with useless comments
    source = flood_file_header(source, count=20)

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
    print(f"  Output lines   : {len(source.splitlines())}")
    print("-" * 55)
    print(f"  Output written : {OUTPUT_FILE}")
    print("=" * 55)


if __name__ == "__main__":
    main()