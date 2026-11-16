use crate::{DistilledSnapshot, InteractiveRef};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DomDiffResult {
    pub has_changed: bool,
    pub summary: String,
    pub added: Vec<InteractiveRef>,
    pub modified: Vec<InteractiveRef>,
    pub removed_ids: Vec<String>,
    pub diff_markdown: String,
}

pub struct RustDiffEngine {
    last_snapshot: Option<DistilledSnapshot>,
}

impl Default for RustDiffEngine {
    fn default() -> Self {
        Self { last_snapshot: None }
    }
}

impl RustDiffEngine {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn compute_diff(&mut self, current: DistilledSnapshot) -> DomDiffResult {
        if self.last_snapshot.is_none() {
            let res = DomDiffResult {
                has_changed: true,
                summary: format!("Initial snapshot: {} elements", current.interactive_elements.len()),
                added: current.interactive_elements.clone(),
                modified: Vec::new(),
                removed_ids: Vec::new(),
                diff_markdown: current.markdown.clone(),
            };
            self.last_snapshot = Some(current);
            return res;
        }

        let prev = self.last_snapshot.as_ref().unwrap();
        let url_changed = prev.url != current.url;

        let mut added = Vec::new();
        let mut modified = Vec::new();
        let mut removed_ids = Vec::new();

        for curr_el in &current.interactive_elements {
            if let Some(prev_el) = prev.interactive_elements.iter().find(|e| e.selector == curr_el.selector) {
                if prev_el.text != curr_el.text || prev_el.attributes != curr_el.attributes {
                    modified.push(curr_el.clone());
                }
            } else {
                added.push(curr_el.clone());
            }
        }

        for prev_el in &prev.interactive_elements {
            if !current.interactive_elements.iter().any(|e| e.selector == prev_el.selector) {
                removed_ids.push(prev_el.ref_id.clone());
            }
        }

        let has_changed = url_changed || !added.is_empty() || !modified.is_empty() || !removed_ids.is_empty();

        let mut diff_lines = Vec::new();
        if url_changed {
            diff_lines.push(format!("**Navigation:** `{}` -> `{}`", prev.url, current.url));
        }
        for a in &added {
            diff_lines.push(format!("+ [@ref:{}] {}: {}", a.ref_id, a.tag, a.text));
        }
        for m in &modified {
            diff_lines.push(format!("* [@ref:{}] {}: modified", m.ref_id, m.tag));
        }

        let summary = format!("+{} added, *{} modified, -{} removed", added.len(), modified.len(), removed_ids.len());
        let diff_md = if diff_lines.is_empty() { "*(No state changes)*".to_string() } else { diff_lines.join("\n") };

        self.last_snapshot = Some(current);

        DomDiffResult {
            has_changed,
            summary,
            added,
            modified,
            removed_ids,
            diff_markdown: diff_md,
        }
    }
}
