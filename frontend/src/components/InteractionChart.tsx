// Diagramme de capacité N-M d'une section béton armé.
// Trace l'enveloppe résistante calculée par Str-lib (norme.EC2.elu.
// interaction_diagram) et y situe le point de calcul (MEd, NEd).
//
// Convention d'axes retenue (usuelle en béton armé) :
//   abscisse = M [kN·m] , ordonnée = N [kN] (compression vers le haut).

import React from "react";
import Svg, { Circle, G, Line, Path, Text as SvgText } from "react-native-svg";

import { colors } from "../theme";

const AXIS = colors.onSurfaceTertiary;
const ANNOT = colors.onSurface;
const CURVE = colors.brand;
const POINT_OK = colors.success ?? colors.brand;
const POINT_KO = colors.error;

export type InteractionData = {
  curve: { N: number; M: number }[];
  point: { N: number; M: number };
  labels?: { x: string; y: string };
};

type Props = {
  width: number;
  height: number;
  data: InteractionData;
};

/** Arrondi « joli » vers le haut pour les bornes d'axes. */
function niceMax(v: number): number {
  if (v <= 0) return 1;
  const exp = Math.floor(Math.log10(v));
  const base = Math.pow(10, exp);
  const n = v / base;
  const step = n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10;
  return step * base;
}

