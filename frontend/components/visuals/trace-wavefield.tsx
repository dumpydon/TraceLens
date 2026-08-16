type WaveVariant = "continuous" | "dotted" | "partial";

type WavePath = {
  d: string;
  variant: WaveVariant;
};

const backgroundWaves: readonly WavePath[] = [
  { d: "M138 198 C230 146 326 18 458 34 C560 48 598 176 684 188 C770 200 842 88 948 52 C1054 18 1134 44 1200 62", variant: "dotted" },
  { d: "M138 199 C238 164 332 46 464 60 C566 72 610 184 692 194 C780 204 850 112 960 78 C1068 44 1144 72 1200 90", variant: "continuous" },
  { d: "M138 201 C234 238 326 354 452 342 C554 332 600 218 688 208 C774 198 846 300 950 334 C1054 368 1138 338 1200 322", variant: "dotted" },
  { d: "M138 202 C226 260 316 390 446 376 C550 364 602 226 696 214 C784 202 856 330 966 366 C1072 400 1146 364 1200 344", variant: "continuous" },
  { d: "M138 198 C244 150 340 70 464 88 C570 104 616 194 700 214 C790 236 854 276 958 308 C1062 340 1136 324 1180 310", variant: "partial" },
  { d: "M138 202 C238 250 330 330 456 316 C566 304 612 206 694 184 C780 160 856 112 964 76 C1070 40 1140 58 1190 74", variant: "dotted" },
] as const;

const structuralWaves: readonly WavePath[] = [
  { d: "M138 198 C244 154 334 58 458 72 C562 84 608 174 686 187 C764 200 832 118 934 88 C1034 58 1120 72 1200 84", variant: "continuous" },
  { d: "M138 198 C250 164 344 78 470 90 C570 102 620 184 692 205 C768 228 842 242 946 286 C1046 328 1126 310 1184 294", variant: "dotted" },
  { d: "M138 199 C252 172 350 98 478 108 C578 118 624 184 696 192 C774 201 846 146 952 122 C1054 98 1132 112 1200 126", variant: "continuous" },
  { d: "M138 199 C258 178 356 118 486 126 C584 134 632 192 700 212 C772 234 850 234 954 264 C1058 294 1136 282 1192 270", variant: "partial" },
  { d: "M138 200 C262 184 364 140 494 146 C590 152 638 188 704 198 C776 208 852 170 962 158 C1068 146 1140 158 1200 168", variant: "dotted" },
  { d: "M138 200 C264 216 360 258 488 250 C586 244 632 212 698 202 C770 192 846 224 950 232 C1056 240 1132 228 1198 218", variant: "continuous" },
  { d: "M138 201 C258 224 354 280 482 270 C580 262 626 212 694 188 C766 162 842 160 944 148 C1046 136 1124 146 1180 158", variant: "dotted" },
  { d: "M138 201 C254 230 348 300 474 288 C574 278 622 220 690 208 C764 194 840 264 946 282 C1050 300 1128 288 1200 276", variant: "continuous" },
  { d: "M138 202 C248 238 340 320 466 306 C568 294 616 216 688 194 C762 170 836 132 938 108 C1040 84 1118 94 1178 110", variant: "partial" },
  { d: "M138 202 C242 246 334 342 458 328 C562 316 610 228 686 214 C766 200 840 292 944 314 C1048 336 1128 318 1192 300", variant: "dotted" },
] as const;

const coreWaves: readonly WavePath[] = [
  { d: "M138 199 C266 180 372 156 500 164 C596 170 636 184 690 186 C750 188 826 156 930 152 C1032 148 1110 158 1170 166", variant: "continuous" },
  { d: "M138 199 C270 186 380 168 506 174 C600 178 640 198 694 210 C752 222 826 224 928 232 C1030 240 1110 232 1182 224", variant: "dotted" },
  { d: "M138 200 C274 190 386 180 512 184 C606 188 646 194 700 193 C758 192 832 172 934 170 C1036 168 1114 176 1190 184", variant: "continuous" },
  { d: "M138 200 C276 194 390 190 516 192 C610 194 650 208 704 216 C762 224 834 214 936 220 C1040 226 1118 218 1200 210", variant: "partial" },
  { d: "M138 200 C274 206 388 218 514 212 C608 208 648 190 702 184 C760 178 832 190 934 190 C1036 190 1114 198 1190 204", variant: "dotted" },
  { d: "M138 201 C270 212 380 232 506 224 C600 218 642 202 696 207 C754 212 826 202 928 206 C1030 210 1110 204 1182 196", variant: "continuous" },
  { d: "M138 201 C266 218 372 244 500 236 C596 230 636 194 690 190 C750 186 826 236 930 246 C1032 256 1110 246 1170 236", variant: "dotted" },
  { d: "M138 202 C262 224 366 258 494 248 C590 240 632 212 686 215 C746 218 820 184 924 178 C1028 172 1106 184 1168 194", variant: "continuous" },
] as const;

