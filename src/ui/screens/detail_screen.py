"""Detail Screen — full build breakdown (items, swaps, ability grid)."""

import os
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QFrame, QScrollArea, QGridLayout)

from ui.components.skeleton import QSkeleton, clear_layout
from core.translations import _t


class DetailScreen(QWidget):
    """Build detail screen — items, swaps, ability grid."""

    def __init__(self, icon_factory=None, parent=None):
        super().__init__(parent)
        self._icon_factory = icon_factory
        self._build_ui()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
            " QWidget { background: transparent; }"
        )
        self._detail_widget = QWidget()
        self._detail_layout = QVBoxLayout(self._detail_widget)
        self._detail_layout.setContentsMargins(0, 0, 0, 0)
        self._detail_layout.setSpacing(10)
        self.scroll.setWidget(self._detail_widget)
        root.addWidget(self.scroll, 1)

    # ------------------------------------------------------------- public
    def populate(self, build, god_name=""): # <-- ZMIANA: Dodajemy god_name
        """Populates the detail view for a given build."""
        clear_layout(self._detail_layout)
        if not build:
            return

        if getattr(build, 'is_stats', False):
            # Render statistical build representation
            self._detail_layout.setSpacing(15)
            
            # --- NOWOŚĆ: Baner Ratatoskra dla wersji Extended ---
            if god_name.lower() == "ratatoskr":
                banner = QFrame()
                banner.setStyleSheet("""
                    QFrame {
                        background-color: rgba(245, 158, 11, 0.15);
                        border: 1px dashed rgba(245, 158, 11, 0.4);
                        border-radius: 8px;
                    }
                """)
                banner_lay = QHBoxLayout(banner)
                banner_lay.setContentsMargins(10, 8, 10, 8)
                banner_lay.setSpacing(10)
                
                if self._icon_factory:
                    icon_lbl = self._icon_factory("Acorn", 32)
                    icon_lbl.setStyleSheet("background: transparent; border: none;")
                else:
                    icon_lbl = QLabel("🌰") 
                    icon_lbl.setStyleSheet("font-size: 20px; background: transparent; border: none;")
                    icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                banner_lay.addWidget(icon_lbl)
                
                text_lbl = QLabel(_t("ratatoskr_acorn_ext"))
                text_lbl.setStyleSheet("color: #fbbf24; font-size: 11px; font-weight: bold; background: transparent; border: none;")
                text_lbl.setWordWrap(True)
                banner_lay.addWidget(text_lbl, 1)
                
                self._detail_layout.addWidget(banner)
            # ----------------------------------------------------
            
            # Subtitle
            uses_obsidian = build.stats_data.get("uses_obsidian", False) if build.stats_data else False
            ranks_str = "Obsidian+, Master+ & Demigod" if uses_obsidian else "Master+ & Demigod"
            
            # Łączymy liczbę upvote'ów i rangi w jeden string, po czym podajemy go do tłumaczenia
            combined_count_str = f"{build.upvotes} ({ranks_str})"
            translated_subtitle = _t("aggregated").format(count=combined_count_str)
            
            sub_lbl = QLabel(translated_subtitle)
            sub_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 600; margin-bottom: 5px;")
            sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._detail_layout.addWidget(sub_lbl)
            
            # Horizontal container for the 8 columns
            cols_widget = QWidget()
            cols_widget.setObjectName("stats_cols_container")
            cols_widget.setStyleSheet("""
                QWidget#stats_cols_container {
                    background-color: rgba(30, 41, 59, 0.35);
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    border-radius: 12px;
                    padding: 10px;
                }
            """)
            cols_layout = QHBoxLayout(cols_widget)
            cols_layout.setContentsMargins(5, 5, 5, 5)
            cols_layout.setSpacing(6)
            
            # Fetch data from build.stats_data
            s_data = build.stats_data or {}
            starters = s_data.get("starter", [])
            slots = s_data.get("slots", [[] for _ in range(6)])
            relics = s_data.get("relic", [])
            
            # Define columns list
            columns_info = [
                (_t("starter"), starters),
                ("Slot 1", slots[0] if len(slots) > 0 else []),
                ("Slot 2", slots[1] if len(slots) > 1 else []),
                ("Slot 3", slots[2] if len(slots) > 2 else []),
                ("Slot 4", slots[3] if len(slots) > 3 else []),
                ("Slot 5", slots[4] if len(slots) > 4 else []),
                ("Slot 6", slots[5] if len(slots) > 5 else []),
                ("Relic", relics)
            ]
            
            for col_title, items_list in columns_info:
                col_w = QWidget()
                col_lay = QVBoxLayout(col_w)
                col_lay.setContentsMargins(0, 0, 0, 0)
                col_lay.setSpacing(8)
                col_lay.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
                
                # Column header
                h_lbl = QLabel(col_title)
                h_lbl.setStyleSheet("color: #94a3b8; font-size: 9px; font-weight: 800; text-transform: uppercase;")
                h_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                col_lay.addWidget(h_lbl)
                
                # Render top 3 options
                # (Pad up to 3 to keep columns perfectly aligned and equal height!)
                for o_idx in range(3):
                    opt_w = QWidget()
                    opt_lay = QVBoxLayout(opt_w)
                    opt_lay.setContentsMargins(0, 0, 0, 0)
                    opt_lay.setSpacing(2)
                    opt_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                    if o_idx < len(items_list):
                        entry = items_list[o_idx]
                        item_name = entry["item"]
                        pct = entry["pct"]
                        
                        # Icon
                        if self._icon_factory:
                            icon_widget = self._icon_factory(item_name, 40)
                            opt_lay.addWidget(icon_widget)
                        
                        # Pct Badge
                        pct_lbl = QLabel(f"{pct}%")
                        pct_lbl.setStyleSheet("color: #60a5fa; font-size: 10px; font-weight: 800;")
                        pct_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        opt_lay.addWidget(pct_lbl)
                    else:
                        # Placeholder
                        empty_spacer = QWidget()
                        empty_spacer.setFixedSize(40, 52)
                        opt_lay.addWidget(empty_spacer)
                        
                    col_lay.addWidget(opt_w)
                
                cols_layout.addWidget(col_w)
                
            self._detail_layout.addWidget(cols_widget)
            self._detail_layout.addStretch()
            
            return

        self._detail_layout.setSpacing(18)

        if build.starter_items:
            self._add_item_row(_t("starter"), build.starter_items, 42)
        if build.final_items:
            self._add_item_row(_t("final_build"), build.final_items, 46,
                               spacer_before_last=True)
        if build.swap_items:
            self._add_swap_rows(build.swap_items)

        if (hasattr(build, 'ability_priority') and build.ability_priority
                and hasattr(build, 'ability_details')):
            self._add_ability_grid(build.ability_priority, build.ability_details)

        self._detail_layout.addStretch()

        if not getattr(build, 'is_stats', False):
            meta = QWidget()
            meta.setObjectName("meta_container")
            
            ml = QHBoxLayout(meta)
            ml.setContentsMargins(0, 0, 0, 0)
            ml.setSpacing(10)
            ml.addStretch()
            self._detail_layout.addWidget(meta)

        if build.is_partner:
            pb = QLabel("PARTNER")
            pb.setProperty("class", "partner_badge")
            ml.addWidget(pb)

        al = QLabel(_t("by_author").format(author=build.author))
        al.setObjectName("card_author")
        al.setStyleSheet("font-size: 12px;")
        ml.addWidget(al)

        ul = QLabel(f"👍 {build.upvotes}")
        ul.setObjectName("upvotes_count")
        ul.setStyleSheet("font-size: 12px;")
        ml.addWidget(ul)

        self._detail_layout.addWidget(meta)

    def show_skeleton(self):
        """Animated skeletons shown during detail loading."""
        clear_layout(self._detail_layout)
        self._detail_layout.setSpacing(18)

        # Starter
        lbl1 = QLabel(_t("starter"))
        lbl1.setProperty("class", "section_label")
        self._detail_layout.addWidget(lbl1)
        r1 = QHBoxLayout()
        for _ in range(2):
            r1.addWidget(QSkeleton(42, 42, 8))
        r1.addStretch()
        self._detail_layout.addLayout(r1)

        # Final Build
        lbl2 = QLabel(_t("final_build"))
        lbl2.setProperty("class", "section_label")
        self._detail_layout.addWidget(lbl2)
        r2 = QHBoxLayout()
        for _ in range(6):
            r2.addWidget(QSkeleton(46, 46, 8))
        r2.addStretch()
        self._detail_layout.addLayout(r2)

        # Ability Grid
        lbl3 = QLabel(_t("ability_path"))
        lbl3.setProperty("class", "section_label")
        self._detail_layout.addWidget(lbl3)
        gs = QWidget()
        gl = QGridLayout(gs)
        gl.setContentsMargins(0, 5, 0, 10)
        gl.setSpacing(2)
        for r in range(4):
            gl.addWidget(QSkeleton(105, 30), r, 0)
            for c in range(1, 21):
                gl.addWidget(QSkeleton(22, 22, 3), r, c)
        self._detail_layout.addWidget(gs)
        self._detail_layout.addStretch()

    # ----------------------------------------------------------- builders
    def _add_item_row(self, title, items, icon_size, spacer_before_last=False):
        if not items:
            return
        if title:
            lbl = QLabel(title)
            lbl.setProperty("class", "section_label")
            self._detail_layout.addWidget(lbl)

        row = QWidget()
        row.setMinimumHeight(icon_size + 4)
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)
        rl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        for i, name in enumerate(items):
            if self._icon_factory:
                rl.addWidget(self._icon_factory(name, icon_size))
            if spacer_before_last and i == len(items) - 2:
                rl.addSpacing(12)
        self._detail_layout.addWidget(row)

    def _add_swap_rows(self, swaps):
        lbl = QLabel(_t("swaps"))
        lbl.setProperty("class", "section_label")
        self._detail_layout.addWidget(lbl)

        for s in swaps:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(5, 2, 5, 2)
            rl.setSpacing(10)
            if self._icon_factory:
                rl.addWidget(self._icon_factory(s.get('from'), 34))
            arrow = QLabel("➔")
            arrow.setProperty("class", "swap_arrow")
            rl.addWidget(arrow)
            if self._icon_factory:
                rl.addWidget(self._icon_factory(s.get('to'), 34))
            reason = QLabel(s.get('reason', 'Situational'))
            reason.setProperty("class", "swap_reason")
            reason.setWordWrap(True)
            rl.addWidget(reason, 1)
            self._detail_layout.addWidget(row)

    def _add_ability_grid(self, priority, details):
        # Sprawdź czy mamy dane
        if all(x is None for x in priority):
            lbl = QLabel(_t("ability_path"))
            lbl.setProperty("class", "section_label")
            self._detail_layout.addWidget(lbl)

            ef = QFrame()
            ef.setObjectName("empty_state_card")
            ef.setFixedHeight(80)
            el = QVBoxLayout(ef)
            el.setAlignment(Qt.AlignmentFlag.AlignCenter)
            el.setContentsMargins(15, 10, 15, 10)
            msg = QLabel(_t("ability_mystery"))
            msg.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 600;")
            msg.setWordWrap(True)
            msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            el.addWidget(msg)
            self._detail_layout.addWidget(ef)
            return

        lbl = QLabel(_t("ability_path"))
        lbl.setProperty("class", "section_label")
        self._detail_layout.addWidget(lbl)

        container = QWidget()
        grid = QGridLayout(container)
        grid.setContentsMargins(0, 5, 0, 10)
        grid.setSpacing(1)
        grid.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # Column headers (1-20)
        for lvl in range(1, 21):
            h = QLabel(str(lvl))
            h.setStyleSheet("color: #94a3b8; font-size: 8px; font-weight: 800;")
            h.setFixedSize(22, 14)
            h.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(h, 0, lvl)

        # 4 ability rows
        for slot_idx in range(1, 5):
            slot_str = str(slot_idx)
            info = details.get(slot_str, {"name": f"Ability {slot_idx}"})

            # Column 0: ability info
            ability_w = QWidget()
            ability_w.setFixedWidth(105)
            ability_w.setFixedHeight(36)
            al = QHBoxLayout(ability_w)
            al.setContentsMargins(0, 0, 4, 0)
            al.setSpacing(6)
            al.setAlignment(Qt.AlignmentFlag.AlignVCenter)

            icon = QLabel()
            icon.setFixedSize(32, 32)
            icon.setStyleSheet(
                "background: #1e293b; border: 1px solid #334155; border-radius: 4px;"
            )
            local_path = info.get("local_path", "")
            loaded = False
            if local_path and os.path.exists(local_path):
                pix = QPixmap(local_path)
                if not pix.isNull():
                    icon.setPixmap(pix.scaled(
                        32, 32,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    ))
                    icon.setStyleSheet(
                        "border: 1px solid #475569; border-radius: 4px;"
                    )
                    loaded = True
                    
            if not loaded:
                icon.setText("?")
                icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
                icon.setStyleSheet(
                    "background: #1e293b; border: 1px solid #334155; border-radius: 4px;"
                    "color: #C5A059; font-weight: bold; font-size: 14px;"
                )
                
            al.addWidget(icon)

            full_name = info.get("name", "Unknown")
            display_name = full_name[:10] + ".." if len(full_name) > 12 else full_name
            n_lbl = QLabel(display_name)
            n_lbl.setStyleSheet("color: #e2e8f0; font-size: 9px; font-weight: 600;")
            n_lbl.setToolTip(full_name)
            al.addWidget(n_lbl)

            grid.addWidget(ability_w, slot_idx, 0,
                           Qt.AlignmentFlag.AlignVCenter)

            # Columns 1-20: tiles
            for lvl in range(1, 21):
                tile = QLabel()
                tile.setFixedSize(22, 22)
                is_active = (lvl <= len(priority)
                             and str(priority[lvl - 1]) == slot_str)
                if is_active:
                    tile.setText(str(lvl))
                    tile.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    tile.setStyleSheet("""
                        background-color: #3b82f6;
                        border: 1px solid #60a5fa;
                        border-radius: 3px;
                        color: white;
                        font-size: 9px;
                        font-weight: 900;
                    """)
                else:
                    tile.setStyleSheet("""
                        background-color: rgba(30, 41, 59, 0.4);
                        border: 1px solid rgba(51, 65, 85, 0.2);
                        border-radius: 3px;
                    """)
                grid.addWidget(tile, slot_idx, lvl,
                               Qt.AlignmentFlag.AlignVCenter)

        self._detail_layout.addWidget(container)
