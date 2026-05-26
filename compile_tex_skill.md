# Compile TeX Skill

This skill compiles LaTeX sources and applies common autofixes for build failures.

## Purpose

- Compile `Mini-Project/Project Documents/Final Paper.tex`
- Compile `Mini-Project/Project Documents/Final Slides.tex`
- Automatically fix typical LaTeX issues such as:
  - missing `\end{document}`
  - unmatched braces `{}`
  - unmatched LaTeX environments
  - missing closing `]` for `\twocolumn[...]`

## Files

- `scripts/compile_tex_skill.py` — Python implementation of the compile/autofix skill
- `scripts/compile_tex.sh` — shell wrapper for convenience

## Usage

From the repo root:

```bash
bash scripts/compile_tex.sh "Mini-Project/Project Documents/Final Paper.tex" "Mini-Project/Project Documents/Final Slides.tex"
```

Or directly:

```bash
python3 scripts/compile_tex_skill.py \
  "Mini-Project/Project Documents/Final Paper.tex" \
  "Mini-Project/Project Documents/Final Slides.tex"
```

## Notes

- Uses `tectonic` if available; falls back to `pdflatex` if not.
- If compilation fails, the skill attempts simple text-based fixes before retrying.
- The autofix logic is heuristic; manual review may still be required for complex macro or package errors.