const signalWaves: readonly WavePath[] = [
  { d: "M138 198 C246 148 342 68 466 86 C568 100 616 186 690 216 C768 248 844 262 950 286 C1056 310 1136 296 1200 278", variant: "dotted" },
  { d: "M138 202 C242 252 334 340 460 320 C564 304 612 210 688 184 C768 156 844 124 948 98 C1052 72 1132 84 1194 102", variant: "continuous" },
  { d: "M138 199 C258 168 356 126 486 140 C584 150 630 192 700 206 C774 220 852 190 958 182 C1064 174 1140 184 1200 194", variant: "partial" },
  { d: "M138 201 C252 230 348 288 476 274 C576 264 624 214 694 194 C768 172 844 230 950 244 C1056 258 1136 246 1196 232", variant: "dotted" },
] as const;

const propagationWaves = [
  backgroundWaves[4].d,
  structuralWaves[1].d,
  structuralWaves[6].d,
  coreWaves[1].d,
  coreWaves[6].d,
  signalWaves[0].d,
  signalWaves[1].d,
  signalWaves[3].d,
] as const;

const localHighlightWaves = [
  structuralWaves[2].d,
  structuralWaves[7].d,
  coreWaves[2].d,
  coreWaves[5].d,
  signalWaves[0].d,
  signalWaves[1].d,
] as const;

const backgroundMarkers = [
  [274, 110, 2.1, 0.34], [386, 48, 2.2, 0.38], [520, 68, 2, 0.3],
  [610, 168, 2.1, 0.34], [886, 82, 2.2, 0.36], [1042, 42, 2, 0.28],
  [302, 300, 2.1, 0.32], [430, 350, 2.2, 0.34], [572, 286, 2, 0.3],
  [902, 316, 2.2, 0.34], [1052, 362, 2, 0.26],
] as const;

const structuralMarkers = [
  [222, 174, 3, 0.68], [292, 134, 3.2, 0.72], [372, 94, 3, 0.68],
  [456, 82, 3.3, 0.74], [540, 126, 2.9, 0.64], [610, 176, 3.1, 0.7],
  [654, 190, 3.2, 0.76], [716, 202, 3.1, 0.74], [780, 198, 3.3, 0.78],
  [846, 170, 3, 0.68], [930, 132, 3.2, 0.72], [1024, 106, 3, 0.64],
  [1118, 126, 2.9, 0.58], [236, 224, 3, 0.66], [318, 270, 3.2, 0.7],
  [408, 300, 3, 0.66], [500, 276, 3.3, 0.72], [584, 226, 3, 0.68],
  [642, 208, 3.2, 0.74], [702, 194, 3.1, 0.76], [764, 204, 3.3, 0.78],
  [834, 226, 3, 0.7], [918, 268, 3.2, 0.72], [1012, 294, 3, 0.64],
  [1108, 278, 2.9, 0.58],
] as const;

const coreMarkers = [
  [286, 180, 2.8, 0.72], [376, 174, 3, 0.74], [470, 184, 2.8, 0.7],
  [552, 190, 3.1, 0.76], [620, 194, 3, 0.78], [672, 190, 3.2, 0.82],
  [724, 198, 3, 0.8], [776, 206, 3.2, 0.82], [834, 202, 3, 0.78],
  [906, 206, 3.1, 0.74], [996, 210, 2.9, 0.68], [1090, 204, 2.8, 0.62],
  [302, 220, 2.8, 0.7], [398, 228, 3, 0.72], [494, 218, 2.8, 0.7],
  [580, 208, 3.1, 0.76], [646, 202, 3, 0.8], [698, 208, 3.2, 0.84],
  [752, 194, 3, 0.82], [806, 190, 3.2, 0.8], [872, 198, 3, 0.76],
] as const;

