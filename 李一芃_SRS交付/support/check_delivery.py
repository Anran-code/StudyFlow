"""Static delivery checks only. Does not run StudyFlow or any user experiment."""
from pathlib import Path
import base64
import hashlib
import json
import re
import urllib.parse
import xml.etree.ElementTree as ET
import zlib
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
MEMBERS = ("董泽福_SRS交付", "雍致鸣_SRS交付", "李一芃_SRS交付")
ERRORS = []


def require(condition, description):
    if not condition:
        ERRORS.append(description)


def graph_pages(path):
    root = ET.parse(path).getroot()
    result = []
    for page in root.findall("diagram"):
        model = page.find("mxGraphModel")
        if model is None:
            raw = zlib.decompress(base64.b64decode(page.text.strip()), -15)
            model = ET.fromstring(urllib.parse.unquote(raw.decode("utf-8")))
        cells = model.findall("./root/mxCell")
        identifiers = [c.attrib["id"] for c in cells]
        require(len(set(identifiers)) == len(identifiers), f"Duplicate IDs: {path}:{page.attrib['name']}")
        require(len(cells) > 2, f"Empty model page: {path}")
        result.append(page.attrib["name"])
    return result


def main():
    ERRORS.clear()
    # Exclude generated archives/cache; only inspect this member's prose.
    markdown = [p for p in ROOT.rglob("*.md") if "dist" not in p.relative_to(ROOT).parts]
    local_links = 0
    for p in markdown:
        content = p.read_text(encoding="utf-8")
        require("\ufffd" not in content, f"Replacement character: {p}")
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", content):
            if target.startswith(("http:", "https:", "#", "C:/")):
                continue
            target = urllib.parse.unquote(target.split("#", 1)[0])
            require((p.parent / target).is_file(), f"Broken link: {p.name} -> {target}")
            local_links += 1
        expected_columns = None
        for line in content.splitlines():
            if line.startswith("|"):
                columns = len(re.split(r"(?<!\\)\|", line)) - 2
                if expected_columns is None:
                    expected_columns = columns
                require(columns == expected_columns, f"Table column mismatch: {p.name}: {line[:80]}")
            else:
                expected_columns = None

    refs = (ROOT / "参考资料与来源核对.md").read_text(encoding="utf-8")
    annotations = re.findall(r"^\> (.+)$", refs, re.M)
    word_counts = [len(a.split()) for a in annotations]
    require(len(annotations) == 5 and all(30 <= n <= 60 for n in word_counts),
            f"Reference annotations: {word_counts}")
    cases = (ROOT / "validation" / "排程案例定义.md").read_text(encoding="utf-8")
    ids = re.findall(r"^\| ([FIB]\d{2})(?:\s| \|)", cases, re.M)
    expected_cases = {f"F{i:02}" for i in range(1, 11)} | {f"I{i:02}" for i in range(1, 11)} | {f"B{i:02}" for i in range(1, 6)}
    require(set(ids) == expected_cases and len(ids) == 25, f"Case definitions: {ids}")
    templates = (ROOT / "validation" / "空白记录模板.md").read_text(encoding="utf-8")
    sample_ids = re.findall(r"^\| (EX-\d{2})", templates, re.M)
    require(set(sample_ids) == {f"EX-{i:02}" for i in range(1, 21)} and len(sample_ids) == 20,
            "Extraction sample register must have 20 unique placeholders")

    main_doc = (ROOT / "StudyFlow_SRS_李一芃部分.md").read_text(encoding="utf-8")
    scenarios = re.findall(r"^\| (V-(?:06|09)[A-Z]) ", main_doc, re.M)
    require(set(scenarios) == {f"V-06{c}" for c in "ABCDEFGHIJ"} | {f"V-09{c}" for c in "ABCDEFGH"},
            f"Use-case acceptance scenarios: {scenarios}")
    baseline = (REPO / MEMBERS[1] / "StudyFlow_SRS_雍致鸣部分.md").read_text(encoding="utf-8")
    for prefix in [r"NFR-[A-Z]\d{2}", r"BR-\d{2}", r"UC-\d{2}", r"A-F\d{2}", r"UI-\d{2}"]:
        for name in set(re.findall(prefix, main_doc)):
            require(name in baseline, f"Unmapped baseline identifier: {name}")
    require("## 2. UC-06" in main_doc and "## 3. UC-09" in main_doc, "Two detailed use cases missing")

    model_details = []
    image_details = []
    svg_count = 0
    for member in MEMBERS:
        for path in sorted((REPO / member).rglob("*.drawio")):
            pages = graph_pages(path)
            model_details.append((path.relative_to(REPO).as_posix(), pages))
        for path in sorted((REPO / member / "assets").glob("*.png")):
            with Image.open(path) as im:
                size = im.size
                im.verify()
            require(min(size) >= 500, f"Low-resolution export: {path}")
            image_details.append((path.relative_to(REPO).as_posix(), size))
        for path in (REPO / member / "assets").glob("*.svg"):
            ET.parse(path)
            svg_count += 1
    require(len(model_details) == 3 and [len(p) for _, p in model_details] == [4, 4, 2],
            f"Model page mapping: {model_details}")
    require(len(image_details) == 10 and svg_count == 6, "Expected 10 PNGs and 6 SVGs")

    adopted = json.loads((ROOT / "support/adopted_images.json").read_text(encoding="utf-8"))
    require(len(adopted["images"]) == 2, "Expected two user-selected PNGs")
    for entry in adopted["images"]:
        path = ROOT / entry["asset"]
        require(hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"],
                f"User-selected image changed: {path.name}")
        with Image.open(path) as im:
            require(list(im.size) == entry["dimensions"], f"Image dimensions changed: {path.name}")
    editable = ET.parse(ROOT / "models/StudyFlow_AI与排程活动图.drawio").getroot()
    expected_nodes = [
        {"发起规划", "授权读取", "理解目标", "校验排程", "结果可用？", "保存草案", "等待确认", "查看并修正"},
        {"审阅草案", "人工确认", "重新检查", "检查通过？", "整体生效", "记录版本", "通知成员", "拒绝并重算"},
    ]
    for page, expected in zip(editable.findall("diagram"), expected_nodes):
        nodes = page.findall("./mxGraphModel/root/mxCell")
        flow_nodes = {c.get("value") for c in nodes
                      if c.get("vertex") == "1" and not c.get("id", "").startswith("legend")
                      and ("rounded=1" in c.get("style", "") or "rhombus;" in c.get("style", ""))}
        require(flow_nodes == expected, f"Editable flow content mismatch: {page.get('name')}")

    if ERRORS:
        raise SystemExit("\n".join(ERRORS))
    lines = [
        "# 交付静态检查记录", "",
        "检查对象：李一芃交付1.1（2026-10-21选图更新）及仓库建模附件；基线97deeb6。",
        "本记录由check_delivery.py产生；不代表产品实现或用户实验通过。", "",
        f"- 本人Markdown文件数：{len(markdown)}；有效相对文件链接：{local_links}。",
        "- Markdown表格列数一致，未发现缺失的本地引用文件或替换乱码。",
        f"- 5项英文参考注释词数：{', '.join(map(str, word_counts))}；均在30～60范围内。",
        "- 排程案例定义：10可行、10有证明不可行、5边界，共25个且编号唯一。",
        "- 抽取样本登记：EX-01～EX-20共20个空位；未填虚构原文、标注或输出。",
        "- UC-06/UC-09详细规格及18个验收场景可定位；本稿A-F/UC/UI/BR/NFR引用沿用基线编号。",
        "- 3个drawio可解析，页面内对象ID唯一，共10页；10张PNG可解码，6份SVG可解析。", "",
        "- 图E/图F与用户原PNG的SHA-256一致；每页重建模型的8个核心节点与选图内容一致。", "",
        "## 模型页清单", ""
    ]
    for name, pages in model_details:
        lines.append(f"- `{name}`：{len(pages)}页（{'、'.join(pages)}）。")
    lines += ["", "## 图像尺寸", ""]
    lines += [f"- `{name}`：{size[0]}×{size[1]}。" for name, size in image_details]
    lines += [
        "", "## 检查范围的界限", "",
        "脚本检查文件、编号、表格与模型结构，不自动证明流程语义或画面排版正确。",
        "本次采用用户提供的两张简洁PNG，并检查其正文图注及可编辑重建版本；来源见图片采用记录。",
        "系统与用户实验、双人标注、组员人工签署均未执行；所有实验结果表保持空白。",
        "ZIP内容及哈希校验由package_delivery.py另行执行并记录在dist/打包检查记录.md。",
        ""
    ]
    (ROOT / "support" / "交付检查记录.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"PASS: {len(markdown)} Markdown files, {local_links} local links, annotations {word_counts}, 25 cases, 20 placeholders, 3 models / 10 pages / 10 PNG / 6 SVG.")


if __name__ == "__main__":
    main()
