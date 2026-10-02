# blog.joshstepakoff.com

Static blog for Josh Stepakoff, Realtor (Pinnacle Estate Properties, DRE #02045840).

- Write posts as Markdown in `posts/` (front matter: title, description, category, date, slug, status).
- `status: published` goes live; anything else is skipped. Unapproved drafts live in `drafts/` (not committed).
- Build: `pip install markdown jinja2 pyyaml` then `python3 build.py` (add `--drafts` to preview drafts).
- Output goes to `docs/`, which GitHub Pages serves (branch `main`, folder `/docs`).
