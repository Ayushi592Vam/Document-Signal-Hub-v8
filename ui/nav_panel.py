"""
ui/nav_panel.py
Left-panel claim navigator: search box + scrollable claim cards
+ LLM Cost & Token tracker panel (Excel/CSV only).
"""

import streamlit as st
from modules.schema_mapping import detect_claim_id, get_val


# ── colour aliases (match dialogs.py light theme) ─────────────────────────────
_GRN  = "#0a9e6a"
_GRN_BG = "#e6f9f2"
_BLU  = "#1a6fd8"
_BLU_BG = "#e8f0fe"
_YEL  = "#c99a00"
_YEL_BG = "#fffbeb"
_RED  = "#d64040"
_RED_BG = "#fff0f0"
_LBL  = "#4a5578"
_TXT  = "#0f1117"
_BDR  = "#d0d6e8"
_BG   = "#f8f9fc"
_BG2  = "#f1f3f8"
_PUR  = "#6b3fd4"


def _render_llm_cost_panel() -> None:
    """
    Renders the LLM cost & token usage section.
    Only shows meaningful data for Excel/CSV files where field-mapping
    and cause-of-loss LLM calls are made.
    """
    totals  = st.session_state.get("_llm_totals", {})
    log     = st.session_state.get("_llm_usage_log", [])
    n_calls = totals.get("calls", 0)

    # ── Section header ────────────────────────────────────────────────────────
    st.markdown(
        f"<div style='font-size:10px;font-weight:800;color:{_TXT};"
        f"font-family:monospace;text-transform:uppercase;letter-spacing:1.5px;"
        f"margin:18px 0 8px;padding-bottom:4px;border-bottom:2px solid {_BDR};'>"
        f"🤖 LLM Usage (this session)</div>",
        unsafe_allow_html=True,
    )

    if n_calls == 0:
        st.markdown(
            f"<div style='color:{_LBL};font-size:12px;font-family:monospace;"
            f"font-style:italic;padding:6px 0;'>"
            f"No LLM calls yet — upload an Excel / CSV file with unrecognised columns "
            f"or claims that need cause-of-loss enrichment.</div>",
            unsafe_allow_html=True,
        )
        return

    cost     = totals.get("cost_usd", 0.0)
    in_tok   = totals.get("prompt_tokens", 0)
    out_tok  = totals.get("output_tokens", 0)
    tot_tok  = totals.get("total_tokens", 0)

    # ── Summary cards ─────────────────────────────────────────────────────────
    cost_color = _GRN if cost < 0.01 else _YEL if cost < 0.10 else _RED
    cost_bg    = _GRN_BG if cost < 0.01 else _YEL_BG if cost < 0.10 else _RED_BG

    st.markdown(
        f"<div style='background:{cost_bg};border:1px solid {cost_color}60;"
        f"border-left:3px solid {cost_color};border-radius:6px;"
        f"padding:8px 12px;margin-bottom:6px;'>"
        f"<div style='font-size:9px;font-weight:700;color:{cost_color};"
        f"font-family:monospace;text-transform:uppercase;letter-spacing:1px;"
        f"margin-bottom:2px;'>Estimated Cost</div>"
        f"<div style='font-size:18px;font-weight:800;color:{cost_color};"
        f"font-family:monospace;'>${cost:.5f}</div>"
        f"<div style='font-size:10px;color:{_LBL};margin-top:1px;'>"
        f"{n_calls} call{'s' if n_calls != 1 else ''}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Token breakdown
    def _tok_row(label, value, color=_LBL):
        return (
            f"<div style='display:flex;justify-content:space-between;"
            f"padding:3px 0;border-bottom:1px solid {_BDR};'>"
            f"<span style='font-size:11px;color:{_LBL};font-family:monospace;'>{label}</span>"
            f"<span style='font-size:11px;font-weight:700;color:{color};"
            f"font-family:monospace;'>{value:,}</span></div>"
        )

    st.markdown(
        f"<div style='background:{_BG};border:1px solid {_BDR};border-radius:6px;"
        f"padding:8px 10px;margin-bottom:8px;'>"
        + _tok_row("Prompt tokens",  in_tok,  _BLU)
        + _tok_row("Output tokens",  out_tok, _GRN)
        + _tok_row("Total tokens",   tot_tok, _TXT)
        + f"</div>",
        unsafe_allow_html=True,
    )

    # ── Per-call breakdown (collapsible) ──────────────────────────────────────
    if log:
        with st.expander(f"Call log ({len(log)} entries)", expanded=False):
            # Group by purpose
            purpose_totals: dict = {}
            for entry in log:
                p = entry["purpose"]
                if p not in purpose_totals:
                    purpose_totals[p] = {"calls": 0, "tokens": 0, "cost": 0.0}
                purpose_totals[p]["calls"]  += 1
                purpose_totals[p]["tokens"] += entry["total_tokens"]
                purpose_totals[p]["cost"]   += entry["cost_usd"]

            # Purpose summary pills
            _PURPOSE_COLORS = {
                "field_mapping": _BLU,
                "cause_of_loss": _GRN,
                "general":       _LBL,
            }
            _PURPOSE_LABELS = {
                "field_mapping": "Field Mapping",
                "cause_of_loss": "Cause of Loss",
                "general":       "General",
            }
            pills_html = ""
            for p, pt in purpose_totals.items():
                pc = _PURPOSE_COLORS.get(p, _PUR)
                pl = _PURPOSE_LABELS.get(p, p.replace("_", " ").title())
                pills_html += (
                    f"<div style='background:{pc}18;border:1px solid {pc}55;"
                    f"border-radius:6px;padding:6px 8px;margin-bottom:4px;'>"
                    f"<div style='font-size:10px;font-weight:700;color:{pc};"
                    f"font-family:monospace;margin-bottom:2px;'>{pl}</div>"
                    f"<div style='font-size:10px;color:{_LBL};font-family:monospace;'>"
                    f"{pt['calls']} call{'s' if pt['calls']!=1 else ''} · "
                    f"{pt['tokens']:,} tok · ${pt['cost']:.5f}</div>"
                    f"</div>"
                )
            st.markdown(pills_html, unsafe_allow_html=True)

            st.markdown(
                f"<div style='font-size:9px;font-weight:700;color:{_TXT};"
                f"font-family:monospace;text-transform:uppercase;letter-spacing:1px;"
                f"margin:8px 0 4px;'>Individual Calls</div>",
                unsafe_allow_html=True,
            )

            for i, entry in enumerate(reversed(log), 1):
                pc = _PURPOSE_COLORS.get(entry["purpose"], _PUR)
                pl = _PURPOSE_LABELS.get(entry["purpose"], entry["purpose"])
                st.markdown(
                    f"<div style='background:{_BG2};border:1px solid {_BDR};"
                    f"border-left:3px solid {pc};border-radius:4px;"
                    f"padding:5px 8px;margin-bottom:4px;font-family:monospace;'>"
                    f"<div style='display:flex;justify-content:space-between;"
                    f"align-items:center;'>"
                    f"<span style='font-size:10px;color:{pc};font-weight:700;'>{pl}</span>"
                    f"<span style='font-size:9px;color:{_LBL};'>{entry['ts']}</span>"
                    f"</div>"
                    f"<div style='font-size:10px;color:{_LBL};margin-top:2px;'>"
                    f"↑{entry['prompt_tokens']:,} ↓{entry['output_tokens']:,} tok"
                    f" · <span style='color:{_TXT};font-weight:600;'>"
                    f"${entry['cost_usd']:.5f}</span></div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # ── Reset button ──────────────────────────────────────────────────────────
    if st.button("🔄 Reset cost counter", key="reset_llm_cost", use_container_width=True):
        st.session_state["_llm_usage_log"] = []
        st.session_state["_llm_totals"]    = {
            "prompt_tokens": 0, "output_tokens": 0,
            "total_tokens": 0, "cost_usd": 0.0, "calls": 0,
        }
        st.rerun()


def render_nav_panel(data: list, selected_sheet: str) -> int | None:
    """
    Renders the claim list navigator inside a fixed-height container,
    followed by the LLM cost panel.
    Returns the index the user clicked, or None if nothing was clicked.
    """
    new_idx: int | None = None

    with st.container(height=500, border=False):   # reduced from 700 to make room for cost panel
        st.markdown("<p class='section-lbl'>Claim Records</p>", unsafe_allow_html=True)

        _search_k = f"search_{selected_sheet}"
        _search_q = st.text_input(
            "",
            key=_search_k,
            placeholder="🔍 Filter claims…",
            label_visibility="collapsed",
        )
        _q_lower = _search_q.strip().lower()

        if _q_lower:
            _hit_indices = [
                i
                for i, row in enumerate(data)
                if any(
                    _q_lower in str(v.get("modified", v.get("value", ""))).lower()
                    for v in row.values()
                )
            ]
            st.markdown(
                f"<div style='font-size:var(--sz-xs);color:var(--green);"
                f"font-family:var(--mono);margin:3px 0 6px;'>"
                f"● {len(_hit_indices)} match{'es' if len(_hit_indices) != 1 else ''}</div>",
                unsafe_allow_html=True,
            )
        else:
            _hit_indices = list(range(len(data)))

        for i in _hit_indices:
            row_data = data[i]
            is_sel   = "selected-card" if st.session_state.selected_idx == i else ""
            c_id     = detect_claim_id(row_data, i)
            c_name   = get_val(
                row_data,
                [
                    "Insured Name", "Claimant Name", "Claimant", "Name",
                    "Company", "TPA_NAME", "insured", "claimant",
                    "injured party", "employee name", "driver name",
                ],
                "Unknown Entity",
            )
            raw_st   = get_val(
                row_data,
                ["Status", "Claim Status", "CLAIM_STATUS", "current status", "file status"],
                "",
            )
            c_status = raw_st or (
                "Yet to Review" if i == 0 else "In Progress" if i == 1 else "Submitted"
            )
            s_cls = (
                "status-progress"
                if "progress" in c_status.lower() or c_status.lower() == "open"
                else "status-text"
            )

            st.markdown(
                f"""<div class="claim-card {is_sel}">
                    <div style="font-weight:700;color:var(--t0);font-size:var(--sz-body);
                         font-family:var(--font-head);">{c_id}</div>
                    <div style="color:var(--t1);font-size:var(--sz-xs);margin-top:3px;
                         font-family:var(--font);">{c_name}</div>
                    <div class="{s_cls}">{c_status}</div>
                </div>""",
                unsafe_allow_html=True,
            )

            if st.button(
                "Select",
                key=f"sel_{selected_sheet}_{i}",
                use_container_width=True,
            ):
                new_idx = i

    # ── LLM cost panel lives below the claim list, outside the scrollable area ──
    _render_llm_cost_panel()

    return new_idx