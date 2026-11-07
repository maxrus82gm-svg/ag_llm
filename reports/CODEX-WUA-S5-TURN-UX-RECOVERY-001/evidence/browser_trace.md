# Bounded actual Chromium observations

2026-11-07. Only this task's disposable loopback server and synthetic A/B Chats.
This note is a reconstruction from actual CUA outputs; saved DOM/screenshot and
server snapshots accompany it. No HAR was captured. Read-only Playwright state,
keyboard operations, documented viewport capability and screenshots were used.

- Initial pipe driver saw stdin EOF and stopped before browser actions. A PTY
  was used to keep the temporary fixture alive. Empty initial fixture artifacts
  can coexist with later session artifacts; these are not user Chats.
- Working first session: port 65326, selected A (B was newest). Enter sent
  S5_BROWSER_SUCCESS. Two keyboard status checks visibly produced completed
  check numbers 1 and 2; the existing successful reply remained.
- S5_BROWSER_CANCEL_AFTER_START: fake transport held for eight seconds. A
  check showed both Turn status and user message badge as active/running.
  Cancel returned UNKNOWN; at this stage the message badge waited for the
  delayed POST to finish. This directly observed inconsistency got its own
  failing JS regression before the small cancel/history refresh correction.
- Reload retained selected A, the cancelled user and UNKNOWN. B was empty;
  returning to A retained the success pair and cancelled user. No new send
  resulted from status checks, reload or Chat switches.
- At requested 480px viewport: keyboard check and Tab worked; DOM observation
  reported scrollWidth == clientWidth == 465 and focus chatTurnNew, with the
  Russian tooltip present. The full-page JPEG was visually unusable. A later
  DOM-style/geometry inspection timed out after 300 seconds. This does NOT
  establish whether CSS, capture, or helper evaluation was at fault. No 480px
  visual PASS. Browser documentation was consulted and viewport reset succeeded.
- Final session after cancel-refresh correction: port 50606. One synthetic
  S5_BROWSER_CANCEL_FINAL was sent. Check showed running; Cancel immediately
  changed BOTH status and message badge to UNKNOWN before the delayed POST
  completed. Screenshot cancel_badge_immediate.jpg binds to final UI hash in
  browser_final/session.json.
- Reload in final session retained selected A and that exact cancelled user;
  manual check completed. DOM saved as browser_final/reload_dom.txt.
- 720px viewport was visibly readable in browser_final/narrow_720.jpg. The
  long Russian button, UNKNOWN badge, check acknowledgement and composer fit
  the narrow view. Viewport reset to normal before finishing.
- The final own fixture was shut down normally and saved RAW/history/fake
  payloads before cleaning up its own TEMP directory. Pressing status check
  against the now unavailable loopback server showed the explicit Russian
  error and did not create a send. DOM/JPEG saved as browser_final/check_error*.

Source hashes differ between initial and final UI session only because the
observed cancellation badge issue was repaired in between. Final session hash
is checked against current ui.py by finalize.py. Fake request counts are saved
by the server driver, not inferred from the mere presence of a message pair.

No new code or persistent profile was injected into the browser. No real
provider, credentials, user TEST Chat or STANDARD storage was used.
