# -*- coding: utf-8 -*-
"""Generate StudyFlow UI wireframes (draw.io source + SVG + PNG).

One structured description per page produces:
  * ui/StudyFlow_界面原型.drawio  (4 editable pages)
  * assets/UI-0x_*.svg            (vector export)
  * assets/UI-0x_*.png            (raster export, 2x supersampled)

Requires Python and Pillow only. Fonts: Microsoft YaHei (Windows).
"""
from pathlib import Path
from dataclasses import dataclass, field
import html
import math
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
UI = ROOT / "ui"
FONT_REG = Path("C:/Windows/Fonts/msyh.ttc")
FONT_BOLD = Path("C:/Windows/Fonts/msyhbd.ttc")

W, H, S = 1440, 1000, 2  # logical page size, supersampling factor

# palette
NAVY = "#12263f"
INK = "#22303f"
MUTED = "#5d6f82"
LINE = "#d7dfe9"
PAGE = "#f3f6fa"
CARD = "#ffffff"
SOFT = "#f8fafc"
BLUE = "#2f6fe4"
BLUE_BG = "#e9f1fe"
TEAL = "#0f8a7c"
TEAL_BG = "#e2f4f0"
AMBER = "#a86500"
AMBER_BG = "#fff3da"
RED = "#b3261e"
RED_BG = "#fdebe9"
PURPLE = "#6a4bb5"
PURPLE_BG = "#efeafc"
GRAY_BG = "#eef2f7"

_font_cache = {}


def font(size, bold=False):
    key = (size, bold)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(str(FONT_BOLD if bold else FONT_REG), int(size * S))
    return _font_cache[key]


def measure(text, size, bold=False):
    return font(size, bold).getlength(text) / S


@dataclass
class Node:
    kind: str
    x: float
    y: float
    w: float = 0
    h: float = 0
    fill: str = CARD
    stroke: str | None = None
    r: float = 0
    dash: bool = False
    sw: float = 1
    text: str = ""
    size: float = 13
    color: str = INK
    bold: bool = False
    align: str = "left"
    valign: str = "top"
    lh: float = 1.5
    lines: list = field(default_factory=list)
    pts: list = field(default_factory=list)
    opacity: float = 1


def wrap(text, size, maxw, bold=False):
    out = []
    for para in str(text).split("\n"):
        if para == "":
            out.append("")
            continue
        line = ""
        i = 0
        tokens = []
        while i < len(para):
            ch = para[i]
            if ch.isascii() and (ch.isalnum() or ch in "._-/:%"):
                j = i
                while j < len(para) and para[j].isascii() and (para[j].isalnum() or para[j] in "._-/:%"):
                    j += 1
                tokens.append(para[i:j])
                i = j
            else:
                tokens.append(ch)
                i += 1
        for tok in tokens:
            cand = line + tok
            if line and measure(cand, size, bold) > maxw:
                out.append(line)
                line = tok.lstrip()
            else:
                line = cand
        out.append(line)
    return out


