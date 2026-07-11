from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP_LAYOUT = ROOT / "frontend" / "src" / "components" / "AppLayout.vue"

MOBILE_820_BLOCK = r'''@media (max-width: 820px) {
  .shell {
    --mobile-safe-top: env(safe-area-inset-top, 0px);
    --mobile-header-x: 10px;
    --mobile-header-top: 8px;
    --mobile-header-height: 58px;
    --mobile-header-bottom: 10px;
    --mobile-header-total: calc(var(--mobile-safe-top) + var(--mobile-header-top) + var(--mobile-header-height) + var(--mobile-header-bottom));
    display: block;
  }

  /*
    Mobile shell rule:
    - closed header is sticky and stays in normal document flow
    - content therefore starts AFTER the header, not behind it
    - open drawer becomes fixed/full-screen and scrollable
  */
  .sidebar {
    width: 100%;
    min-height: 0;
    height: auto;
    max-height: none;
    position: sticky;
    top: 0;
    inset: auto;
    z-index: 1000;
    padding: calc(var(--mobile-safe-top) + var(--mobile-header-top)) var(--mobile-header-x) var(--mobile-header-bottom);
    overflow: visible;
    border-radius: 0 0 24px 24px;
    box-shadow: 0 12px 30px rgba(8,31,80,.20);
    overscroll-behavior: contain;
    -webkit-overflow-scrolling: touch;
    transition: border-radius .22s ease, box-shadow .22s ease;
  }

  .sidebar.menu-open {
    position: fixed;
    inset: 0 0 auto 0;
    height: 100dvh;
    max-height: 100dvh;
    overflow: hidden;
    border-radius: 0;
    box-shadow: 0 26px 72px rgba(2,6,23,.36);
  }

  @supports (height: 100svh) {
    .sidebar.menu-open {
      height: 100svh;
      max-height: 100svh;
    }
  }

  .brand-card {
    min-height: var(--mobile-header-height);
    padding: 8px 10px;
    border-radius: 18px;
    gap: 8px;
    box-shadow: inset 0 1px 0 rgba(255,255,255,.14);
  }
  .brand-left { flex: 1 1 auto; min-width: 0; justify-content: flex-start; }
  .brand-logo { width: 58px; border-radius: 10px; }
  .brand-card strong { font-size: 15px; white-space: nowrap; }
  .brand-copy > span { display: none; }
  .mobile-menu-btn { display: inline-flex; }
  .mobile-logout-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 38px;
    padding: 0 12px;
    border: 1px solid rgba(255,255,255,.24);
    border-radius: 999px;
    background: rgba(255,255,255,.16);
    color: white;
    font-size: 13px;
    font-weight: 900;
    white-space: nowrap;
    flex: 0 0 auto;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
  }
  .mobile-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    z-index: 999;
    background: rgba(15,23,42,.38);
    backdrop-filter: blur(3px);
  }

  .main-nav {
    margin: 0;
    padding: 0;
    grid-template-columns: 1fr;
    gap: 8px;
    max-height: 0;
    overflow: hidden;
    overscroll-behavior: contain;
    -webkit-overflow-scrolling: touch;
    opacity: 0;
    visibility: hidden;
    pointer-events: none;
    transform: translateY(-6px);
    transition: max-height .22s ease, opacity .18s ease, transform .18s ease, visibility .18s ease, margin .18s ease, padding .18s ease;
  }
  .menu-open .main-nav {
    margin-top: 10px;
    padding-bottom: calc(20px + env(safe-area-inset-bottom, 0px));
    max-height: calc(100dvh - var(--mobile-header-total) - env(safe-area-inset-bottom, 0px));
    overflow-y: auto;
    opacity: 1;
    visibility: visible;
    pointer-events: auto;
    transform: translateY(0);
  }
  @supports (height: 100svh) {
    .menu-open .main-nav {
      max-height: calc(100svh - var(--mobile-header-total) - env(safe-area-inset-bottom, 0px));
    }
  }

  .drawer-user-card {
    display: block;
    padding: 12px 14px;
    border-radius: 16px;
    background: rgba(255,255,255,.11);
    border: 1px solid rgba(255,255,255,.12);
    margin-bottom: 6px;
    color: white;
  }
  .drawer-user-card small { display: block; color: #bfdbfe; font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 4px; }
  .drawer-user-card strong { display: block; font-size: 14px; line-height: 1.3; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .drawer-user-card span { display: inline-flex; margin-top: 6px; padding: 4px 8px; border-radius: 999px; background: rgba(255,255,255,.16); color: white; font-size: 11px; font-weight: 900; }
  .main-nav a { display: flex; align-items: center; justify-content: space-between; min-height: 48px; padding: 13px 14px; border-radius: 14px; background: rgba(255,255,255,.075); }
  .main-nav a::after { content: '›'; opacity: .72; font-size: 20px; line-height: 1; }
  .main-nav a:has(.nav-review-pill)::after { content: ''; }
  .sidebar-note { display: none; }

  .content {
    margin-left: 0;
    padding: 14px 14px calc(22px + env(safe-area-inset-bottom, 0px));
    min-height: auto;
    scroll-margin-top: var(--mobile-header-total);
  }
  .topbar { display: none; }
  .review-notice-backdrop { padding: 16px; }
  .review-notice-modal { padding: 24px 18px; border-radius: 24px; }
  .review-notice-actions { display: grid; grid-template-columns: 1fr; }
}'''

