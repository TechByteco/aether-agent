pub mod diff;

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// An interactive element identified in the DOM with a deterministic action ref.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct InteractiveRef {
    pub ref_id: String,
    pub tag: String,
    pub text: String,
    pub selector: String,
    pub role: Option<String>,
    pub attributes: HashMap<String, String>,
}

/// Token-compressed snapshot of a web page tailored for LLM agents.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DistilledSnapshot {
    pub url: String,
    pub title: String,
    pub markdown: String,
    pub interactive_elements: Vec<InteractiveRef>,
    pub raw_char_count: usize,
    pub distilled_char_count: usize,
    pub token_savings_pct: f64,
}

/// Fast semantic distiller implemented in pure Rust.
pub struct RustDistiller {
    pub token_char_ratio: f64,
}

impl Default for RustDistiller {
    fn default() -> Self {
        Self {
            token_char_ratio: 4.0,
        }
    }
}

impl RustDistiller {
    pub fn new() -> Self {
        Self::default()
    }

    /// Strips noise tags, extracts headings, links, and forms with deterministic [@ref:ID] tags.
    pub fn distill(&self, raw_html: &str, url: &str, title: &str) -> DistilledSnapshot {
        let raw_char_count = raw_html.len();
        let mut elements = Vec::new();
        let mut md_lines = Vec::new();

        if !title.is_empty() {
            md_lines.push(format!("# {title}"));
            md_lines.push(format!("**URL:** {url}\n---"));
        }

        // Fast regex-based distillation pass for native performance
        let tag_regex = regex::Regex::new(r"(?is)<(?P<tag>h[1-6]|p|a|button|input|select|textarea|li)[^>]*>(?P<content>.*?)</(?P=tag)>|<(?P<void>input|hr|br)[^>]*>").unwrap();
        let attr_regex = regex::Regex::new(r#"(?i)(href|type|placeholder|name|id|value)=["']([^"']*)["']"#).unwrap();
        let strip_tags = regex::Regex::new(r"<[^>]+>").unwrap();

        let mut ref_counter = 1;

        for cap in tag_regex.captures_iter(raw_html) {
            let full_match = cap.get(0).unwrap().as_str();
            let mut attrs = HashMap::new();
            for attr_cap in attr_regex.captures_iter(full_match) {
                attrs.insert(attr_cap[1].to_lowercase(), attr_cap[2].to_string());
            }

            if let Some(tag_match) = cap.name("tag") {
                let tag = tag_match.as_str().to_lowercase();
                let inner_raw = cap.name("content").map_or("", |m| m.as_str());
                let clean_text = strip_tags.replace_all(inner_raw, "").trim().to_string();

                match tag.as_str() {
                    "h1" => md_lines.push(format!("\n# {clean_text}\n")),
                    "h2" => md_lines.push(format!("\n## {clean_text}\n")),
                    "h3" => md_lines.push(format!("\n### {clean_text}\n")),
                    "p" if !clean_text.is_empty() => md_lines.push(format!("\n{clean_text}\n")),
                    "li" if !clean_text.is_empty() => md_lines.push(format!("- {clean_text}")),
                    "a" => {
                        let ref_id = ref_counter.to_string();
                        ref_counter += 1;
                        let href = attrs.get("href").cloned().unwrap_or_else(|| "#".to_string());
                        let display = if clean_text.is_empty() { &href } else { &clean_text };
                        md_lines.push(format!("[[@ref:{ref_id}] {display}]({href})"));

                        elements.push(InteractiveRef {
                            ref_id,
                            tag: "a".to_string(),
                            text: clean_text,
                            selector: format!("a[href='{href}']"),
                            role: Some("link".to_string()),
                            attributes: attrs,
                        });
                    }
                    "button" => {
                        let ref_id = ref_counter.to_string();
                        ref_counter += 1;
                        md_lines.push(format!("[[@ref:{ref_id}] (Button: {clean_text})]"));

                        elements.push(InteractiveRef {
                            ref_id: ref_id.clone(),
                            tag: "button".to_string(),
                            text: clean_text,
                            selector: format!("button:nth-of-type({ref_id})"),
                            role: Some("button".to_string()),
                            attributes: attrs,
                        });
                    }
                    _ => {}
                }
            } else if let Some(void_match) = cap.name("void") {
                let tag = void_match.as_str().to_lowercase();
                if tag == "input" {
                    let ref_id = ref_counter.to_string();
                    ref_counter += 1;
                    let placeholder = attrs.get("placeholder").cloned().unwrap_or_default();
                    let itype = attrs.get("type").cloned().unwrap_or_else(|| "text".to_string());
                    let val = attrs.get("value").cloned().unwrap_or_default();

                    md_lines.push(format!("[Input: [@ref:{ref_id}] type='{itype}' placeholder='{placeholder}' value='{val}']"));
                    elements.push(InteractiveRef {
                        ref_id: ref_id.clone(),
                        tag: "input".to_string(),
                        text: placeholder,
                        selector: format!("input:nth-of-type({ref_id})"),
                        role: Some("textbox".to_string()),
                        attributes: attrs,
                    });
                }
            }
        }

        let distilled_markdown = md_lines.join("\n");
        let distilled_char_count = distilled_markdown.len();
        let savings_pct = if raw_char_count > 0 {
            ((1.0 - (distilled_char_count as f64 / raw_char_count as f64)) * 100.0).max(0.0)
        } else {
            0.0
        };

        DistilledSnapshot {
            url: url.to_string(),
            title: title.to_string(),
            markdown: distilled_markdown,
            interactive_elements: elements,
            raw_char_count,
            distilled_char_count,
            token_savings_pct: (savings_pct * 10.0).round() / 10.0,
        }
    }
}