class Page:
    def __init__(self, name, kicker, title, subtitle=""):
        self.name = name
        self.nodes = []
        self.overflow = []

    # primitives -----------------------------------------------------
    def rect(self, x, y, w, h, fill=CARD, stroke=None, r=0, dash=False, sw=1):
        self.nodes.append(Node("rect", x, y, w, h, fill, stroke, r, dash, sw))
        return Node("rect", x, y, w, h, fill, stroke, r, dash, sw)

    def line(self, x1, y1, x2, y2, color=LINE, width=1, dash=False):
        n = Node("line", min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
        n.pts = [(x1, y1), (x2, y2)]
        n.stroke, n.sw, n.dash = color, width, dash
        self.nodes.append(n)

    def text(self, x, y, w, h, text, size=13, color=INK, bold=False,
             align="left", valign="top", lh=1.5):
        n = Node("text", x, y, w, h, text=text, size=size, color=color, bold=bold,
                 align=align, valign=valign, lh=lh)
        n.lines = wrap(text, size, w, bold)
        need = len(n.lines) * size * lh
        if need > h + 1:
            self.overflow.append((text[:24], round(need, 1), h))
        self.nodes.append(n)

    def rich(self, x, y, segs, size=13, lh=1.5):
        """Single-line multi-colour text; segs = [(text, color, bold)]."""
        cx = x
        for s, c, b in segs:
            self.text(cx, y, measure(s, size, b) + 2, size * lh, s, size, c, b, lh=lh)
            cx += measure(s, size, b)

    def circle(self, cx, cy, r, fill, stroke=None):
        n = Node("circle", cx - r, cy - r, 2 * r, 2 * r, fill=fill, stroke=stroke)
        self.nodes.append(n)

    # composite helpers ---------------------------------------------
    def badge(self, x, y, text, fg, bg, size=11, bold=False, padx=8, h=None):
        h = h or size + 12
        w = measure(text, size, bold) + padx * 2
        self.rect(x, y, w, h, bg, r=h / 2)
        self.text(x, y, w, h, text, size, fg, bold, "center", "middle", 1.0)
        return w

    def chip(self, x, y, text, fg=MUTED, bg=GRAY_BG, size=11):
        return self.badge(x, y, text, fg, bg, size, h=size + 12)

    def card(self, x, y, w, h, radius=10):
        self.rect(x, y, w, h, CARD, LINE, r=radius, sw=1)

    def topbar(self, active="作业", manager=True):
        self.rect(0, 0, W, 56, NAVY)
        self.rect(24, 16, 24, 24, BLUE, r=6)
        self.text(58, 0, 150, 56, "StudyFlow 课办", 16, "#ffffff", True, "left", "middle", 1.0)
        nav = [("作业", 214), ("任务", 268), ("排程", 326), ("交付检查", 384)]
        for label, nx in nav:
            nw = measure(label, 13.5) + 24
            if label == active:
                self.rect(nx - 12, 14, nw, 28, "#24476f", r=8)
                self.text(nx - 12, 14, nw, 28, label, 13.5, "#ffffff", True, "center", "middle", 1.0)
            else:
                self.text(nx - 12, 14, nw, 28, label, 13.5, "#c3d3e6", False, "center", "middle", 1.0)
        self.rect(1078, 16, 180, 26, "#1c3a5f", r=13)
        self.text(1078, 16, 180, 26, "第 24 组 · 软件工程", 11.5, "#d8e6f5", False, "center", "middle", 1.0)
        role = "负责人" if manager else "成员"
        self.text(1266, 0, 92, 56, "董泽福 · " + role, 12, "#e8eef6", False, "right", "middle", 1.0)
        self.circle(1388, 28, 15, "#3f6fa8", "#ffffff")
        self.text(1373, 13, 30, 30, "董", 13, "#ffffff", True, "center", "middle", 1.0)

    def kicker(self, text, y=74, x=24):
        self.text(x, y, 700, 18, text, 11.5, BLUE, True, lh=1.2)

    def h1(self, text, y=94, x=24, size=24):
        self.text(x, y, 900, 34, text, size, NAVY, True, lh=1.2)

    def footer(self, text):
        self.line(24, 962, 1416, 962, LINE)
        self.text(24, 968, 1360, 20, text, 11, MUTED, lh=1.2)

    # render ---------------------------------------------------------
    def render(self):
        ASSETS.mkdir(exist_ok=True)
        png = Image.new("RGB", (W * S, H * S), PAGE)
        d = ImageDraw.Draw(png)
        svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
               '<g font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif">']

        def dash_tuple(n):
            return [int(4 * S), int(4 * S)] if n.dash else None

        for n in self.nodes:
            if n.kind == "rect":
                x, y, w, h = [v * S for v in (n.x, n.y, n.w, n.h)]
                r = n.r * S
                if n.fill != "none":
                    d.rounded_rectangle((x, y, x + w, y + h), radius=r, fill=n.fill,
                                        outline=n.stroke, width=max(1, int(n.sw * S)) if n.stroke else 0)
                elif n.stroke:
                    d.rounded_rectangle((x, y, x + w, y + h), radius=r, outline=n.stroke,
                                        width=max(1, int(n.sw * S)))
                da = ' stroke-dasharray="6 5"' if n.dash else ""
                stroke = f' stroke="{n.stroke}" stroke-width="{n.sw}"' if n.stroke else ""
                svg.append(f'<rect x="{n.x}" y="{n.y}" width="{n.w}" height="{n.h}" rx="{n.r}" ry="{n.r}" fill="{n.fill}"{stroke}{da}/>')
            elif n.kind == "line":
                (x1, y1), (x2, y2) = n.pts
                da = ' stroke-dasharray="5 4"' if n.dash else ""
                d.line((x1 * S, y1 * S, x2 * S, y2 * S), fill=n.stroke, width=max(1, int(n.sw * S)))
                svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{n.stroke}" stroke-width="{n.sw}"{da}/>')
            elif n.kind == "circle":
                x, y, w, h = n.x * S, n.y * S, n.w * S, n.h * S
                d.ellipse((x, y, x + w, y + h), fill=n.fill, outline=n.stroke, width=2)
                stroke = f' stroke="{n.stroke}" stroke-width="2"' if n.stroke else ""
                svg.append(f'<circle cx="{n.x + n.w / 2}" cy="{n.y + n.h / 2}" r="{n.w / 2}" fill="{n.fill}"{stroke}/>')
            elif n.kind == "text":
                f = font(n.size, n.bold)
                lh = n.size * n.lh
                total = len(n.lines) * lh
                if n.valign == "middle":
                    top = n.y + (n.h - total) / 2
                elif n.valign == "bottom":
                    top = n.y + n.h - total
                else:
                    top = n.y
                for i, line in enumerate(n.lines):
                    if not line:
                        continue
                    tw = measure(line, n.size, n.bold)
                    if n.align == "center":
                        sx = n.x + (n.w - tw) / 2
                        anchor = "middle"
                        svg_x = n.x + n.w / 2
                    elif n.align == "right":
                        sx = n.x + n.w - tw
                        anchor = "end"
                        svg_x = n.x + n.w
                    else:
                        sx = n.x
                        anchor = "start"
                        svg_x = n.x
                    baseline = top + i * lh + n.size * 0.82
                    d.text((sx * S, (top + i * lh) * S), line, font=f, fill=n.color)
                    svg.append(f'<text x="{svg_x}" y="{baseline}" text-anchor="{anchor}" font-size="{n.size}" '
                               f'fill="{n.color}" font-weight="{700 if n.bold else 400}">{html.escape(line)}</text>')
        svg.append('</g></svg>')
        out = png.resize((W, H), Image.LANCZOS)
        out.save(ASSETS / f"{self.name}.png", optimize=True)
        (ASSETS / f"{self.name}.svg").write_text("\n".join(svg), encoding="utf-8")
        if self.overflow:
            print("[overflow]", self.name, self.overflow)

    def drawio(self, root):
        diagram = ET.SubElement(root, "diagram", {"id": self.name, "name": self.name})
        model = ET.SubElement(diagram, "mxGraphModel", {
            "dx": "1600", "dy": "1200", "grid": "1", "gridSize": "10", "page": "1",
            "pageScale": "1", "pageWidth": str(W), "pageHeight": str(H), "math": "0", "shadow": "0"})
        cells = ET.SubElement(model, "root")
        ET.SubElement(cells, "mxCell", {"id": "0"})
        ET.SubElement(cells, "mxCell", {"id": "1", "parent": "0"})
        for i, n in enumerate(self.nodes):
            if n.kind == "line":
                (x1, y1), (x2, y2) = n.pts
                style = ("endArrow=none;html=1;rounded=0;strokeColor=%s;strokeWidth=%s;%s"
                         % (n.stroke or LINE, n.sw, "dashed=1;" if n.dash else ""))
                cell = ET.SubElement(cells, "mxCell", {"id": f"e{i}", "value": "", "style": style,
                                                       "edge": "1", "parent": "1"})
                geo = ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
                ET.SubElement(geo, "mxPoint", {"x": str(x1), "y": str(y1), "as": "sourcePoint"})
                ET.SubElement(geo, "mxPoint", {"x": str(x2), "y": str(y2), "as": "targetPoint"})
                continue
            if n.kind == "circle":
                style = (f"ellipse;whiteSpace=wrap;html=1;fillColor={n.fill};"
                         f"strokeColor={n.stroke or n.fill};fontFamily=Microsoft YaHei;")
            elif n.kind == "text":
                style = (f"text;html=1;whiteSpace=wrap;strokeColor=none;fillColor=none;align={n.align};"
                         f"verticalAlign={n.valign};fontFamily=Microsoft YaHei;fontSize={n.size};"
                         f"fontColor={n.color};fontStyle={1 if n.bold else 0};")
            else:
                style = (f"rounded={1 if n.r else 0};arcSize={int(min(50, n.r / max(n.h, 1) * 100))};html=1;"
                         f"whiteSpace=wrap;fillColor={n.fill};strokeColor={n.stroke or 'none'};"
                         f"fontFamily=Microsoft YaHei;fontSize={n.size};fontColor={n.color};"
                         f"{'dashed=1;' if n.dash else ''}align={n.align};verticalAlign={n.valign};")
            value = html.escape(n.text).replace("\n", "<br>") if n.text else ""
            cell = ET.SubElement(cells, "mxCell", {"id": f"n{i}", "value": value, "style": style,
                                                   "vertex": "1", "parent": "1"})
            ET.SubElement(cell, "mxGeometry", {"x": str(round(n.x, 1)), "y": str(round(n.y, 1)),
                                              "width": str(round(n.w, 1)), "height": str(round(n.h, 1)),
                                              "as": "geometry"})


