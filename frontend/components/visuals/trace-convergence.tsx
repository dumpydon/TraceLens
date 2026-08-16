type ConvergenceVariant = "continuous" | "dotted" | "partial";

type ConvergencePath = {
  d: string;
  variant: ConvergenceVariant;
};

const outerExpansionPaths: readonly ConvergencePath[] = [
  { d: "M0 -18 C220 -24 420 -6 574 52 C680 92 730 150 790 180", variant: "dotted" },
  { d: "M0 -2 C224 -10 424 8 580 64 C684 102 734 154 790 180", variant: "continuous" },
  { d: "M0 14 C228 6 430 24 586 78 C690 114 738 160 790 180", variant: "partial" },
  { d: "M0 30 C232 20 436 40 592 96 C694 132 742 166 790 180", variant: "continuous" },
  { d: "M0 330 C232 340 436 320 592 264 C694 228 742 194 790 180", variant: "continuous" },
  { d: "M0 346 C228 354 430 336 586 282 C690 246 738 200 790 180", variant: "partial" },
  { d: "M0 362 C224 370 424 352 580 296 C684 258 734 206 790 180", variant: "continuous" },
  { d: "M0 378 C220 384 420 366 574 308 C680 268 730 210 790 180", variant: "dotted" },
] as const;

const backgroundPaths: readonly ConvergencePath[] = [
  { d: "M0 42 C210 -20 390 22 528 112 C650 192 692 236 790 180", variant: "dotted" },
  { d: "M0 96 C190 42 378 74 540 136 C650 178 716 196 790 180", variant: "continuous" },
  { d: "M0 264 C190 318 378 286 540 224 C650 182 716 164 790 180", variant: "continuous" },
  { d: "M0 318 C210 380 390 338 528 248 C650 168 692 124 790 180", variant: "dotted" },
] as const;

const structuralPaths: readonly ConvergencePath[] = [
  { d: "M56 20 C250 0 420 64 566 146 C650 194 708 218 790 180", variant: "continuous" },
  { d: "M32 72 C226 48 406 92 570 152 C662 186 724 196 790 180", variant: "dotted" },
  { d: "M18 132 C220 108 410 124 584 160 C674 180 728 188 790 180", variant: "continuous" },
  { d: "M0 180 C220 154 414 166 590 178 C676 184 734 182 790 180", variant: "partial" },
  { d: "M18 228 C220 252 410 236 584 200 C674 180 728 172 790 180", variant: "continuous" },
  { d: "M32 288 C226 312 406 268 570 208 C662 174 724 164 790 180", variant: "dotted" },
  { d: "M56 340 C250 360 420 296 566 214 C650 166 708 142 790 180", variant: "continuous" },
] as const;

const corePaths: readonly ConvergencePath[] = [
  { d: "M180 76 C350 68 496 124 620 170 C688 196 732 202 790 180", variant: "dotted" },
  { d: "M150 132 C332 116 494 144 630 168 C696 180 742 188 790 180", variant: "continuous" },
  { d: "M132 180 C326 204 494 194 634 182 C700 176 744 178 790 180", variant: "dotted" },
  { d: "M150 228 C332 244 494 216 630 192 C696 180 742 172 790 180", variant: "continuous" },
  { d: "M180 284 C350 292 496 236 620 190 C688 164 732 158 790 180", variant: "partial" },
] as const;

const signalPaths: readonly ConvergencePath[] = [
  { d: "M84 36 C270 32 438 100 590 166 C682 206 732 212 790 180", variant: "dotted" },
  { d: "M84 324 C270 328 438 260 590 194 C682 154 732 148 790 180", variant: "dotted" },
] as const;

const outputPaths = [
  "M790 180 C914 180 1048 178 1200 179",
] as const;

