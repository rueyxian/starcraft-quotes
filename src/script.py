# from dataclasses import dataclass
import urllib.request
import re
import os
from typing import List, Union, Set
from enum import Enum

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
out_dir = root_dir + "/py-out/"
cache_dir = root_dir + "/py-cache/"


class RawHtml:
    url = "https://web.archive.org/web/20240602054927/https://starcraft.fandom.com/wiki/StarCraft_campaign_quotations"
    path = cache_dir + "html"

    def get():
        try:
            with open(RawHtml.path, "r") as f:
                return f.read()
        except FileNotFoundError:
            print(f"GET: `{RawHtml.url}`")
            raw = urllib.request.urlopen(RawHtml.url).read().decode("utf-8")
            os.makedirs(cache_dir, exist_ok=True)
            trimmed = re.compile(r"<h2>.*?(?=<!--)", re.DOTALL).search(raw).group()
            with open(RawHtml.path, "w") as f:
                f.write(trimmed)
            return trimmed


# NOTE: serves as tokens, not exactly html tags
class Tag(Enum):
    LB = "<lb/>"
    LB_EXTRA = "<lb_extra/>"
    QUOTE_OPEN = "<quote>"
    QUOTE_CLOSE = "</quote>"

    BR = "<br/>"
    H2_OPEN = "<h2>"
    H2_CLOSE = "</h2>"
    H3_OPEN = "<h3>"
    H3_CLOSE = "</h3>"
    H4_OPEN = "<h4>"
    H4_CLOSE = "</h4>"
    H5_OPEN = "<h5>"
    H5_CLOSE = "</h5>"
    P_OPEN = "<p>"
    P_CLOSE = "</p>"
    I_OPEN = "<i>"
    I_CLOSE = "</i>"
    B_OPEN = "<b>"
    B_CLOSE = "</b>"
    UL_OPEN = "<ul>"
    UL_CLOSE = "</ul>"
    LI_OPEN = "<li>"
    LI_CLOSE = "</li>"
    TT_OPEN = "<tt>"
    TT_CLOSE = "</tt>"

    A_OPEN = "<a>"
    A_CLOSE = "</a>"
    PRE_OPEN = "<pre>"
    PRE_CLOSE = "</pre>"
    DIV_OPEN = "<div>"
    DIV_CLOSE = "</div>"
    DL_OPEN = "<dl>"
    DL_CLOSE = "</dl>"
    DD_OPEN = "<dd>"
    DD_CLOSE = "</dd>"
    IMG_OPEN = "<img>"
    IMG_CLOSE = "</img>"
    SPAN_OPEN = "<span>"
    SPAN_CLOSE = "</span>"
    SVG_OPEN = "<svg>"
    SVG_CLOSE = "</svg>"
    USE_OPEN = "<use>"
    USE_CLOSE = "</use>"


class Iterator:
    def __init__(self, input, skips: Set[str]):
        self.cursor = 0
        self.input = input
        self.skips = skips

    def next(self):
        while True:
            if self.cursor == len(self.input):
                return None
            ret = self.input[self.cursor]
            self.cursor += 1
            if ret not in self.skips:
                return ret

    def peek(self):
        while True:
            if self.cursor == len(self.input):
                return None
            ret = self.input[self.cursor]
            if ret not in self.skips:
                return ret
            self.cursor += 1


