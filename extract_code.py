import os
import re

doc_path = r"c:\Github\24openClaw\ZEROCLAW_PHASE0_COMPLETE_GUIDE.md"
base_dir = r"c:\Github\24openClaw\zeroclaw"

with open(doc_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

current_file = None
in_code_block = False
code_content = []

for line in lines:
    # Match headers like `### 4.2 crates/common/src/types.rs`
    # or `### 3.1 Root Workspace Cargo.toml`
    header_match = re.match(r'^###\s+\d+\.\d+\s+(.*)', line)
    if header_match:
        title = header_match.group(1).strip()
        if "Root Workspace Cargo.toml" in title:
            current_file = "Cargo.toml"
        else:
            # Extract out the path
            # usually the last word, or the first word if it contains /
            words = title.split()
            path_candidate = None
            for w in words:
                if '/' in w or w.endswith('.rs') or w.endswith('.toml'):
                    path_candidate = w
                    break
            
            if path_candidate:
                current_file = path_candidate
            else:
                current_file = None
        continue

    if line.strip().startswith("```") and "```bash" not in line.strip() and not line.strip().startswith("```text"):
        if not in_code_block and current_file:
            in_code_block = True
            code_content = []
        elif in_code_block:
            in_code_block = False
            
            # avoid writing tree views
            content_str = "".join(code_content)
            if "├──" in content_str or "└──" in content_str or "zeroclaw/" in content_str and "Cargo.toml" not in content_str:
                current_file = None
                continue
                
            if current_file:
                # Handle edge cases
                full_path = os.path.join(base_dir, current_file)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w", encoding="utf-8") as out:
                    # check if the first line is exactly '# zeroclaw/Cargo.toml'
                    if len(code_content) > 0 and code_content[0].strip() == "# zeroclaw/Cargo.toml":
                        out.write("".join(code_content[1:]).lstrip()) # remove that line
                    else:
                        out.write(content_str)
                print(f"Created {full_path}")
            current_file = None
        continue

    if in_code_block:
        code_content.append(line)
