#!/usr/bin/env python3
"""Pixels-per-module (PPM) helper: why a barcode does or doesn't scan.

Five sub-commands:
  modules  - module count of a symbol (width for 1D, side length for 2D)
  ppm      - PPM from a measured pixel width + verdict
  location - PPM from what the SDK reports for a decoded code: the location corners
             (sc_barcode_get_location / barcode.location) and the module counts
             (sc_barcode_get_module_counts, C 7.5+; not in the 8.6 Python bindings)
  profile  - estimate PPM from the image itself along a line drawn across a 1D code
             (for codes the SDK neither decodes nor localizes; needs numpy + Pillow)
  plan     - PPM a camera setup will deliver (or the max distance for a target PPM)

Examples:
  ppm_calc.py modules code128 --chars 12
  ppm_calc.py ppm code39 --chars 16 --ratio 2.5 --pixels 400
  ppm_calc.py ppm qr --version 3 --pixels 120
  ppm_calc.py modules codabar --data A12345B
  ppm_calc.py modules code11 --data 123455 --ratio 2
  ppm_calc.py ppm section --section-modules 34 --pixels 340      # e.g. 2 PDF417 codewords
  ppm_calc.py location --corners 100,200 520,210 518,300 98,290 --modules-x 156
  ppm_calc.py location --corners 10,10 130,12 128,132 8,130 --modules-x 25 --modules-y 25
  ppm_calc.py location --corners 0,0 600,0 600,150 0,150 --modules-x 205 --modules-y 20 --stacked
  ppm_calc.py profile frame.png --from 120,340 --to 860,352
  ppm_calc.py plan --res-px 3840 --hfov 60 --distance-mm 1000 --x-mm 0.5 --angle 40
  ppm_calc.py plan --res-px 2592 --sensor-mm 5.6 --focal-mm 16 --x-mm 0.33 --target-ppm 3

Module counts follow the symbology standards and EXCLUDE quiet zones. Measure the
pixel width from the first to the last bar (no quiet zone) on the exact image buffer
that is passed to the SDK (not a resized preview or screenshot).
"""
import argparse, math, sys

ROBUST = 2.0      # 2-4 PPM = robust (all symbologies, 1D and 2D)
PRODUCTION = 3.0  # recommended for production margin
BORDERLINE = 1.0  # ~1-2 PPM: intermittent; below 1: very unlikely