# ---------------------------------------------------------------------------
# shared pieces
# ---------------------------------------------------------------------------
def page_header(u, kicker, title, chips):
    u.topbar(active={"UI-01": "作业", "UI-02": "任务", "UI-03": "排程", "UI-04": "交付检查"}[kicker[:5]])
    u.kicker(kicker)
    u.h1(title)
    x = 1416
    for text, fg, bg in reversed(chips):
        w = measure(text, 11.5) + 20
        x -= w
        u.badge(x, 100, text, fg, bg, 11.5, True, padx=10, h=24)
        x -= 10


def ui_01(u):
    page_header(u, "UI-01｜作业录入与要求确认", "作业录入与确认要求", [
        ("状态：待确认要求", AMBER, AMBER_BG),
        ("作业：第三次小组作业", MUTED, GRAY_BG),
    ])
    u.text(24, 132, 900, 18, "课程：软件工程（2026 秋） · 空间：第 24 组 · 最后一次编辑 10-19 21:14",
           11.5, MUTED, lh=1.2)

    # ---------------- left: source text ----------------
    u.card(24, 158, 470, 782)
    u.text(44, 174, 300, 24, "作业原文", 15, NAVY, True, lh=1.2)
    u.text(314, 176, 160, 20, "原文版本 v1", 11, MUTED, align="right", lh=1.2)
    u.line(44, 206, 474, 206, LINE)
    u.badge(44, 218, "粘贴文本（P0）", BLUE, BLUE_BG, 11, True)
    u.badge(150, 218, "PDF 导入 · P1 首版不启用", MUTED, GRAY_BG, 11)
    u.text(44, 246, 420, 18, "直接粘贴课程平台通知，系统保留原文与版本，不依赖学校接口。", 11, MUTED, lh=1.2)

    u.rect(44, 272, 430, 548, "#fbfcfe", "#e3e9f1", r=6)
    tx = 58
    ty = 286
    lh = 22
    lines = [
        [("课程：软件工程（2026 秋） 第三次小组作业", INK, True)],
        [("题目：校园学习行为调研与改进方案", INK, False)],
        [("", INK, False)],
        [("要求：", INK, True)],
        [("1. 每组 3–4 人，提交一份 ", INK, False), ("PDF 报告", BLUE, True),
         ("，正文不少于 ", INK, False), ("3000 字", BLUE, True), ("；", INK, False)],
        [("报告需包含调研方法、数据分析、问题诊断与改进建议。", INK, False)],
        [("2. 报告提交截止：", INK, False), ("第 8 周周日 23:59", AMBER, True),
         ("（通知未给出具体日期）。", INK, False)],
        [("3. 每组成员需在课堂展示 ", INK, False), ("8–10 分钟", BLUE, True), ("，并提交 ", INK, False)],
        [("10 页以内的幻灯片。", BLUE, True)],
        [("4. 提交材料包括：报告 PDF、展示幻灯片、小组分工说明", INK, False)],
        [("（含每人贡献比例）。", INK, False)],
        [("5. 引用格式采用 GB/T 7714；查重率不得高于 20%。", INK, False)],
        [("6. 迟交每天扣 10%，超过 3 天不予受理。", INK, False)],
        [("", INK, False)],
        [("7. 评分构成：报告 60%，课堂展示 30%，", INK, False)],
        [("小组协作与分工 10%。", INK, False)],
        [("8. 请在课程平台“作业 3”处提交；逾期按第 6 条处理。", INK, False)],
        [("9. 课堂展示顺序由抽签决定，展示当天请全员到场。", INK, False)],
        [("10. 如需延期，须在第 8 周前向任课教师书面申请。", INK, False)],
    ]
    for segs in lines:
        u.rich(tx, ty, segs, 12.5, lh=1.55)
        ty += lh
    u.line(44, 838, 474, 838, LINE)
    u.badge(44, 850, "业务数据", PURPLE, PURPLE_BG, 10.5)
    u.text(102, 849, 360, 40,
           "原文中的命令性文字只作业务内容，不会扩大系统或 AI 的权限；保存与修改均记录操作者与版本。",
           10.5, MUTED, lh=1.35)
    u.rect(44, 892, 430, 34, CARD, LINE, r=8)
    u.text(56, 892, 340, 34, "原文 10 条 · 抽取候选 7 项 · 来源已定位 7 项", 10.8, MUTED, valign="middle", lh=1.0)
    u.text(340, 892, 122, 34, "滚动查看全文 ↓", 11, BLUE, align="right", valign="middle", lh=1.0)

    # ---------------- right: extracted requirements ----------------
    u.card(514, 158, 902, 782)
    u.text(534, 174, 260, 24, "抽取候选要求", 15, NAVY, True, lh=1.2)
    u.text(770, 176, 300, 22, "已确认 5 · 待确认 2 · 共 7", 11.5, MUTED, align="right", lh=1.2)
    # legend
    for i, (label, color) in enumerate([("明确要求", TEAL), ("AI 建议", BLUE), ("人工补充 / 修改", PURPLE)]):
        lx = 534 + i * 130
        u.circle(lx + 4, 218, 4, color)
        u.text(lx + 14, 208, 120, 20, label, 11, MUTED, lh=1.2)
    u.text(1050, 208, 346, 20, "每项均保留原文位置；确认前不进入任务与排程。", 11, MUTED, align="right", lh=1.2)

    cols = [("要求内容", 534, 344), ("类型", 884, 64), ("原文来源", 952, 130),
            ("确认状态", 1086, 150), ("操作", 1244, 152)]
    u.rect(534, 236, 862, 34, "#f1f5fa", r=6)
    for name, cx, cw in cols:
        u.text(cx, 236, cw, 34, name, 11.5, MUTED, True, valign="middle", lh=1.0)

    rows = [
        ("提交一份 PDF 报告，正文不少于 3000 字", "交付物", "第 1 条 · 第 1 句", ("已确认", TEAL, TEAL_BG), "定位原文"),
        ("报告提交截止：第 8 周周日 23:59", "日期", "第 1 条 · 第 2 句", ("待确认 · 缺具体日期", AMBER, AMBER_BG), "补全字段"),
        ("课堂展示 8–10 分钟", "交付物", "第 1 条 · 第 3 句", ("已确认", TEAL, TEAL_BG), "定位原文"),
        ("提交展示幻灯片，10 页以内", "交付物", "第 1 条 · 第 3 句", ("已确认", TEAL, TEAL_BG), "定位原文"),
        ("小组分工说明（含每人贡献比例）", "交付物", "第 1 条 · 第 4 句", ("已确认", TEAL, TEAL_BG), "定位原文"),
        ("调研方法、数据分析、问题诊断与改进建议", "内容要求", "第 1 条 · 第 1 句", ("AI 建议 · 已人工修改", PURPLE, PURPLE_BG), "查看修改"),
        ("引用格式 GB/T 7714；查重率 ≤ 20%", "格式约束", "第 1 条 · 第 5 句", ("已确认", TEAL, TEAL_BG), "定位原文"),
    ]
    y = 276
    for i, (txt, typ, src, status, action) in enumerate(rows):
        if i % 2 == 1:
            u.rect(534, y, 862, 64, SOFT)
        u.line(534, y + 64, 1396, y + 64, "#e8eef5")
        u.text(542, y + 8, 334, 48, txt, 12.5, INK, lh=1.35)
        u.text(884, y, 64, 64, typ, 11.5, MUTED, valign="middle", lh=1.2)
        u.text(952, y, 130, 64, src, 11.5, MUTED, valign="middle", lh=1.2)
        label, fg, bg = status
        u.badge(1086, y + 20, label, fg, bg, 10.5, True, padx=8, h=24)
        u.text(1244, y, 152, 64, action + " ↗", 11.5, BLUE, valign="middle", lh=1.2)
        if txt.startswith("报告提交截止"):
            u.rect(1086, y + 48, 150, 12, CARD)
        y += 64

    # exception / pending panel
    u.rect(534, 736, 862, 92, AMBER_BG, "#f0cf92", r=8)
    u.text(550, 744, 150, 20, "待确认与冲突提示", 11.5, AMBER, True, lh=1.2)
    u.text(550, 766, 830, 56,
           "① R2 只有“第 8 周周日 23:59”，系统无法确定具体日期，未生成“官方截止日期”，需人工补全；"
           "② R6 为 AI 补充的内容要求，原文未单列，已人工修改并待确认；"
           "③ 第 1 条与第 5 条都涉及提交材料，抽取结果已合并，请确认是否遗漏。",
           11, "#6b4a12", lh=1.45)

    # action bar
    u.rect(534, 842, 862, 78, "#ffffff", LINE, r=8)
    u.text(550, 852, 380, 20, "确认后生成正式要求集合 v2，并记录确认人、时间与 AI 版本。", 11, MUTED, lh=1.3)
    u.text(550, 878, 420, 30, "未确认项不会进入任务拆解；已确认要求被引用后修改，会使相关计划草案失效。", 10.5, MUTED, lh=1.3)
    u.badge(1000, 858, "重新抽取", BLUE, BLUE_BG, 11.5, True, padx=12, h=32)
    u.badge(1104, 858, "保存草稿", MUTED, GRAY_BG, 11.5, True, padx=12, h=32)
    u.rect(1216, 856, 162, 36, BLUE, r=8)
    u.text(1216, 856, 162, 36, "确认所选 2 项", 12.5, "#ffffff", True, "center", "middle", 1.0)

    u.footer("UI-01 对应 UC-03；异常状态覆盖：来源缺失、日期待确认、AI 建议与人工补充区分、确认前不得进入排程。")


