"""Centralised stylesheet for the entire overlay application.

All visual styling lives here — screens and components should NOT define
inline stylesheets except for truly dynamic, per-widget values (e.g. the
active ability tile colour).
"""

# Definicje palet kolorystycznych dla Theme Engine
THEMES = {
    "gold": {
        "primary": "#C5A059",
        "primary_rgb": "197, 160, 89",
        "bg_base": "#0f172a",
        "bg_card_start": "rgba(30, 45, 75, 0.6)",
        "bg_card_end": "rgba(15, 25, 45, 0.8)",
        "border_subtle": "rgba(197, 160, 89, 0.15)",
        "border_solid": "#3d4a66"
    },
    "ruby": {
        "primary": "#EF4444",
        "primary_rgb": "239, 68, 68",
        "bg_base": "#1a0f0f",
        "bg_card_start": "rgba(75, 30, 30, 0.6)",
        "bg_card_end": "rgba(45, 15, 15, 0.8)",
        "border_subtle": "rgba(239, 68, 68, 0.15)",
        "border_solid": "#663d3d"
    },
    "blizzard": {
        "primary": "#3B82F6",
        "primary_rgb": "59, 130, 246",
        "bg_base": "#0f142a",
        "bg_card_start": "rgba(30, 50, 75, 0.6)",
        "bg_card_end": "rgba(15, 20, 45, 0.8)",
        "border_subtle": "rgba(59, 130, 246, 0.15)",
        "border_solid": "#3d4b66"
    },
    "emerald": {
        "primary": "#10B981",
        "primary_rgb": "16, 185, 129",
        "bg_base": "#0f1a15",
        "bg_card_start": "rgba(30, 75, 50, 0.6)",
        "bg_card_end": "rgba(15, 45, 25, 0.8)",
        "border_subtle": "rgba(16, 185, 129, 0.15)",
        "border_solid": "#3d664f"
    },
    "void": {
        "primary": "#8B5CF6",
        "primary_rgb": "139, 92, 246",
        "bg_base": "#170f2a",
        "bg_card_start": "rgba(55, 30, 75, 0.6)",
        "bg_card_end": "rgba(30, 15, 45, 0.8)",
        "border_subtle": "rgba(139, 92, 246, 0.15)",
        "border_solid": "#4f3d66"
    },
    "cyber": {
        "primary": "#F472B6",
        "primary_rgb": "244, 114, 182",
        "bg_base": "#0f0514",
        "bg_card_start": "rgba(40, 10, 60, 0.6)",
        "bg_card_end": "rgba(15, 5, 25, 0.9)",
        "border_subtle": "rgba(244, 114, 182, 0.2)",
        "border_solid": "#4c1d95"
    },
    "toxic": {
        "primary": "#A3E635",
        "primary_rgb": "163, 230, 53",
        "bg_base": "#0a0c08",
        "bg_card_start": "rgba(20, 40, 10, 0.6)",
        "bg_card_end": "rgba(5, 10, 0, 0.9)",
        "border_subtle": "rgba(163, 230, 53, 0.2)",
        "border_solid": "#365314"
    },
    "abyss": {
        "primary": "#FF003C",
        "primary_rgb": "255, 0, 60",
        "bg_base": "#050505",
        "bg_card_start": "rgba(30, 0, 5, 0.8)",
        "bg_card_end": "rgba(10, 0, 0, 1.0)",
        "border_subtle": "rgba(255, 0, 60, 0.3)",
        "border_solid": "#40000a"
    }
}

FONTS = {
    "standard": "'Segoe UI', sans-serif",
    "terminal": "'Consolas', 'Courier New', monospace",
    "heavy": "'Impact', 'Arial Black', sans-serif",
    "gothic": "'Georgia', 'Palatino Linotype', serif"
}