const staticBlueMarkers = [
  [70, 38, 1.5, 0.34], [194, 38, 1.7, 0.4], [326, 66, 1.8, 0.46],
  [456, 108, 1.9, 0.52], [566, 154, 2, 0.6],
  [40, 132, 1.5, 0.34], [210, 118, 1.7, 0.42], [380, 132, 1.8, 0.48],
  [530, 158, 1.9, 0.56], [40, 228, 1.5, 0.34],
  [210, 242, 1.7, 0.42], [380, 228, 1.8, 0.48], [530, 202, 1.9, 0.56],
  [70, 322, 1.5, 0.34], [194, 322, 1.7, 0.4], [326, 294, 1.8, 0.46],
  [456, 252, 1.9, 0.52], [566, 206, 2, 0.6],
] as const;

const staticPaleMarkers = [
  [276, 74, 1.05, 0.58], [596, 164, 1.15, 0.66], [276, 286, 1.05, 0.58],
  [596, 196, 1.15, 0.66], [714, 180, 1.1, 0.76], [758, 180, 1.05, 0.84],
] as const;

const incomingSignals = [
  { path: backgroundPaths[0].d, duration: "16s", begin: "-5.2s", radius: 2.1, tone: "blue" },
  { path: backgroundPaths[1].d, duration: "14s", begin: "-10.8s", radius: 1.55, tone: "pale" },
  { path: backgroundPaths[2].d, duration: "17.5s", begin: "-8.4s", radius: 2.2, tone: "blue" },
  { path: backgroundPaths[3].d, duration: "12.5s", begin: "-3.1s", radius: 1.6, tone: "pale" },
  { path: structuralPaths[1].d, duration: "11s", begin: "-7.7s", radius: 2.3, tone: "blue" },
  { path: structuralPaths[3].d, duration: "9.5s", begin: "-4.6s", radius: 1.5, tone: "pale" },
  { path: structuralPaths[5].d, duration: "14.5s", begin: "-11.2s", radius: 2.2, tone: "blue" },
  { path: corePaths[2].d, duration: "8s", begin: "-5.9s", radius: 1.45, tone: "pale" },
] as const;

const outgoingSignals = [
  { path: outputPaths[0], duration: "8s", begin: "-2.1s", radius: 2.2, tone: "blue" },
  { path: outputPaths[0], duration: "9.5s", begin: "-6.8s", radius: 1.55, tone: "pale" },
  { path: outputPaths[0], duration: "12.5s", begin: "-9.2s", radius: 2.1, tone: "blue" },
  { path: outputPaths[0], duration: "16s", begin: "-12.3s", radius: 1.5, tone: "pale" },
] as const;

function PathLayer({ className, paths }: { className: string; paths: readonly ConvergencePath[] }) {
  return (
    <g className={className}>
      {paths.map(({ d, variant }) => <path className={`convergence-path convergence-path--${variant}`} key={d} d={d} />)}
    </g>
  );
}

function MovingSignals({ signals, className }: { signals: readonly { path: string; duration: string; begin: string; radius: number; tone: string }[]; className: string }) {
  return (
    <g className={className}>
      {signals.map(({ path, duration, begin, radius, tone }, index) => (
        <circle className={`convergence-moving-signal convergence-moving-signal--${tone}`} key={`${duration}-${begin}`} r={radius} opacity={index % 2 ? 0.78 : 0.92}>
          <animateMotion path={path} dur={duration} begin={begin} repeatCount="indefinite" />
        </circle>
      ))}
    </g>
  );
}