def ui_02(u):
    page_header(u, "UI-02｜任务与协作看板", "任务与协作看板", [
        ("计划版本 v3 · 已确认 10-20 09:12", TEAL, TEAL_BG),
        ("作业：第三次小组作业", MUTED, GRAY_BG),
    ])
    # toolbar
    u.rect(24, 138, 1016, 44, CARD, LINE, r=8)
    u.text(40, 138, 460, 44, "负责人：全部成员 ▼     要求：全部 ▼     仅看阻塞 □", 11.5, MUTED, valign="middle", lh=1.0)
    u.text(520, 138, 380, 44, "任务 10 · 进行中 2 · 待验收 1 · 阻塞 1", 11.5, MUTED, align="right", valign="middle", lh=1.0)
    u.badge(916, 145, "新建任务", BLUE, BLUE_BG, 11.5, True, padx=12, h=30)

    cols = [
        ("待开始", "3", MUTED),
        ("进行中", "2", BLUE),
        ("待验收", "1", AMBER),
        ("已完成", "4", TEAL),
    ]
    colx = [24, 281, 538, 795]
    for (name, count, color), cx in zip(cols, colx):
        u.rect(cx, 198, 245, 748, "#eef3f9", None, r=10)
        u.rect(cx, 198, 245, 44, "#e3eaf3", None, r=10)
        u.rect(cx, 222, 245, 20, "#e3eaf3")
        u.circle(cx + 18, 220, 5, color)
        u.text(cx + 30, 198, 150, 44, name, 13.5, INK, True, valign="middle", lh=1.0)
        u.text(cx + 190, 198, 40, 44, count, 13, MUTED, True, align="right", valign="middle", lh=1.0)

    def task_card(x, y, w, title, owner, hours, pre, req, extra=None, h=132):
        u.rect(x, y, w, h, CARD, "#dde5ef", r=8)
        u.text(x + 12, y + 10, w - 24, 36, title, 12.5, INK, True, lh=1.35)
        u.text(x + 12, y + 50, w - 24, 16, "负责人：" + owner, 10.5, MUTED, lh=1.2)
        u.text(x + 12, y + 68, w - 24, 16, "预计 " + hours + " · 前置 " + pre, 10.5, MUTED, lh=1.2)
        u.text(x + 12, y + 86, w - 24, 16, "覆盖要求 " + req, 10.5, MUTED, lh=1.2)
        if extra:
            label, fg, bg = extra
            u.badge(x + 12, y + h - 32, label, fg, bg, 10, True, padx=7, h=22)

    # 待开始
    task_card(36, 254, 221, "T5 演示脚本撰写", "李一芃", "2h", "T4", "R6", ("阻塞：等待报告定稿", AMBER, AMBER_BG))
    task_card(36, 396, 221, "T6 幻灯片制作", "雍致鸣", "3h", "T5", "R6")
    task_card(36, 538, 221, "T7 提交前完整性检查", "董泽福", "1h", "T6", "R7、R8")
    u.text(36, 676, 221, 34, "点击卡片查看职责与依赖详情；普通成员不能修改他人任务。", 10, MUTED, lh=1.3)

    # 进行中
    task_card(293, 254, 221, "T2 实验结果整理", "李一芃", "4h", "T1", "R2", ("计划待重排", AMBER, AMBER_BG), 132)
    task_card(293, 396, 221, "T3 报告正文撰写", "雍致鸣", "6h", "T2", "R1、R2")
    u.rect(293, 538, 221, 74, AMBER_BG, "#f0cf92", r=8)
    u.text(305, 546, 200, 58, "T2 预计工时由 3h 改为 4h，当前计划待重排；旧安排保留历史，不静默移动。",
           10, "#6b4a12", lh=1.35)

    # 待验收
    u.rect(550, 254, 221, 250, CARD, "#dde5ef", r=8)
    u.text(562, 264, 197, 36, "T1 调研数据收集", 12.5, INK, True, lh=1.35)
    u.text(562, 302, 197, 16, "负责人：李一芃 · 预计 3h", 10.5, MUTED, lh=1.2)
    u.text(562, 320, 197, 16, "前置：— · 覆盖要求 R2", 10.5, MUTED, lh=1.2)
    u.rect(562, 344, 197, 56, SOFT, "#dfe7f0", r=6)
    u.text(572, 350, 180, 44, "成果证据\n数据表.xlsx  ↗（10-20 21:40 提交）", 10, MUTED, lh=1.3)
    u.rect(562, 414, 92, 30, TEAL, r=6)
    u.text(562, 414, 92, 30, "通过验收", 10.5, "#ffffff", True, "center", "middle", 1.0)
    u.rect(662, 414, 92, 30, CARD, "#c9d4e2", r=6)
    u.text(662, 414, 92, 30, "退回修改", 10.5, RED, True, "center", "middle", 1.0)
    u.text(562, 456, 197, 40, "验收退回 → 任务回到“进行中”，并记录退回原因；已完成的证据仍可查看。",
           9.8, MUTED, lh=1.3)

    # 已完成
    u.rect(807, 254, 221, 120, CARD, "#dde5ef", r=8)
    u.text(819, 264, 197, 18, "T0 要求确认", 11.5, MUTED, True, lh=1.2)
    u.text(819, 286, 197, 18, "董泽福 · 10-18 完成", 10, MUTED, lh=1.2)
    u.text(819, 310, 197, 18, "T4 问卷设计", 11.5, MUTED, True, lh=1.2)
    u.text(819, 332, 197, 18, "董泽福 · 10-19 完成", 10, MUTED, lh=1.2)
    u.text(819, 356, 197, 18, "另有 2 项已完成 · 查看全部", 10, BLUE, lh=1.2)
    u.text(807, 390, 221, 34, "已完成任务重新打开须记录理由，并重查下游阻塞与证据有效性。", 10, MUTED, lh=1.3)

    # drawer
    u.rect(1062, 138, 354, 808, CARD, LINE, r=10)
    u.rect(1062, 138, 354, 50, "#f1f5fa", None, r=10)
    u.rect(1062, 168, 354, 20, "#f1f5fa")
    u.text(1078, 138, 300, 50, "任务详情 · T1 调研数据收集", 13, NAVY, True, valign="middle", lh=1.2)
    u.text(1382, 138, 26, 50, "×", 18, MUTED, align="right", valign="middle", lh=1.0)

    steps = ["待开始", "进行中", "待验收", "已完成"]
    sx = 1082
    for i, s in enumerate(steps):
        active = i <= 2
        u.circle(sx + 7, 214, 7, TEAL if active else "#dfe6ee")
        if i < 3:
            u.line(sx + 14, 214, sx + 66, 214, TEAL if i < 2 else "#dfe6ee", 2)
        u.text(sx - 6, 226, 64, 16, s, 9.5, TEAL if active else MUTED, active, lh=1.2)
        sx += 78

    info = [("负责人", "李一芃（普通成员，仅可更新本人任务）"), ("预计工时", "3h · 由负责人确认"),
            ("前置任务", "无"), ("覆盖要求", "R2 调研数据与数据分析"),
            ("计划安排", "周三 19:00–21:00 · 当前计划 v3")]
    y = 256
    for k, v in info:
        u.text(1078, y, 90, 18, k, 10.5, MUTED, lh=1.2)
        u.text(1160, y, 240, 34, v, 10.8, INK, lh=1.35)
        y += 42
    u.line(1078, 466, 1400, 466, LINE)
    u.text(1078, 476, 200, 20, "成果与验收", 12, NAVY, True, lh=1.2)
    u.rect(1078, 502, 306, 62, SOFT, "#dfe7f0", r=6)
    u.text(1090, 510, 282, 48, "证据链接：数据表.xlsx ↗\n提交人 李一芃 · 10-20 21:40", 10.5, MUTED, lh=1.4)
    u.text(1078, 574, 120, 20, "验收意见", 10.5, MUTED, lh=1.2)
    u.rect(1078, 596, 306, 48, "#ffffff", "#cfd9e5", r=6)
    u.text(1090, 604, 282, 34, "（退回时必填）说明需补充的数据范围或来源…", 10.2, "#9aa9b8", lh=1.35)
    u.rect(1078, 656, 146, 34, TEAL, r=7)
    u.text(1078, 656, 146, 34, "通过验收", 11.5, "#ffffff", True, "center", "middle", 1.0)
    u.rect(1234, 656, 150, 34, CARD, "#c9d4e2", r=7)
    u.text(1234, 656, 150, 34, "退回修改", 11.5, RED, True, "center", "middle", 1.0)
    u.line(1078, 706, 1400, 706, LINE)
    u.text(1078, 716, 200, 20, "状态历史", 12, NAVY, True, lh=1.2)
    hist = [("10-20 21:40", "李一芃 提交成果 → 待验收"),
            ("10-19 18:05", "开始任务 → 进行中"),
            ("10-18 15:20", "负责人分配任务 → 待开始")]
    y = 744
    for t, s in hist:
        u.circle(1086, y + 7, 4, "#b9c6d6")
        u.text(1098, y, 90, 18, t, 9.8, MUTED, lh=1.2)
        u.text(1168, y, 232, 18, s, 10.2, INK, lh=1.2)
        y += 30
    u.rect(1078, 846, 306, 84, AMBER_BG, "#f0cf92", r=8)
    u.text(1090, 854, 282, 68,
           "当前角色：负责人。可验收他人成果；普通成员只能更新本人任务字段，"
           "越权请求由服务端按当前空间权限拒绝，不依赖前端隐藏按钮。", 10, "#6b4a12", lh=1.35)

    u.footer("UI-02 对应 UC-04、UC-10；状态机：待开始 → 进行中 → 待验收 → 已完成，退回回到进行中；阻塞与“待重排”均为独立标记。")


