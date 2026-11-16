"""DOM Mutation Delta Tracker (Diff Engine).

Computes semantic differences between consecutive agent turns, emitting
compact mutations rather than re-transmitting entire page snapshots to the LLM.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from .types import DistilledSnapshot, DomDiff, InteractiveElement


class DomDiffEngine:
    """Calculates semantic diffs between sequential snapshots of a web session."""

    def __init__(self):
        self._last_snapshot: Optional[DistilledSnapshot] = None

    def reset(self) -> None:
        """Clears stored history."""
        self._last_snapshot = None

    def compute_diff(self, current: DistilledSnapshot) -> DomDiff:
        """Compare current snapshot against previous snapshot and output semantic mutations."""
        if self._last_snapshot is None:
            # First turn: everything is newly introduced
            self._last_snapshot = current
            return DomDiff(
                previous_url=current.url,
                current_url=current.url,
                has_changed=True,
                summary=f"Initial page loaded: '{current.title}' with {len(current.interactive_elements)} controls.",
                added_elements=current.interactive_elements,
                modified_elements=[],
                removed_ref_ids=[],
                diff_markdown=current.markdown
            )

        prev = self._last_snapshot
        url_changed = prev.url != current.url

        # Build element maps by selector and text signature
        prev_map: Dict[str, InteractiveElement] = {
            self._element_signature(el): el for el in prev.interactive_elements
        }
        curr_map: Dict[str, InteractiveElement] = {
            self._element_signature(el): el for el in current.interactive_elements
        }

        added: List[InteractiveElement] = []
        modified: List[InteractiveElement] = []
        removed_ids: List[str] = []

        for sig, el in curr_map.items():
            if sig not in prev_map:
                added.append(el)
            else:
                prev_el = prev_map[sig]
                if prev_el.value != el.value or prev_el.text != el.text:
                    modified.append(el)

        for sig, el in prev_map.items():
            if sig not in curr_map:
                removed_ids.append(el.ref_id)

        has_changed = (
            url_changed or
            bool(added) or
            bool(modified) or
            bool(removed_ids) or
            prev.title != current.title
        )

        # Generate human- and LLM-friendly diff markdown
        diff_lines = []
        if url_changed:
            diff_lines.append(f"**Navigation:** `{prev.url}` ➔ `{current.url}`")
        if prev.title != current.title:
            diff_lines.append(f"**Title Changed:** '{prev.title}' ➔ '{current.title}'")

        if added:
            diff_lines.append(f"\n### Newly Appeared Controls ({len(added)}):")
            for el in added[:20]:
                diff_lines.append(f"+ [@ref:{el.ref_id}] {el.tag_name.upper()}: '{el.text or el.selector}'")
            if len(added) > 20:
                diff_lines.append(f"+ ... and {len(added) - 20} more items.")

        if modified:
            diff_lines.append(f"\n### Modified Elements ({len(modified)}):")
            for el in modified[:15]:
                diff_lines.append(f"* [@ref:{el.ref_id}] {el.tag_name.upper()} ({el.selector}): '{el.text or el.value}'")

        if removed_ids:
            diff_lines.append(f"\n### Disappeared Elements ({len(removed_ids)}):")
            diff_lines.append(f"- Ref IDs removed: {', '.join(removed_ids[:20])}")

        if not has_changed:
            summary = "No DOM mutations or visual state changes detected."
            diff_md = "*(Page state unchanged)*"
        else:
            summary = (
                f"State updated: +{len(added)} added, *{len(modified)} modified, "
                f"-{len(removed_ids)} removed."
            )
            diff_md = "\n".join(diff_lines)

        self._last_snapshot = current

        return DomDiff(
            previous_url=prev.url,
            current_url=current.url,
            has_changed=has_changed,
            summary=summary,
            added_elements=added,
            modified_elements=modified,
            removed_ref_ids=removed_ids,
            diff_markdown=diff_md
        )

    def _element_signature(self, el: InteractiveElement) -> str:
        """Deterministic fingerprint for matching elements across mutations."""
        return f"{el.tag_name}::{el.selector}::{el.attributes.get('id', '')}::{el.attributes.get('name', '')}"