export function TraceConvergence() {
  return (
    <div className="trace-visual trace-visual--convergence" aria-hidden="true">
      <svg viewBox="0 -25 1200 410" preserveAspectRatio="xMidYMid meet" focusable="false">
        <defs>
          <linearGradient id="convergence-background" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="var(--trace-wave-blue-background)" stopOpacity="0.5" />
            <stop offset="0.7" stopColor="var(--trace-wave-blue-structural)" stopOpacity="0.78" />
            <stop offset="1" stopColor="var(--trace-blue-bright)" stopOpacity="0.7" />
          </linearGradient>
          <linearGradient id="convergence-structural" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="var(--trace-wave-blue-background)" stopOpacity="0.62" />
            <stop offset="0.64" stopColor="var(--trace-wave-blue-structural)" stopOpacity="0.92" />
            <stop offset="1" stopColor="var(--trace-wave-blue-signal)" stopOpacity="0.82" />
          </linearGradient>
          <linearGradient id="convergence-core" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="var(--trace-wave-blue-structural)" stopOpacity="0.7" />
            <stop offset="0.72" stopColor="var(--trace-blue-bright)" stopOpacity="0.94" />
            <stop offset="1" stopColor="var(--trace-wave-blue-signal)" stopOpacity="0.9" />
          </linearGradient>
          <linearGradient id="convergence-output" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="var(--trace-wave-blue-signal)" stopOpacity="0.88" />
            <stop offset="0.5" stopColor="var(--trace-wave-blue-structural)" stopOpacity="0.58" />
            <stop offset="1" stopColor="var(--trace-wave-blue-background)" stopOpacity="0.14" />
          </linearGradient>
          <radialGradient id="convergence-focus-outer">
            <stop offset="0" stopColor="var(--trace-wave-blue-glow)" stopOpacity="0.18" />
            <stop offset="0.42" stopColor="var(--trace-wave-blue-structural)" stopOpacity="0.065" />
            <stop offset="1" stopColor="var(--trace-wave-blue-background)" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="convergence-focus-inner">
            <stop offset="0" stopColor="var(--trace-wave-blue-signal)" stopOpacity="0.34" />
            <stop offset="0.38" stopColor="var(--trace-wave-blue-glow)" stopOpacity="0.12" />
            <stop offset="1" stopColor="var(--trace-wave-blue-background)" stopOpacity="0" />
          </radialGradient>
        </defs>

        <ellipse className="convergence-glow convergence-glow--outer" cx="790" cy="180" rx="190" ry="104" fill="url(#convergence-focus-outer)" />
        <ellipse className="convergence-glow convergence-glow--inner" cx="790" cy="180" rx="82" ry="48" fill="url(#convergence-focus-inner)" />

        <PathLayer className="trace-layer trace-layer--outer-expansion" paths={outerExpansionPaths} />
        <PathLayer className="trace-layer trace-layer--background" paths={backgroundPaths} />
        <PathLayer className="trace-layer trace-layer--structural" paths={structuralPaths} />
        <PathLayer className="trace-layer trace-layer--core" paths={corePaths} />
        <PathLayer className="trace-layer trace-layer--signal" paths={signalPaths} />

        <g className="trace-particles trace-particles--blue">
          {staticBlueMarkers.map(([cx, cy, radius, opacity], index) => <circle key={`${cx}-${cy}-${index}`} cx={cx} cy={cy} r={radius} opacity={opacity} />)}
        </g>
        <g className="trace-particles trace-particles--pale">
          {staticPaleMarkers.map(([cx, cy, radius, opacity], index) => <circle key={`${cx}-${cy}-${index}`} cx={cx} cy={cy} r={radius} opacity={opacity} />)}
        </g>

        <g className="trace-output-paths">
          {outputPaths.map((path) => <path className="trace-output trace-output--primary" key={path} d={path} />)}
        </g>

        <MovingSignals className="convergence-moving-signals convergence-moving-signals--incoming" signals={incomingSignals} />
        <MovingSignals className="convergence-moving-signals convergence-moving-signals--outgoing" signals={outgoingSignals} />

        <g className="trace-focus trace-focus--convergence">
          <circle className="trace-focus-ring trace-focus-ring--outer" cx="790" cy="180" r="17" />
          <circle className="trace-focus-ring" cx="790" cy="180" r="10" />
          <circle className="trace-focus-core" cx="790" cy="180" r="4.5" />
        </g>
      </svg>
    </div>
  );
}