def ui_03(u):
    page_header(u, "UI-03｜排程与计划确认", "排程与计划确认", [
        ("草案 D-43-02 · 待确认", AMBER, AMBER_BG),
        ("依据：任务集 v5 / 可用时段 v2 / 当前计划 v3", MUTED, GRAY_BG),
    ])
    # stale banner
    u.rect(24, 138, 1392, 52, AMBER_BG, "#f0cf92", r=8)
    u.text(40, 146, 1120, 36,
           "草案已过期：成员可用时段于 10-20 14:02 更新，当前草案基于 v1 生成，不能直接确认。请重新计算后再确认。",
           11.8, "#6b4a12", True, valign="middle", lh=1.3)
    u.badge(1236, 148, "重新计算", AMBER, "#ffe4b0", 11.5, True, padx=12, h=30)

    # left: availability
    u.card(24, 206, 350, 736)
    u.text(44, 222, 300, 24, "成员可用时段（本周）", 13.5, NAVY, True, lh=1.2)
    u.text(44, 250, 310, 40, "本人维护本人的窗口；其他成员只看到排程所需的忙闲信息。", 10.5, MUTED, lh=1.35)
    u.line(44, 296, 354, 296, LINE)
    people = [
        ("董泽福", ["周三 19:00–21:00", "周五 20:00–22:00"], TEAL_BG),
        ("雍致鸣", ["周三 19:30–22:00", "周六 09:00–12:00"], BLUE_BG),
        ("李一芃", ["周四 19:00–21:00", "周六 10:00–12:00（已更新）"], AMBER_BG),
    ]
    y = 310
    for name, slots, bg in people:
        u.circle(52, y + 12, 12, bg, "#c9d6e4")
        u.text(44, y + 32, 60, 16, name, 11, INK, True, "center", lh=1.2)
        for j, s in enumerate(slots):
            u.text(118, y + j * 22, 226, 20, s, 10.5, INK, lh=1.2)
        y += 92
    u.rect(44, 596, 310, 116, SOFT, "#dfe7f0", r=8)
    u.text(56, 604, 286, 24, "其他空间的占用", 10.8, NAVY, True, lh=1.2)
    u.text(56, 628, 286, 76,
           "周四 19:00–20:00 显示为“不可用”，不展示课程名、任务名或地点；"
           "代理与接口同样只返回忙闲信息。", 10, MUTED, lh=1.35)
    u.rect(44, 726, 310, 34, CARD, "#c9d6e4", r=7)
    u.text(44, 726, 310, 34, "编辑我的可用时段", 11.5, BLUE, True, "center", "middle", 1.0)
    u.text(44, 772, 310, 40, "可用时段变化后，受影响安排标记“待重排”，旧计划保留历史，不静默移动。",
           10, MUTED, lh=1.35)
    u.line(44, 820, 354, 820, LINE)
    u.text(44, 830, 310, 90,
           "硬约束：窗口内安排、不与其他已确认占用重叠、前置结束不晚于后继开始、不越过截止日期。"
           "相邻区间可首尾相接（按 [start, end) 判断）。", 10, MUTED, lh=1.4)
    u.text(44, 916, 310, 16, "“已更新”仅表示输入变化，不代表计划已调整。", 9.5, MUTED, lh=1.2)

    # center: week grid
    u.card(390, 206, 630, 736)
    u.text(410, 218, 300, 24, "本周排程草案", 13.5, NAVY, True, lh=1.2)
    u.text(410, 244, 590, 20, "任务时间块为草案，未占用正式时间；确认后才生成正式版本。", 10.5, MUTED, lh=1.2)
    days = ["一", "二", "三", "四", "五", "六", "日"]
    gx, gy = 440, 300
    dayw, rowh = 82, 40
    hours = list(range(9, 23))
    for i, d in enumerate(days):
        cx = gx + i * dayw
        u.text(cx, gy - 24, dayw, 18, "周" + d, 10.5, MUTED, True, "center", lh=1.2)
        u.line(cx, gy, cx, gy + len(hours) * rowh, "#e4eaf3")
    u.line(gx + 7 * dayw, gy, gx + 7 * dayw, gy + len(hours) * rowh, "#e4eaf3")
    for k, hh in enumerate(hours):
        yy = gy + k * rowh
        u.line(gx, yy, gx + 7 * dayw, yy, "#eef3f8")
        u.text(390, yy - 8, 42, 16, f"{hh:02d}:00", 9.2, MUTED, align="right", lh=1.2)

    def block(day, start, end, lines, fg, bg, border, conflict=False):
        x = gx + day * dayw + 3
        y = gy + (start - 9) * rowh + 2
        h = (end - start) * rowh - 4
        u.rect(x, y, dayw - 6, h, bg, border, r=5)
        if conflict:
            u.rect(x + 2, y + 2, dayw - 10, rowh - 8, "none", RED, r=4, dash=True)
        ty = y + 4
        for s, color, bold in lines:
            u.text(x + 4, ty, dayw - 14, 16, s, 8.6, color, bold, lh=1.25)
            ty += 15
        return y

    block(0, 19, 21, [("T3 正文初稿", INK, True), ("雍致鸣 · 2h", MUTED, False)], INK, BLUE_BG, BLUE)
    block(2, 19, 21, [("T2 数据整理", INK, True), ("李一芃 · 2h", MUTED, False)], INK, TEAL_BG, TEAL)
    block(3, 19, 21, [("T4 问卷修订", INK, True), ("董泽福 · 3h", MUTED, False)], INK, RED_BG, RED, True)
    block(4, 20, 22, [("T6 幻灯片", INK, True), ("李一芃 · 3h", MUTED, False)], INK, BLUE_BG, BLUE)
    block(5, 9, 12, [("T5 演示脚本", INK, True), ("雍致鸣 · 2h", MUTED, False)], INK, BLUE_BG, BLUE)
    block(5, 14, 16, [("T7 交付检查", INK, True), ("董泽福 · 1h", MUTED, False)], INK, BLUE_BG, BLUE)

    block(5, 16, 17, [("T8 展示排练", INK, True), ("全员 · 1h", MUTED, False)], INK, BLUE_BG, BLUE)

    u.rect(410, 846, 590, 52, AMBER_BG, "#f0cf92", r=8)
    u.text(424, 854, 562, 38,
           "容量缺口 3h：本周需 17h、可用 14h；至少 1 个任务无法安排。"
           "系统不放宽硬约束，也不伪造可行计划。", 10.3, "#6b4a12", lh=1.35)

    # right: diff & confirm
    u.card(1038, 206, 378, 736)
    u.text(1058, 220, 340, 24, "调整前后差异", 13.5, NAVY, True, lh=1.2)
    u.text(1058, 246, 340, 20, "与当前计划 v3 对比 · 变更 3 项", 10.5, MUTED, lh=1.2)
    diffs = [
        ("T6 幻灯片制作", "周四 19:00–21:00 → 周五 20:00–22:00", "原因：可用时段更新", AMBER, AMBER_BG),
        ("T2 实验数据整理", "3h → 2h，时间块缩短 1h", "原因：负责人修改预计工时", BLUE, BLUE_BG),
        ("T8 展示排练", "新增草案时间块 周六 16:00–17:00", "原因：依赖 T5 完成", TEAL, TEAL_BG),
    ]
    y = 278
    for title, change, reason, fg, bg in diffs:
        u.rect(1058, y, 338, 88, SOFT, "#e3eaf3", r=8)
        u.rect(1058, y, 4, 88, fg)
        u.text(1072, y + 8, 310, 20, title, 11.5, INK, True, lh=1.2)
        u.text(1072, y + 30, 310, 20, change, 10.3, INK, lh=1.2)
        u.text(1072, y + 52, 310, 18, reason, 9.8, MUTED, lh=1.2)
        y += 100

    u.text(1058, 588, 340, 20, "未解决冲突（2）", 12, RED, True, lh=1.2)
    u.rect(1058, 612, 338, 96, RED_BG, "#f0b8b3", r=8)
    u.text(1072, 620, 312, 82,
           "① 周四 19:00–21:00 T4 与个人作业占用重叠；\n"
           "② 容量缺口 3h，T8 无法安排。\n"
           "需调整分工、工时或时间窗口后重新排程。",
           10.2, "#7a201a", lh=1.4)
    u.text(1058, 720, 340, 20, "AI 说明（不参与校验）", 10.5, MUTED, True, lh=1.2)
    u.text(1058, 742, 338, 44,
           "“周四冲突主要来自同一成员的跨课程占用，建议把 T4 移到周五晚间。”——由确定性排程服务校验，模型不直接生效。",
           9.8, MUTED, lh=1.35)
    u.line(1058, 794, 1396, 794, LINE)
    u.rect(1058, 806, 338, 34, "#c8d2df", r=7)
    u.text(1058, 806, 338, 34, "确认并应用（存在冲突，不可用）", 11.5, "#ffffff", True, "center", "middle", 1.0)
    u.rect(1058, 848, 160, 32, CARD, "#c9d6e4", r=7)
    u.text(1058, 848, 160, 32, "仅保存草案", 10.8, MUTED, True, "center", "middle", 1.0)
    u.rect(1228, 848, 168, 32, CARD, "#c9d6e4", r=7)
    u.text(1228, 848, 168, 32, "撤回草案", 10.8, MUTED, True, "center", "middle", 1.0)
    u.text(1058, 892, 338, 38,
           "确认时将重新校验权限、版本与全部硬约束；确认后生成正式版本 v4，并通知受影响成员。"
           "此操作不等于向学校提交作业。", 9.6, MUTED, lh=1.35)

    u.footer("UI-03 对应 UC-06、UC-08；异常覆盖：草案过期、时间冲突、容量缺口、依赖无位置、禁止放宽硬约束。")


