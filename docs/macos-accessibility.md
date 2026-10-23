# macOS selected-list accessibility crash

The macOS runtime can crash in `QMacAccessibilityElement::accessibilitySelectedChildren`
after successful parsing, when an accessibility client reads the resulting list.
The application log already contains the parse-success entry. This is separate
from Gatekeeper/notarization and from a failed network request.

Qt's synthesized row, column, and placeholder-cell objects borrow the table's
accessibility ID. Their cleanup incorrectly deletes the table interface. The
remaining selected-cell pointers can then reference freed interfaces.

Upstream tracks this as [QTBUG-149612](https://bugreports.qt.io/browse/QTBUG-149612),
with [Qt Gerrit 765434](https://codereview.qt-project.org/c/qt/qtbase/+/765434).
That change was still under review when this compatibility backport was added.

## Backport

`src/util/misc/native/qt_cocoa_ownership.m` implements the two ownership guards
in that change using the Objective-C runtime. It filters parent-managed objects
out of cache removal and clears their borrowed ID immediately before calling
Qt's original deallocator. Deleting ID zero is a no-op in the affected Qt cache;
all original array and Objective-C cleanup is preserved.

The loader runs after `QApplication` loads the Cocoa plugin, before the main
window is constructed. It is restricted to the validated Qt versions, checks
the native ivar layout, and keeps deallocation entirely in native code. It does
not disable accessibility or suppress selected children. No system settings,
background services, credentials, or download records are changed.

This uses Qt-private implementation details and should be removed once the
packaged runtime includes the upstream fix. Do not extend the version allowlist
without the native regression below. A newer version alone is not evidence that
the upstream fix is included.

## Building from source on macOS

With Apple's Command Line Tools installed, run from the repository root:

```sh
python scripts/build_macos_compat.py
python src/main.py
```

The macOS release workflow builds the library into the packaged `script`
directory. Windows and Linux do not build or load it. A paid Apple developer
membership is not needed to compile or test this local library.

## Native regression

Install the intended PySide6 version in an isolated environment, then run in a
logged-in macOS GUI session:

```sh
python scripts/build_macos_compat.py --test-probe
python tests/macos_accessibility_regression.py --patched
```

The test uses only its own synthetic Qt widgets and native Cocoa objects. It
does not query other apps or need Accessibility permission. It checks 1,400
selected/empty-selection reads across table column changes and tree model
resets, expected selected-child counts and native roles, stable parent-table
IDs, and widget destruction. The native `QNSView` entry point is activated so
Qt emits real accessibility updates when models change. `QAccessible.setActive`
alone does not activate the Cocoa platform state.

For the failing control, omit `--patched`; affected runtimes terminate with
`SIGSEGV`. Run this control separately because the expected crash exits Python.
Tests require a GUI session with a display; a sandbox with no WindowServer
access aborts before the regression and is not a valid failing control.

The tree's selected items retain Qt's existing `AXGroup` mapping; table cells
remain `AXCell`. Spoken VoiceOver announcements and Intel hardware are separate
acceptance checks and are not implied by this in-process test.