const eventMarkers = [
  [404, 94, 5.4, 0.8], [576, 176, 4.8, 0.78], [692, 200, 5.6, 0.9],
  [812, 198, 4.6, 0.82], [952, 112, 5.2, 0.78], [1082, 276, 5, 0.72],
] as const;

const crossingMarkers = [
  [640, 194, 3.6, 0.84], [672, 202, 3.8, 0.9], [704, 196, 4.1, 0.94],
  [736, 205, 3.7, 0.88], [770, 198, 3.6, 0.84],
] as const;

const movingSignals = [
  { path: backgroundWaves[4].d, duration: "10s", begin: "-3.2s", radius: 2.05, tone: "pale" },
  { path: structuralWaves[1].d, duration: "12.5s", begin: "-8.4s", radius: 1.9, tone: "pale" },
  { path: structuralWaves[6].d, duration: "15s", begin: "-5.7s", radius: 2, tone: "pale" },
  { path: coreWaves[1].d, duration: "9s", begin: "-6.2s", radius: 1.85, tone: "pale" },
  { path: coreWaves[6].d, duration: "11.5s", begin: "-9.1s", radius: 1.95, tone: "pale" },
  { path: signalWaves[0].d, duration: "16.5s", begin: "-2.1s", radius: 2.2, tone: "pale" },
  { path: signalWaves[1].d, duration: "13.5s", begin: "-10.8s", radius: 2.25, tone: "pale" },
  { path: signalWaves[3].d, duration: "17.5s", begin: "-7.3s", radius: 2.1, tone: "pale" },
  { path: backgroundWaves[0].d, duration: "14.5s", begin: "-6.8s", radius: 2.4, tone: "blue" },
  { path: backgroundWaves[0].d, duration: "12.2s", begin: "-10.4s", radius: 2.5, tone: "blue" },
  { path: backgroundWaves[0].d, duration: "16.8s", begin: "-4.9s", radius: 2.6, tone: "blue" },
  { path: backgroundWaves[3].d, duration: "10.6s", begin: "-2.7s", radius: 2.4, tone: "blue" },
  { path: backgroundWaves[3].d, duration: "12.8s", begin: "-7.1s", radius: 2.6, tone: "blue" },
  { path: backgroundWaves[3].d, duration: "15.4s", begin: "-8.6s", radius: 2.5, tone: "blue" },
  { path: backgroundWaves[3].d, duration: "17.2s", begin: "-13.4s", radius: 2.8, tone: "blue" },
  { path: structuralWaves[2].d, duration: "8.8s", begin: "-1.7s", radius: 2.7, tone: "blue" },
  { path: structuralWaves[5].d, duration: "11.8s", begin: "-9.4s", radius: 2.8, tone: "blue" },
  { path: coreWaves[0].d, duration: "13.2s", begin: "-4.4s", radius: 2.5, tone: "blue" },
  { path: coreWaves[4].d, duration: "9.8s", begin: "-7.6s", radius: 2.6, tone: "blue" },
  { path: signalWaves[2].d, duration: "16.2s", begin: "-12.1s", radius: 3, tone: "blue" },
] as const;