def ui_04(u):
    page_header(u, "UI-04｜交付完整性检查", "交付完整性检查", [
        ("依据：要求集合 v2 / 任务集 v5 / 计划版本 v3", MUTED, GRAY_BG),
        ("检查时间 10-21 16:20", MUTED, GRAY_BG),
    ])
    # summary cards
    cards = [("已确认要求", "8", INK, "#ffffff"), ("已覆盖", "4", TEAL, TEAL_BG),
             ("未覆盖", "1", AMBER, AMBER_BG), ("证据失效", "2", RED, RED_BG),
             ("无关联任务", "1", RED, RED_BG)]
    x = 24
    for label, num, fg, bg in cards:
        u.rect(x, 138, 268, 78, bg if bg != "#ffffff" else CARD, LINE, r=8)
        u.text(x + 16, 148, 160, 18, label, 11, MUTED, lh=1.2)
        u.text(x + 16, 166, 120, 40, num, 24, fg, True, lh=1.0)
        x += 280
    u.text(24, 222, 700, 20, "另有 1 项待确认要求不参与覆盖计算；覆盖状态只表示“存在交付证据”，不代表内容质量达标。",
           10.5, MUTED, lh=1.2)

    # table
    cols = [("要求条目", 40, 300), ("原文来源", 348, 112), ("关联任务", 462, 112),
            ("交付证据", 580, 180), ("覆盖状态", 766, 120), ("操作", 892, 96)]
    u.rect(24, 250, 992, 42, "#eef3f9", r=8)
    for name, cx, cw in cols:
        u.text(cx, 250, cw, 42, name, 11, MUTED, True, valign="middle", lh=1.0)
    rows = [
        ("R1 提交 PDF 报告，正文 ≥ 3000 字", "第 1 条·1 句", "T3、T7", "报告_v3.pdf ↗", "已覆盖", TEAL, TEAL_BG, "查看证据"),
        ("R2 调研方法与数据分析", "第 1 条·1 句", "T2", "数据分析.xlsx ↗", "已覆盖", TEAL, TEAL_BG, "查看证据"),
        ("R3 课堂展示 8–10 分钟", "第 1 条·3 句", "T5、T8", "展示脚本_v1.md ↗", "已覆盖", TEAL, TEAL_BG, "查看证据"),
        ("R4 提交幻灯片，10 页以内", "第 1 条·3 句", "T6", "— 未提交", "未覆盖", AMBER, AMBER_BG, "补充证据"),
        ("R5 小组分工说明（含贡献比例）", "第 1 条·4 句", "—", "分工说明.docx ↗", "证据失效", RED, RED_BG, "重新关联"),
        ("R6 引用格式 GB/T 7714", "第 1 条·5 句", "T3", "引用检查.md ↗（404）", "证据失效", RED, RED_BG, "重新关联"),
        ("R7 查重率 ≤ 20%", "第 1 条·5 句", "T7", "查重报告.pdf ↗", "已覆盖", TEAL, TEAL_BG, "查看证据"),
        ("R8 历史版本 / 过程材料", "人工补充·已确认", "—", "— 未安排任务", "无关联任务", RED, RED_BG, "新增任务"),
    ]
    y = 292
    for i, (req, src, tasks, ev, status, fg, bg, action) in enumerate(rows):
        if i % 2 == 1:
            u.rect(24, y, 992, 52, SOFT)
        u.line(24, y + 52, 1016, y + 52, "#e8eef5")
        u.text(40, y, 300, 52, req, 11.5, INK, valign="middle", lh=1.3)
        u.text(348, y, 108, 52, src, 10.3, MUTED, valign="middle", lh=1.2)
        u.text(462, y, 108, 52, tasks, 10.3, MUTED, valign="middle", lh=1.2)
        u.text(580, y, 180, 52, ev, 10.3, MUTED, valign="middle", lh=1.2)
        u.badge(766, y + 14, status, fg, bg, 10.3, True, padx=8, h=24)
        u.text(892, y, 96, 52, action + " ↗", 10.3, BLUE, valign="middle", lh=1.2)
        y += 52
    # pending row
    u.rect(24, y, 992, 44, "#f6f7f9")
    u.line(24, y + 44, 1016, y + 44, "#e8eef5")
    u.text(40, y, 300, 44, "R9 改进建议（人工补充，待确认）", 11.3, MUTED, valign="middle", lh=1.3)
    u.text(348, y, 108, 44, "人工补充", 10.3, MUTED, valign="middle", lh=1.2)
    u.text(462, y, 108, 44, "—", 10.3, MUTED, valign="middle", lh=1.2)
    u.text(580, y, 180, 44, "—（尚未确认）", 10.3, MUTED, valign="middle", lh=1.2)
    u.badge(766, y + 10, "待确认", MUTED, GRAY_BG, 10.3, True, padx=8, h=24)
    u.text(892, y, 96, 44, "去确认 ↗", 10.3, BLUE, valign="middle", lh=1.2)

    # right panel
    u.card(1034, 250, 382, 694)
    u.text(1054, 266, 300, 24, "未覆盖与失效项（4）", 13.5, NAVY, True, lh=1.2)
    issues = [
        ("R4 幻灯片未提交", "T6 处于“待开始”，尚无证据", AMBER, AMBER_BG),
        ("R8 无关联任务", "要求已确认但未拆解任务", RED, RED_BG),
        ("R5 证据链接失效", "链接不可访问（10-21 检查）", RED, RED_BG),
        ("R6 引用检查证据失效", "文件被移动或删除", RED, RED_BG),
    ]
    y = 298
    for title, reason, fg, bg in issues:
        u.rect(1054, y, 342, 72, bg, "#e6d3b3", r=8)
        u.text(1068, y + 8, 314, 20, title, 11, fg, True, lh=1.2)
        u.text(1068, y + 30, 314, 36, reason, 10, MUTED, lh=1.3)
        y += 80

    u.text(1054, 632, 340, 20, "检查说明", 11.5, NAVY, True, lh=1.2)
    u.text(1054, 656, 342, 120,
           "“已覆盖”只表示该要求存在关联交付证据，不代表内容质量达标、验收通过或系统已评分。"
           "证据失效后重新计算覆盖；删除任务或证据会产生新的未覆盖项。"
           "最终提交仍由学生在学校指定渠道完成。", 10, MUTED, lh=1.4)
    u.rect(1054, 712, 342, 70, SOFT, "#dfe7f0", r=8)
    u.text(1066, 720, 318, 56,
           "本次检查基于要求集合 v2（10-21 15:40 更新）与计划版本 v3；要求再次修改后须重新检查。",
           9.6, MUTED, lh=1.35)
    u.rect(1054, 806, 342, 36, BLUE, r=8)
    u.text(1054, 806, 342, 36, "重新检查（基于最新版本）", 11.5, "#ffffff", True, "center", "middle", 1.0)
    u.rect(1054, 852, 164, 34, CARD, "#c9d6e4", r=7)
    u.text(1054, 852, 164, 34, "导出检查清单", 10.8, BLUE, True, "center", "middle", 1.0)
    u.rect(1228, 852, 168, 34, CARD, "#c9d6e4", r=7)
    u.text(1228, 852, 168, 34, "通知负责人", 10.8, BLUE, True, "center", "middle", 1.0)
    u.text(1054, 898, 342, 34, "通知只发给当前作业负责人；普通成员可补充本人任务的证据。",
           9.6, MUTED, lh=1.3)

    # bottom
    u.rect(24, 772, 992, 120, CARD, LINE, r=8)
    u.text(40, 784, 600, 24, "提交前确认", 12.5, NAVY, True, lh=1.2)
    u.text(40, 810, 760, 62,
           "本页只核对“要求—任务—证据”的对应关系，不检查文件内容质量，也不代表学校平台已收到提交。"
           "确认清单后，请到学校指定的提交渠道上传：报告 PDF、展示幻灯片、小组分工说明。",
           10.4, MUTED, lh=1.4)
    u.badge(840, 826, "前往学校平台提交 ↗", BLUE, BLUE_BG, 11.2, True, padx=12, h=30)

    u.footer("UI-04 对应 UC-12；异常覆盖：未覆盖、证据失效、无关联任务、待确认要求不参与计算、权限与外部提交边界。")


def main():
    pages = []
    for name, fn in [("UI-01_作业录入与要求确认", ui_01), ("UI-02_任务与协作看板", ui_02),
                     ("UI-03_排程与计划确认", ui_03), ("UI-04_交付完整性检查", ui_04)]:
        p = Page(name, "", "")
        fn(p)
        p.render()
        pages.append(p)
    root = ET.Element("mxfile", {"host": "app.diagrams.net", "version": "24.7.17", "type": "device"})
    for p in pages:
        p.drawio(root)
    ET.indent(root, space="  ")
    UI.mkdir(exist_ok=True)
    ET.ElementTree(root).write(UI / "StudyFlow_界面原型.drawio", encoding="utf-8", xml_declaration=True)
    print("Generated", len(pages), "pages: drawio, svg, png.")


if __name__ == "__main__":
    main()