def modules(sym, a):
    s = sym.lower()
    r = a.ratio
    if s in ("ean13", "upca"):
        return 95
    if s == "ean8":
        return 67
    if s == "upce":
        return 51
    if s in ("code128", "gs1-128"):
        # start(11) + N symbol chars(11) + check(11) + stop(13). Code set C packs 2 digits per char.
        # GS1-128 adds FNC1 (1 symbol char) - pass it in --chars.
        return 11 * (a.chars + 2) + 13
    if s == "code39":
        # each char: 3 wide + 6 narrow elements = 3R + 6; start/stop '*' added; inter-char gap (default 1X)
        n = a.chars + 2 + a.checks
        return n * (3 * r + 6) + (n - 1) * a.gap
    if s == "code93":
        # start(9) + N chars(9) + 2 check chars(9) + stop(9) + termination bar(1)
        return 9 * (a.chars + 4) + 1
    if s in ("itf", "itf14", "interleaved2of5"):
        # each digit: 2 wide + 3 narrow = 2R + 3; start 4X; stop R + 2. Digit count must be even.
        return a.chars * (2 * r + 3) + 4 + (r + 2)
    if s in ("msi", "msi-plessey"):
        # each digit: 4 bits x 3 modules = 12; start 3; stop 4
        return 12 * (a.chars + a.checks) + 7
    if s == "qr":
        return 21 + 4 * (a.version - 1)
    if s == "microqr":
        return 11 + 2 * (a.version - 1)
    if s in ("datamatrix", "dm"):
        return a.size  # modules per side incl. finder pattern, e.g. 10, 12, ... 144
    if s == "pdf417":
        # one row: start(17) + left RI(17) + data columns(17 each) + right RI(17) + stop(18)
        return 17 * a.columns + 69
    if s == "section":
        return a.section_modules
    if s == "codabar":
        # Character width depends on the character (Scandit PPM guide, wide:narrow R):
        #   standard 0-9 - $       : 2 wide + 5 narrow = 2R + 5  (10 at R = 2.5)
        #   oversized : / . + A-D  : 3 wide + 4 narrow = 3R + 4  (11.5 at R = 2.5)
        #   plus (characters - 1) inter-character gaps (default 1X, spec allows 1-4.5X)
        # --data should include the start/stop letters; if they are missing, A...A is assumed.
        if a.data:
            d = a.data.upper()
            if not (d[0] in "ABCD" and d[-1] in "ABCD"):
                d = "A" + d + "A"
            bad = [c for c in d if c not in "0123456789-$:/.+ABCD"]
            if bad:
                sys.exit(f"Not a Codabar character: {''.join(sorted(set(bad)))}")
            big = sum(1 for c in d if c in ":/.+ABCD")
            std = len(d) - big
        else:
            if not a.chars:
                sys.exit("Codabar: pass --data <content incl. start/stop> (exact) or --chars N (digits only)")
            std, big = a.chars, 2  # digits only + start/stop letters
        return std * (2 * r + 5) + big * (3 * r + 4) + (std + big - 1) * a.gap
    if s == "code11":
        # Elements per character: 3 bars + 2 spaces. Characters 0, 9 and '-' have 1 wide element (R + 4),
        # all other digits and the start/stop character have 2 (2R + 3); 1X gap after each character.
        # --data should include any check digits (C, or C and K).
        if a.data:
            bad = [c for c in a.data if c not in "0123456789-"]
            if bad:
                sys.exit(f"Not a Code 11 character: {''.join(sorted(set(bad)))}")
            one = sum(1 for c in a.data if c in "09-")
            two = len(a.data) - one
            stopstart = 2 * (2 * r + 3) + 1  # start + gap + stop
            return one * (r + 4 + 1) + two * (2 * r + 3 + 1) + stopstart
        if not a.chars:
            sys.exit("Code 11: pass --data <digits incl. check digits> (exact) or --chars N (approximate)")
        # Approximation from the Scandit PPM guide: 7N + 15 (assumes R = 2 and 1-wide characters,
        # so it is a lower bound; real codes can be up to ~1 module per character wider).
        print("note: Code 11 --chars uses the approximation 7N + 15 (lower bound). "
              "Pass --data for the exact count.", file=sys.stderr)
        return 7 * a.chars + 15
    sys.exit(f"Unsupported symbology '{sym}'. Measure a section and use: "
             "ppm section --section-modules M --pixels P")


def verdict(p):
    if p >= PRODUCTION:
        return "GOOD - comfortably in the robust range (>=3 PPM)"
    if p >= ROBUST:
        return "OK - robust range (2-4 PPM), little margin for blur/angle/print variation"
    if p >= BORDERLINE:
        return "BORDERLINE - expect intermittent results; small changes decide scan/no-scan"
    return "TOO LOW - below 1 PPM there is very little signal; reads are unlikely"


