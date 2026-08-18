// Courbe SVG du spectre de réponse sismique (Se élastique + Sd de
// dimensionnement), mise à jour en direct à partir des choix utilisateur —
// pas d'aller-retour serveur (voir src/lib/seismicSpectrum.ts).

import React from "react";
import Svg, { Circle, G, Line, Path, Text as SvgText } from "react-native-svg";

import { colors } from "../theme";
import { buildSpectrumCurves, pointAt, Country } from "../lib/seismicSpectrum";

const AXIS = colors.onSurfaceTertiary;
const ANNOT = colors.onSurface;
const SE_COLOR = colors.onSurfaceTertiary;
const SD_COLOR = colors.brand;
const POINT_COLOR = colors.error;

type Props = {
  width: number;
  height: number;
  data: Record<string, string>;
};

export function SpectrumChart({ width, height, data }: Props) {
  const country: Country = data.country === "CH" ? "CH" : "FR";
  const q = parseFloat(data.q ?? "1.5") || 1.5;
  const xi = parseFloat(data.xi_percent ?? "5") || 5;
  const spectrumInputs = {
    country,
    zone: data.zone ?? "",
    soilClass: data.soil_class ?? "",
    q,
    importanceClass: data.importance_class ?? (country === "FR" ? "II" : "III"),
    xiPercent: xi,
  };
  const curves = buildSpectrumCurves(spectrumInputs, 60, 4);

  const tPointRaw = parseFloat(data.t_point ?? "");
  const hasTPoint = Number.isFinite(tPointRaw) && tPointRaw >= 0;
  const point = hasTPoint ? pointAt(spectrumInputs, tPointRaw) : null;

  const padL = 46;
  const padR = 16;
  const padT = 18;
  const padB = 34;
  const plotW = Math.max(width - padL - padR, 10);
  const plotH = Math.max(height - padT - padB, 10);

  if (!curves) {
    return (
      <Svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
        <SvgText
          x={width / 2}
          y={height / 2}
          fill={ANNOT}
          fontSize={12}
          textAnchor="middle"
        >
          Choisir une zone et une classe de sol
        </SvgText>
      </Svg>
    );
  }

  const Tmax = 4;
  const pointInRange = point !== null && tPointRaw <= Tmax;
  const Smax =
    Math.max(...curves.Se, ...curves.Sd, ...(pointInRange && point ? [point.Se, point.Sd] : [])) * 1.12;

  const xAt = (T: number) => padL + (T / Tmax) * plotW;
  const yAt = (S: number) => padT + plotH - (S / Smax) * plotH;

  const pathFor = (values: number[]) =>
    curves.T.map((t, i) => `${i === 0 ? "M" : "L"} ${xAt(t).toFixed(1)} ${yAt(values[i]).toFixed(1)}`).join(" ");

  // Repères T (axe horizontal) et S (axe vertical).
  const xTicks = [0, 1, 2, 3, 4];
  const yTicksCount = 4;
  const yTicks = Array.from({ length: yTicksCount + 1 }, (_, i) => (Smax * i) / yTicksCount);

  const { TB, TC, TD } = curves.soil;

  return (
    <Svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <G>
        {/* Grille horizontale + labels axe Y */}
        {yTicks.map((s, i) => (
          <G key={`y-${i}`}>
            <Line
              x1={padL}
              y1={yAt(s)}
              x2={padL + plotW}
              y2={yAt(s)}
              stroke={AXIS}
              strokeWidth={0.5}
              opacity={0.25}
            />
            <SvgText x={padL - 6} y={yAt(s) + 3} fill={AXIS} fontSize={9} textAnchor="end">
              {s.toFixed(1)}
            </SvgText>
          </G>
        ))}

        {/* Repères TB / TC / TD */}
        {[TB, TC, TD].map((t, i) => (
          <G key={`marker-${i}`}>
            <Line
              x1={xAt(t)}
              y1={padT}
              x2={xAt(t)}
              y2={padT + plotH}
              stroke={AXIS}
              strokeWidth={0.5}
              strokeDasharray="3,3"
              opacity={0.4}
            />
          </G>
        ))}

        {/* Axe X + labels */}
        {xTicks.map((t) => (
          <G key={`x-${t}`}>
            <Line x1={xAt(t)} y1={padT + plotH} x2={xAt(t)} y2={padT + plotH + 4} stroke={AXIS} strokeWidth={1} />
            <SvgText x={xAt(t)} y={padT + plotH + 16} fill={AXIS} fontSize={9} textAnchor="middle">
              {t}
            </SvgText>
          </G>
        ))}
        <Line x1={padL} y1={padT + plotH} x2={padL + plotW} y2={padT + plotH} stroke={AXIS} strokeWidth={1} />
        <Line x1={padL} y1={padT} x2={padL} y2={padT + plotH} stroke={AXIS} strokeWidth={1} />

        {/* Courbe Se — spectre de réponse élastique */}
        <Path d={pathFor(curves.Se)} stroke={SE_COLOR} strokeWidth={1.5} strokeDasharray="4,3" fill="none" />
        {/* Courbe Sd — spectre de dimensionnement */}
        <Path d={pathFor(curves.Sd)} stroke={SD_COLOR} strokeWidth={2.5} fill="none" />

        {/* Point lu sur la courbe pour une période T donnée */}
        {pointInRange && point && (
          <G>
            <Line
              x1={xAt(tPointRaw)}
              y1={padT}
              x2={xAt(tPointRaw)}
              y2={padT + plotH}
              stroke={POINT_COLOR}
              strokeWidth={1}
              strokeDasharray="2,2"
              opacity={0.6}
            />
            <Line
              x1={padL}
              y1={yAt(point.Sd)}
              x2={xAt(tPointRaw)}
              y2={yAt(point.Sd)}
              stroke={POINT_COLOR}
              strokeWidth={1}
              strokeDasharray="2,2"
              opacity={0.6}
            />
            <Circle cx={xAt(tPointRaw)} cy={yAt(point.Se)} r={3.5} fill={SE_COLOR} stroke={colors.surface} strokeWidth={1} />
            <Circle cx={xAt(tPointRaw)} cy={yAt(point.Sd)} r={4.5} fill={POINT_COLOR} stroke={colors.surface} strokeWidth={1.5} />
            <SvgText
              x={Math.min(xAt(tPointRaw) + 8, padL + plotW - 90)}
              y={Math.max(yAt(point.Sd) - 10, padT + 10)}
              fill={POINT_COLOR}
              fontSize={10}
              fontWeight="700"
            >
              {`T=${tPointRaw.toFixed(2)}s · Sd=${point.Sd.toFixed(3)}`}
            </SvgText>
          </G>
        )}

        {/* Légende */}
        <Line x1={padL + 4} y1={padT + 6} x2={padL + 22} y2={padT + 6} stroke={SE_COLOR} strokeWidth={1.5} strokeDasharray="4,3" />
        <SvgText x={padL + 27} y={padT + 9} fill={ANNOT} fontSize={10}>
          Se — réponse élastique
        </SvgText>
        <Line x1={padL + 4} y1={padT + 20} x2={padL + 22} y2={padT + 20} stroke={SD_COLOR} strokeWidth={2.5} />
        <SvgText x={padL + 27} y={padT + 23} fill={ANNOT} fontSize={10}>
          Sd — dimensionnement (q={q.toFixed(2)})
        </SvgText>

        {/* Axe labels */}
        <SvgText x={padL + plotW / 2} y={height - 4} fill={AXIS} fontSize={10} textAnchor="middle">
          T [s]
        </SvgText>
        <SvgText
          x={12}
          y={padT + plotH / 2}
          fill={AXIS}
          fontSize={10}
          textAnchor="middle"
          transform={`rotate(-90 12 ${padT + plotH / 2})`}
        >
          S [m/s²]
        </SvgText>
      </G>
    </Svg>
  );
}
