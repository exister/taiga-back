import hashlib
import functools

from django.core.cache import cache
from django.utils.encoding import force_bytes

from markdown import Markdown

from .extensions.autolink import AutolinkExtension
from .extensions.automail import AutomailExtension
from .extensions.semi_sane_lists import SemiSaneListExtension
from .extensions.spaced_link import SpacedLinkExtension
from .extensions.strikethrough import StrikethroughExtension
from .extensions.wikilinks import WikiLinkExtension
from .extensions.emojify import EmojifyExtension
from .extensions.mentions import MentionsExtension
from .extensions.references import TaigaReferencesExtension


def _make_extensions_list(wikilinks_config=None, project=None):
    return [AutolinkExtension(),
            AutomailExtension(),
            SemiSaneListExtension(),
            SpacedLinkExtension(),
            StrikethroughExtension(),
            WikiLinkExtension(wikilinks_config),
            EmojifyExtension(),
            MentionsExtension(),
            TaigaReferencesExtension(project),
            "extra",
            "codehilite"]


import diff_match_patch


def cache_by_sha(func):
    @functools.wraps(func)
    def _decorator(project, text):
        sha1_hash = hashlib.sha1(force_bytes(text)).hexdigest()
        key = "{}-{}".format(sha1_hash, project.id)

        # Try to get it from the cache
        cached = cache.get(key)
        if cached is not None:
            return cached

        returned_value = func(project, text)
        cache.set(key, returned_value, timeout=None)
        return returned_value

    return _decorator


def _get_markdown(project):
    wikilinks_config = {"base_url": "#/project/{}/wiki/".format(project.slug),
                        "end_url": ""}
    extensions = _make_extensions_list(wikilinks_config=wikilinks_config,
                                       project=project)
    md = Markdown(extensions=extensions)
    md.extracted_data = {"mentions": [], "references": []}
    return md


@cache_by_sha
def render(project, text):
    md = _get_markdown(project)
    return md.convert(text)


def render_and_extract(project, text):
    md = _get_markdown(project)
    result = md.convert(text)
    return (result, md.extracted_data)


class DiffMatchPatch(diff_match_patch.diff_match_patch):
    def diff_pretty_html(self, diffs):
        html = []
        for (op, data) in diffs:
            text = (data.replace("&", "&amp;").replace("<", "&lt;")
                    .replace(">", "&gt;").replace("\n", "<br />"))
            if op == self.DIFF_INSERT:
                html.append("<ins style=\"background:#e6ffe6;\">%s</ins>" % text)
            elif op == self.DIFF_DELETE:
                html.append("<del style=\"background:#ffe6e6;\">%s</del>" % text)
            elif op == self.DIFF_EQUAL:
                html.append("<span>%s</span>" % text)
        return "".join(html)


def get_diff_of_htmls(html1, html2):
    diffutil = DiffMatchPatch()
    diff = diffutil.diff_main(html1, html2)
    return diffutil.diff_pretty_html(diff)

__all__ = ["render", "get_diff_of_htmls", "render_and_extract"]