const junctionSignals = [
  { path: "M684 188 C770 200 842 88 948 52 C1054 18 1134 44 1200 62", duration: "11.6s", begin: "-4.2s", radius: 2.2, tone: "blue" },
  { path: "M692 194 C780 204 850 112 960 78 C1068 44 1144 72 1200 90", duration: "10.4s", begin: "-8.1s", radius: 1.55, tone: "pale" },
  { path: "M688 208 C774 198 846 300 950 334 C1054 368 1138 338 1200 322", duration: "12.8s", begin: "-6.5s", radius: 2.3, tone: "blue" },
  { path: "M696 214 C784 202 856 330 966 366 C1072 400 1146 364 1200 344", duration: "13.4s", begin: "-10.7s", radius: 1.7, tone: "pale" },
  { path: "M700 214 C790 236 854 276 958 308 C1062 340 1136 324 1180 310", duration: "10.9s", begin: "-2.9s", radius: 2.1, tone: "blue" },
  { path: "M694 184 C780 160 856 112 964 76 C1070 40 1140 58 1190 74", duration: "12.1s", begin: "-9.3s", radius: 1.6, tone: "pale" },
  { path: "M686 187 C764 200 832 118 934 88 C1034 58 1120 72 1200 84", duration: "7.2s", begin: "-1.4s", radius: 2.4, tone: "blue" },
  { path: "M692 205 C768 228 842 242 946 286 C1046 328 1126 310 1184 294", duration: "9.6s", begin: "-6.8s", radius: 1.7, tone: "pale" },
  { path: "M696 192 C774 201 846 146 952 122 C1054 98 1132 112 1200 126", duration: "8.4s", begin: "-4.1s", radius: 2.5, tone: "blue" },
  { path: "M700 212 C772 234 850 234 954 264 C1058 294 1136 282 1192 270", duration: "9.9s", begin: "-7.7s", radius: 1.6, tone: "pale" },
  { path: "M704 198 C776 208 852 170 962 158 C1068 146 1140 158 1200 168", duration: "7.8s", begin: "-5.2s", radius: 2.2, tone: "blue" },
  { path: "M698 202 C770 192 846 224 950 232 C1056 240 1132 228 1198 218", duration: "8.7s", begin: "-2.4s", radius: 1.55, tone: "pale" },
  { path: "M694 188 C766 162 842 160 944 148 C1046 136 1124 146 1180 158", duration: "9.3s", begin: "-8.5s", radius: 2.3, tone: "blue" },
  { path: "M690 208 C764 194 840 264 946 282 C1050 300 1128 288 1200 276", duration: "10.8s", begin: "-8.7s", radius: 1.75, tone: "pale" },
  { path: "M688 194 C762 170 836 132 938 108 C1040 84 1118 94 1178 110", duration: "10.1s", begin: "-3.8s", radius: 2.4, tone: "blue" },
  { path: "M686 214 C766 200 840 292 944 314 C1048 336 1128 318 1192 300", duration: "11.4s", begin: "-9.9s", radius: 1.65, tone: "pale" },
  { path: "M690 186 C750 188 826 156 930 152 C1032 148 1110 158 1170 166", duration: "6.8s", begin: "-3.5s", radius: 2.3, tone: "blue" },
  { path: "M694 210 C752 222 826 224 928 232 C1030 240 1110 232 1182 224", duration: "8.9s", begin: "-7.3s", radius: 1.65, tone: "pale" },
  { path: "M700 193 C758 192 832 172 934 170 C1036 168 1114 176 1190 184", duration: "7.5s", begin: "-1.9s", radius: 2.1, tone: "blue" },
  { path: "M704 216 C762 224 834 214 936 220 C1040 226 1118 218 1200 210", duration: "8.2s", begin: "-5.9s", radius: 1.5, tone: "pale" },
  { path: "M702 184 C760 178 832 190 934 190 C1036 190 1114 198 1190 204", duration: "7.1s", begin: "-4.6s", radius: 2.2, tone: "blue" },
  { path: "M696 207 C754 212 826 202 928 206 C1030 210 1110 204 1182 196", duration: "7.9s", begin: "-6.7s", radius: 1.55, tone: "pale" },
  { path: "M690 190 C750 186 826 236 930 246 C1032 256 1110 246 1170 236", duration: "8.6s", begin: "-2.6s", radius: 2.25, tone: "blue" },
  { path: "M686 215 C746 218 820 184 924 178 C1028 172 1106 184 1168 194", duration: "9.1s", begin: "-7.8s", radius: 1.6, tone: "pale" },
  { path: "M690 216 C768 248 844 262 950 286 C1056 310 1136 296 1200 278", duration: "10.2s", begin: "-5.6s", radius: 2.5, tone: "blue" },
  { path: "M688 184 C768 156 844 124 948 98 C1052 72 1132 84 1194 102", duration: "9.2s", begin: "-2.8s", radius: 1.8, tone: "pale" },
  { path: "M700 206 C774 220 852 190 958 182 C1064 174 1140 184 1200 194", duration: "8.8s", begin: "-7.1s", radius: 2.35, tone: "blue" },
  { path: "M694 194 C768 172 844 230 950 244 C1056 258 1136 246 1196 232", duration: "9.7s", begin: "-4.7s", radius: 1.7, tone: "pale" },
] as const;

function WaveGroup({ className, paths }: { className: string; paths: readonly WavePath[] }) {
  return (
    <g className={className}>
      {paths.map(({ d, variant }) => (
        <path className={`trace-wave-path trace-wave-path--${variant}`} key={d} d={d} />
      ))}
    </g>
  );
}

