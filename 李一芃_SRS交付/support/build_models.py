"""Reconstruct editable simple diagrams from the user-approved flow content.

The supplied PNGs are the report figures. This script ONLY writes drawio/SVG,
never replaces the PNGs, and does not claim to reproduce their raster styling.
"""
import hashlib
import json
import xml.etree.ElementTree as ET
from drawing import Diagram, ROOT

USER = "#b8def6"
SERVICE = "#d1f0bc"
AI = "#ddd0f5"
ERROR = "#ffd08d"
NEUTRAL = "#f4f4f4"


def base(name, title, legend):
    d = Diagram(name, title, "", 1672, 941)
    d.nodes[0].size = 46
    d.nodes[0].y = 45
    d.nodes[0].h = 75
    d.nodes = [n for n in d.nodes if n.id != "subtitle"]
    for i, (text, color) in enumerate(legend):
        x = 1160 + i * 160
        d.node(f"legend{i}", "box", "", x, 170, 32, 28, color)
        d.node(f"legend_text{i}", "text", text, x + 42, 163, 115, 42, "white", 24)
    return d


def block(d, key, text, x, color, y=300, width=190):
    d.node(key, "box", text, x, y, width, 114, color, 30)


def generation():
    d = base("图E_AI与排程_生成草案", "StudyFlow｜排程草案生成",
             [("用户", USER), ("AI", AI), ("业务服务", SERVICE)])
    for key, text, x, color in [
        ("request", "发起规划", 20, USER),
        ("read", "授权读取", 250, SERVICE),
        ("understand", "理解目标", 480, AI),
        ("schedule", "校验排程", 710, SERVICE),
        ("save", "保存草案", 1230, SERVICE),
        ("wait", "等待确认", 1470, SERVICE),
    ]:
        block(d, key, text, x, color)
    d.node("available", "diamond", "结果可用？", 940, 265, 230, 184, NEUTRAL, 30)
    block(d, "fix", "查看并修正", 950, USER, 565, 220)
    d.node("inputs", "text", "要求 · 任务 · 忙闲", 250, 430, 340, 50, "white", 24)
    d.node("footnote", "text", "草案尚未生效", 650, 840, 500, 65, "white", 36)
    for start, end in [(210,250), (440,480), (670,710), (900,940), (1420,1470)]:
        d.edge([(start,357),(end,357)])
    d.edge([(1170,357),(1230,357)], "是", label_at=(1200,332))
    d.edge([(1055,449),(1055,565)], "否", label_at=(1085,495))
    d.edge([(950,622),(115,622),(115,414)], "重新发起", label_at=(535,598))
    return d


def handoff():
    d = base("图F_AI与排程_人工交接", "StudyFlow｜计划确认与生效",
             [("用户", USER), ("业务服务", SERVICE), ("异常处理", ERROR)])
    for key, text, x, color in [
        ("review", "审阅草案", 20, USER),
        ("confirm", "人工确认", 250, USER),
        ("check", "重新检查", 480, SERVICE),
        ("apply", "整体生效", 1000, SERVICE),
        ("version", "记录版本", 1230, SERVICE),
        ("notify", "通知成员", 1470, SERVICE),
    ]:
        block(d, key, text, x, color)
    d.node("passed", "diamond", "检查通过？", 710, 265, 230, 184, NEUTRAL, 30)
    block(d, "reject", "拒绝并重算", 715, ERROR, 565, 220)
    d.node("constraints", "text", "权限 · 版本 · 时间约束", 465, 430, 440, 50, "white", 24)
    d.node("back", "text", "返回图E", 760, 685, 210, 50, "white", 28)
    d.node("human", "text", "AI不能代替人工确认", 600, 795, 760, 52, "white", 32)
    d.node("notification", "text", "通知失败不回滚计划", 600, 850, 760, 52, "white", 32)
    for start, end in [(210,250), (440,480), (670,710), (1190,1230), (1420,1470)]:
        d.edge([(start,357),(end,357)])
    d.edge([(940,357),(1000,357)], "是", label_at=(970,332))
    d.edge([(825,449),(825,565)], "否", label_at=(855,495))
    return d


def main():
    adopted = json.loads((ROOT / "support/adopted_images.json").read_text(encoding="utf-8"))
    for entry in adopted["images"]:
        assert hashlib.sha256((ROOT / entry["asset"]).read_bytes()).hexdigest() == entry["sha256"]
    root = ET.Element("mxfile", {"host":"app.diagrams.net","type":"device","version":"24.7.17"})
    for diagram in [generation(), handoff()]:
        diagram.render(save_png=False)
        diagram.drawio(root)
    ET.indent(root, space="  ")
    (ROOT / "models").mkdir(exist_ok=True)
    ET.ElementTree(root).write(ROOT / "models/StudyFlow_AI与排程活动图.drawio",
                               encoding="utf-8", xml_declaration=True)
    for entry in adopted["images"]:
        assert hashlib.sha256((ROOT / entry["asset"]).read_bytes()).hexdigest() == entry["sha256"]
    print("Rebuilt 2 simple editable pages and SVGs; both user PNGs preserved byte-for-byte.")


if __name__ == "__main__":
    main()
