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

    def __init__(self, icon_factory=None, tooltip_filter=None, parent=None):
        super().__init__(parent)
        self._icon_factory = icon_factory
        self._tooltip_filter = tooltip_filter
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
        if getattr(build, 'special_equipment', None):
            self._add_item_row(_t("special_equipment"), build.special_equipment, 42)

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

            if build.is_partner:
                pb = QLabel(_t("partner_badge"))
                pb.setProperty("class", "partner_badge")
                ml.addWidget(pb)

            al = QLabel(_t("by_author").format(author=build.author))
            al.setObjectName("card_author")
            al.setStyleSheet("font-size: 12px;")
            ml.addWidget(al)

            tt_html = self.get_build_tooltip_html(build)
            if getattr(build, 'win_rate', None) and build.win_rate:
                if getattr(build, 'tier', None) and build.tier and build.tier != "-":
                    tb = QLabel(f"TIER {build.tier}")
                    tb.setStyleSheet(self._get_tier_badge_style(build.tier))
                    self._attach_tooltip(tb, tt_html)
                    ml.addWidget(tb)
                    
                wr_lbl = QLabel(f"{build.win_rate} WR ({build.wins}W - {build.losses}L)")
                wr_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #10b981;")
                self._attach_tooltip(wr_lbl, tt_html)
                ml.addWidget(wr_lbl)
                
                if getattr(build, 'cost', 0):
                    cost_lbl = QLabel(f"💰 {build.cost:,}g".replace(",", " "))
                    cost_lbl.setStyleSheet("font-size: 12px; color: #fbbf24; font-weight: bold;")
                    self._attach_tooltip(cost_lbl, tt_html)
                    ml.addWidget(cost_lbl)
            else:
                unranked_badge = QLabel(_t("unranked_badge"))
                unranked_badge.setStyleSheet(self._get_tier_badge_style("Unranked"))
                self._attach_tooltip(unranked_badge, tt_html)
                ml.addWidget(unranked_badge)
                if getattr(build, 'cost', 0):
                    cost_lbl = QLabel(f"💰 {build.cost:,}g".replace(",", " "))
                    cost_lbl.setStyleSheet("font-size: 12px; color: #fbbf24; font-weight: bold;")
                    self._attach_tooltip(cost_lbl, tt_html)
                    ml.addWidget(cost_lbl)

            self._detail_layout.addWidget(meta)

    def _attach_tooltip(self, widget, tooltip_html):
        if not widget or not tooltip_html:
            return
        widget.setProperty("tooltip_html", tooltip_html)
        widget.setObjectName("build_stats_badge")
        widget.setMouseTracking(True)
        if hasattr(self, '_tooltip_filter') and self._tooltip_filter:
            widget.installEventFilter(self._tooltip_filter)

    def get_build_tooltip_html(self, build) -> str:
        """Zwraca jednolity, elegancki tooltip HTML dla buildów ze statystykami oraz Unranked."""
        has_wr = bool(getattr(build, 'win_rate', None) and build.win_rate)
        cost_val = getattr(build, 'cost', 0)
        cost_str = f"{cost_val:,}g".replace(",", " ") if cost_val else ""

        if has_wr:
            tier_str = getattr(build, 'tier', '') or ''
            tier_html = f" <span style='color: #60a5fa; font-weight: bold;'>[{tier_str}]</span>" if tier_str else ""
            total_matches_str = _t("tt_total").format(count=build.total_matches)
            lines = [
                f"<div style='margin-bottom: 3px;'><b style='color: #93c5fd;'>{_t('tt_win_rate')}</b> <span style='color: #10b981; font-weight: bold;'>{build.win_rate}</span>{tier_html}</div>",
                f"<div style='margin-bottom: 3px;'><b style='color: #93c5fd;'>{_t('tt_matches')}</b> <span style='color: #34d399; font-weight: bold;'>{build.wins}W</span> - <span style='color: #f87171; font-weight: bold;'>{build.losses}L</span> <span style='color: #94a3b8;'>({total_matches_str})</span></div>"
            ]
        else:
            lines = [
                f"<div style='margin-bottom: 3px;'><b style='color: #93c5fd;'>{_t('tt_status')}</b> <span style='color: #60a5fa; font-weight: bold;'>{_t('tt_unranked')}</span></div>",
                f"<div style='margin-bottom: 3px;'><b style='color: #93c5fd;'>{_t('tt_matches')}</b> <span style='color: #e2e8f0;'>{_t('tt_unranked_desc')}</span></div>"
            ]

        if cost_str:
            lines.append(f"<div><b style='color: #93c5fd;'>{_t('tt_build_cost')}</b> <span style='color: #fbbf24; font-weight: bold;'>{cost_str}</span></div>")

        return f"<div style='line-height: 140%; padding: 2px 4px;'>{''.join(lines)}</div>"

    def _get_tier_badge_style(self, tier_str: str) -> str:
        t = (tier_str or "").strip().upper()
        if t in ("S+", "S"):
            bg, border, text = "rgba(16, 185, 129, 0.15)", "rgba(16, 185, 129, 0.45)", "#34d399"
        elif t in ("A+", "A"):
            bg, border, text = "rgba(132, 204, 22, 0.15)", "rgba(132, 204, 22, 0.45)", "#a3e635"
        elif t == "B":
            bg, border, text = "rgba(245, 158, 11, 0.15)", "rgba(245, 158, 11, 0.45)", "#fbbf24"
        elif t == "C":
            bg, border, text = "rgba(249, 115, 22, 0.15)", "rgba(249, 115, 22, 0.45)", "#fb923c"
        elif t == "D":
            bg, border, text = "rgba(239, 68, 68, 0.15)", "rgba(239, 68, 68, 0.45)", "#f87171"
        else:
            bg, border, text = "rgba(30, 41, 59, 0.6)", "rgba(59, 130, 246, 0.35)", "#93c5fd"
        return f"QLabel {{ font-size: 11px; font-weight: 800; color: {text}; background: {bg}; border: 1px solid {border}; border-radius: 4px; padding: 2px 6px; }}"

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
            img_rel = info.get("img", "")
            resolved_path = ""
            if local_path and os.path.exists(local_path):
                resolved_path = local_path
            elif local_path or img_rel:
                fname = os.path.basename((local_path or img_rel).replace("\\", "/"))
                cand1 = os.path.join("assets", "abilities", fname)
                appdata_dir = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
                cache_ab_dir = os.path.join(appdata_dir, "KuzenBot", "cache", "abilities")
                cand2 = os.path.join(cache_ab_dir, fname)
                if os.path.exists(cand1):
                    resolved_path = cand1
                elif os.path.exists(cand2):
                    resolved_path = cand2
                elif img_rel:
                    try:
                        import requests
                        os.makedirs(cache_ab_dir, exist_ok=True)
                        clean_img = img_rel.lstrip("/")
                        url = f"https://cdn.smitesource.com/cdn-cgi/image/width=128,format=auto,quality=75/{clean_img}"
                        resp = requests.get(url, timeout=4)
                        if resp.status_code == 200:
                            with open(cand2, "wb") as f:
                                f.write(resp.content)
                            resolved_path = cand2
                    except Exception:
                        pass

            loaded = False
            if resolved_path and os.path.exists(resolved_path):
                pix = QPixmap(resolved_path)
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
