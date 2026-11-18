
"""Step 4 - Decide Release, Hold or Rework."""

from ..common import ERROR, WARN


def decide(issues, image_stems, cfg, reviewed=frozenset()):
    """Evaluate dataset quality and return the gate decision."""

    stems = set(image_stems)
    reviewed = set(reviewed)

    n_images = len(stems)

    # Mandatory errors always block release, even when reviewed.
    n_errors = sum(
        1 for issue in issues
        if issue.severity == ERROR
    )

    # Count unique images with unresolved warnings.
    warn_images = {
        issue.image
        for issue in issues
        if (
            issue.severity == WARN
            and issue.image in stems
            and issue.image not in reviewed
        )
    }

    n_warn_images = len(warn_images)

    warn_ratio = (
        n_warn_images / n_images
        if n_images > 0
        else 0.0
    )

    threshold = cfg["gate"]["warn_ratio_hold"]

    if n_errors > 0:
        decision = "Rework"
        reasons = [
            f"Con {n_errors} loi bat buoc (ERROR) can sua.",
            "Du lieu chua du dieu kien phat hanh.",
        ]

    elif warn_ratio >= threshold:
        decision = "Hold"
        reasons = [
            (
                f"Co {n_warn_images}/{n_images} anh "
                f"canh bao ({warn_ratio:.2%})."
            ),
            (
                f"Ty le canh bao dat hoac vuot "
                f"nguong {threshold:.2%}; can nguoi review."
            ),
        ]

    else:
        decision = "Release"
        reasons = [
            "Khong con loi bat buoc (ERROR).",
            (
                f"Co {n_warn_images}/{n_images} anh "
                f"canh bao ({warn_ratio:.2%}), "
                f"duoi nguong {threshold:.2%}."
            ),
        ]

    return {
        "decision": decision,
        "n_errors": n_errors,
        "n_warn_images": n_warn_images,
        "n_images": n_images,
        "warn_ratio": round(warn_ratio, 4),
        "reasons": reasons,
    }
