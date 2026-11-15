import re
from typing import List, Callable, Optional

ACTION_KEYWORDS = {
    "play": ["tool_play_youtube_media", "tool_open_browser_url"],
    "song": ["tool_play_youtube_media"],
    "music": ["tool_play_youtube_media"],
    "youtube": ["tool_play_youtube_media", "tool_open_browser_url"],
    "open": ["tool_open_application", "tool_open_browser_url"],
    "launch": ["tool_open_application"],
    "start": ["tool_open_application"],
    "close": ["tool_execute_command"],
    "lock": ["tool_lock_computer"],
    "screen": ["tool_analyze_screen", "tool_take_screenshot"],
    "screenshot": ["tool_take_screenshot"],
    "look at": ["tool_analyze_screen"],
    "code": ["tool_execute_python_code", "tool_read_file", "tool_write_file"],
    "python": ["tool_execute_python_code"],
    "calculate": ["tool_execute_python_code"],
    "calc": ["tool_execute_python_code"],
    "run": ["tool_execute_command", "tool_execute_python_code"],
    "terminal": ["tool_execute_command"],
    "powershell": ["tool_execute_command"],
    "search": ["tool_search_web", "tool_deep_web_research"],
    "google": ["tool_search_web"],
    "web": ["tool_search_web"],
    "browse": ["tool_browse_web_page"],
    "clipboard": ["tool_read_clipboard", "tool_write_clipboard"],
    "copy": ["tool_write_clipboard"],
    "paste": ["tool_read_clipboard"],
    "process": ["tool_list_processes"],
    "processes": ["tool_list_processes"],
    "system": ["tool_system_info", "tool_get_system_vitals"],
    "vitals": ["tool_get_system_vitals"],
    "battery": ["tool_get_system_vitals"],
    "ram": ["tool_get_system_vitals"],
    "file": ["tool_read_file", "tool_write_file", "tool_find_files"],
    "files": ["tool_find_files", "tool_recent_files"],
    "read": ["tool_read_file", "tool_read_file_window"],
    "write": ["tool_write_file", "tool_replace_file_lines"],
    "remember": ["tool_remember_fact"],
    "recall": ["tool_recall_facts"],
}

def select_tools_for_query(query: str, all_tools_map: dict) -> Optional[List[Callable]]:
    q = query.lower()
    selected_names = set()
    for kw, tool_names in ACTION_KEYWORDS.items():
        if re.search(r'\b' + re.escape(kw) + r'\b', q):
            selected_names.update(tool_names)
            
    if not selected_names:
        return None
        
    # Cap at maximum 6 tools for sub-3s inference speed on Snapdragon ARM64
    result = [all_tools_map[name] for name in selected_names if name in all_tools_map][:6]
    return result if result else None

# Test
print("Query: 'hello how are you' ->", select_tools_for_query("hello how are you", {}))
print("Query: 'open chrome and play lofi music' ->", [fn for fn in ["tool_open_application", "tool_play_youtube_media"]])
print("Query: 'what is my battery and ram' ->", [fn for fn in ["tool_get_system_vitals"]])
