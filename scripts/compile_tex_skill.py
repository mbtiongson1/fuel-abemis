#!/usr/bin/env python3
import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

env_open_re = re.compile(r"\\begin\{([^}]+)\}")
env_close_re = re.compile(r"\\end\{([^}]+)\}")


def strip_comments(line: str) -> str:
    if "%" in line:
        return line.split("%", 1)[0]
    return line


def count_braces(text: str) -> tuple[int, int]:
    open_count = 0
    close_count = 0
    for line in text.splitlines():
        line = strip_comments(line)
        open_count += line.count("{")
        close_count += line.count("}")
    return open_count, close_count


def find_unmatched_envs(text: str) -> list[str]:
    stack: list[str] = []
    for line in text.splitlines():
        line = strip_comments(line)
        for match in env_open_re.finditer(line):
            stack.append(match.group(1))
        for match in env_close_re.finditer(line):
            name = match.group(1)
            if stack and stack[-1] == name:
                stack.pop()
            elif name in stack:
                stack.remove(name)
            else:
                pass
    return stack


def has_matching_twocolumn_brackets(text: str) -> bool:
    if "\\twocolumn[" not in text:
        return True
    start = text.index("\\twocolumn[")
    bracket_count = 0
    for ch in text[start:]:
        if ch == "[":
            bracket_count += 1
        elif ch == "]":
            bracket_count -= 1
            if bracket_count == 0:
                return True
    return False


def compile_tex(tex_path: Path, keep_logs: bool = False) -> tuple[int, str, str]:
    if shutil.which("tectonic"):
        cmd = ["tectonic", str(tex_path)]
        if keep_logs:
            cmd.append("--keep-logs")
    elif shutil.which("pdflatex"):
        cmd = ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", str(tex_path)]
    else:
        raise RuntimeError("Neither tectonic nor pdflatex is installed on PATH.")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    output = proc.stdout + proc.stderr
    return proc.returncode, proc.stdout, proc.stderr


def autofix_file(tex_path: Path) -> list[str]:
    changes = []
    text = tex_path.read_text(encoding="utf-8")
    original = text
    if not text.rstrip().endswith("\\end{document}"):
        text = text.rstrip() + "\n\n\\end{document}\n"
        changes.append("Appended missing\\end{document}")
    open_braces, close_braces = count_braces(text)
    if open_braces > close_braces:
        missing = open_braces - close_braces
        text = text + ("}" * missing) + "\n"
        changes.append(f"Appended {missing} missing closing brace(s)")
    unmatched_envs = find_unmatched_envs(text)
    if unmatched_envs:
        for env in reversed(unmatched_envs):
            text = text + f"\\end{{{env}}}\n"
        changes.append(f"Appended closing environment(s): {', '.join(reversed(unmatched_envs))}")
    if not has_matching_twocolumn_brackets(text):
        text = text + "\n]"
        changes.append("Added closing bracket for \twocolumn[ ... ]")
    if text != original:
        tex_path.write_text(text, encoding="utf-8")
    return changes


def compile_and_fix(tex_files: list[Path], keep_logs: bool = False) -> int:
    result_code = 0
    for tex_path in tex_files:
        print(f"=== Processing: {tex_path} ===")
        if not tex_path.exists():
            print(f"ERROR: file not found: {tex_path}")
            result_code = 1
            continue
        compile_code, stdout, stderr = compile_tex(tex_path, keep_logs)
        if compile_code == 0:
            print("SUCCESS: compiled without errors.")
            continue
        print("Compile failed. Attempting autofix heuristics...")
        fixes = autofix_file(tex_path)
        if fixes:
            print("Autofix actions:")
            for fix in fixes:
                print(f"  - {fix}")
        else:
            print("No autofixes were applied.")
        compile_code, stdout, stderr = compile_tex(tex_path, keep_logs)
        if compile_code == 0:
            print("FIXED: compilation succeeded after applying autofixes.")
        else:
            print("FAILED: compilation still failed after autofixes.")
            print("--- Compiler output ---")
            print(stdout)
            print(stderr)
            result_code = 1
    return result_code


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compile TeX files and apply common autofixes.")
    parser.add_argument("files", nargs="+", help="TeX files to compile")
    parser.add_argument("--keep-logs", action="store_true", help="Keep TeX log files when using tectonic")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tex_files = [Path(f).expanduser().resolve() for f in args.files]
    exit_code = compile_and_fix(tex_files, keep_logs=args.keep_logs)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
