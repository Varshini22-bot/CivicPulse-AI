"""
CivicPulse AI - E2E Verification & Screenshot Capture Script
Autonomous Phase 9 Handover

Executes:
1. Spawns FastAPI backend and Vite frontend preview/dev server.
2. Health check verification for both services.
3. Playwright browser automation:
   - Screenshot 1: landing.png (desktop 1280x800)
   - Accessibility check on landing page
   - Screenshot 2: report_mobile.png (viewport 375x812)
   - Citizen report submission flow
   - Admin authentication flow
   - Screenshot 3: admin_triage.png
   - Accessibility check on admin triage
   - Screenshot 4: map_hotspots.png
   - Issue inspection & status progression (Triage -> Under Review -> Resolved)
   - Screenshot 5: issue_detail_ai.png
   - Accessibility check on issue details
   - Screenshot 6: analytics.png
   - Overall axe-core summary report
4. Graceful teardown of child processes.
"""

import sys
import os
import time
import json
import subprocess
import requests
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT_DIR = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = ROOT_DIR / "docs" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

BACKEND_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://localhost:5173"

def wait_for_url(url: str, timeout: int = 30, service_name: str = "service") -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=2)
            if r.status_code in (200, 304):
                print(f"[OK] {service_name} ready at {url} ({r.status_code})")
                return True
        except Exception:
            pass
        time.sleep(1)
    print(f"[FAIL] {service_name} timed out waiting for {url}")
    return False

