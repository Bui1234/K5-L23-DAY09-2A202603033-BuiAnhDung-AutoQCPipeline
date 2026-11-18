
"""CHECK 6 - Compare annotations with model predictions."""

from ..common import WARN, Issue, iou_xywh, parse_yolo_line
from ..model_cache import get_preds


def run(ds, cfg, preds=None):
    if preds is None:
        preds = get_preds(ds, cfg, "checker")

    options = cfg["second_opinion"]
    conf_thr = options["conf"]
    min_area = options["min_area_px"]
    fp_conf = options["fp_conf"]
    iou_missing = options["iou_missing"]
    iou_match = options["iou_match"]
    iou_loose = options["iou_loose"]

    issues = []

    for image_file in ds.image_files():
        stem = image_file.stem

        if stem not in preds:
            continue

        lines = ds.read_label_lines(stem)
        if lines is None:
            continue

        size = ds.image_size(stem)
        if size is None:
            continue

        image_w, image_h = size

        labels = []
        for line_number, text in lines:
            try:
                cls, cx, cy, w, h = parse_yolo_line(text)
            except (ValueError, OverflowError):
                continue

            if not 0 <= cls < len(ds.classes):
                continue
            if w <= 0 or h <= 0:
                continue

            labels.append((line_number, cls, (cx, cy, w, h)))

        predictions = preds[stem]

        # Check model predictions for missing, loose or wrong labels.
        for prediction in predictions:
            pred_cls, confidence, cx, cy, w, h = prediction
            pred_box = (cx, cy, w, h)

            area_px = w * image_w * h * image_h
            if confidence < conf_thr or area_px < min_area:
                continue

            candidates = []
            for line_number, label_cls, label_box in labels:
                overlap = iou_xywh(pred_box, label_box)
                if overlap >= iou_missing:
                    candidates.append((label_cls, overlap))

            code = None
            extra = {"conf": confidence}

            if not candidates:
                code = "POSSIBLE_MISSING"

            else:
                same_class = [
                    overlap
                    for label_cls, overlap in candidates
                    if label_cls == pred_cls
                ]

                if same_class:
                    best_iou = max(same_class)
                    if best_iou < iou_loose:
                        code = "POSSIBLE_LOOSE_BOX"
                        extra["iou"] = best_iou

                else:
                    other_class = [
                        overlap
                        for label_cls, overlap in candidates
                        if label_cls != pred_cls
                    ]

                    if other_class and max(other_class) >= iou_match:
                        code = "POSSIBLE_WRONG_CLASS"
                        extra["iou"] = max(other_class)

            if code:
                issues.append(Issue(
                    check="second_opinion",
                    severity=WARN,
                    code=code,
                    image=stem,
                    message=f"{code}: model confidence {confidence:.3f}",
                    extra=extra,
                ))

        # Check annotations that do not match any model prediction.
        for line_number, label_cls, label_box in labels:
            best_iou = 0.0

            for prediction in predictions:
                pred_cls, confidence, cx, cy, w, h = prediction

                if confidence < fp_conf:
                    continue

                pred_box = (cx, cy, w, h)
                overlap = iou_xywh(label_box, pred_box)
                best_iou = max(best_iou, overlap)

            if best_iou < iou_missing:
                issues.append(Issue(
                    check="second_opinion",
                    severity=WARN,
                    code="POSSIBLE_FALSE_POS",
                    image=stem,
                    message="Annotation has no matching model prediction",
                    line=line_number,
                    extra={"iou": best_iou},
                ))

    return issues
