#!/usr/bin/env python3
"""Build the static academic website using only Python's standard library."""

from __future__ import annotations

import argparse
from datetime import date
from html import escape
import json
from pathlib import Path
import re
import shutil
from string import Template

ROOT = Path(__file__).resolve().parent


def icon(name: str) -> str:
    paths = {
        "location": '<path d="M20 10c0 6-8 11-8 11S4 16 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/>',
        "email": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 6 9 7 9-7"/>',
        "group": '<path d="m3 9 9-6 9 6M4 10h16M5 11v7m5-7v7m4-7v7m5-7v7M3 21h18"/>',
    }
    return f'<svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{paths[name]}</svg>'


def bibtex_text(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}", "{": r"\{", "}": r"\}",
        "&": r"\&", "%": r"\%", "#": r"\#", "_": r"\_",
        "$": r"\$", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in value)


def bibtex(paper: dict) -> str:
    return (
        f'@article{{{paper["id"]},\n'
        f'  author = {{{" and ".join(bibtex_text(author) for author in paper["authors"])}}},\n'
        f'  title = {{{{{bibtex_text(paper["title"])}}}}},\n'
        f'  journal = {{{bibtex_text(paper["journal"])}}},\n'
        f'  volume = {{{paper["volume"]}}},\n'
        f'  pages = {{{paper["article"]}}},\n'
        f'  year = {{{paper["year"]}}},\n'
        f'  doi = {{{paper["doi"]}}},\n'
        f'  eprint = {{{paper["arxiv"]}}},\n'
        '  archivePrefix = {arXiv},\n'
        f'  url = {{https://doi.org/{paper["doi"]}}}\n'
        '}\n'
    )


def publication(paper: dict, profile: dict, root: str, heading: str = "h3") -> str:
    authors = [
        f'<strong>{escape(author)}</strong>' if author == profile["name"] else escape(author)
        for author in paper["authors"]
    ]
    author_line = ", ".join(authors[:-1]) + " and " + authors[-1] if len(authors) > 1 else authors[0]
    doi_url = f'https://doi.org/{escape(paper["doi"], quote=True)}'
    arxiv = escape(paper["arxiv"], quote=True)
    return f'''<li class="publication-item">
      <article aria-labelledby="{escape(paper['id'])}">
        <{heading} class="publication-title" id="{escape(paper['id'])}"><a href="{doi_url}">{escape(paper['title'])}</a></{heading}>
        <p class="publication-authors">{author_line}.</p>
        <p class="publication-venue"><cite>{escape(paper['journal'])}</cite> <strong>{escape(paper['volume'])}</strong>, {escape(paper['article'])} ({paper['year']}).</p>
        <div class="publication-links" aria-label="Paper links">
          <a href="{doi_url}">Journal article<span class="visually-hidden">: {escape(paper['title'])}</span></a>
          <a href="https://arxiv.org/abs/{arxiv}">arXiv:{arxiv}</a>
          <a href="https://arxiv.org/pdf/{arxiv}">PDF<span class="visually-hidden">: {escape(paper['title'])}</span></a>
          <a href="{root}/publications/{escape(paper['id'])}.bib" download>BibTeX<span class="visually-hidden">: {escape(paper['title'])}</span></a>
        </div>
      </article>
    </li>'''


def render(template: Template, profile: dict, content: str, page: str, root: str) -> str:
    values = {key: escape(str(value), quote=True) for key, value in profile.items() if isinstance(value, str)}
    title = f'{profile["name"]} | {page}'
    if page == "About":
        title = profile.get("homepage_title", title)
    photo = profile.get("photo", "")
    portrait = (
        f'<img class="profile-photo" src="{root}/{escape(photo, quote=True)}" alt="{escape(profile.get("photo_alt", profile["name"]), quote=True)}" width="168" height="168" fetchpriority="high">'
        if photo else '<div class="profile-avatar" aria-hidden="true">SW</div>'
    )
    return template.substitute(
        values,
        title=escape(title),
        year=date.today().year,
        root=root,
        content=content,
        portrait=portrait,
        about_current=' aria-current="page"' if page == "About" else "",
        publications_current=' aria-current="page"' if page == "Publications" else "",
        cv_current=' aria-current="page"' if page == "CV" else "",
        location_icon=icon("location"),
        email_icon=icon("email"),
        group_icon=icon("group"),
    )


