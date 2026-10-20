"""Package existing team materials with an explicit non-final status and hashes."""
from pathlib import Path
import hashlib
import json
import zipfile
from check_delivery import main as check_delivery

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
MEMBERS = ("董泽福_SRS交付", "雍致鸣_SRS交付", "李一芃_SRS交付")
NAME = "第24组_StudyFlow_SRS_合并素材"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    check_delivery()
    files = [REPO / name for name in [
        "第二次作业分工.md",
        "System Analysis & Design Assignment_1.pdf",
        "StudyFlow_项目构想与AI工具反思.pdf",
    ]]
    for member in MEMBERS:
        for path in (REPO / member).rglob("*"):
            relative = path.relative_to(REPO / member)
            if path.is_file() and not any(part in ("dist", "__pycache__", ".git") for part in relative.parts):
                if path.suffix != ".pyc":
                    files.append(path)
    entries = {p.relative_to(REPO).as_posix(): p.read_bytes() for p in sorted(files)}
    entries["合并须知.md"] = (
        "# StudyFlow SRS合并素材\n\n"
        "此包收录三位成员的现有正文、模型源文件、导出图、AI记录和李一芃新增交付，"
        "保持原始相对路径。\n\n"
        "这是供董泽福整合的素材快照，不是最终Canvas提交包。包中"
        "StudyFlow_项目构想与AI工具反思.pdf是第一次报告，"
        "System Analysis & Design Assignment_1.pdf是课程要求；"
        "**没有将它们冒充最终SRS PDF**。\n\n"
        "最终报告尚需合并章节/目录/页码、处理交叉评审项、补录真实人工工时，"
        "导出并检查PDF后由上传负责人提交。\n\n"
        "先读李一芃_SRS交付/README.md及附件索引.md；"
        "图E/F已更新为2026年10月21日用户选定的简洁PNG，附内容对应的可编辑重建模型。"
        "实验结果未执行，不填虚构数据。MANIFEST.json用于核对文件内容。\n"
    ).encode("utf-8")
    manifest = {
        "kind": "SRS integration materials, not final Canvas submission",
        "revision": "1.1, user-selected figures adopted 2026-10-21",
        "baseline_commit": "97deeb605f4a02a16384e7543a8b7373eec28fb3",
        "files": [{"path": name, "bytes": len(data), "sha256": sha(data)} for name, data in sorted(entries.items())],
    }
    entries["MANIFEST.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    outdir = ROOT / "dist"
    outdir.mkdir(exist_ok=True)
    output = outdir / (NAME + ".zip")
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(entries.items()):
            info = zipfile.ZipInfo(NAME + "/" + name, (2026, 10, 21, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist()) == len(set(archive.namelist())) == len(entries)
        for entry in manifest["files"]:
            data = archive.read(NAME + "/" + entry["path"])
            assert sha(data) == entry["sha256"], entry["path"]
    digest = sha(output.read_bytes())
    (outdir / (NAME + ".sha256")).write_text(f"{digest}  {output.name}\n", encoding="utf-8")
    (outdir / "打包检查记录.md").write_text(
        f"# 打包检查\n\n- ZIP条目数：{len(entries)}。\n"
        f"- 除清单自身外，{len(manifest['files'])}个条目均逐项读取并通过SHA-256核对。\n"
        "- ZIP CRC检查通过，无重复路径；未包含Git历史、缓存或旧ZIP。\n"
        f"- ZIP SHA-256：`{digest}`。\n"
        "- 这是三人合并素材；最终SRS PDF及Canvas上传不在本次打包结果内。\n",
        encoding="utf-8",
    )
    print(f"PACKAGED {len(entries)} entries; verified hashes and CRC: {output}")


if __name__ == "__main__":
    main()
