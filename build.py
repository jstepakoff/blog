#!/usr/bin/env python3
"""Build blog.joshstepakoff.com into ./docs (served by GitHub Pages from main /docs).

Usage:
  python3 build.py            # published posts only (what goes live)
  python3 build.py --drafts   # include drafts, for previewing
"""
import datetime as dt, html, json, re, shutil, sys
from pathlib import Path
import markdown, yaml
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).parent
OUT = ROOT / "docs"
SITE = yaml.safe_load((ROOT / "site.yml").read_text())
A = SITE["agent"]
env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=False)
base = env.get_template("base.html")
esc = html.escape


def agent_schema():
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "RealEstateAgent",
        "@id": f"{A['site']}/#agent",
        "name": A["name"],
        "alternateName": A["legal_name"],
        "jobTitle": "Realtor",
        "url": A["site"],
        "image": f"{SITE['url']}/assets/img/headshot.jpg",
        "telephone": A["phone_e164"],
        "address": {"@type": "PostalAddress", "streetAddress": A["street"],
                    "addressLocality": A["city"], "addressRegion": A["region"],
                    "postalCode": A["zip"], "addressCountry": "US"},
        "areaServed": [{"@type": "Place", "name": f"{x}, CA"} for x in A["areas"]],
        "parentOrganization": {"@type": "RealEstateAgent", "name": A["brokerage"]},
        "hasCredential": {"@type": "EducationalOccupationalCredential",
                          "credentialCategory": "California DRE License", "identifier": A["dre"]},
        "sameAs": A["same_as"],
    })


def page(path, body, title, description, og_type="website", post_schema=None, faq_schema=None):
    canonical = SITE["url"] + path
    out = base.render(site=SITE, a=A, body=body, page_title=esc(title), page_description=esc(description),
                      canonical=canonical, og_type=og_type, agent_schema=agent_schema(),
                      post_schema=post_schema, faq_schema=faq_schema)
    dest = OUT / path.strip("/") / "index.html" if path != "/" else OUT / "index.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(out)
    return canonical


def load_posts(include_drafts):
    posts = []
    files = sorted((ROOT / "posts").glob("*.md"))
    if include_drafts:
        files += sorted((ROOT / "drafts").glob("*.md"))
    for f in files:
        raw = f.read_text()
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
        meta, text = yaml.safe_load(m.group(1)), m.group(2)
        if meta.get("status", "draft") != "published" and not include_drafts:
            continue
        meta["date"] = meta["date"] if isinstance(meta["date"], dt.date) else dt.date.fromisoformat(str(meta["date"]))
        meta["slug"] = meta.get("slug") or f.stem
        meta["md"] = text
        posts.append(meta)
    return sorted(posts, key=lambda p: p["date"], reverse=True)


def faq_from(md_text):
    """Turn '### Question?' headings under a 'Frequently asked questions' H2 into FAQPage schema."""
    sec = re.search(r"^## Frequently asked questions\s*\n(.*?)(?=^## |\Z)", md_text, re.S | re.M)
    if not sec:
        return None
    pairs = re.findall(r"^### (.+?)\n+(.+?)(?=\n### |\Z)", sec.group(1), re.S | re.M)
    if not pairs:
        return None
    return json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q.strip(),
         "acceptedAnswer": {"@type": "Answer", "text": re.sub(r"\s+", " ", a_).strip()}}
        for q, a_ in pairs]})


def fmt(d):
    return d.strftime("%B ") + str(d.day) + d.strftime(", %Y")