class Parser:
    def __init__(self):
        self.out = []

    def sanitize_and_parse(self, raw_html: str) -> List[Union[Tag, str]]:
        for part in re.compile(r"<h2>(?:(?!<h2>).)+", re.DOTALL).findall(raw_html):
            self._parse_part(part)
        return self.out

    def _parse_part(self, html: str):
        m = re.compile(r"<h2>.+?>(.+?)</span>.+?\n(<h3>.+)", re.DOTALL).search(html)
        self.out.append(Tag.H2_OPEN)
        self.out.append(m.group(1))
        self.out.append(Tag.H2_CLOSE)
        for chapter in re.compile(r"<h3>(?:(?!<h3>).)+", re.DOTALL).findall(m.group(2)):
            self._parse_chapter(chapter)

    def _parse_chapter(self, html):
        m = re.compile(r'<h3>.+?">(.+?)</span>.+?</h3>\n(.+)', re.DOTALL).search(html)
        self.out.append(Tag.H3_OPEN)
        self.out.append(m.group(1))
        self.out.append(Tag.H3_CLOSE)

        m_intro = re.compile(r"([\s\S]*?)\n(?:<h4>|$)").search(m.group(2))
        if m.group(1) == "Opening Cinematic":
            self._parse_dialogue(m_intro.group(1))
        else:
            self._parse_narration(m_intro.group(1))

        for mission in re.compile(r"<h4>(?:(?!<h4>).)+", re.DOTALL).findall(m.group(2)):
            self._parse_subsection(mission)

    def _parse_subsection(self, html):
        m = re.compile(
            r'<h4>.*?"mw-headline".+?">(.+?)</span>.+?</h4>\n(?:<div .*?>.+</div>)*(.*)',
            re.DOTALL,
        ).search(html)

        m_title = re.compile('^(.+?)[:-] ?"?(.+?)"?$').search(m.group(1))
        title = (
            m.group(1)
            if m_title is None
            else m_title.group(1) + ": " + m_title.group(2)
        )
        self.out.append(Tag.H4_OPEN)
        self.out.append(title)
        self.out.append(Tag.H4_CLOSE)

        if (
            re.compile(
                r'Mission [\d\.]+: .+|Tutorial: "Boot Camp"|Cut Mission: .+'
            ).search(m.group(1))
            is not None
        ):
            self._parse_mission(m.group(2))
        elif m.group(1) == "Introduction Movie":
            self._parse_dialogue(m.group(2))
        elif (
            m.group(1) == "Opening"
            or m.group(1) == "Cinematic - Wasteland Patrol"
            or m.group(1) == "Cinematic - Norad II's Downfall"
        ):
            self._parse_narration(m.group(2))
        elif (
            m.group(1) == 'Cinematic: "The Dream"'
            or m.group(1) == 'Cinematic: "Battle on the Amerigo"'
            or m.group(1) == 'Cinematic: "The Warp"'
            or m.group(1) == 'Cinematic: "The Invasion of Aiur"'
            or m.group(1) == 'Cinematic: "The Ambush"'
        ):
            self._parse_dialogue(m.group(2))
        elif m.group(1) == "Cinematic - The Inauguration":
            self._parse_dialogue(m.group(2).replace("\n", " ", 1))
        elif m.group(1) == "Cinematic - Open Rebellion":
            self._parse_dialogue(m.group(2))
        elif m.group(1) == 'Cinematic: "UED Victory Report"':
            self._parse_dialogue(
                m.group(2).replace("\n", " ", 1).replace("<dd></dd>\n", "")
            )
        elif m.group(1) == 'Ending Cinematic: "The Ascension"':
            self._parse_dialogue(m.group(2).replace("<br/>By now", " By now"))
        elif (
            m.group(1) == 'Cinematic: "The Fall of Fenix"'
            or m.group(1) == 'Cinematic: "The Return to Aiur"'
            or m.group(1) == 'Cinematic: "The Death of the Overmind"'
            or m.group(1) == 'Cinematic: "Fury of the Xel\'Naga"'
        ):
            pass
        else:
            raise AssertionError("unreachable", m.group(1))
        return

    def _parse_mission(self, html: str):
        html = html.replace("During Mision", "During Mission")  # NOTE: fix typo
        self._parse_intro(html)
        self.out.extend([Tag.H5_OPEN, "Briefing", Tag.H5_CLOSE])
        self._parse_context(html)

        self._parse_briefing(html)
        self._parse_remains(html)

    def _parse_intro(self, html: str):
        m = re.compile(r"(<p>[\s\S]+</p>)\n<ul><li><i>Briefing").search(html)
        if m is None:
            return None

        for i, s in enumerate(
            re.compile(r"<p>([\s\S]+?)</p>").findall(
                re.compile("<a .+?>|</a>|\n").sub("", m.group(1))
            )
        ):
            if i != 0:
                self.out.append(Tag.LB_EXTRA)
            self.out.append(s)

    def _parse_context(self, html: str):
        m = re.compile(r"<p>((?:<i>.+</i><br/>\n)+)").search(html)
        if m is None:
            return None

        for i, s in enumerate(
            re.compile(r"<i>(.+)</i><br/>").findall(
                re.compile("<a .+?>|</a>").sub("", m.group(1))
            )
        ):
            if i != 0:
                self.out.append(Tag.LB)
            self.out.append(Tag.TT_OPEN)
            self.out.append(s)
            self.out.append(Tag.TT_CLOSE)

    def _parse_briefing(self, html: str):
        block = (
            re.compile(
                r"((?:<.+>)*?<[i|b]>.+?</[i|b]>: .+?\n[\s\S]*?</p>\n)(?:<ul><li>(?:<i>)?During Mission)?"
            )
            .search(html)
            .group(1)
        )
        self._parse_dialogue(block)

    def _parse_remains(self, html: str):
        m = re.compile(r"<ul><li>(?:<i>)?During Mission[\s\S]*").search(html)
        if m is None:
            return
        for block in re.compile(r"<ul>.+</ul>(?:(?!<ul>.+</ul>)[\s\S])+").findall(
            m.group()
        ):
            m = re.compile(
                r"<ul><li>(?:<i>)?(.+?)(?:</i>)?</li></ul>\n([\s\S]+)"
            ).search(block)

            self.out.append(Tag.H5_OPEN)
            self.out.append(m.group(1))
            self.out.append(Tag.H5_CLOSE)
            self._parse_dialogue(m.group(2))

    def _parse_dialogue(self, html: str):
        self.out.append(Tag.QUOTE_OPEN)
        for i, html_line in enumerate(
            re.compile("<a .+?>|</a>").sub("", html).splitlines()
        ):
            assert len(html_line) != 0
            if i != 0:
                self.out.append(Tag.LB_EXTRA)

            m = re.compile(
                r"^(?:<(?:p|/p|ul)>)*(?:<(?:li|i|b)+>)+?(\w.+?)(?:(?:</.+?>)*?:|:(?:</.+?>)*?) ?(.+?)$"
            ).search(html_line)
            if m is not None:
                name = m.group(1)
                line = m.group(2)
                assert name is not None
                assert line is not None

                self.out.append(Tag.B_OPEN)
                self.out.append(Tag.I_OPEN)
                self.out.append(name)
                self.out.append(Tag.I_CLOSE)
                self.out.append(Tag.B_CLOSE)
                self.out.append(": ")
                self._parse_misc(line)
            else:
                self._parse_misc(html_line)

        if self.out[len(self.out) - 1] == Tag.LB_EXTRA:
            _ = self.out.pop()

        self.out.append(Tag.QUOTE_CLOSE)

    def _parse_narration(self, html: str):
        for i, s in enumerate(
            re.compile(r"<p>([\s\S]+?)</p>").findall(
                re.compile("<a .+?>|</a>|\n|<i>|</i>").sub("", html)
            )
        ):
            if i != 0:
                self.out.append(Tag.LB_EXTRA)
            self.out.append(s)

    def _parse_misc(self, html: str):
        it = Iterator(html, {"\n"})
        while True:
            peek = it.peek()
            assert peek != "\n"
            if peek is None:
                break
            elif peek == "<":
                tag = []
                skip = False
                while True:
                    c = it.next()
                    assert c != "\n"
                    if c == " ":
                        skip = True
                    elif c == ">":
                        tag.append(c)
                        break
                    elif not skip:
                        tag.append(c)
                tag = Tag("".join(tag))
                match tag:
                    case Tag.I_OPEN | Tag.I_CLOSE | Tag.B_OPEN | Tag.B_CLOSE:
                        self.out.append(tag)
                    case (
                        Tag.BR
                        # | Tag.A_OPEN
                        # | Tag.A_CLOSE
                        | Tag.P_OPEN
                        | Tag.P_CLOSE
                        | Tag.UL_OPEN
                        | Tag.UL_CLOSE
                        | Tag.LI_OPEN
                        | Tag.LI_CLOSE
                        | Tag.DIV_OPEN
                        | Tag.DIV_CLOSE
                        | Tag.PRE_OPEN
                        | Tag.PRE_CLOSE
                        | Tag.IMG_OPEN
                        | Tag.IMG_CLOSE
                        | Tag.SPAN_OPEN
                        | Tag.SPAN_CLOSE
                        | Tag.SVG_OPEN
                        | Tag.SVG_CLOSE
                        | Tag.USE_OPEN
                        | Tag.USE_CLOSE
                        | Tag.DL_OPEN
                        | Tag.DL_CLOSE
                        | Tag.DD_OPEN
                        | Tag.DD_CLOSE
                    ):
                        pass
                    case _:
                        raise AssertionError("unreachable", tag)
            else:
                s = []
                while True:
                    peek = it.peek()
                    assert peek != "\n"
                    if peek is None or peek == "<":
                        break
                    s.append(it.next())
                self.out.append("".join(s))