def supervisor_line(entry: dict) -> str:
    names = entry.get("advisors", [])
    if not names:
        return ""
    roles = entry.get("advisor_roles", [])
    if len(roles) == len(names):
        text = "; ".join(f"{role}: {name}" for role, name in zip(roles, names))
    else:
        label = "Supervisor" if len(names) == 1 else "Supervisors"
        text = f'{label}: {" and ".join(names)}'
    return f'<p class="cv-entry-meta">{escape(text)}.</p>'


def build(base_path: str = "") -> None:
    if base_path and not re.fullmatch(r"/[A-Za-z0-9._/-]+", base_path):
        raise ValueError("The base path must be a URL path such as /my-repository.")
    base_path = base_path.rstrip("/")
    profile = json.loads((ROOT / "data/profile.json").read_text(encoding="utf-8"))
    papers = sorted(
        json.loads((ROOT / "data/publications.json").read_text(encoding="utf-8")),
        key=lambda paper: paper["published"], reverse=True,
    )
    if not papers:
        raise ValueError("Add at least one publication to data/publications.json.")
    template = Template((ROOT / "templates/base.html").read_text(encoding="utf-8"))
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    shutil.copytree(ROOT / "assets", output / "assets", dirs_exist_ok=True)
    if (ROOT / "files").exists():
        shutil.copytree(ROOT / "files", output / "files", dirs_exist_ok=True)
    (output / "publications").mkdir(exist_ok=True)
    (output / ".nojekyll").touch()
    paragraphs = "\n".join(f'<p>{escape(paragraph)}</p>' for paragraph in profile["bio"])
    interests = "\n".join(f'<li>{escape(interest)}</li>' for interest in profile["interests"])
    personal = profile.get("outside_physics", {})
    personal_paragraphs = "\n".join(f'<p>{escape(paragraph)}</p>' for paragraph in personal.get("paragraphs", []))
    personal_links = ' · '.join(
        f'<a href="{escape(link["url"], quote=True)}">{escape(link["label"])}</a>'
        for link in personal.get("links", [])
    )
    personal_section = (
        '<section class="section-block" aria-labelledby="outside-physics"><h2 id="outside-physics">Outside physics</h2>'
        + personal_paragraphs + (f'<p>{personal_links}</p>' if personal_links else '') + '</section>'
        if personal_paragraphs else ''
    )
    address_lines = [escape(line) for line in profile.get("postal_address", [])]
    if profile.get("office"):
        address_lines.insert(0, f'<strong>Office {escape(profile["office"])}</strong>')
    contact_address = (
        '<address class="contact-address">' + '<br>'.join(address_lines) + '</address>'
        if address_lines else ''
    )
    home = f'''<header class="page-header"><h1>About me</h1></header>
      <div class="intro">{paragraphs}</div>
      <section class="section-block" aria-labelledby="research-interests">
        <h2 id="research-interests">Research interests</h2>
        <ul class="research-list">{interests}</ul>
      </section>
      <section class="section-block selected-publications" aria-labelledby="recent-publication">
        <h2 id="recent-publication">Recent publication</h2>
        <ol class="publication-list">{publication(papers[0], profile, base_path)}</ol>
        <p><a class="text-link" href="{base_path}/publications/">View all publications <span aria-hidden="true">→</span></a></p>
      </section>
      {personal_section}
      <section class="section-block" aria-labelledby="contact">
        <h2 id="contact">Contact</h2>
        <p class="contact-note">You can reach me at <a href="mailto:{escape(profile['email'])}">{escape(profile['email'])}</a>.</p>
        {contact_address}
      </section>'''
    (output / "index.html").write_text(render(template, profile, home, "About", base_path), encoding="utf-8")
    groups = []
    for year in sorted({paper["year"] for paper in papers}, reverse=True):
        entries = "\n".join(publication(paper, profile, base_path) for paper in papers if paper["year"] == year)
        groups.append(f'<section class="section-block" aria-labelledby="year-{year}"><h2 class="year-heading" id="year-{year}">{year}</h2><ol class="publication-list">{entries}</ol></section>')
    bibliography = f'''<header class="page-header">
        <h1>Publications</h1>
        <p class="lede">Research in quantum dynamics, statistical physics and fluctuations.</p>
      </header>
      {''.join(groups)}
      <p><a class="button-link" href="{base_path}/publications/publications.bib" download>Download all citations (BibTeX)</a></p>'''
    (output / "publications/index.html").write_text(render(template, profile, bibliography, "Publications", base_path), encoding="utf-8")
    for paper in papers:
        (output / f'publications/{paper["id"]}.bib').write_text(bibtex(paper), encoding="utf-8")
    (output / "publications/publications.bib").write_text("\n".join(bibtex(paper) for paper in papers), encoding="utf-8")
    (output / "cv").mkdir(exist_ok=True)
    education = []
    for entry in profile.get("education", []):
        dates = f'<span class="muted">{escape(entry["dates"])}</span>' if entry.get("dates") else ""
        location = f'<span class="muted"> · {escape(entry["location"])}</span>' if entry.get("location") else ""
        details = (
            '<ul class="cv-details">' + ''.join(f'<li>{escape(detail)}</li>' for detail in entry['details']) + '</ul>'
            if entry.get('details') else ''
        )
        education.append(f'''<div class="cv-entry">
          <div class="cv-entry-head"><h3>{escape(entry['university'])}</h3>{dates}</div>
          <p>{escape(entry['degree'])}{location}</p>{supervisor_line(entry)}{details}
        </div>''')
    research_entries = []
    for entry in profile.get("research_experience", []):
        research_entries.append(f'''<div class="cv-entry">
          <div class="cv-entry-head"><h3>{escape(entry['role'])}</h3><span class="muted">{escape(entry['dates'])}</span></div>
          <p><strong>{escape(entry['institution'])}</strong><span class="muted"> · {escape(entry['location'])}</span></p>
          {supervisor_line(entry)}<p>{escape(entry['description'])}</p>
        </div>''')
    research_section = (
        '<section class="section-block" aria-labelledby="cv-experience"><h2 id="cv-experience">Research experience</h2>'
        + ''.join(research_entries) + '</section>' if research_entries else ''
    )
    languages = ''.join(
        f'<li><strong>{escape(entry["language"])}:</strong> {escape(entry["level"])}</li>'
        for entry in profile.get('languages', [])
    )
    language_section = (
        '<section class="section-block" aria-labelledby="cv-languages"><h2 id="cv-languages">Languages</h2>'
        + '<ul class="language-list">' + languages + '</ul></section>' if languages else ''
    )
    downloads = []
    if (ROOT / "files/shiyi-wei-cv.pdf").exists():
        downloads.append(f'<a class="button-link" href="{base_path}/files/shiyi-wei-cv.pdf" download>CV in English (PDF)</a>')
    if (ROOT / "files/shiyi-wei-cv-fr.pdf").exists():
        downloads.append(f'<a class="button-link" href="{base_path}/files/shiyi-wei-cv-fr.pdf" lang="fr" download>CV en français (PDF)</a>')
    download = '<div class="cv-downloads">' + ''.join(downloads) + '</div>' if downloads else ''
    cv = f'''<header class="page-header"><h1>CV</h1>{download}</header>
      <section class="section-block" aria-labelledby="cv-research">
        <h2 id="cv-research">Research interests</h2><p>{escape(profile['bio'][1])}</p>
      </section>
      <section class="section-block" aria-labelledby="cv-education">
        <h2 id="cv-education">Education</h2>{''.join(education)}
      </section>
      <section class="section-block" aria-labelledby="cv-publications">
        <h2 id="cv-publications">Publications</h2>
        <ol class="publication-list">{''.join(publication(paper, profile, base_path) for paper in papers)}</ol>
      </section>{research_section}{language_section}'''
    (output / "cv/index.html").write_text(render(template, profile, cv, "CV", base_path), encoding="utf-8")
    not_found = f'<header class="page-header"><h1>Page not found</h1></header><p>This page could not be found. <a href="{base_path}/">Return to the home page</a>.</p>'
    (output / "404.html").write_text(render(template, profile, not_found, "Page not found", base_path), encoding="utf-8")
    # Removed source files must also disappear from the generated website.
    generated = {
        Path("index.html"), Path("404.html"), Path(".nojekyll"),
        Path("cv/index.html"), Path("publications/index.html"),
        Path("publications/publications.bib"),
    }
    generated.update(Path(f'publications/{paper["id"]}.bib') for paper in papers)
    for directory in ("assets", "files"):
        generated.update(path.relative_to(ROOT) for path in (ROOT / directory).rglob("*") if path.is_file())
    for path in output.rglob("*"):
        if path.is_file() and path.relative_to(output) not in generated:
            path.unlink()
    print(f"Built About, Publications ({len(papers)} papers) and CV in {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-path", default="", help="URL prefix for a GitHub project site, e.g. /my-repository")
    build(parser.parse_args().base_path)
