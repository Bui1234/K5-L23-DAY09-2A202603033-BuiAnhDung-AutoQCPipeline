
"""CHECK 2 - Validate YOLO label format and bounding boxes."""

from ..common import ERROR, WARN, Issue, iou_xywh, parse_yolo_line


def run(ds, cfg):
    issues = []
    options = cfg["label_format"]

    overflow_tol = options["overflow_tol"]
    min_box_px = options["min_box_px"]
    max_box_frac = options["max_box_frac"]
    dup_box_iou = options["dup_box_iou"]

    for label_file in ds.label_files():
        stem = label_file.stem
        previous_boxes = []
        image_size = ds.image_size(stem)

        for line_number, text in ds.read_label_lines(stem) or []:

            # 1. Check YOLO format
            try:
                class_id, cx, cy, w, h = parse_yolo_line(text)
            except (ValueError, OverflowError) as exc:
                issues.append(Issue(
                    check="label_format",
                    severity=ERROR,
                    code="BAD_FORMAT",
                    image=stem,
                    message=f"Invalid YOLO format: {exc}",
                    line=line_number,
                ))
                continue

            # 2. Check class ID
            if not 0 <= class_id < len(ds.classes):
                issues.append(Issue(
                    check="label_format",
                    severity=ERROR,
                    code="BAD_CLASS_ID",
                    image=stem,
                    message=f"Invalid class ID: {class_id}",
                    line=line_number,
                ))
                continue

            # 3. Check zero or negative box size
            if w <= 0 or h <= 0:
                issues.append(Issue(
                    check="label_format",
                    severity=ERROR,
                    code="BOX_ZERO",
                    image=stem,
                    message="Box width or height is not positive",
                    line=line_number,
                ))
                continue

            box = (cx, cy, w, h)

            # 4. Check image boundary overflow
            x1 = cx - w / 2
            y1 = cy - h / 2
            x2 = cx + w / 2
            y2 = cy + h / 2

            overflow = max(
                0.0,
                -x1,
                -y1,
                x2 - 1.0,
                y2 - 1.0,
            )

            if overflow > overflow_tol:
                issues.append(Issue(
                    check="label_format",
                    severity=ERROR,
                    code="BOX_OUT_OF_IMAGE",
                    image=stem,
                    message=f"Box overflow: {overflow:.6f}",
                    line=line_number,
                    extra={"overflow": overflow},
                ))

            # 5. Check tiny boxes
            if image_size is not None:
                image_w, image_h = image_size
                short_side = min(
                    w * image_w,
                    h * image_h,
                )

                if short_side < min_box_px:
                    issues.append(Issue(
                        check="label_format",
                        severity=WARN,
                        code="BOX_TINY",
                        image=stem,
                        message=f"Tiny box: {short_side:.2f}px",
                        line=line_number,
                    ))

            # 6. Check huge boxes
            if w * h > max_box_frac:
                issues.append(Issue(
                    check="label_format",
                    severity=WARN,
                    code="BOX_HUGE",
                    image=stem,
                    message="Box occupies too much image area",
                    line=line_number,
                ))

            # 7. Check duplicate boxes of the same class
            for prev_class, prev_box in previous_boxes:
                if (
                    prev_class == class_id
                    and iou_xywh(prev_box, box) > dup_box_iou
                ):
                    issues.append(Issue(
                        check="label_format",
                        severity=ERROR,
                        code="DUP_BOX",
                        image=stem,
                        message="Duplicate bounding box",
                        line=line_number,
                    ))
                    break

            previous_boxes.append((class_id, box))

    return issues