class Latex:
    lb_extra = "\\\\[0.5em]\n"
    lb = "\\\\\n"

    def __init__(self):
        self.title = "StarCraft Campaign Quotations"
        self.author = "Blizzard Entertainment"
        self.font_size = 4
        self.out = []

    def stringify(self, elems: List[Union[Tag, str]]):
        self.out.append(f"\\documentclass[{self.font_size}pt]{{article}}\n")
        self.out.append("\\usepackage{{csquotes, geometry}}")
        self.out.append(f"\\author{{{self.author}}}\n")
        self.out.append("\\date{}\n")
        self.out.append(
            "\\geometry{a4paper, left=12mm, right=12mm, top=12mm, bottom=19.5mm, foot=7.5mm}\n"
        )
        self.out.append("\\begin{document}\n")

        for elem in elems:
            if isinstance(elem, str):
                self.out.append(elem)
                continue

            assert isinstance(elem, Tag)

            match elem:
                case Tag.H2_OPEN:
                    self.out.append("\n\\part*{")
                case Tag.H3_OPEN:
                    self.out.append("\n\\section{")
                case Tag.H4_OPEN:
                    self.out.append("\n\\subsection{")
                case Tag.H5_OPEN:
                    self.out.append("\n\\subsubsection*{")
                case Tag.QUOTE_OPEN:
                    self.out.append("\n\\begin{displayquote}\n")
                case Tag.QUOTE_CLOSE:
                    self.out.append("\n\\end{displayquote}\n")
                case Tag.TT_OPEN:
                    self.out.append("\\texttt{")
                case Tag.I_OPEN:
                    self.out.append("\\textit{")
                case Tag.B_OPEN:
                    self.out.append("\\textbf{")
                case Tag.TT_CLOSE | Tag.I_CLOSE | Tag.B_CLOSE:
                    self.out.append("}")
                case Tag.H2_CLOSE | Tag.H3_CLOSE | Tag.H4_CLOSE | Tag.H5_CLOSE:
                    self.out.append("}\n")
                case Tag.LB:
                    self.out.append(Latex.lb)
                case Tag.LB_EXTRA:
                    self.out.append(Latex.lb_extra)
                case Tag.BR:
                    raise AssertionError("unreachable", elem)

        self.out.append("\n\\end{document}\n")
        return "".join(self.out)


elems = Parser().sanitize_and_parse(RawHtml.get())
output = Latex().stringify(elems)

os.makedirs(out_dir, exist_ok=True)
with open(out_dir + "output.tex", "w") as f:
    f.write(output)