def build(include_drafts=False):
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT / "assets", OUT / "assets")
    posts = load_posts(include_drafts)
    urls = []

    for p in posts:
        body_html = markdown.markdown(p["md"], extensions=["tables", "sane_lists"])
        url = f"/{p['slug']}/"
        iso = p["date"].isoformat()
        schema = json.dumps({
            "@context": "https://schema.org", "@type": "BlogPosting",
            "headline": p["title"], "description": p["description"],
            "datePublished": iso, "dateModified": str(p.get("updated", iso)),
            "mainEntityOfPage": SITE["url"] + url, "image": f"{SITE['url']}/assets/img/headshot.jpg",
            "author": {"@type": "Person", "@id": f"{A['site']}/#agent", "name": A["name"], "url": A["site"]},
            "publisher": {"@id": f"{A['site']}/#agent"},
        })
        draft_flag = '<p class="draft-flag">DRAFT PREVIEW</p>' if p.get("status") != "published" else ""
        body = f"""<article class="post">
  {draft_flag}
  <header class="post-header">
    <p class="eyebrow">{esc(p.get('category', ''))}</p>
    <h1>{esc(p['title'])}</h1>
    <p class="byline">By <a href="{A['site']}">Josh Stepakoff</a>, Realtor | <time datetime="{iso}">{fmt(p['date'])}</time></p>
  </header>
  <div class="post-body">
{body_html}
  </div>
  <aside class="cta-box">
    <h2>Have a question about your home or neighborhood?</h2>
    <p>I'm a resource for all things real estate, from pricing and timing to remodel opinions and contractor names. Reach out anytime.</p>
    <p class="cta-links"><a class="btn" href="tel:{A['phone_e164']}">Call {A['phone']}</a> <a class="btn btn-ghost" href="{A['site']}">Visit joshstepakoff.com</a></p>
  </aside>
  <p class="back"><a href="/">&larr; All posts</a></p>
</article>"""
        urls.append((page(url, body, f"{p['title']} | Josh Stepakoff", p["description"], "article",
                          schema, faq_from(p["md"])), iso))

    cards = "\n".join(f"""  <article class="post-card">
    <p class="eyebrow">{esc(p.get('category', ''))}</p>
    <h2><a href="/{p['slug']}/">{esc(p['title'])}</a></h2>
    <p class="card-date">{fmt(p['date'])}</p>
    <p>{esc(p['description'])}</p>
    <a class="read-more" href="/{p['slug']}/">Read more &rarr;</a>
  </article>""" for p in posts) or '  <p class="empty">First posts are on the way.</p>'
    home = f"""<section class="intro">
  <h1>Valley real estate, explained by a local</h1>
  <p class="lede">Market updates, neighborhood guides, and straight answers for homeowners and buyers in Porter Ranch, Northridge, Granada Hills, Chatsworth, and across the San Fernando Valley.</p>
</section>
<section class="post-list">
{cards}
</section>"""
    today = dt.date.today().isoformat()
    urls.append((page("/", home, "San Fernando Valley Real Estate Blog | Josh Stepakoff", SITE["description"]), today))

    about_md = (ROOT / "templates" / "about.md").read_text()
    about = f"""<article class="post about">
<h1>About Josh</h1>
<img class="about-photo" src="/assets/img/headshot.jpg" alt="Josh Stepakoff">
{markdown.markdown(about_md)}
</article>"""
    urls.append((page("/about/", about, "About Josh Stepakoff | San Fernando Valley Realtor",
                      "Josh Stepakoff is a San Fernando Valley native and Realtor with Pinnacle Estate Properties, serving Porter Ranch, Northridge, Granada Hills, Chatsworth, and the greater Valley."), today))

    # sitemap, feed, robots, CNAME
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{u}</loc><lastmod>{d}</lastmod></url>\n" for u, d in urls) + "</urlset>\n")
    items = "".join(f"""  <item><title>{esc(p['title'])}</title><link>{SITE['url']}/{p['slug']}/</link><guid>{SITE['url']}/{p['slug']}/</guid><pubDate>{dt.datetime.combine(p['date'], dt.time(8)).strftime('%a, %d %b %Y %H:%M:%S -0700')}</pubDate><description>{esc(p['description'])}</description></item>\n""" for p in posts)
    (OUT / "feed.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel><title>{esc(SITE["title"])}</title><link>{SITE["url"]}/</link><description>{esc(SITE["description"])}</description>\n{items}</channel></rss>\n')
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE['url']}/sitemap.xml\n")
    (OUT / "CNAME").write_text("blog.joshstepakoff.com\n")
    (OUT / ".nojekyll").write_text("")
    print(f"Built {len(posts)} post(s) into {OUT}")


if __name__ == "__main__":
    build("--drafts" in sys.argv)
