from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend" / "src"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    print(f"patched: {path.relative_to(ROOT)}")


def replace_between(text: str, start_marker: str, end_marker: str, replacement: str, path: Path) -> str:
    start = text.find(start_marker)
    if start == -1:
        raise RuntimeError(f"Could not find start marker in {path}: {start_marker!r}")
    end = text.find(end_marker, start)
    if end == -1:
        raise RuntimeError(f"Could not find end marker in {path}: {end_marker!r}")
    return text[:start] + replacement.rstrip() + "\n" + text[end:]


def upsert_before_style_end(text: str, marker: str, block: str, path: Path) -> str:
    if marker in text:
        start = text.find(marker)
        end_marker = f"/* END {marker.strip('/* ').strip()} */"
        end = text.find(end_marker, start)
        if end != -1:
            end += len(end_marker)
            return text[:start] + block.rstrip() + "\n" + text[end:]
    idx = text.rfind("</style>")
    if idx == -1:
        raise RuntimeError(f"Could not find </style> in {path}")
    return text[:idx].rstrip() + "\n\n" + block.rstrip() + "\n" + text[idx:]


def append_global_mobile_css() -> None:
    path = FRONTEND / "assets" / "styles.css"
    text = read(path)
    marker = "/* MOBILE-FIRST HARDENING PATCH */"
    end_marker = "/* END MOBILE-FIRST HARDENING PATCH */"
    block = f"""
{marker}
html.mobile-nav-locked,
body.mobile-nav-locked {{
  overscroll-behavior: none;
}}

body.mobile-nav-locked {{
  position: fixed;
  width: 100%;
  overflow: hidden;
  touch-action: none;
}}

.mobile-scroll-area {{
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
}}

@media (max-width: 820px) {{
  :root {{
    --page-pad: 12px;
    --card-radius: 18px;
  }}

  html,
  body,
  #app {{
    min-height: 100svh;
  }}

  body {{
    font-size: 15px;
  }}

  input,
  select,
  textarea {{
    font-size: 16px;
  }}

  .page {{
    overflow-x: hidden;
  }}

  .content,
  .card,
  .hero-panel,
  .table-wrap,
  .toolbar,
  .filter-grid,
  .stat-grid,
  .grid {{
    min-width: 0;
    max-width: 100%;
  }}

  .card {{
    padding: 14px;
    border-radius: 18px;
    box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
  }}

  .hero-panel {{
    display: grid;
    gap: 12px;
  }}

  .hero-subtitle {{
    line-height: 1.45;
    font-size: 14px;
  }}

  .toolbar,
  .form-actions,
  .button-row,
  .review-modal-actions,
  .submit-actions,
  .pdf-actions,
  .pagination-bar {{
    display: grid;
    grid-template-columns: 1fr;
    align-items: stretch;
    justify-content: stretch;
    gap: 10px;
    width: 100%;
  }}

  .toolbar > *,
  .form-actions > *,
  .button-row > *,
  .review-modal-actions > *,
  .submit-actions > *,
  .pdf-actions > *,
  .pagination-bar > * {{
    min-width: 0;
  }}

  .btn,
  a.btn,
  button.btn {{
    width: 100%;
    min-height: 44px;
    white-space: normal;
    text-align: center;
  }}

  .btn-sm {{
    min-height: 40px;
  }}

  .grid-2,
  .grid-3,
  .grid-4,
  .filter-grid,
  .stat-grid {{
    grid-template-columns: 1fr !important;
  }}

  .span-2 {{
    grid-column: auto !important;
  }}

  .table-wrap {{
    width: 100%;
    max-width: calc(100vw - 24px);
    overflow-x: auto;
    overflow-y: hidden;
    border-radius: 16px;
    -webkit-overflow-scrolling: touch;
  }}

  .table {{
    min-width: 720px;
  }}

  .table th,
  .table td {{
    padding: 10px 11px;
    overflow-wrap: anywhere;
    word-break: break-word;
  }}

  .desktop-table {{
    display: none !important;
  }}

  .mobile-list {{
    display: grid !important;
    gap: 12px;
  }}

  .review-notice-modal,
  .tracker-modal-card,
  .media-modal-card {{
    width: min(100%, calc(100vw - 24px));
    max-height: calc(100svh - 24px);
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
  }}
}}

@media (max-width: 700px) {{
  .table-wrap.mobile-cards {{
    overflow-x: visible;
    border: 0;
    background: transparent;
    border-radius: 0;
  }}

  .table-wrap.mobile-cards .table {{
    min-width: 0;
    width: 100%;
    border-collapse: separate;
    border-spacing: 0 12px;
  }}

  .table-wrap.mobile-cards thead {{
    display: none;
  }}

  .table-wrap.mobile-cards tbody,
  .table-wrap.mobile-cards tr {{
    display: block;
    width: 100%;
  }}

  .table-wrap.mobile-cards tr {{
    background: #fff;
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 10px 12px;
    box-shadow: 0 8px 24px rgba(15, 23, 42, .06);
    margin-bottom: 12px;
  }}

  .table-wrap.mobile-cards td {{
    display: grid;
    grid-template-columns: minmax(96px, 38%) minmax(0, 1fr);
    gap: 12px;
    border-bottom: 1px solid #edf2f7;
    padding: 10px 0;
    text-align: right;
  }}

  .table-wrap.mobile-cards td:last-child {{
    border-bottom: 0;
  }}

  .table-wrap.mobile-cards td::before {{
    content: attr(data-label);
    color: #64748b;
    font-size: 12px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: .04em;
    text-align: left;
  }}
}}

@media (max-width: 420px) {{
  .content {{
    padding-left: 10px !important;
    padding-right: 10px !important;
  }}

  .table-wrap {{
    max-width: calc(100vw - 20px);
  }}

  .card-title {{
    display: grid;
    gap: 8px;
  }}
}}
{end_marker}
"""
    if marker in text and end_marker in text:
        start = text.find(marker)
        end = text.find(end_marker, start) + len(end_marker)
        text = text[:start] + block.rstrip() + text[end:]
    else:
        text = text.rstrip() + "\n\n" + block.rstrip() + "\n"
    write(path, text)