def profile(a):
    try:
        import numpy as np
        from PIL import Image
    except ImportError:
        sys.exit("profile needs numpy and Pillow (pip package names: numpy, pillow)")
    img = np.asarray(Image.open(a.image).convert("L"), dtype=float)
    (x0, y0), (x1, y1) = [tuple(float(v) for v in p.split(",")) for p in (a.p0, a.p1)]
    length = math.hypot(x1 - x0, y1 - y0)
    n = max(int(length * 4), 2)                       # sample 4x per pixel along the line
    t = np.linspace(0, 1, n)
    xs, ys = x0 + t * (x1 - x0), y0 + t * (y1 - y0)
    # bilinear sampling, averaged over 5 parallel lines (+-2 px) to reduce noise
    nx, ny = -(y1 - y0) / length, (x1 - x0) / length
    vals = []
    for off in (-2, -1, 0, 1, 2):
        X = np.clip(xs + off * nx, 0, img.shape[1] - 1.001); Y = np.clip(ys + off * ny, 0, img.shape[0] - 1.001)
        xi, yi = X.astype(int), Y.astype(int); fx, fy = X - xi, Y - yi
        v = (img[yi, xi] * (1 - fx) * (1 - fy) + img[yi, xi + 1] * fx * (1 - fy)
             + img[yi + 1, xi] * (1 - fx) * fy + img[yi + 1, xi + 1] * fx * fy)
        vals.append(v)
    v = np.mean(vals, axis=0)
    lo, hi = np.percentile(v, 5), np.percentile(v, 95)
    print(f"line length: {length:.1f} px; grey range on the line: {lo:.0f}..{hi:.0f} of 255 "
          f"(contrast {hi - lo:.0f})")
    if hi - lo < 40:
        print("warning: very low contrast on this line - the estimate is unreliable, and contrast "
              "itself is a likely cause (guide section 3.2)")
    dark = v < (lo + hi) / 2
    edges = np.flatnonzero(np.diff(dark.astype(int))) + 1
    if len(edges) < 6:
        sys.exit("found fewer than 6 bar edges: check that the line crosses the bars, or the code is too blurry/low-contrast to resolve")
    runs = np.diff(edges) / 4.0                       # element widths in px (bars and spaces, without the outer quiet zone)
    span = (edges[-1] - edges[0]) / 4.0
    narrow = np.percentile(runs, 20)                   # the narrowest elements = ~1 module
    print(f"bars+spaces found: {len(runs)}; span first to last edge: {span:.1f} px")
    print(f"narrowest elements: ~{narrow:.2f} px (20th percentile of element widths)")
    est = narrow
    if a.modules:
        est = span / a.modules
        print(f"ppm from span / known modules: {span:.1f} / {a.modules:g} = {est:.2f}")
    print(f"estimated ppm: {est:.2f}")
    print(f"verdict: {verdict(est)}")
    if not a.modules:
        print("note: without --modules this is the width of the narrowest bars, which snaps to whole pixels "
              "at low PPM (e.g. a real 1.3 can show as 1.0). Pass --modules N (count from 'modules', or a "
              "known pattern from guide section 2.2) for an exact value.")
    print("note: blur and low contrast can merge thin bars; confirm borderline results with a manual "
          "measurement (guide section 2.2)")