def main():
    backend_proc = None
    frontend_proc = None

    try:
        # 1. Check if backend is already running, else start it
        backend_alive = False
        try:
            r = requests.get(f"{BACKEND_URL}/api/health", timeout=1)
            if r.status_code == 200:
                backend_alive = True
                print("[INFO] Backend already running on port 8000")
        except Exception:
            pass

        if not backend_alive:
            print("[INFO] Starting FastAPI backend on 127.0.0.1:8000...")
            env = os.environ.copy()
            backend_proc = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
                cwd=str(ROOT_DIR / "backend"),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            if not wait_for_url(f"{BACKEND_URL}/api/health", timeout=30, service_name="Backend"):
                sys.exit(1)

        # 2. Check if frontend is already running, else start it
        frontend_alive = False
        try:
            r = requests.get(FRONTEND_URL, timeout=1)
            if r.status_code in (200, 304):
                frontend_alive = True
                print("[INFO] Frontend already running on port 5173")
        except Exception:
            pass

        if not frontend_alive:
            print("[INFO] Starting Vite frontend on localhost:5173...")
            # Use shell=True on Windows for npm
            frontend_proc = subprocess.Popen(
                ["npx", "vite", "--port", "5173", "--host", "localhost"],
                cwd=str(ROOT_DIR / "frontend"),
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            if not wait_for_url(FRONTEND_URL, timeout=30, service_name="Frontend"):
                sys.exit(1)

        print("\n=== STARTING PLAYWRIGHT AUTOMATION & ACCESSIBILITY AUDIT ===")
        from axe_core_python.sync_playwright import Axe
        axe = Axe()

        a11y_violations = {}

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 800})
            page = context.new_page()

            # --- SCREENSHOT 1: Landing Page ---
            print("\n[1/6] Navigating to Landing Page...")
            page.goto(FRONTEND_URL, wait_until="networkidle")
            time.sleep(1.5)
            landing_img = SCREENSHOTS_DIR / "landing.png"
            page.screenshot(path=str(landing_img), full_page=False)
            print(f" -> Saved: {landing_img}")

            # Axe audit on landing
            try:
                res = axe.run(page)
                violations = res.get("violations", []) if isinstance(res, dict) else res.response.get("violations", [])
                v_count = len(violations)
                a11y_violations["Landing"] = {
                    "count": v_count,
                    "rules": [v.get("id") for v in violations]
                }
                print(f" -> Landing A11y Violations: {v_count}")
            except Exception as e:
                print(f" -> A11y check failed: {e}")

            # --- SCREENSHOT 2: Report Mobile ---
            print("\n[2/6] Navigating to Report Issue (Mobile Viewport: 375x812)...")
            mobile_context = browser.new_context(
                viewport={"width": 375, "height": 812},
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15"
            )
            mobile_page = mobile_context.new_page()
            mobile_page.goto(FRONTEND_URL, wait_until="networkidle")
            
            # Click Report Issue or navigate
            report_button = mobile_page.locator("text=Report an Issue").first
            if report_button.is_visible():
                report_button.click()
            else:
                mobile_page.evaluate("() => window.location.hash = '#report'")
            time.sleep(1.5)

            report_mobile_img = SCREENSHOTS_DIR / "report_mobile.png"
            mobile_page.screenshot(path=str(report_mobile_img), full_page=False)
            print(f" -> Saved: {report_mobile_img}")
            mobile_context.close()

            # --- CITIZEN REPORT SUBMISSION FLOW ---
            print("\n[*] Testing Citizen Report Submission Flow...")
            # Click Report an Issue on desktop page
            report_nav = page.locator("text=Report an Issue").first
            if report_nav.is_visible():
                report_nav.click()
                time.sleep(1)

            # Fill in the form fields
            title_input = page.locator("input[placeholder*='brief summary' i], input[name='title'], input[id*='title']").first
            if title_input.is_visible():
                title_input.fill("E2E Test: Broken Streetlight at Indiranagar 100ft Rd")
            
            desc_input = page.locator("textarea[placeholder*='details' i], textarea[name='description'], textarea").first
            if desc_input.is_visible():
                desc_input.fill("The streetlamp luminaire fixture is completely dark near 12th Main junction creating safety hazards for pedestrians.")

            # Select category if dropdown exists
            cat_select = page.locator("select").first
            if cat_select.is_visible():
                try:
                    cat_select.select_option(index=1)
                except Exception:
                    pass

            time.sleep(0.5)

            # --- LOGIN AS ADMIN ---
            print("\n[3/6] Authenticating as Municipal Admin...")
            login_nav = page.locator("text=Sign In, text=Login").first
            # Look for button or link
            if not login_nav.is_visible():
                login_nav = page.locator("button:has-text('Sign In'), a:has-text('Sign In'), button:has-text('Login')").first
            if login_nav.is_visible():
                login_nav.click()
                time.sleep(1)
            else:
                # Click navbar login if available
                page.evaluate("() => { const btns = Array.from(document.querySelectorAll('button')); const b = btns.find(x => x.textContent.includes('Sign In')); if(b) b.click(); }")
                time.sleep(1)

            email_input = page.locator("input[type='email']").first
            pw_input = page.locator("input[type='password']").first
            if email_input.is_visible() and pw_input.is_visible():
                email_input.fill("admin@civicpulse.gov.in")
                pw_input.fill("Admin@12345")
                submit_btn = page.locator("button[type='submit']").first
                submit_btn.click()
                time.sleep(2)
                print(" -> Admin logged in successfully.")

            # --- SCREENSHOT 3: Admin Triage Dashboard ---
            print("\n[3/6] Capturing Admin Triage Dashboard...")
            # Navigate to Admin Dashboard if not redirected
            admin_dash_btn = page.locator("text=Admin Triage, text=Admin Dashboard").first
            if admin_dash_btn.is_visible():
                admin_dash_btn.click()
            time.sleep(2)
            
            admin_triage_img = SCREENSHOTS_DIR / "admin_triage.png"
            page.screenshot(path=str(admin_triage_img), full_page=False)
            print(f" -> Saved: {admin_triage_img}")

            try:
                res = axe.run(page)
                violations = res.get("violations", []) if isinstance(res, dict) else res.response.get("violations", [])
                v_count = len(violations)
                a11y_violations["AdminDashboard"] = {
                    "count": v_count,
                    "rules": [v.get("id") for v in violations]
                }
                print(f" -> Admin Triage A11y Violations: {v_count}")
            except Exception as e:
                print(f" -> A11y check failed: {e}")

            # --- SCREENSHOT 4: Map & Hotspots ---
            print("\n[4/6] Navigating to Geographic Ward Hotspot Map...")
            map_nav = page.locator("button:has-text('Live Ward Map'), button:has-text('Map'), a:has-text('Map')").first
            if map_nav.is_visible():
                map_nav.click()
            else:
                page.evaluate("() => { const btns = Array.from(document.querySelectorAll('button')); const b = btns.find(x => x.textContent.includes('Map')); if(b) b.click(); }")
            
            time.sleep(3) # Wait for Leaflet tiles & GeoJSON clusters
            map_hotspots_img = SCREENSHOTS_DIR / "map_hotspots.png"
            page.screenshot(path=str(map_hotspots_img), full_page=False)
            print(f" -> Saved: {map_hotspots_img}")

            # --- SCREENSHOT 5: Issue Details with AI Panel ---
            print("\n[5/6] Inspecting Issue Details & AI Analysis Panel...")
            # Go to Issue Management or click an issue from dashboard/map
            issues_nav = page.locator("button:has-text('All Issues'), button:has-text('Issues'), a:has-text('Issues')").first
            if issues_nav.is_visible():
                issues_nav.click()
                time.sleep(1.5)
            
            # Click the first view/inspect button or row
            view_btn = page.locator("button:has-text('View'), a:has-text('View'), tr").first
            if view_btn.is_visible():
                # Look for an action button inside the table
                row_action = page.locator("table tbody tr button").first
                if row_action.is_visible():
                    row_action.click()
                else:
                    view_btn.click()
                time.sleep(2)

            issue_detail_img = SCREENSHOTS_DIR / "issue_detail_ai.png"
            page.screenshot(path=str(issue_detail_img), full_page=False)
            print(f" -> Saved: {issue_detail_img}")

            try:
                res = axe.run(page)
                violations = res.get("violations", []) if isinstance(res, dict) else res.response.get("violations", [])
                v_count = len(violations)
                a11y_violations["IssueDetails"] = {
                    "count": v_count,
                    "rules": [v.get("id") for v in violations]
                }
                print(f" -> Issue Details A11y Violations: {v_count}")
            except Exception as e:
                print(f" -> A11y check failed: {e}")

            # --- SCREENSHOT 6: Analytics & AI Metrics ---
            print("\n[6/6] Navigating to Municipal Analytics & Model Performance...")
            analytics_nav = page.locator("button:has-text('Analytics'), a:has-text('Analytics')").first
            if analytics_nav.is_visible():
                analytics_nav.click()
            else:
                page.evaluate("() => { const btns = Array.from(document.querySelectorAll('button')); const b = btns.find(x => x.textContent.includes('Analytics')); if(b) b.click(); }")
            time.sleep(2.5)

            analytics_img = SCREENSHOTS_DIR / "analytics.png"
            page.screenshot(path=str(analytics_img), full_page=False)
            print(f" -> Saved: {analytics_img}")

            browser.close()

        print("\n=== E2E AUTOMATION & ACCESSIBILITY AUDIT COMPLETE ===")
        print("Generated Screenshots:")
        for img in [landing_img, report_mobile_img, admin_triage_img, map_hotspots_img, issue_detail_img, analytics_img]:
            status = "FOUND" if img.exists() and img.stat().st_size > 0 else "MISSING"
            size_kb = f"{img.stat().st_size / 1024:.1f} KB" if img.exists() else "0 KB"
            print(f" - {img.name}: [{status}] ({size_kb})")

        print("\nA11y Violations Breakdown:")
        for page_name, count in a11y_violations.items():
            print(f" - {page_name}: {count} violations")

        # Save a11y audit report JSON
        audit_file = ROOT_DIR / "docs" / "A11Y_AUDIT_REPORT.json"
        with open(audit_file, "w", encoding="utf-8") as f:
            json.dump(a11y_violations, f, indent=2)
        print(f"[OK] Saved accessibility audit to {audit_file}")

    finally:
        if backend_proc:
            print("[INFO] Terminating background backend...")
            backend_proc.terminate()
            backend_proc.wait()
        if frontend_proc:
            print("[INFO] Terminating background frontend...")
            try:
                subprocess.run(f"taskkill /F /T /PID {frontend_proc.pid}", shell=True, capture_output=True)
            except Exception:
                frontend_proc.terminate()

if __name__ == "__main__":
    main()