def patch_app_layout() -> None:
    path = FRONTEND / "components" / "AppLayout.vue"
    text = read(path)

    old_lock = """function lockPageScroll() {
  if (typeof window === 'undefined' || typeof document === 'undefined') return
  lockedScrollY = window.scrollY || document.documentElement.scrollTop || 0
  previousBodyPosition = document.body.style.position
  previousBodyTop = document.body.style.top
  previousBodyLeft = document.body.style.left
  previousBodyRight = document.body.style.right
  previousBodyWidth = document.body.style.width
  previousBodyOverflow = document.body.style.overflow
  previousHtmlOverscroll = document.documentElement.style.overscrollBehavior
  document.body.style.position = 'fixed'
  document.body.style.top = `-${lockedScrollY}px`
  document.body.style.left = '0'
  document.body.style.right = '0'
  document.body.style.width = '100%'
  document.body.style.overflow = 'hidden'
  document.documentElement.style.overscrollBehavior = 'none'
}

function unlockPageScroll() {
  if (typeof window === 'undefined' || typeof document === 'undefined') return
  document.body.style.position = previousBodyPosition
  document.body.style.top = previousBodyTop
  document.body.style.left = previousBodyLeft
  document.body.style.right = previousBodyRight
  document.body.style.width = previousBodyWidth
  document.body.style.overflow = previousBodyOverflow
  document.documentElement.style.overscrollBehavior = previousHtmlOverscroll
  window.scrollTo(0, lockedScrollY)
}"""
    new_lock = """function lockPageScroll() {
  if (typeof window === 'undefined' || typeof document === 'undefined') return
  lockedScrollY = window.scrollY || document.documentElement.scrollTop || 0
  previousBodyPosition = document.body.style.position
  previousBodyTop = document.body.style.top
  previousBodyLeft = document.body.style.left
  previousBodyRight = document.body.style.right
  previousBodyWidth = document.body.style.width
  previousBodyOverflow = document.body.style.overflow
  previousHtmlOverscroll = document.documentElement.style.overscrollBehavior
  document.documentElement.classList.add('mobile-nav-locked')
  document.body.classList.add('mobile-nav-locked')
  document.body.style.top = `-${lockedScrollY}px`
  document.body.style.left = '0'
  document.body.style.right = '0'
  document.body.style.width = '100%'
}

function unlockPageScroll() {
  if (typeof window === 'undefined' || typeof document === 'undefined') return
  document.documentElement.classList.remove('mobile-nav-locked')
  document.body.classList.remove('mobile-nav-locked')
  document.body.style.position = previousBodyPosition
  document.body.style.top = previousBodyTop
  document.body.style.left = previousBodyLeft
  document.body.style.right = previousBodyRight
  document.body.style.width = previousBodyWidth
  document.body.style.overflow = previousBodyOverflow
  document.documentElement.style.overscrollBehavior = previousHtmlOverscroll
  window.scrollTo(0, lockedScrollY)
}"""
    if old_lock in text:
        text = text.replace(old_lock, new_lock)

    mobile_block = """
@media (max-width: 820px) {
  .shell { min-height: 100svh; }
  .sidebar {
    --safe-top: env(safe-area-inset-top, 0px);
    --safe-bottom: env(safe-area-inset-bottom, 0px);
    --header-x: 10px;
    --header-top: 8px;
    --header-height: 58px;
    --header-total: calc(var(--safe-top) + var(--header-top) + var(--header-height) + 10px);
    width: 100%;
    min-height: 0;
    height: var(--header-total);
    max-height: 100svh;
    position: fixed;
    inset: 0 0 auto 0;
    z-index: 1000;
    display: flex;
    flex-direction: column;
    padding: calc(var(--safe-top) + var(--header-top)) var(--header-x) 10px;
    overflow: hidden;
    border-radius: 0 0 24px 24px;
    box-shadow: 0 12px 30px rgba(8,31,80,.20);
    transition: height .22s ease, border-radius .22s ease, box-shadow .22s ease;
    touch-action: pan-y;
  }
  .sidebar.menu-open {
    height: 100svh;
    max-height: 100svh;
    border-radius: 0;
    box-shadow: 0 26px 72px rgba(2,6,23,.36);
  }
  .brand-card {
    flex: 0 0 auto;
    min-height: var(--header-height);
    padding: 8px 10px;
    border-radius: 18px;
    gap: 8px;
    box-shadow: inset 0 1px 0 rgba(255,255,255,.14);
  }
  .brand-left { flex: 1 1 auto; min-width: 0; justify-content: flex-start; }
  .brand-logo { width: 58px; border-radius: 10px; }
  .brand-card strong { font-size: 15px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .brand-copy > span { display: none; }
  .mobile-menu-btn { display: inline-flex; }
  .mobile-logout-btn { display: inline-flex; align-items: center; justify-content: center; min-height: 38px; padding: 0 12px; border: 1px solid rgba(255,255,255,.24); border-radius: 999px; background: rgba(255,255,255,.16); color: white; font-size: 13px; font-weight: 900; white-space: nowrap; flex: 0 0 auto; cursor: pointer; -webkit-tap-highlight-color: transparent; }
  .mobile-backdrop { display: block; position: fixed; inset: 0; z-index: 999; background: rgba(15,23,42,.38); backdrop-filter: blur(3px); }
  .main-nav {
    flex: 1 1 auto;
    min-height: 0;
    margin: 10px 0 0;
    padding: 0 0 calc(24px + var(--safe-bottom));
    grid-template-columns: 1fr;
    gap: 8px;
    max-height: 0;
    overflow-y: hidden;
    overscroll-behavior: contain;
    -webkit-overflow-scrolling: touch;
    opacity: 0;
    visibility: hidden;
    pointer-events: none;
    transform: translateY(-6px);
    transition: opacity .18s ease, transform .18s ease, visibility .18s ease;
    touch-action: pan-y;
  }
  .menu-open .main-nav {
    max-height: none;
    overflow-y: auto;
    opacity: 1;
    visibility: visible;
    pointer-events: auto;
    transform: translateY(0);
  }
  .drawer-user-card { display: block; padding: 12px 14px; border-radius: 16px; background: rgba(255,255,255,.11); border: 1px solid rgba(255,255,255,.12); margin-bottom: 6px; color: white; }
  .drawer-user-card small { display: block; color: #bfdbfe; font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 4px; }
  .drawer-user-card strong { display: block; font-size: 14px; line-height: 1.3; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .drawer-user-card span { display: inline-flex; margin-top: 6px; padding: 4px 8px; border-radius: 999px; background: rgba(255,255,255,.16); color: white; font-size: 11px; font-weight: 900; }
  .main-nav a {
    display: flex;
    align-items: center;
    justify-content: space-between;
    min-height: 48px;
    padding: 13px 14px;
    border-radius: 14px;
    background: rgba(255,255,255,.075);
    line-height: 1.25;
    word-break: break-word;
    flex: 0 0 auto;
  }
  .main-nav a::after { content: '›'; opacity: .72; font-size: 20px; line-height: 1; margin-left: auto; }
  .main-nav a .nav-review-pill { margin-left: auto; flex: 0 0 auto; }
  .main-nav a:has(.nav-review-pill)::after { content: ''; }
  .sidebar-note { display: none; }
  .content { margin-left: 0; padding: calc(var(--header-total, 86px) + 14px) 12px calc(18px + var(--safe-bottom)); }
  .topbar { display: none; }
  .review-notice-backdrop { padding: 12px; align-items: end; }
  .review-notice-modal { padding: 22px 16px; border-radius: 22px; width: 100%; max-height: calc(100svh - 24px); }
  .review-notice-actions { display: grid; grid-template-columns: 1fr; }
}
"""
    text = replace_between(text, "@media (max-width: 820px) {", "@media (max-width: 420px)", mobile_block, path)
    write(path, text)