def add_sym_args(p):
    p.add_argument("symbology")
    p.add_argument("--chars", type=int, default=0, help="data characters / symbol characters / digits")
    p.add_argument("--ratio", type=float, default=2.5, help="wide:narrow ratio (Code39/ITF/Codabar/Code11), default 2.5")
    p.add_argument("--gap", type=float, default=1.0, help="Code39/Codabar inter-character gap in X, default 1")
    p.add_argument("--data", default="", help="Codabar / Code 11: the encoded content (exact module count)")
    p.add_argument("--checks", type=int, default=0, help="check characters (Code39/MSI)")
    p.add_argument("--version", type=int, default=1, help="QR / Micro QR version")
    p.add_argument("--size", type=int, default=0, help="Data Matrix modules per side")
    p.add_argument("--columns", type=int, default=0, help="PDF417 data columns")
    p.add_argument("--section-modules", type=float, default=0, help="modules in a measured section")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("modules"); add_sym_args(m)
    p = sub.add_parser("ppm"); add_sym_args(p)
    p.add_argument("--pixels", type=float, required=True, help="measured width (1D) or side length (2D) in px")
    lo = sub.add_parser("location")
    lo.add_argument("--corners", nargs=4, required=True, metavar="X,Y",
                    help="top-left top-right bottom-right bottom-left corners in px, as reported by the SDK")
    lo.add_argument("--modules-x", type=float, required=True, help="module count along the code (module_counts.x)")
    lo.add_argument("--modules-y", type=float, default=-1, help="modules per side across (module_counts.y); -1 for 1D")
    lo.add_argument("--stacked", action="store_true", help="PDF417/DataBar stacked: module_counts.y counts rows")
    pr = sub.add_parser("profile")
    pr.add_argument("image", help="the original frame (PNG/BMP/TIFF; not a JPEG or screenshot if avoidable)")
    pr.add_argument("--from", dest="p0", required=True, metavar="X,Y", help="point just before the first bar")
    pr.add_argument("--to", dest="p1", required=True, metavar="X,Y", help="point just after the last bar")
    pr.add_argument("--modules", type=float, default=0, help="known module count (from 'modules'), if available")
    pl = sub.add_parser("plan")
    pl.add_argument("--res-px", type=float, required=True, help="horizontal pixels of the frame given to the SDK")
    pl.add_argument("--hfov", type=float, help="horizontal field of view in degrees")
    pl.add_argument("--sensor-mm", type=float, help="active sensor width in mm (alternative to --hfov)")
    pl.add_argument("--focal-mm", type=float, help="lens focal length in mm (with --sensor-mm)")
    pl.add_argument("--x-mm", type=float, required=True, help="module size / X-dimension in mm (1 mil = 0.0254 mm)")
    pl.add_argument("--distance-mm", type=float, help="camera-to-code distance in mm")
    pl.add_argument("--angle", type=float, default=0.0, help="tilt of the code vs. the camera, degrees")
    pl.add_argument("--target-ppm", type=float, help="solve for the max distance that still gives this PPM")
    a = ap.parse_args()

    if a.cmd in ("modules", "ppm"):
        n = modules(a.symbology, a)
        print(f"modules: {n:g}")
        if a.cmd == "ppm":
            v = a.pixels / n
            print(f"ppm: {a.pixels:g} px / {n:g} modules = {v:.2f}")
            print(f"verdict: {verdict(v)}")
            if v < PRODUCTION:
                print(f"to reach {PRODUCTION:g} PPM the code must span >= {n*PRODUCTION:.0f} px "
                      f"(x{PRODUCTION/v:.1f} via print size, resolution or distance)")
        return

    if a.cmd == "location":
        c = [tuple(float(v) for v in xy.split(",")) for xy in a.corners]
        d = lambda p, q: math.hypot(q[0] - p[0], q[1] - p[1])
        along = (d(c[0], c[1]) + d(c[3], c[2])) / 2          # top and bottom edge
        across = (d(c[0], c[3]) + d(c[1], c[2])) / 2          # left and right edge
        v = along / a.modules_x
        print(f"edge along the code: {along:.1f} px / {a.modules_x:g} modules = {v:.2f} PPM")
        if a.modules_y > 0:
            v2 = across / a.modules_y
            print(f"edge across the code: {across:.1f} px / {a.modules_y:g} = {v2:.2f} px per module/row")
            if a.stacked:   # y counts rows, not modules
                print("note: stacked code - y counts rows, so the PPM is the value along the code")
            else:
                v = min(v, v2)
        print(f"verdict: {verdict(v)}")
        print("note: the reported location is approximate; treat this as an estimate of the margin")
        return

    if a.cmd == "profile":
        profile(a)
        return

    # plan
    if a.hfov:
        fov_per_mm = 2 * math.tan(math.radians(a.hfov / 2))          # FOV width per mm of distance
    elif a.sensor_mm and a.focal_mm:
        fov_per_mm = a.sensor_mm / a.focal_mm
    else:
        sys.exit("plan needs --hfov, or --sensor-mm and --focal-mm")
    cos = math.cos(math.radians(a.angle))
    if a.target_ppm:
        d = a.res_px * a.x_mm * cos / (fov_per_mm * a.target_ppm)
        print(f"max distance for {a.target_ppm:g} PPM at {a.angle:g} deg: {d:.0f} mm "
              f"(FOV width there: {fov_per_mm*d:.0f} mm)")
        return
    if not a.distance_mm:
        sys.exit("plan needs --distance-mm or --target-ppm")
    w = fov_per_mm * a.distance_mm
    pxmm = a.res_px / w
    v = pxmm * a.x_mm * cos
    print(f"FOV width: {w:.0f} mm, {pxmm:.2f} px/mm")
    print(f"ppm: {v:.2f} (X={a.x_mm:g} mm, angle {a.angle:g} deg)")
    print(f"verdict: {verdict(v)}")


if __name__ == "__main__":
    main()
