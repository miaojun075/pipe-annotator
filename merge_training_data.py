#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import io
import sys

# 修复 Windows GBK 控制台无法输出 emoji 的问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

"""
管件标注训练数据合并工具
========================
合并多人（多文件夹）的 YOLO 标注训练数据。

用法:
    python merge_training_data.py ann_01/data ann_02/data -o merged_data

    ann_01/data/        ann_02/data/        →   merged_data/
    ├── images/         ├── images/             ├── images/
    ├── labels/         ├── labels/             ├── labels/
    └── data.yaml       └── data.yaml           └── data.yaml

参数:
    sources              多个标注文件夹路径（至少2个）
    -o, --output         输出目录（默认 merged_data）
    -n, --no-prefix      文件名不加标注者前缀（会检测重名冲突）
    -d, --dry-run        只检查不生成
    --split-val N        切出 N%% 做验证集（默认 0，不切）
"""

import argparse
import shutil
import sys
from pathlib import Path

# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────


def parse_args():
    p = argparse.ArgumentParser(
        description="合并多人 YOLO 标注训练数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("sources", nargs="+", help="标注文件夹路径（至少2个）")
    p.add_argument("-o", "--output", default="merged_data", help="输出目录")
    p.add_argument("-n", "--no-prefix", action="store_true", help="不加标注者前缀")
    p.add_argument("-d", "--dry-run", action="store_true", help="只检查，不生成文件")
    p.add_argument("--split-val", type=float, default=0, help="切出验证集比例，如 20（表示 20%%）")
    return p.parse_args()


# ──────────────────────────────────────────────
# Core logic
# ──────────────────────────────────────────────


def read_data_yaml(src: Path) -> dict:
    """读取 data.yaml，解析类别列表。返回 {name: idx} 映射和 raw names 列表。"""
    yaml_path = src / "data.yaml"
    if not yaml_path.exists():
        return {"names": [], "name2id": {}}

    # 简单解析，避免依赖 yaml 库（只用内置）
    names = []
    in_names = False
    try:
        for line in yaml_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("names:"):
                in_names = True
                # 行内可能直接跟列表
                bracket = line[6:].strip()
                if bracket.startswith("[") and bracket.endswith("]"):
                    import ast
                    try:
                        names = ast.literal_eval(bracket)
                    except Exception:
                        names = _parse_bracket_list(bracket)
                    break
                continue
            if in_names:
                if line.startswith("- "):
                    names.append(_unquote(line[2:].strip()))
                elif line.startswith('"') or line.startswith("'"):
                    names.append(_unquote(line.strip().rstrip(",")))
                elif not line:
                    continue
                else:
                    break  # names block ended
    except Exception:
        pass

    if not names and in_names:
        # Try reading the whole YAML inline format
        pass

    return {"names": names, "name2id": {n: i for i, n in enumerate(names)}}


def _unquote(s: str) -> str:
    """去除首尾引号。"""
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        return s[1:-1]
    return s


def _parse_bracket_list(text: str) -> list:
    """朴素解析 ["a", "b"] 格式。"""
    import re
    items = re.findall(r'"([^"]*)"|\'([^\']*)\'', text)
    return [a or b for a, b in items]


def scan_source(src: Path, idx: int) -> dict:
    """扫描单个标注者的目录。"""
    name = src.name  # annotator label
    images_dir = src / "images"
    labels_dir = src / "labels"

    images = sorted(images_dir.glob("*")) if images_dir.exists() else []
    labels = sorted(labels_dir.glob("*")) if labels_dir.exists() else []

    # 支持常见图片格式
    image_files = [f for f in images if f.suffix.lower() in
                   {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}]
    label_files = [f for f in labels if f.suffix.lower() == ".txt"]

    # 按 stem 匹配
    img_stems = {f.stem: f for f in image_files}
    lbl_stems = {f.stem: f for f in label_files}

    paired = []
    unpaired_img = []
    unpaired_lbl = []

    for stem, img in img_stems.items():
        if stem in lbl_stems:
            paired.append((img, lbl_stems[stem]))
        else:
            unpaired_img.append(img)

    for stem, lbl in lbl_stems.items():
        if stem not in img_stems:
            unpaired_lbl.append(lbl)

    yaml_info = read_data_yaml(src)

    return {
        "path": src,
        "annotator": name,
        "idx": idx,
        "paired": paired,
        "unpaired_img": unpaired_img,
        "unpaired_lbl": unpaired_lbl,
        "categories": yaml_info["names"],
        "name2id": yaml_info["name2id"],
        "total_images": len(image_files),
        "total_labels": len(label_files),
    }


def merge_categories(sources: list[dict]) -> dict:
    """合并所有标注者的类别，返回统一映射。"""
    merged_names = []
    # 先合并去重但保持顺序
    seen = set()
    for src in sources:
        for name in src["categories"]:
            if name not in seen:
                seen.add(name)
                merged_names.append(name)

    unified = {name: i for i, name in enumerate(merged_names)}

    # 为每个 source 生成 class_id 换算表
    mappings = []
    for src in sources:
        old2new = {}
        for old_name, old_id in src["name2id"].items():
            if old_name in unified:
                old2new[old_id] = unified[old_name]
        mappings.append(old2new)

    return {
        "names": merged_names,
        "unified": unified,
        "mappings": mappings,  # [ {old_id: new_id}, ... ]
        "total_classes": len(merged_names),
    }


def _read_text_any(src_path: Path) -> str:
    """读取文本文件，自动检测编码。"""
    raw = src_path.read_bytes()
    for enc in ["utf-8", "utf-8-sig", "utf-16", "gbk", "latin-1"]:
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return raw.decode("utf-8", errors="replace")


def remap_label(src_path: Path, dst_path: Path, mapping: dict[int, int]):
    """重映射标签文件中的 class_id。"""
    lines = _read_text_any(src_path).strip().splitlines()
    new_lines = []
    changed = 0
    skipped = 0
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            new_lines.append(line)
            continue
        parts = line.split()
        if len(parts) < 5:
            new_lines.append(line)
            continue
        try:
            old_id = int(parts[0])
        except ValueError:
            new_lines.append(line)
            skipped += 1
            continue
        new_id = mapping.get(old_id)
        if new_id is None:
            # 类别不在统一列表中，跳过
            skipped += 1
            continue
        parts[0] = str(new_id)
        new_lines.append(" ".join(parts))
        changed += 1
    dst_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return changed, skipped


def generate_data_yaml(out_dir: Path, names: list, train_dir: str = "images",
                       val_dir: str = None):
    """生成新的 data.yaml。"""
    yaml_path = out_dir / "data.yaml"
    nc = len(names)
    names_str = "[" + ", ".join(f'"{n}"' for n in names) + "]"

    content = f"""# 管件检测 YOLOv11 训练配置
# 由 merge_training_data.py 合并生成
# 图片数: (合并后需统计) | 类别数: {nc}

path: {out_dir.resolve().as_posix()}
train: {train_dir}
"""
    if val_dir:
        content += f"val: {val_dir}\n"
    else:
        content += f"val: {train_dir}\n"

    content += f"""
nc: {nc}
names: {names_str}
"""
    yaml_path.write_text(content, encoding="utf-8")
    return yaml_path


def split_train_val(out_dir: Path, split_pct: float):
    """按比例切分训练/验证集（通过移动文件到 val/ 子目录）。"""
    if split_pct <= 0:
        return

    images_dir = out_dir / "images"
    labels_dir = out_dir / "labels"
    val_images = out_dir / "val_images"
    val_labels = out_dir / "val_labels"

    val_images.mkdir(parents=True, exist_ok=True)
    val_labels.mkdir(parents=True, exist_ok=True)

    import random
    image_files = sorted(images_dir.glob("*"))
    random.seed(42)
    random.shuffle(image_files)
    split_n = max(1, int(len(image_files) * split_pct / 100))
    val_set = set(image_files[:split_n])

    for img in val_set:
        stem = img.stem
        lbl = labels_dir / f"{stem}.txt"
        shutil.move(str(img), str(val_images / img.name))
        if lbl.exists():
            shutil.move(str(lbl), str(val_labels / lbl.name))

    return len(val_set)


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────


def main():
    args = parse_args()

    if len(args.sources) < 2:
        print("[错误] 至少需要 2 个标注文件夹")
        sys.exit(1)

    # ── 扫描所有来源 ──
    sources = []
    print("=" * 60)
    print("  扫描标注文件夹...")
    print("=" * 60)

    for i, src_path in enumerate(args.sources):
        src = Path(src_path).resolve()
        if not src.exists():
            print(f"  [错误] 路径不存在: {src}")
            sys.exit(1)
        info = scan_source(src, i)
        sources.append(info)
        print(f"  [{i+1}] {info['annotator']}: "
              f"{info['total_images']} images, "
              f"{info['total_labels']} labels, "
              f"{len(info['categories'])} classes")
        if info["unpaired_img"]:
            print(f"       [!] {len(info['unpaired_img'])} images 无对应标签")
        if info["unpaired_lbl"]:
            print(f"       [!] {len(info['unpaired_lbl'])} labels 无对应图片")
        if info["categories"]:
            print(f"       类别: {info['categories']}")

    # ── 合并类别 ──
    print()
    print("=" * 60)
    print("  合并类别...")
    print("=" * 60)

    merged = merge_categories(sources)
    print(f"  统一类别数: {merged['total_classes']}")
    print(f"  类别列表: {merged['names']}")

    # 检测类别差异
    for i, src in enumerate(sources):
        only_src = set(src["categories"]) - set(merged["names"])
        only_others = set(merged["names"]) - set(src["categories"])
        if only_src:
            # 这些只在当前 source 有
            pass  # 已在合并中保留
        if only_others:
            print(f"  [{src['annotator']}] 缺少类别: {sorted(only_others)}")

    # ── 检查重名冲突 ──
    if args.no_prefix:
        all_stems = []
        for src in sources:
            all_stems.extend(p.stem for p, _ in src["paired"])
        duplicates = [s for s in set(all_stems) if all_stems.count(s) > 1]
        if duplicates:
            print()
            print(f"  [!] 有 {len(duplicates)} 个重名文件！建议使用前缀模式（去掉 -n）")
            for d in duplicates[:10]:
                print(f"    - {d}")
            if len(duplicates) > 10:
                print(f"    ... 还有 {len(duplicates) - 10} 个")
            if not args.dry_run:
                print("  添加 -n 重新运行，或删除 --no-prefix")
                sys.exit(1)

    # ── 生成合并 ──
    out = Path(args.output).resolve()
    total_paired = sum(len(s["paired"]) for s in sources)

    print()
    print("=" * 60)
    if args.dry_run:
        print(f"  [DRY RUN] 将合并 {total_paired} 对图片+标签 → {out}")
    else:
        print(f"  合并 {total_paired} 对图片+标签 → {out}")

    print("=" * 60)

    if args.dry_run:
        print("  未创建任何文件。去掉 -d 执行实际合并。")
        return

    # 创建输出目录
    out_images = out / "images"
    out_labels = out / "labels"
    out_images.mkdir(parents=True, exist_ok=True)
    out_labels.mkdir(parents=True, exist_ok=True)

    stats = {"copied_images": 0, "copied_labels": 0, "remapped": 0, "skipped": 0}

    for src in sources:
        prefix = "" if args.no_prefix else f"{src['annotator']}_"
        mapping = merged["mappings"][src["idx"]]

        for img_path, lbl_path in src["paired"]:
            # 新文件名
            new_stem = prefix + img_path.stem
            new_img = out_images / f"{new_stem}{img_path.suffix}"
            new_lbl = out_labels / f"{new_stem}.txt"

            shutil.copy2(img_path, new_img)
            stats["copied_images"] += 1

            if mapping:
                changed, skipped = remap_label(lbl_path, new_lbl, mapping)
                stats["remapped"] += changed
                stats["skipped"] += skipped
            else:
                shutil.copy2(lbl_path, new_lbl)
            stats["copied_labels"] += 1

    # 切分验证集
    val_count = 0
    if args.split_val > 0:
        val_count = split_train_val(out, args.split_val)
        val_dir = "val_images"
    else:
        val_dir = None

    # 生成 data.yaml
    data_yaml = generate_data_yaml(out, merged["names"], val_dir=val_dir)
    print(f"  输出 data.yaml → {data_yaml}")

    # ── 报告 ──
    print()
    print("=" * 60)
    print("  合并完成！")
    print("=" * 60)
    print(f"  总图片数:      {stats['copied_images']}")
    print(f"  总标签数:      {stats['copied_labels']}")
    if stats["remapped"]:
        print(f"  class_id 重映射: {stats['remapped']} 条")
    if stats["skipped"]:
        print(f"  [!] 跳过:        {stats['skipped']} 条 (类别不匹配)")
    print(f"  统一类别数:     {merged['total_classes']}")
    if val_count:
        print(f"  [V] 验证集:      {val_count} 张（{args.split_val}%）")
    print(f"  输出目录:       {out}")

    # 类别清单
    print()
    print("  类别映射表:")
    for i, name in enumerate(merged["names"]):
        print(f"    {i:>3d}  {name}")

    # 警告
    total_unpaired = sum(len(s["unpaired_img"]) for s in sources) + \
                     sum(len(s["unpaired_lbl"]) for s in sources)
    if total_unpaired:
        print()
        print(f"  [!] 有 {total_unpaired} 个未配对的图片/标签，未包含在合并中。")


if __name__ == "__main__":
    main()