export function InteractionChart({ width, height, data }: Props) {
  const padL = 54;
  const padR = 18;
  const padT = 22;
  const padB = 40;
  const plotW = Math.max(width - padL - padR, 10);
  const plotH = Math.max(height - padT - padB, 10);

  const curve = data.curve ?? [];
  if (curve.length < 2) {
    return (
      <Svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
        <SvgText
          x={width / 2}
          y={height / 2}
          fill={ANNOT}
          fontSize={12}
          textAnchor="middle"
        >
          Diagramme indisponible
        </SvgText>
      </Svg>
    );
  }

  const Ms = curve.map((p) => p.M);
  const Ns = curve.map((p) => p.N);
  const mMax = niceMax(Math.max(...Ms, Math.abs(data.point.M)) * 1.1);
  const nMax = niceMax(Math.max(...Ns, data.point.N) * 1.05);
  // La branche de traction descend sous zéro : on garde une borne basse.
  const nMinRaw = Math.min(...Ns, data.point.N, 0);
  const nMin = -niceMax(Math.abs(nMinRaw) * 1.1);

  const xAt = (M: number) => padL + (M / mMax) * plotW;
  const yAt = (N: number) => padT + plotH - ((N - nMin) / (nMax - nMin)) * plotH;

  const path = curve
    .map(
      (p, i) =>
        `${i === 0 ? "M" : "L"} ${xAt(p.M).toFixed(1)} ${yAt(p.N).toFixed(1)}`,
    )
    .join(" ");

  // Le point de calcul est-il dans l'enveloppe ? On compare son M à celui
  // de la courbe interpolée au même N.
  const pt = data.point;
  let mCap = 0;
  for (let i = 1; i < curve.length; i++) {
    const a = curve[i - 1];
    const b = curve[i];
    if ((a.N <= pt.N && pt.N <= b.N) || (b.N <= pt.N && pt.N <= a.N)) {
      const t = b.N === a.N ? 0 : (pt.N - a.N) / (b.N - a.N);
      mCap = Math.max(mCap, a.M + t * (b.M - a.M));
    }
  }
  const inside = Math.abs(pt.M) <= mCap;
  const ptColor = inside ? POINT_OK : POINT_KO;

  const xTicks = 4;
  const yTicks = 4;

  return (
    <Svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <G>
        {/* Grille horizontale + labels N */}
        {Array.from({ length: yTicks + 1 }).map((_, i) => {
          const n = nMin + ((nMax - nMin) * i) / yTicks;
          return (
            <G key={`y-${i}`}>
              <Line
                x1={padL}
                y1={yAt(n)}
                x2={padL + plotW}
                y2={yAt(n)}
                stroke={AXIS}
                strokeWidth={0.5}
                opacity={0.22}
              />
              <SvgText
                x={padL - 6}
                y={yAt(n) + 3}
                fill={AXIS}
                fontSize={9}
                textAnchor="end"
              >
                {n.toFixed(0)}
              </SvgText>
            </G>
          );
        })}

        {/* Grille verticale + labels M */}
        {Array.from({ length: xTicks + 1 }).map((_, i) => {
          const m = (mMax * i) / xTicks;
          return (
            <G key={`x-${i}`}>
              <Line
                x1={xAt(m)}
                y1={padT}
                x2={xAt(m)}
                y2={padT + plotH}
                stroke={AXIS}
                strokeWidth={0.5}
                opacity={0.15}
              />
              <SvgText
                x={xAt(m)}
                y={padT + plotH + 15}
                fill={AXIS}
                fontSize={9}
                textAnchor="middle"
              >
                {m.toFixed(0)}
              </SvgText>
            </G>
          );
        })}

        {/* Axe N = 0 */}
        {nMin < 0 && (
          <Line
            x1={padL}
            y1={yAt(0)}
            x2={padL + plotW}
            y2={yAt(0)}
            stroke={AXIS}
            strokeWidth={1}
            opacity={0.6}
          />
        )}

        {/* Cadre */}
        <Line x1={padL} y1={padT} x2={padL} y2={padT + plotH} stroke={AXIS} strokeWidth={1} />
        <Line
          x1={padL}
          y1={padT + plotH}
          x2={padL + plotW}
          y2={padT + plotH}
          stroke={AXIS}
          strokeWidth={1}
        />

        {/* Enveloppe résistante */}
        <Path d={path} stroke={CURVE} strokeWidth={2.5} fill="none" />

        {/* Point de calcul */}
        <Line
          x1={xAt(Math.abs(pt.M))}
          y1={padT + plotH}
          x2={xAt(Math.abs(pt.M))}
          y2={yAt(pt.N)}
          stroke={ptColor}
          strokeWidth={1}
          strokeDasharray="3,3"
          opacity={0.6}
        />
        <Line
          x1={padL}
          y1={yAt(pt.N)}
          x2={xAt(Math.abs(pt.M))}
          y2={yAt(pt.N)}
          stroke={ptColor}
          strokeWidth={1}
          strokeDasharray="3,3"
          opacity={0.6}
        />
        <Circle
          cx={xAt(Math.abs(pt.M))}
          cy={yAt(pt.N)}
          r={5}
          fill={ptColor}
          stroke={colors.surface}
          strokeWidth={1.5}
        />
        <SvgText
          x={Math.min(xAt(Math.abs(pt.M)) + 9, padL + plotW - 96)}
          y={Math.max(yAt(pt.N) - 9, padT + 10)}
          fill={ptColor}
          fontSize={10}
          fontWeight="700"
        >
          {`(${pt.M.toFixed(1)} ; ${pt.N.toFixed(0)})`}
        </SvgText>

        {/* Légende */}
        <Line
          x1={padL + 6}
          y1={padT + 8}
          x2={padL + 24}
          y2={padT + 8}
          stroke={CURVE}
          strokeWidth={2.5}
        />
        <SvgText x={padL + 29} y={padT + 11} fill={ANNOT} fontSize={10}>
          Enveloppe résistante
        </SvgText>
        <Circle cx={padL + 15} cy={padT + 22} r={4} fill={ptColor} />
        <SvgText x={padL + 29} y={padT + 25} fill={ANNOT} fontSize={10}>
          {inside ? "Point de calcul — intérieur" : "Point de calcul — EXTÉRIEUR"}
        </SvgText>

        {/* Titres d'axes */}
        <SvgText
          x={padL + plotW / 2}
          y={height - 5}
          fill={AXIS}
          fontSize={10}
          textAnchor="middle"
        >
          {data.labels?.x ?? "M [kN·m]"}
        </SvgText>
        <SvgText
          x={13}
          y={padT + plotH / 2}
          fill={AXIS}
          fontSize={10}
          textAnchor="middle"
          transform={`rotate(-90 13 ${padT + plotH / 2})`}
        >
          {data.labels?.y ?? "N [kN]"}
        </SvgText>
      </G>
    </Svg>
  );
}