def patch_weekly_compliance() -> None:
    path = FRONTEND / "views" / "WeeklyComplianceView.vue"
    if not path.exists():
        return
    text = read(path)
    replacements = {
        '<div class="table-wrap compliance-table-wrap">': '<div class="table-wrap compliance-table-wrap mobile-cards">',
        '<td>\n                <strong>{{ row.inspector_name }}</strong>': '<td data-label="Inspector">\n                <strong>{{ row.inspector_name }}</strong>',
        '<td>\n                <strong>{{ row.station_name }}</strong>': '<td data-label="Station">\n                <strong>{{ row.station_name }}</strong>',
        '<td>{{ row.required }}</td>': '<td data-label="Target">{{ row.required }}</td>',
        '<td>{{ row.completed }}</td>': '<td data-label="Done">{{ row.completed }}</td>',
        '<td><strong>{{ row.remaining }}</strong></td>': '<td data-label="Remaining"><strong>{{ row.remaining }}</strong></td>',
        '<td><span class="badge" :class="statusClass(row)">{{ statusLabel(row.status) }}</span></td>': '<td data-label="Status"><span class="badge" :class="statusClass(row)">{{ statusLabel(row.status) }}</span></td>',
        '<td>{{ row.line_manager || \'-\' }}</td>': '<td data-label="Line Manager">{{ row.line_manager || \'-\' }}</td>',
        '<td>{{ row.dgm || \'-\' }}</td>': '<td data-label="DGM">{{ row.dgm || \'-\' }}</td>',
        '<td>{{ row.gm || \'-\' }}</td>': '<td data-label="GM/Ops">{{ row.gm || \'-\' }}</td>',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    mobile_css = """
/* MOBILE-FIRST WEEKLY COMPLIANCE PATCH */
@media (max-width: 700px) {
  .summary-grid { grid-template-columns: 1fr 1fr; gap: 10px; }
  .summary-card { padding: 13px; border-radius: 16px; }
  .summary-card strong { font-size: 26px; }
  .week-strip { display: grid; gap: 6px; }
  .compliance-table { min-width: 0; }
  .compliance-table tbody tr.pending,
  .compliance-table tbody tr.complete { background: white; }
  .compliance-table td { align-items: start; }
}
@media (max-width: 420px) {
  .summary-grid { grid-template-columns: 1fr; }
}
/* END MOBILE-FIRST WEEKLY COMPLIANCE PATCH */
"""
    text = upsert_before_style_end(text, "/* MOBILE-FIRST WEEKLY COMPLIANCE PATCH */", mobile_css, path)
    write(path, text)


def patch_help_forum() -> None:
    path = FRONTEND / "views" / "HelpForumView.vue"
    if not path.exists():
        return
    text = read(path)
    css = """
/* MOBILE-FIRST HELP FORUM PATCH */
@media (max-width: 760px) {
  .forum-list-card,
  .topic-detail-card { min-height: auto; }
  .topic-card-head,
  .comment-head,
  .detail-header,
  .media-modal-header { display: grid; grid-template-columns: 1fr; }
  .topic-card { padding: 12px; border-radius: 16px; }
  .topic-card p { -webkit-line-clamp: 3; }
  .topic-meta { display: grid; grid-template-columns: 1fr; gap: 4px; }
  .question-body,
  .comment-card,
  .admin-box { padding: 12px; border-radius: 16px; }
  .form-actions { display: grid; grid-template-columns: 1fr; justify-content: stretch; }
  .media-list { display: grid; grid-template-columns: 1fr; }
  .media-chip { width: 100%; border-radius: 14px; text-align: left; overflow-wrap: anywhere; }
  .media-modal-backdrop { padding: 10px; align-items: end; }
  .media-modal-card { width: 100%; max-height: calc(100svh - 20px); border-radius: 18px 18px 0 0; padding: 14px; }
  .media-preview-body { min-height: 180px; }
  .media-preview-body img,
  .media-preview-body video { max-height: 68svh; }
  .media-preview-body iframe { height: 72svh; }
  .floating-error { left: 10px; right: 10px; bottom: 10px; max-width: none; }
}
/* END MOBILE-FIRST HELP FORUM PATCH */
"""
    text = upsert_before_style_end(text, "/* MOBILE-FIRST HELP FORUM PATCH */", css, path)
    write(path, text)


def patch_start_view() -> None:
    path = FRONTEND / "views" / "InspectionStartView.vue"
    if not path.exists():
        return
    text = read(path)
    css = """
/* MOBILE-FIRST START INSPECTION PATCH */
@media (max-width: 760px) {
  form.card.grid { gap: 14px; }
  .mini { padding: 12px; }
  .hint { line-height: 1.4; }
}
/* END MOBILE-FIRST START INSPECTION PATCH */
"""
    text = upsert_before_style_end(text, "/* MOBILE-FIRST START INSPECTION PATCH */", css, path)
    write(path, text)


def main() -> None:
    required = [FRONTEND / "components" / "AppLayout.vue", FRONTEND / "assets" / "styles.css"]
    for path in required:
        if not path.exists():
            raise SystemExit(f"Missing expected file: {path}")
    patch_app_layout()
    append_global_mobile_css()
    patch_weekly_compliance()
    patch_help_forum()
    patch_start_view()
    print("\nMobile-first UI patch applied. Rebuild frontend/API with: docker compose up -d --build frontend api")


if __name__ == "__main__":
    main()