MOBILE_420_BLOCK = r'''@media (max-width: 420px) {
  .shell {
    --mobile-header-x: 10px;
    --mobile-header-top: 8px;
    --mobile-header-height: 54px;
    --mobile-header-bottom: 10px;
  }
  .brand-card { padding: 7px 8px; }
  .mobile-menu-btn { width: 42px; height: 42px; border-radius: 13px; }
  .brand-logo { width: 52px; }
  .brand-card strong { font-size: 14px; }
  .mobile-logout-btn { min-height: 36px; padding: 0 10px; font-size: 12px; }
}'''

MOBILE_360_BLOCK = r'''@media (max-width: 360px) {
  .brand-logo { width: 46px; }
  .brand-card strong { font-size: 13px; }
  .mobile-logout-btn { padding: 0 8px; }
}'''


def find_matching_brace(text: str, open_brace: int) -> int:
    depth = 0
    for idx in range(open_brace, len(text)):
        char = text[idx]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return idx
    raise RuntimeError("Could not find matching closing brace for media block")


def replace_media_block(text: str, marker: str, replacement: str, required: bool = False) -> tuple[str, bool]:
    start = text.find(marker)
    if start == -1:
        if required:
            raise RuntimeError(f"Could not find media block: {marker}")
        return text, False
    open_brace = text.find("{", start)
    if open_brace == -1:
        raise RuntimeError(f"Malformed media block: {marker}")
    end = find_matching_brace(text, open_brace)
    return text[:start] + replacement + text[end + 1 :], True


def main() -> None:
    if not APP_LAYOUT.exists():
        raise SystemExit(f"AppLayout.vue not found at: {APP_LAYOUT}")

    original = APP_LAYOUT.read_text(encoding="utf-8")
    updated = original
    updated, changed_820 = replace_media_block(updated, "@media (max-width: 820px)", MOBILE_820_BLOCK, required=True)
    updated, _ = replace_media_block(updated, "@media (max-width: 420px)", MOBILE_420_BLOCK, required=False)
    updated, _ = replace_media_block(updated, "@media (max-width: 360px)", MOBILE_360_BLOCK, required=False)

    if not changed_820 or updated == original:
        print("No changes were required.")
        return

    backup = APP_LAYOUT.with_suffix(APP_LAYOUT.suffix + ".bak.mobile-sticky-header")
    if not backup.exists():
        backup.write_text(original, encoding="utf-8")
    APP_LAYOUT.write_text(updated, encoding="utf-8")
    print("Mobile sticky header flow fix applied to frontend/src/components/AppLayout.vue")
    print("Backup created at:", backup)


if __name__ == "__main__":
    main()