def get_stylesheet(theme_name: str = "gold", font_key: str = "standard") -> str:
    # Pobieramy zestaw kolorów dla wybranego motywu (lub fallback do gold)
    c = THEMES.get(theme_name.lower().strip(), THEMES["gold"])
    f = FONTS.get(font_key.lower().strip(), FONTS["standard"])
    
    return f"""
        /* ========== MAIN CONTAINER ========== */
        #main_container {{
            background-color: rgba(10, 15, 25, 245);
            border: 2px solid {c["primary"]};
            border-radius: 15px;
        }}

        /* ========== HEADER ========== */
        #god_name {{
            color: {c["primary"]};
            font-family: {f};
            font-size: 18px;
            font-weight: 900;
        }}
        #role_tag {{
            color: #8E9AAF; font-size: 10px; font-weight: bold;
            background: rgba(40, 50, 70, 0.6);
            padding: 4px 10px; border-radius: 5px;
        }}
        #nav_btn, #toggle_btn {{
            background: rgba({c["primary_rgb"]}, 0.1);
            color: {c["primary"]};
            border: 1px solid rgba({c["primary_rgb"]}, 0.4);
            border-radius: 6px; font-weight: bold;
        }}
        #nav_btn:hover, #toggle_btn:hover {{
            background: rgba({c["primary_rgb"]}, 0.3);
        }}
        #patch_badge {{
            background: rgba(40, 50, 70, 0.6);
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 4px;
            color: #94a3b8;
            font-size: 10px;
            font-weight: bold;
            padding: 4px 8px;
            margin-right: 5px;
        }}
        #mini_filter_btn {{
            background: rgba({c["primary_rgb"]}, 0.1);
            border: 1px solid rgba({c["primary_rgb"]}, 0.4);
            border-radius: 6px;
            color: {c["primary"]};
            font-size: 13px;
            padding: 0px;
        }}
        #mini_filter_btn:hover {{
            background: rgba({c["primary_rgb"]}, 0.3);
        }}

        /* ========== FILTER BAR ========== */
        #filter_btn {{
            background: #1A2233; color: {c["primary"]};
            border: 1px solid #3d4a66; border-radius: 6px;
            font-size: 10px; font-weight: bold;
        }}

        /* ========== SECTION LABELS ========== */
        .section_label {{
            color: #8E9AAF; font-size: 10px; font-weight: 900;
            text-transform: uppercase; letter-spacing: 2px;
            margin-top: 15px; margin-bottom: 2px;
        }}

        /* ========== ITEM ICONS ========== */
        #item_icon {{
            background-color: rgba(15, 25, 40, 0.9);
            border: 2px solid #3d4a66; border-radius: 8px;
        }}
        #item_icon:hover {{ border-color: {c["primary"]}; }}

        /* ========== TOOLTIP ========== */
        #float_tooltip_frame {{
            background-color: #0A0F19;
            border: 2px solid {c["primary"]};
            border-radius: 10px;
        }}
        #float_tooltip_text {{
            color: #FFFFFF;
            font-family: {f};
            font-size: 11px;
            font-weight: bold;
        }}

        /* ========== SWAPS ========== */
        .swap_arrow {{ color: {c["primary"]}; font-weight: bold; font-size: 14px; }}
        .swap_reason {{ color: #94a3b8; font-size: 11px; font-style: italic; font-weight: 600; }}

        /* ========== BUILD CARDS (LIST) ========== */
        #build_card {{
            background: rgba(20, 30, 50, 0.8);
            border: 1px solid #3d4a66;
            border-radius: 10px;
        }}
        #build_card:hover {{
            border-color: {c["primary"]};
            background: rgba(30, 40, 60, 0.9);
        }}
        #card_title {{
            color: #E0E0E0;
            font-family: {f};
            font-size: 13px;
            font-weight: bold;
        }}
        #card_meta {{
            color: #8E9AAF;
            font-size: 10px;
        }}
        #card_aspect_badge {{
            color: #fcd34d;
            background: rgba(245, 158, 11, 0.2);
            border: 1px solid rgba(245, 158, 11, 0.4);
            border-radius: 4px;
            font-size: 9px;
            font-weight: bold;
            padding: 2px 6px;
        }}
        #card_aspect_badge:hover {{
            background: rgba(245, 158, 11, 0.4);
            border-color: #fcd34d;
        }}
        .role_link {{
            color: #94a3b8;
            font-size: 10px;
        }}
        .role_link:hover {{
            color: #f8fafc;
            text-decoration: underline;
        }}
        .partner_badge {{
            color: #3b82f6;
            background: rgba(59, 130, 246, 0.15);
            border: 1px solid rgba(59, 130, 246, 0.3);
            border-radius: 4px;
            font-size: 8px;
            font-weight: bold;
            padding: 1px 5px;
            margin-left: 4px;
        }}
        #card_author {{
            color: {c["primary"]};
            font-weight: 600;
        }}
        #upvotes_count {{
            color: #10b981;
            font-weight: bold;
        }}

        /* ========== EMPTY STATES ========== */
        #empty_state_card {{
            background: rgba(30, 40, 60, 0.4);
            border: 2px dashed #3d4a66;
            border-radius: 12px;
        }}
        #empty_state_text {{
            color: #94a3b8;
            font-size: 14px;
            font-weight: 600;
        }}
        #mini_empty_card {{
            background: rgba(30, 40, 60, 0.4);
            border: 1px dashed rgba(148, 163, 184, 0.4);
            border-radius: 8px;
        }}
        #mini_empty_text {{
            color: #94a3b8;
            font-size: 12px;
            font-weight: 600;
        }}

        /* ========== SYSTEM ERROR PANELS ========== */
        #error_state_card_container {{
            background-color: rgba(239, 68, 68, 0.05);
            border: 2px solid rgba(239, 68, 68, 0.15);
            border-radius: 12px;
            padding: 20px;
        }}
        
        #error_state_card {{
            background-color: transparent;
            border: none;
        }}
        
        /* Specyficzny styl tylko dla przycisku wewnątrz błędu */
        #error_state_card_container #nav_btn {{
            background-color: rgba(15, 23, 42, 0.8);
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 6px;
            color: #f87171;
            font-weight: 800;
            font-size: 11px;
            padding: 8px 16px;
            margin-top: 5px;
        }}
        
        #error_state_card_container #nav_btn:hover {{
            background-color: #f87171;
            color: #ffffff;
            border: 1px solid transparent;
        }}
        
        #error_state_card_container #nav_btn:pressed {{
            background-color: #ef4444;
            color: rgba(255, 255, 255, 0.8);
        }}

        /* ========== HOME PAGE (PREMIUM LOOK) ========== */
        #mode_card {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                        stop:0 {c["bg_card_start"]}, 
                                        stop:1 {c["bg_card_end"]});
            border: 1px solid {c["border_subtle"]};
            border-radius: 16px;
        }}
        #mode_card:hover {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                        stop:0 {c["border_subtle"]}, 
                                        stop:1 rgba({c["primary_rgb"]}, 0.15));
            border: 1px solid {c["primary"]};
        }}
        #mode_icon_lbl {{
            font-size: 42px;
            background: rgba({c["primary_rgb"]}, 0.1);
            border-radius: 12px;
            padding: 8px;
            margin-bottom: 5px;
        }}
        #mode_card:hover #mode_icon_lbl {{
            background: rgba({c["primary_rgb"]}, 0.25);
        }}
        #mode_info_btn {{
            color: rgba(148, 163, 184, 0.6);
            font-size: 14px;
            font-weight: bold;
            background: rgba(148, 163, 184, 0.1);
            border-radius: 10px;
        }}
        #mode_info_btn:hover {{
            color: {c["primary"]};
            background: rgba({c["primary_rgb"]}, 0.2);
        }}
        #auto_wait_card {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                        stop:0 rgba({c["primary_rgb"]}, 0.05), 
                                        stop:1 rgba({c["primary_rgb"]}, 0.15));
            border: 1px solid rgba({c["primary_rgb"]}, 0.2);
            border-radius: 16px;
        }}
        #mode_title_lbl {{
            color: #f8fafc;
            font-size: 18px;
            font-weight: 800;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }}
        #mode_card:hover #mode_title_lbl {{
            color: {c["primary"]};
        }}
        #mode_desc_lbl {{
            color: #94a3b8;
            font-size: 11px;
            line-height: 1.5;
        }}
        #welcome_title {{
            color: {c["primary"]};
            font-size: 32px;
            font-weight: 900;
            letter-spacing: -1.5px;
            text-transform: uppercase;
        }}
        #welcome_subtitle {{
            color: #64748b;
            font-size: 12px;
            font-weight: 600;
            letter-spacing: 2px;
            text-transform: uppercase;
        }}

        /* ========== SEARCH PAGE ========== */
        #search_input {{
            background: rgba(15, 23, 42, 0.6);
            border: 2px solid rgba(148, 163, 184, 0.1);
            border-radius: 20px;
            color: #f8fafc;
            font-size: 14px;
            padding: 0 20px;
            font-weight: 500;
        }}
        #search_input:focus {{
            border-color: {c["primary"]};
            background: rgba(30, 41, 59, 0.8);
        }}
        
        #search_btn {{
            background: rgba({c["primary_rgb"]}, 0.1);
            color: {c["primary"]};
            border: 1px solid rgba({c["primary_rgb"]}, 0.4);
            border-radius: 18px;
            font-weight: 900;
            font-size: 11px;
            letter-spacing: 1px;
        }}
        #search_btn:hover {{
            background: rgba({c["primary_rgb"]}, 0.3);
            border-color: {c["primary"]};
        }}

        /* --- GOD PORTRAIT GRID --- */
        #god_scroll_area {{
            background: transparent;
        }}
        
        #god_results_box {{
            background: rgba(15, 23, 42, 0.4);
            border: 2px solid rgba(51, 65, 85, 0.3);
            border-radius: 15px;
        }}
        
        #god_portrait_container {{
            background: rgba(30, 41, 59, 0.3);
            border: 1px solid rgba(148, 163, 184, 0.1);
            border-radius: 12px;
        }}
        #god_portrait_container:hover {{
            background: rgba({c["primary_rgb"]}, 0.05);
            border: 1px solid rgba({c["primary_rgb"]}, 0.5);
        }}
        #god_portrait_img {{
            background: #0f172a;
            border: 2px solid #1e293b;
            border-radius: 35px;
        }}
        #god_portrait_container:hover #god_portrait_img {{
            border-color: {c["primary"]};
        }}
        #god_portrait_name {{
            color: #94a3b8;
            font-size: 9px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        #god_portrait_container:hover #god_portrait_name {{
            color: {c["primary"]};
        }}

        /* --- MINI RIBBON STYLE --- */
        #god_portrait_container[mini="true"] {{
            background: rgba(30, 41, 59, 0.5);
            border-radius: 25px;
            border: 1px solid rgba(148, 163, 184, 0.1);
        }}
        #god_portrait_container[mini="true"]:hover {{
            border-color: {c["primary"]};
            background: rgba({c["primary_rgb"]}, 0.1);
        }}
        #god_portrait_container[mini="true"] #god_portrait_img {{
            border-radius: 20px;
            border: none;
        }}

        /* --- MINI BUILD LIST ROWS --- */
        #mini_build_row {{
            background: rgba(30, 41, 59, 0.4);
            border: 1px solid rgba(148, 163, 184, 0.1);
            border-radius: 6px;
        }}
        #mini_build_row:hover {{
            background: rgba({c["primary_rgb"]}, 0.1);
            border-color: rgba({c["primary_rgb"]}, 0.4);
        }}
        #mini_build_title {{
            color: #f8fafc;
            font-family: {f};
        }}

        /* ========== GLOBAL SCROLLBARS ========== */
        QScrollBar:vertical {{
            border: none;
            background: rgba(15, 23, 42, 0.1);
            width: 6px;
            margin: 0px;
            border-radius: 3px;
        }}
        QScrollBar::handle:vertical {{
            background: rgba({c["primary_rgb"]}, 0.3);
            min-height: 40px;
            border-radius: 3px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: rgba({c["primary_rgb"]}, 0.7);
        }}

        #build_list_scroll, #god_scroll_area {{
            border: none;
            background: transparent;
        }}
        #build_list_scroll QWidget, #god_scroll_area QWidget {{
            background: transparent;
        }}

        /* Override for horizontal god scroll */
        #god_scroll_area QScrollBar:horizontal {{
            border: none;
            background: rgba(15, 23, 42, 0.1);
            height: 6px;
            margin: 0px 40px 2px 40px;
            border-radius: 3px;
        }}
        #god_scroll_area QScrollBar::handle:horizontal {{
            background: rgba({c["primary_rgb"]}, 0.3);
            min-width: 60px;
            border-radius: 3px;
        }}
        #god_scroll_area QScrollBar::handle:horizontal:hover {{
            border-color: {c["primary"]};
        }}
    """