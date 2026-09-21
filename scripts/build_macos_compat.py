"""Build the small Cocoa ownership backport; no Qt SDK or paid signing needed."""
import argparse
from pathlib import Path
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
                        default=root / 'src/util/misc/qt_cocoa_ownership.dylib')
    parser.add_argument('--test-probe', action='store_true')
    args = parser.parse_args()
    if sys.platform != 'darwin':
        parser.error('This compatibility library is only built on macOS.')

    compiler = subprocess.check_output(['xcrun', '--find', 'clang'], text=True).strip()
    source = root / 'src/util/misc/native/qt_cocoa_ownership.m'
    outputs = [(source, args.output)]
    if args.test_probe:
        outputs.append((root / 'tests/native/qt_cocoa_probe.m',
                        root / 'tests/native/qt_cocoa_probe.dylib'))
    for source, output in outputs:
        output.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([compiler, '-dynamiclib', '-fno-objc-arc', '-Wall', '-Wextra',
                        '-Werror', '-mmacosx-version-min=12.0', '-framework', 'AppKit',
                        str(source), '-o', str(output)], check=True)
        print(f'Built {output}')


if __name__ == '__main__':
    main()