function MarkerGroup({ className, markers, radiusScale = 1 }: { className: string; markers: readonly (readonly [number, number, number, number])[]; radiusScale?: number }) {
  return (
    <g className={className}>
      {markers.map(([cx, cy, radius, opacity], index) => (
        <circle key={`${cx}-${cy}-${index}`} cx={cx} cy={cy} r={radius * radiusScale} opacity={opacity} />
      ))}
    </g>
  );
}

export function TraceWavefield() {
  return (
    <div className="trace-visual trace-visual--wavefield" aria-hidden="true">
      <svg viewBox="0 0 1200 400" preserveAspectRatio="xMidYMid meet" focusable="false">
        <defs>
          <linearGradient id="wavefield-background" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="var(--trace-wave-blue-background)" stopOpacity="0.84" />
            <stop offset="0.58" stopColor="var(--trace-wave-blue-background)" stopOpacity="1" />
            <stop offset="1" stopColor="var(--trace-wave-blue-background)" stopOpacity="0.7" />
          </linearGradient>
          <linearGradient id="wavefield-structural" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="var(--trace-wave-blue-structural)" stopOpacity="0.9" />
            <stop offset="0.56" stopColor="var(--trace-wave-blue-structural)" stopOpacity="0.84" />
            <stop offset="1" stopColor="var(--trace-wave-blue-background)" stopOpacity="0.66" />
          </linearGradient>
          <linearGradient id="wavefield-core" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="var(--trace-wave-blue-structural)" stopOpacity="0.94" />
            <stop offset="0.58" stopColor="var(--trace-wave-blue-signal)" stopOpacity="0.9" />
            <stop offset="1" stopColor="var(--trace-wave-blue-structural)" stopOpacity="0.74" />
          </linearGradient>
          <linearGradient id="wavefield-signal" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="var(--trace-wave-blue-signal)" stopOpacity="0.98" />
            <stop offset="0.58" stopColor="var(--trace-wave-blue-structural)" stopOpacity="0.94" />
            <stop offset="1" stopColor="var(--trace-wave-blue-structural)" stopOpacity="0.8" />
          </linearGradient>
          <linearGradient id="wavefield-source-line" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="var(--trace-wave-blue-background)" stopOpacity="0.08" />
            <stop offset="0.72" stopColor="var(--trace-wave-blue-structural)" stopOpacity="0.66" />
            <stop offset="1" stopColor="var(--trace-wave-blue-signal)" stopOpacity="0.94" />
          </linearGradient>
          <linearGradient id="wavefield-phase" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="var(--trace-wave-blue-signal)" stopOpacity="0" />
            <stop offset="0.5" stopColor="var(--trace-wave-blue-signal)" stopOpacity="1" />
            <stop offset="1" stopColor="var(--trace-wave-blue-signal)" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="wavefield-local-highlight" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="var(--trace-wave-blue-structural)" stopOpacity="0" />
            <stop offset="0.48" stopColor="var(--trace-wave-blue-signal)" stopOpacity="0.86" />
            <stop offset="1" stopColor="var(--trace-wave-blue-structural)" stopOpacity="0" />
          </linearGradient>
          <radialGradient id="wavefield-source">
            <stop offset="0" stopColor="var(--trace-wave-blue-glow)" stopOpacity="0.22" />
            <stop offset="0.42" stopColor="var(--trace-wave-blue-glow)" stopOpacity="0.09" />
            <stop offset="1" stopColor="var(--trace-wave-blue-glow)" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="wavefield-source-outer">
            <stop offset="0" stopColor="var(--trace-wave-blue-glow)" stopOpacity="0.18" />
            <stop offset="0.32" stopColor="var(--trace-wave-blue-glow)" stopOpacity="0.08" />
            <stop offset="0.68" stopColor="var(--trace-wave-blue-background)" stopOpacity="0.026" />
            <stop offset="1" stopColor="var(--trace-wave-blue-background)" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="wavefield-source-node">
            <stop offset="0" stopColor="var(--trace-wave-blue-signal)" stopOpacity="0.84" />
            <stop offset="0.25" stopColor="var(--trace-wave-blue-glow)" stopOpacity="0.34" />
            <stop offset="1" stopColor="var(--trace-wave-blue-glow)" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="wavefield-crossing-glow">
            <stop offset="0" stopColor="var(--trace-wave-blue-glow)" stopOpacity="0.24" />
            <stop offset="0.44" stopColor="var(--trace-wave-blue-structural)" stopOpacity="0.08" />
            <stop offset="1" stopColor="var(--trace-wave-blue-background)" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="wavefield-atmosphere">
            <stop offset="0" stopColor="var(--trace-wave-blue-glow)" stopOpacity="0.075" />
            <stop offset="0.52" stopColor="var(--trace-wave-blue-background)" stopOpacity="0.026" />
            <stop offset="1" stopColor="var(--trace-wave-blue-background)" stopOpacity="0" />
          </radialGradient>
        </defs>

        <ellipse className="trace-source-glow trace-source-glow--outer" cx="138" cy="200" rx="320" ry="190" fill="url(#wavefield-source-outer)" />
        <ellipse className="trace-source-glow trace-source-glow--ambient" cx="138" cy="200" rx="170" ry="116" fill="url(#wavefield-source)" />
        <ellipse className="trace-source-glow trace-source-glow--mid" cx="138" cy="200" rx="92" ry="66" fill="url(#wavefield-source)" />
        <circle className="trace-source-node-halo" cx="138" cy="200" r="32" fill="url(#wavefield-source-node)" />
        <circle className="trace-source-medium-ring" cx="138" cy="200" r="19" />
        <path className="trace-source-line" d="M0 200 C52 200 98 200 138 200" />

        <ellipse className="trace-atmospheric-glow trace-atmospheric-glow--center" cx="700" cy="200" rx="230" ry="106" fill="url(#wavefield-atmosphere)" />
        <ellipse className="trace-atmospheric-glow trace-atmospheric-glow--right" cx="1020" cy="188" rx="230" ry="146" fill="url(#wavefield-atmosphere)" />
        <ellipse className="trace-crossing-glow" cx="700" cy="200" rx="112" ry="48" fill="url(#wavefield-crossing-glow)" />
        <ellipse className="trace-crossing-glow trace-crossing-glow--secondary" cx="770" cy="198" rx="72" ry="38" fill="url(#wavefield-crossing-glow)" />

        <WaveGroup className="trace-wave trace-wave--background" paths={backgroundWaves} />
        <WaveGroup className="trace-wave trace-wave--structural" paths={structuralWaves} />
        <WaveGroup className="trace-wave trace-wave--core" paths={coreWaves} />
        <WaveGroup className="trace-wave trace-wave--signal" paths={signalWaves} />

        <g className="trace-wave trace-wave--local-highlights">
          {localHighlightWaves.map((path, index) => <path key={path} d={path} pathLength="100" data-highlight={index + 1} />)}
        </g>
        <g className="trace-wave trace-wave--phase">
          {propagationWaves.map((path) => <path key={path} d={path} />)}
        </g>

        <MarkerGroup className="trace-wave-particles trace-wave-particles--background" markers={backgroundMarkers} />
        <MarkerGroup className="trace-wave-particles trace-wave-particles--structural" markers={structuralMarkers} />
        <MarkerGroup className="trace-wave-particles trace-wave-particles--core" markers={coreMarkers} />
        <MarkerGroup className="trace-wave-particles trace-wave-particles--events" markers={eventMarkers} radiusScale={1 / 3} />
        <MarkerGroup className="trace-wave-particles trace-wave-particles--crossing" markers={crossingMarkers} radiusScale={1 / 3} />

        <g className="trace-moving-signals">
          {movingSignals.map(({ path, duration, begin, radius, tone }, index) => (
            <circle className={`trace-moving-signal trace-moving-signal--${tone}`} key={`${tone}-${duration}-${begin}`} r={radius} opacity={index % 2 ? 0.86 : 0.98}>
              <animateMotion path={path} dur={duration} begin={begin} repeatCount="indefinite" />
            </circle>
          ))}
          {junctionSignals.map(({ path, duration, begin, radius, tone }, index) => (
            <circle className={`trace-moving-signal trace-moving-signal--${tone} trace-moving-signal--junction`} key={`junction-${tone}-${duration}-${begin}`} r={radius} opacity={index % 2 ? 0.78 : 0.9}>
              <animateMotion path={path} dur={duration} begin={begin} repeatCount="indefinite" />
            </circle>
          ))}
        </g>

        <g className="trace-focus">
          <circle className="trace-focus-ring" cx="138" cy="200" r="12" />
          <circle className="trace-focus-core" cx="138" cy="200" r="5" />
        </g>
      </svg>
    </div>
  );
}
