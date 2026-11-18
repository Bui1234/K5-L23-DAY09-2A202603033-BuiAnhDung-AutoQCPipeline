
"""Step 2 - Safely fix dataset errors."""

from collections import defaultdict

import yaml

from ..common import ERROR, parse_yolo_line


DROP_CODES = {
    "BAD_FORMAT",
    "BAD_CLASS_ID",
    "BOX_ZERO",
    "DUP_BOX",
}

REMOVE_CODES = {
    "LEAK_TEST",
    "CORRUPT_IMAGE",
    "BAD_SIZE",
}


def fix(ds, issues, cfg):
    fixes = []
    line_issues = defaultdict(lambda: defaultdict(set))
    removed = set()

    errors = [i for i in issues if i.severity == ERROR]

    def record(image, line, action, before, after):
        fixes.append({
            "image": image,
            "line": line,
            "action": action,
            "before": before,
            "after": after,
        })

    # Remove images first, including their label files.
    for issue in errors:
        code = issue.code
        if code not in REMOVE_CODES and not code.startswith("DUP_IMAGE_"):
            continue

        stem = issue.image
        if stem in removed:
            continue

        image_paths = [
            p for p in ds.image_files() if p.stem == stem
        ]
        label_path = ds.label_path(stem)

        if not image_paths and not label_path.exists():
            continue

        for path in image_paths:
            path.unlink()

        if label_path.exists():
            label_path.unlink()

        removed.add(stem)
        record(stem, issue.line, "remove_image", stem, "(removed)")

    # Handle missing labels and class names.
    for issue in errors:
        stem = issue.image

        if stem in removed:
            continue

        if issue.code == "MISSING_LABEL_FILE":
            if not ds.label_path(stem).exists():
                record(
                    stem, issue.line, "needs_label",
                    "(khong co file)", "chuyen nguoi gan",
                )

        elif issue.code == "BAD_CLASS_NAME":
            yaml_path = ds.root / "data.yaml"
            if yaml_path.exists():
                data = yaml.safe_load(
                    yaml_path.read_text(encoding="utf-8")
                ) or {}

                old_names = data.get("names")
                new_names = list(cfg["classes"])

                if old_names != new_names:
                    data["names"] = new_names
                    yaml_path.write_text(
                        yaml.safe_dump(
                            data, allow_unicode=True,
                            sort_keys=False,
                        ),
                        encoding="utf-8",
                    )
                    record(
                        stem, issue.line, "rename_classes",
                        str(old_names), str(new_names),
                    )

        elif issue.code in DROP_CODES or issue.code == "BOX_OUT_OF_IMAGE":
            if issue.line is not None:
                line_issues[stem][issue.line].add(issue.code)

    # Edit each label file once, preserving original line numbers.
    for stem, by_line in line_issues.items():
        if stem in removed:
            continue

        path = ds.label_path(stem)
        if not path.exists():
            continue

        original = path.read_text(encoding="utf-8").splitlines()
        output = []
        changed = False

        for number, before in enumerate(original, start=1):
            codes = by_line.get(number, set())

            if not codes:
                output.append(before)
                continue

            if codes & DROP_CODES:
                record(stem, number, "drop_line", before, "")
                changed = True
                continue

            if "BOX_OUT_OF_IMAGE" in codes:
                try:
                    cls, cx, cy, w, h = parse_yolo_line(before)
                except (ValueError, OverflowError):
                    record(stem, number, "drop_line", before, "")
                    changed = True
                    continue

                x1 = max(0.0, cx - w / 2)
                y1 = max(0.0, cy - h / 2)
                x2 = min(1.0, cx + w / 2)
                y2 = min(1.0, cy + h / 2)

                new_w = x2 - x1
                new_h = y2 - y1

                if new_w <= 0 or new_h <= 0:
                    record(stem, number, "drop_line", before, "")
                    changed = True
                    continue

                new_cx = (x1 + x2) / 2
                new_cy = (y1 + y2) / 2

                after = (
                    f"{cls} {new_cx:.8f} {new_cy:.8f} "
                    f"{new_w:.8f} {new_h:.8f}"
                )

                output.append(after)
                if after != before:
                    record(stem, number, "clip_box", before, after)
                    changed = True
                continue

            output.append(before)

        if changed:
            path.write_text(
                "\n".join(output) + ("\n" if output else ""),
                encoding="utf-8",
            )

    return fixes
