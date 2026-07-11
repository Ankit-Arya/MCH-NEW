from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
app_layout = ROOT / "frontend" / "src" / "components" / "AppLayout.vue"

if not app_layout.exists():
    raise SystemExit(f"File not found: {app_layout}")

text = app_layout.read_text(encoding="utf-8")
original = text

# 1) Define mobile header metrics on the shell, not only on .sidebar.
text = re.sub(
    r"\.shell\s*\{\s*display:\s*block;\s*min-height:\s*100vh;\s*\}",
    ".shell {\n"
    "  display: block;\n"
    "  min-height: 100vh;\n"
    "  /* Shared mobile fixed-header measurements.\n"
    "     Keep these on .shell so both .sidebar and .content can use the same height. */\n"
    "  --mobile-safe-top: env(safe-area-inset-top, 0px);\n"
    "  --mobile-header-x: 10px;\n"
    "  --mobile-header-top: 8px;\n"
    "  --mobile-header-height: 58px;\n"
    "  --mobile-header-bottom-gap: 16px;\n"
    "  --mobile-header-total: calc(var(--mobile-safe-top) + var(--mobile-header-top) + var(--mobile-header-height) + var(--mobile-header-bottom-gap));\n"
    "}",
    text,
    count=1,
)

# 2) Replace the mobile media block rules that cause overlap/cut-off.
replacements = {
    r"\.sidebar \{ --safe-top: env\(safe-area-inset-top, 0px\); --header-x: 10px; --header-top: 8px; --header-height: 58px; --header-total: calc\(var\(--safe-top\) \+ var\(--header-top\) \+ var\(--header-height\) \+ 10px\); width: 100%; min-height: 0; height: var\(--header-total\); max-height: 100dvh; position: fixed; inset: 0 0 auto 0; z-index: 1000; padding: calc\(var\(--safe-top\) \+ var\(--header-top\)\) var\(--header-x\) 10px; overflow: hidden; border-radius: 0 0 24px 24px; box-shadow: 0 12px 30px rgba\(8,31,80,\.20\); transition: height \.22s ease, border-radius \.22s ease, box-shadow \.22s ease; \}":
    ".sidebar { width: 100%; min-height: 0; height: var(--mobile-header-total); max-height: 100dvh; position: fixed; inset: 0 0 auto 0; z-index: 1000; padding: calc(var(--mobile-safe-top) + var(--mobile-header-top)) var(--mobile-header-x) var(--mobile-header-bottom-gap); overflow: hidden; border-radius: 0 0 24px 24px; box-shadow: 0 12px 30px rgba(8,31,80,.20); transition: height .22s ease, border-radius .22s ease, box-shadow .22s ease; }",

    r"\.sidebar\.menu-open \{ height: min\(100dvh, 700px\); border-radius: 0 0 26px 26px; box-shadow: 0 26px 72px rgba\(2,6,23,\.36\); \}":
    ".sidebar.menu-open { height: 100dvh; max-height: 100dvh; padding-bottom: max(16px, env(safe-area-inset-bottom, 0px)); border-radius: 0; box-shadow: 0 26px 72px rgba(2,6,23,.36); }",

    r"\.brand-card \{ min-height: var\(--header-height\); padding: 8px 10px; border-radius: 18px; gap: 8px; box-shadow: inset 0 1px 0 rgba\(255,255,255,\.14\); \}":
    ".brand-card { min-height: var(--mobile-header-height); padding: 8px 10px; border-radius: 18px; gap: 8px; box-shadow: inset 0 1px 0 rgba(255,255,255,.14); }",

    r"\.menu-open \.main-nav \{ max-height: calc\(100dvh - var\(--header-total\) - 12px\); opacity: 1; visibility: visible; pointer-events: auto; transform: translateY\(0\); \}":
    ".menu-open .main-nav { max-height: calc(100dvh - var(--mobile-header-total) - max(16px, env(safe-area-inset-bottom, 0px))); opacity: 1; visibility: visible; pointer-events: auto; transform: translateY(0); }",

    r"\.content \{ margin-left: 0; padding: calc\(var\(--header-total, 86px\) \+ 14px\) 14px 14px; \}":
    ".content { margin-left: 0; padding: calc(var(--mobile-header-total) + 10px) 14px max(18px, env(safe-area-inset-bottom, 0px)); }",
}

for pattern, replacement in replacements.items():
    text, n = re.subn(pattern, replacement, text, count=1)
    if n == 0:
        print(f"Warning: exact mobile CSS rule not found, skipped pattern: {pattern[:90]}...")

# 3) The 420px override must also set shell-level variables, not sidebar-only variables.
text = re.sub(
    r"@media \(max-width: 420px\) \{ \.sidebar \{ --header-x: 10px; --header-top: 8px; --header-height: 54px; \}",
    "@media (max-width: 420px) { .shell { --mobile-header-x: 10px; --mobile-header-top: 8px; --mobile-header-height: 54px; }",
    text,
    count=1,
)

# 4) Add mobile scroll padding so in-page focus/anchor/validation scrolls do not hide fields under the fixed header.
if "scroll-padding-top: calc(var(--mobile-header-total) + 12px);" not in text:
    text = text.replace(
        "  .topbar { display: none; }",
        "  .topbar { display: none; }\n"
        "  .shell { scroll-padding-top: calc(var(--mobile-header-total) + 12px); }",
        1,
    )

if text == original:
    raise SystemExit("No changes made. AppLayout.vue may already be patched or has unexpected CSS.")

app_layout.write_text(text, encoding="utf-8")
print("Patched mobile fixed-header offset in frontend/src/components/AppLayout.vue")
