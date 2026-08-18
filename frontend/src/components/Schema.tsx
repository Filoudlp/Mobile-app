// SVG blueprint-style schemas for each module.
// Rendered on a CAD-grid background (the parent supplies the grid).

import React from "react";
import Svg, {
  Circle,
  G,
  Line,
  Path,
  Polygon,
  Rect,
  Text as SvgText,
} from "react-native-svg";

import { colors } from "../theme";

type Props = {
  type: "beam" | "column" | "bolt" | "roof" | "wind" | "rc-column";
  width: number;
  height: number;
  data: Record<string, string>;
};

const STROKE = colors.brandSecondary;
const ANNOT = colors.onSurface;
const DIM = colors.onSurfaceTertiary;

export function Schema({ type, width, height, data }: Props) {
  return (
    <Svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      style={{ position: "absolute", top: 0, left: 0 }}
    >
      {type === "beam" && <BeamSchema width={width} height={height} data={data} />}
      {type === "column" && (
        <ColumnSchema width={width} height={height} data={data} />
      )}
      {type === "bolt" && <BoltSchema width={width} height={height} data={data} />}
      {type === "roof" && <RoofSchema width={width} height={height} data={data} />}
      {type === "wind" && <WindSchema width={width} height={height} data={data} />}
      {type === "rc-column" && (
        <RcColumnSchema width={width} height={height} data={data} />
      )}
    </Svg>
  );
}

function BeamSchema({
  width,
  height,
  data,
}: {
  width: number;
  height: number;
  data: Record<string, string>;
}) {
  const padX = 48;
  const beamY = height * 0.62;
  const beamW = width - padX * 2;
  const beamH = 14;
  const arrowSpace = 70;

  // Distributed load arrows
  const arrows = 9;
  const step = beamW / (arrows - 1);

  return (
    <G>
      {/* Distributed load bar */}
      <Rect
        x={padX}
        y={beamY - arrowSpace - 10}
        width={beamW}
        height={6}
        fill={colors.brand}
        opacity={0.85}
      />
      {/* Arrows */}
      {Array.from({ length: arrows }).map((_, i) => {
        const x = padX + step * i;
        return (
          <G key={i}>
            <Line
              x1={x}
              y1={beamY - arrowSpace}
              x2={x}
              y2={beamY - 8}
              stroke={colors.brand}
              strokeWidth={1.5}
            />
            <Polygon
              points={`${x - 4},${beamY - 12} ${x + 4},${beamY - 12} ${x},${beamY - 4}`}
              fill={colors.brand}
            />
          </G>
        );
      })}
      <SvgText
        x={width / 2}
        y={beamY - arrowSpace - 18}
        fill={ANNOT}
        fontSize={12}
        textAnchor="middle"
      >
        {`q = ${data.q_els ?? data.load ?? "—"} kN/m`}
      </SvgText>

      {/* Beam */}
      <Rect
        x={padX}
        y={beamY}
        width={beamW}
        height={beamH}
        fill={colors.surfaceTertiary}
        stroke={STROKE}
        strokeWidth={2}
      />
      <SvgText
        x={padX + beamW / 2}
        y={beamY + beamH / 2 + 4}
        fill={ANNOT}
        fontSize={11}
        textAnchor="middle"
      >
        {data.profile ?? "—"}
      </SvgText>

      {/* Left support (pinned) */}
      <Polygon
        points={`${padX},${beamY + beamH} ${padX - 14},${beamY + beamH + 22} ${padX + 14},${beamY + beamH + 22}`}
        fill="none"
        stroke={STROKE}
        strokeWidth={2}
      />
      <Line
        x1={padX - 22}
        y1={beamY + beamH + 22}
        x2={padX + 22}
        y2={beamY + beamH + 22}
        stroke={STROKE}
        strokeWidth={2}
      />
      {/* Right support (roller) */}
      <Polygon
        points={`${padX + beamW},${beamY + beamH} ${padX + beamW - 14},${beamY + beamH + 22} ${padX + beamW + 14},${beamY + beamH + 22}`}
        fill="none"
        stroke={STROKE}
        strokeWidth={2}
      />
      <Circle
        cx={padX + beamW - 8}
        cy={beamY + beamH + 28}
        r={4}
        fill="none"
        stroke={STROKE}
        strokeWidth={1.5}
      />
      <Circle
        cx={padX + beamW + 8}
        cy={beamY + beamH + 28}
        r={4}
        fill="none"
        stroke={STROKE}
        strokeWidth={1.5}
      />
      <Line
        x1={padX + beamW - 22}
        y1={beamY + beamH + 34}
        x2={padX + beamW + 22}
        y2={beamY + beamH + 34}
        stroke={STROKE}
        strokeWidth={2}
      />

      {/* Length dimension */}
      <Line
        x1={padX}
        y1={beamY + beamH + 56}
        x2={padX + beamW}
        y2={beamY + beamH + 56}
        stroke={DIM}
        strokeWidth={1}
      />
      <Line
        x1={padX}
        y1={beamY + beamH + 50}
        x2={padX}
        y2={beamY + beamH + 62}
        stroke={DIM}
        strokeWidth={1}
      />
      <Line
        x1={padX + beamW}
        y1={beamY + beamH + 50}
        x2={padX + beamW}
        y2={beamY + beamH + 62}
        stroke={DIM}
        strokeWidth={1}
      />
      <SvgText
        x={padX + beamW / 2}
        y={beamY + beamH + 75}
        fill={DIM}
        fontSize={11}
        textAnchor="middle"
      >
        {`L = ${data.L_m ?? data.span ?? "—"} m`}
      </SvgText>

      {/* Efforts de calcul (module poutre) */}
      <SvgText x={padX} y={beamY - arrowSpace - 34} fill={DIM} fontSize={11}>
        {[
          data.My_ed && parseFloat(data.My_ed) !== 0
            ? `My,Ed = ${data.My_ed} kN·m`
            : null,
          data.Vz_ed && parseFloat(data.Vz_ed) !== 0
            ? `Vz,Ed = ${data.Vz_ed} kN`
            : null,
          data.N_ed && parseFloat(data.N_ed) !== 0
            ? `N,Ed = ${data.N_ed} kN`
            : null,
        ]
          .filter(Boolean)
          .join("   ")}
      </SvgText>
    </G>
  );
}

function ColumnSchema({
  width,
  height,
  data,
}: {
  width: number;
  height: number;
  data: Record<string, string>;
}) {
  const cx = width / 2;
  const colW = 36;
  const top = 96;
  const bottom = height - 60;
  const colH = bottom - top;

  const num = (v: string | undefined): number => {
    const n = parseFloat(v ?? "");
    return Number.isFinite(n) ? n : 0;
  };
  const N = data.N_ed;
  const Vz = num(data.Vz_ed);
  const Vy = num(data.Vy_ed);
  const My = num(data.My_ed);
  const Mz = num(data.Mz_ed);
  const hasV = Vz !== 0 || Vy !== 0;
  const hasM = My !== 0 || Mz !== 0;

  const vLabels = [
    Vz !== 0 ? `Vz = ${data.Vz_ed} kN` : null,
    Vy !== 0 ? `Vy = ${data.Vy_ed} kN` : null,
  ].filter((s): s is string => s !== null);
  const mLabels = [
    My !== 0 ? `My = ${data.My_ed} kN·m` : null,
    Mz !== 0 ? `Mz = ${data.Mz_ed} kN·m` : null,
  ].filter((s): s is string => s !== null);

  return (
    <G>
      {/* N — effort normal (axial), flèche verticale */}
      <Line
        x1={cx}
        y1={20}
        x2={cx}
        y2={top - 6}
        stroke={colors.brand}
        strokeWidth={2.5}
      />
      <Polygon
        points={`${cx - 6},${top - 12} ${cx + 6},${top - 12} ${cx},${top - 2}`}
        fill={colors.brand}
      />
      <SvgText x={cx + 12} y={36} fill={ANNOT} fontSize={12}>
        {`N = ${N ?? "—"} kN`}
      </SvgText>

      {/* V — effort tranchant, flèche horizontale appliquée en tête de poteau */}
      {hasV && (
        <G>
          <Line
            x1={cx - 64}
            y1={top + 16}
            x2={cx - colW / 2 - 6}
            y2={top + 16}
            stroke={colors.warning}
            strokeWidth={2.5}
          />
          <Polygon
            points={`${cx - colW / 2 - 12},${top + 10} ${cx - colW / 2 - 12},${top + 22} ${cx - colW / 2 - 2},${top + 16}`}
            fill={colors.warning}
          />
          {vLabels.map((label, i) => (
            <SvgText
              key={label}
              x={cx - 70}
              y={top + 12 + i * 13}
              fill={ANNOT}
              fontSize={11}
              textAnchor="end"
            >
              {label}
            </SvgText>
          ))}
        </G>
      )}

      {/* M — moment fléchissant, flèche courbe en tête de poteau */}
      {hasM && (
        <G>
          <Path
            d={`M ${cx + colW / 2 + 8} ${top - 6} A 15 15 0 1 1 ${cx + colW / 2 + 8} ${top + 24}`}
            stroke={colors.error}
            strokeWidth={2}
            fill="none"
          />
          <Polygon
            points={`${cx + colW / 2},${top + 20} ${cx + colW / 2 + 14},${top + 20} ${cx + colW / 2 + 7},${top + 30}`}
            fill={colors.error}
          />
          {mLabels.map((label, i) => (
            <SvgText
              key={label}
              x={cx + colW / 2 + 32}
              y={top + 10 + i * 13}
              fill={ANNOT}
              fontSize={11}
            >
              {label}
            </SvgText>
          ))}
        </G>
      )}

      {/* Column body */}
      <Rect
        x={cx - colW / 2}
        y={top}
        width={colW}
        height={colH}
        fill={colors.surfaceTertiary}
        stroke={STROKE}
        strokeWidth={2}
      />
      <SvgText
        x={cx}
        y={top + colH / 2}
        fill={ANNOT}
        fontSize={11}
        textAnchor="middle"
        transform={`rotate(-90 ${cx} ${top + colH / 2})`}
      >
        {data.profile ?? "—"}
      </SvgText>

      {/* Base plate */}
      <Rect
        x={cx - colW}
        y={bottom}
        width={colW * 2}
        height={6}
        fill={STROKE}
      />
      {/* Hatching for ground */}
      {Array.from({ length: 8 }).map((_, i) => {
        const x = cx - colW + i * ((colW * 2) / 7);
        return (
          <Line
            key={i}
            x1={x}
            y1={bottom + 6}
            x2={x - 8}
            y2={bottom + 18}
            stroke={STROKE}
            strokeWidth={1}
          />
        );
      })}

      {/* Height dimension */}
      <Line
        x1={cx + colW + 30}
        y1={top}
        x2={cx + colW + 30}
        y2={bottom}
        stroke={DIM}
        strokeWidth={1}
      />
      <Line
        x1={cx + colW + 24}
        y1={top}
        x2={cx + colW + 36}
        y2={top}
        stroke={DIM}
        strokeWidth={1}
      />
      <Line
        x1={cx + colW + 24}
        y1={bottom}
        x2={cx + colW + 36}
        y2={bottom}
        stroke={DIM}
        strokeWidth={1}
      />
      <SvgText
        x={cx + colW + 40}
        y={top + colH / 2}
        fill={DIM}
        fontSize={11}
      >
        {`L = ${data.length_m ?? "—"} m`}
      </SvgText>
    </G>
  );
}

function BoltSchema({
  width,
  height,
  data,
}: {
  width: number;
  height: number;
  data: Record<string, string>;
}) {
  const cx = width / 2;
  const cy = height / 2;
  const plateW = 200;
  const plateH = 140;
  const count = Math.max(1, Math.min(8, parseInt(data.count ?? "4", 10) || 4));

  // Arrange bolts on a grid
  const cols = count <= 2 ? count : 2;
  const rows = Math.ceil(count / cols);
  const dx = 40;
  const dy = 40;

  const positions: { x: number; y: number }[] = [];
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      if (positions.length >= count) break;
      const x = cx - ((cols - 1) * dx) / 2 + c * dx;
      const y = cy - ((rows - 1) * dy) / 2 + r * dy;
      positions.push({ x, y });
    }
  }

  return (
    <G>
      {/* Plate */}
      <Rect
        x={cx - plateW / 2}
        y={cy - plateH / 2}
        width={plateW}
        height={plateH}
        fill={colors.surfaceTertiary}
        stroke={STROKE}
        strokeWidth={2}
      />
      {/* Diagonal hatching inside plate */}
      {Array.from({ length: 10 }).map((_, i) => {
        const off = i * 30 - 100;
        return (
          <Line
            key={i}
            x1={cx - plateW / 2 + off}
            y1={cy - plateH / 2}
            x2={cx - plateW / 2 + off + plateH}
            y2={cy + plateH / 2}
            stroke={STROKE}
            strokeWidth={0.5}
            opacity={0.25}
          />
        );
      })}

      {/* Bolts */}
      {positions.map((p, i) => (
        <G key={i}>
          <Circle
            cx={p.x}
            cy={p.y}
            r={10}
            fill={colors.surface}
            stroke={STROKE}
            strokeWidth={1.5}
          />
          <Circle cx={p.x} cy={p.y} r={3} fill={STROKE} />
          <Path
            d={`M ${p.x - 6} ${p.y - 6} L ${p.x + 6} ${p.y + 6} M ${p.x + 6} ${p.y - 6} L ${p.x - 6} ${p.y + 6}`}
            stroke={STROKE}
            strokeWidth={0.8}
            opacity={0.5}
          />
        </G>
      ))}

      {/* Force arrow */}
      <Line
        x1={cx - plateW / 2 - 70}
        y1={cy}
        x2={cx - plateW / 2 - 10}
        y2={cy}
        stroke={colors.brand}
        strokeWidth={2.5}
      />
      <Polygon
        points={`${cx - plateW / 2 - 16},${cy - 6} ${cx - plateW / 2 - 16},${cy + 6} ${cx - plateW / 2 - 4},${cy}`}
        fill={colors.brand}
      />
      <SvgText
        x={cx - plateW / 2 - 70}
        y={cy - 12}
        fill={ANNOT}
        fontSize={12}
      >
        {`V = ${data.force ?? "—"} kN`}
      </SvgText>

      {/* Bolt label */}
      <SvgText
        x={cx}
        y={cy + plateH / 2 + 22}
        fill={DIM}
        fontSize={11}
        textAnchor="middle"
      >
        {`${count} × ${data.diameter ?? "—"} cl.${data.class ?? "—"}`}
      </SvgText>
    </G>
  );
}

function RoofSchema({
  width,
  height,
  data,
}: {
  width: number;
  height: number;
  data: Record<string, string>;
}) {
  const cx = width / 2;
  const eavesY = height * 0.62;
  const halfSpan = Math.min(width * 0.32, 150);
  // Angle réel utilisé pour le calcul, mais borné à l'affichage pour que
  // le pictogramme reste lisible (un toit à 2° ou à 85° reste dessinable).
  const angleRaw = parseFloat(data.angle_deg ?? "20") || 0;
  const angleDraw = Math.min(Math.max(angleRaw, 8), 50);
  const apexRise = halfSpan * Math.tan((angleDraw * Math.PI) / 180);
  const apexY = eavesY - apexRise;
  const wallDrop = 40;

  const country = data.country ?? "FR";
  const isFR = country !== "CH";

  // Flèches de charge de neige au-dessus des deux versants.
  const arrowsPerSide = 4;
  const buildArrows = (xStart: number, xEnd: number, yStart: number, yEnd: number) => {
    const items = [];
    for (let i = 0; i < arrowsPerSide; i++) {
      const t = i / (arrowsPerSide - 1);
      const x = xStart + (xEnd - xStart) * t;
      const yRoof = yStart + (yEnd - yStart) * t;
      const yTop = yRoof - 34;
      items.push(
        <G key={`${xStart}-${i}`}>
          <Line x1={x} y1={yTop} x2={x} y2={yRoof - 6} stroke={colors.brand} strokeWidth={1.5} />
          <Polygon
            points={`${x - 4},${yRoof - 10} ${x + 4},${yRoof - 10} ${x},${yRoof - 2}`}
            fill={colors.brand}
          />
        </G>,
      );
    }
    return items;
  };

  return (
    <G>
      {/* Flèches de neige */}
      {buildArrows(cx - halfSpan, cx, eavesY, apexY)}
      {buildArrows(cx, cx + halfSpan, apexY, eavesY)}

      <SvgText x={cx} y={apexY - 42} fill={ANNOT} fontSize={12} textAnchor="middle">
        {`s (neige)`}
      </SvgText>

      {/* Toiture à deux versants */}
      <Path
        d={`M ${cx - halfSpan} ${eavesY} L ${cx} ${apexY} L ${cx + halfSpan} ${eavesY}`}
        stroke={STROKE}
        strokeWidth={2.5}
        fill="none"
      />

      {/* Murs */}
      <Line x1={cx - halfSpan} y1={eavesY} x2={cx - halfSpan} y2={eavesY + wallDrop} stroke={STROKE} strokeWidth={2} />
      <Line x1={cx + halfSpan} y1={eavesY} x2={cx + halfSpan} y2={eavesY + wallDrop} stroke={STROKE} strokeWidth={2} />
      <Line
        x1={cx - halfSpan - 12}
        y1={eavesY + wallDrop}
        x2={cx + halfSpan + 12}
        y2={eavesY + wallDrop}
        stroke={STROKE}
        strokeWidth={2}
      />

      {/* Angle α */}
      <Path
        d={`M ${cx - 28} ${eavesY} A 28 28 0 0 1 ${cx - 28 + 28 * Math.cos((angleDraw * Math.PI) / 180)} ${eavesY - 28 * Math.sin((angleDraw * Math.PI) / 180)}`}
        stroke={DIM}
        strokeWidth={1}
        fill="none"
      />
      <SvgText x={cx - 52} y={eavesY - 10} fill={DIM} fontSize={11}>
        {`α = ${angleRaw.toFixed(0)}°`}
      </SvgText>

      {/* Localisation */}
      <SvgText x={cx} y={eavesY + wallDrop + 26} fill={ANNOT} fontSize={12} textAnchor="middle">
        {isFR
          ? `France — zone ${data.zone ?? "—"} — ${data.altitude_m ?? "—"} m`
          : `Suisse — h = ${data.altitude_m ?? "—"} m — h0 = ${data.h0_m ?? "—"} m`}
      </SvgText>
    </G>
  );
}

function WindSchema({
  width,
  height,
  data,
}: {
  width: number;
  height: number;
  data: Record<string, string>;
}) {
  const cx = width / 2;
  const buildingW = Math.min(width * 0.34, 170);
  const top = 74;
  const ground = height - 64;
  const buildingH = ground - top;
  const left = cx - buildingW / 2;
  const right = cx + buildingW / 2;

  const country = data.country ?? "FR";
  const isFR = country !== "CH";
  const arrows = 4;
  const step = buildingH / (arrows + 1);

  return (
    <G>
      {/* Flèches de vent (face au vent, zone D) */}
      {Array.from({ length: arrows }).map((_, i) => {
        const y = top + step * (i + 1);
        return (
          <G key={`d-${i}`}>
            <Line x1={left - 62} y1={y} x2={left - 10} y2={y} stroke={colors.brand} strokeWidth={2} />
            <Polygon points={`${left - 16},${y - 5} ${left - 16},${y + 5} ${left - 4},${y}`} fill={colors.brand} />
          </G>
        );
      })}
      <SvgText x={left - 36} y={top - 12} fill={ANNOT} fontSize={11} textAnchor="middle">
        {`we,D`}
      </SvgText>

      {/* Flèches de succion (face sous le vent, zone E) */}
      {Array.from({ length: arrows }).map((_, i) => {
        const y = top + step * (i + 1);
        return (
          <G key={`e-${i}`}>
            <Line x1={right + 10} y1={y} x2={right + 46} y2={y} stroke={colors.error} strokeWidth={2} />
            <Polygon points={`${right + 46},${y - 5} ${right + 46},${y + 5} ${right + 58},${y}`} fill={colors.error} />
          </G>
        );
      })}
      <SvgText x={right + 40} y={top - 12} fill={ANNOT} fontSize={11} textAnchor="middle">
        {`we,E`}
      </SvgText>

      {/* Bâtiment (élévation) */}
      <Rect
        x={left}
        y={top}
        width={buildingW}
        height={buildingH}
        fill={colors.surfaceTertiary}
        stroke={STROKE}
        strokeWidth={2.5}
      />
      {/* Séparation zones A / B (mur latéral vu de face, indicatif) */}
      <Line x1={left + buildingW * 0.22} y1={top} x2={left + buildingW * 0.22} y2={ground} stroke={DIM} strokeWidth={1} opacity={0.5} />
      <SvgText x={left + buildingW * 0.11} y={top + buildingH / 2} fill={DIM} fontSize={10} textAnchor="middle">A</SvgText>
      <SvgText x={left + buildingW * 0.6} y={top + buildingH / 2} fill={DIM} fontSize={10} textAnchor="middle">B</SvgText>

      {/* Sol */}
      <Line x1={left - 24} y1={ground} x2={right + 24} y2={ground} stroke={STROKE} strokeWidth={2} />
      {Array.from({ length: 9 }).map((_, i) => {
        const x = left - 20 + i * ((buildingW + 40) / 8);
        return (
          <Line key={i} x1={x} y1={ground} x2={x - 8} y2={ground + 12} stroke={STROKE} strokeWidth={1} />
        );
      })}

      {/* Dimension h */}
      <Line x1={right + 74} y1={top} x2={right + 74} y2={ground} stroke={DIM} strokeWidth={1} />
      <Line x1={right + 68} y1={top} x2={right + 80} y2={top} stroke={DIM} strokeWidth={1} />
      <Line x1={right + 68} y1={ground} x2={right + 80} y2={ground} stroke={DIM} strokeWidth={1} />
      <SvgText x={right + 86} y={top + buildingH / 2} fill={DIM} fontSize={11}>
        {`h = ${data.h_m ?? "—"} m`}
      </SvgText>

      {/* qp(ze) */}
      <SvgText x={cx} y={top + buildingH / 2 - 6} fill={ANNOT} fontSize={11} textAnchor="middle">
        {`qp(ze)`}
      </SvgText>
      <SvgText x={cx} y={top + buildingH / 2 + 10} fill={DIM} fontSize={10} textAnchor="middle">
        {`d = ${data.d_m ?? "—"} m`}
      </SvgText>

      {/* Localisation */}
      <SvgText x={cx} y={ground + 30} fill={ANNOT} fontSize={12} textAnchor="middle">
        {isFR
          ? `France — région ${data.region ?? "—"} — terrain ${data.terrain_category ?? "—"}`
          : `Suisse — qp0 = ${data.qp0_kn_m2 ?? "—"} kN/m² — terrain ${data.terrain_category ?? "—"}`}
      </SvgText>
    </G>
  );
}

function RcColumnSchema({
  width,
  height,
  data,
}: {
  width: number;
  height: number;
  data: Record<string, string>;
}) {
  const num = (v: string | undefined): number => {
    const n = parseFloat(v ?? "");
    return Number.isFinite(n) ? n : 0;
  };

  const isCirc = data.shape === "circ";
  const N = num(data.N_ed_kn);
  const Mtop = num(data.M0_top_knm);
  const Mbot = num(data.M0_bot_knm);
  const l0 = data.l0_m ?? "—";

  // Élévation du poteau, à gauche ; coupe de section, à droite.
  const elevX = width * 0.34;
  const top = 92;
  const bottom = height - 74;
  const colH = bottom - top;
  const colW = 52;

  // Coupe : proportionnelle aux dimensions saisies, bornée pour rester lisible.
  const bMm = isCirc ? num(data.D_mm) : num(data.b_mm);
  const hMm = isCirc ? num(data.D_mm) : num(data.h_mm);
  const maxDim = Math.max(bMm, hMm, 1);
  const secMax = Math.min(width * 0.22, 150);
  const secW = (bMm / maxDim) * secMax;
  const secH = (hMm / maxDim) * secMax;
  const secX = width * 0.74 - secW / 2;
  const secY = top + colH / 2 - secH / 2;
  const cover = 8;

  return (
    <G>
      {/* ---- Effort normal N ---- */}
      <Line x1={elevX} y1={22} x2={elevX} y2={top - 8} stroke={colors.brand} strokeWidth={2.5} />
      <Polygon
        points={`${elevX - 6},${top - 14} ${elevX + 6},${top - 14} ${elevX},${top - 3}`}
        fill={colors.brand}
      />
      <SvgText x={elevX + 12} y={38} fill={ANNOT} fontSize={12} fontWeight="700">
        {`NEd = ${N.toFixed(0)} kN`}
      </SvgText>

      {/* ---- Moment en tête ---- */}
      {Mtop !== 0 && (
        <G>
          <Path
            d={`M ${elevX - colW / 2 - 30} ${top + 6} A 18 18 0 1 1 ${elevX - colW / 2 - 30} ${top + 40}`}
            stroke={colors.error}
            strokeWidth={2}
            fill="none"
          />
          <Polygon
            points={`${elevX - colW / 2 - 37},${top + 36} ${elevX - colW / 2 - 23},${top + 36} ${elevX - colW / 2 - 30},${top + 46}`}
            fill={colors.error}
          />
          <SvgText
            x={elevX - colW / 2 - 46}
            y={top + 12}
            fill={colors.error}
            fontSize={11}
            textAnchor="end"
          >
            {`M0,top = ${Mtop.toFixed(1)} kN·m`}
          </SvgText>
        </G>
      )}

      {/* ---- Moment en pied ---- */}
      {Mbot !== 0 && (
        <G>
          <Path
            d={`M ${elevX - colW / 2 - 30} ${bottom - 40} A 18 18 0 1 1 ${elevX - colW / 2 - 30} ${bottom - 6}`}
            stroke={colors.error}
            strokeWidth={2}
            fill="none"
          />
          <Polygon
            points={`${elevX - colW / 2 - 37},${bottom - 10} ${elevX - colW / 2 - 23},${bottom - 10} ${elevX - colW / 2 - 30},${bottom}`}
            fill={colors.error}
          />
          <SvgText
            x={elevX - colW / 2 - 46}
            y={bottom - 2}
            fill={colors.error}
            fontSize={11}
            textAnchor="end"
          >
            {`M0,bot = ${Mbot.toFixed(1)} kN·m`}
          </SvgText>
        </G>
      )}

      {/* ---- Fût du poteau ---- */}
      <Rect
        x={elevX - colW / 2}
        y={top}
        width={colW}
        height={colH}
        fill={colors.surfaceTertiary}
        stroke={STROKE}
        strokeWidth={2}
      />
      {/* Aciers longitudinaux vus en élévation */}
      <Line x1={elevX - colW / 2 + 9} y1={top + 6} x2={elevX - colW / 2 + 9} y2={bottom - 6} stroke={colors.brand} strokeWidth={1.5} opacity={0.75} />
      <Line x1={elevX + colW / 2 - 9} y1={top + 6} x2={elevX + colW / 2 - 9} y2={bottom - 6} stroke={colors.brand} strokeWidth={1.5} opacity={0.75} />
      {/* Cadres transversaux */}
      {Array.from({ length: 7 }).map((_, i) => {
        const y = top + 18 + (i * (colH - 36)) / 6;
        return (
          <Line
            key={`stirrup-${i}`}
            x1={elevX - colW / 2 + 6}
            y1={y}
            x2={elevX + colW / 2 - 6}
            y2={y}
            stroke={colors.brand}
            strokeWidth={1}
            opacity={0.45}
          />
        );
      })}

      {/* ---- Encastrement en pied ---- */}
      <Line x1={elevX - colW} y1={bottom} x2={elevX + colW} y2={bottom} stroke={STROKE} strokeWidth={2.5} />
      {Array.from({ length: 8 }).map((_, i) => {
        const x = elevX - colW + (i * 2 * colW) / 7;
        return (
          <Line key={`hatch-${i}`} x1={x} y1={bottom} x2={x - 9} y2={bottom + 13} stroke={STROKE} strokeWidth={1} />
        );
      })}

      {/* ---- Cote l0 ---- */}
      <Line x1={elevX + colW} y1={top} x2={elevX + colW} y2={bottom} stroke={DIM} strokeWidth={1} />
      <Line x1={elevX + colW - 6} y1={top} x2={elevX + colW + 6} y2={top} stroke={DIM} strokeWidth={1} />
      <Line x1={elevX + colW - 6} y1={bottom} x2={elevX + colW + 6} y2={bottom} stroke={DIM} strokeWidth={1} />
      <SvgText x={elevX + colW + 10} y={top + colH / 2} fill={DIM} fontSize={11}>
        {`l0 = ${l0} m`}
      </SvgText>

      {/* ---- Coupe de section ---- */}
      <SvgText x={secX + secW / 2} y={secY - 14} fill={DIM} fontSize={10} textAnchor="middle">
        COUPE
      </SvgText>
      {isCirc ? (
        <G>
          <Circle
            cx={secX + secW / 2}
            cy={secY + secH / 2}
            r={secW / 2}
            fill={colors.surfaceTertiary}
            stroke={STROKE}
            strokeWidth={2}
          />
          <Circle
            cx={secX + secW / 2}
            cy={secY + secH / 2}
            r={secW / 2 - cover}
            fill="none"
            stroke={colors.brand}
            strokeWidth={1}
            opacity={0.6}
          />
          {Array.from({ length: 6 }).map((_, i) => {
            const a = (i * Math.PI) / 3;
            const rr = secW / 2 - cover;
            return (
              <Circle
                key={`bar-${i}`}
                cx={secX + secW / 2 + rr * Math.cos(a)}
                cy={secY + secH / 2 + rr * Math.sin(a)}
                r={3.5}
                fill={colors.brand}
              />
            );
          })}
        </G>
      ) : (
        <G>
          <Rect
            x={secX}
            y={secY}
            width={secW}
            height={secH}
            fill={colors.surfaceTertiary}
            stroke={STROKE}
            strokeWidth={2}
          />
          <Rect
            x={secX + cover}
            y={secY + cover}
            width={secW - 2 * cover}
            height={secH - 2 * cover}
            fill="none"
            stroke={colors.brand}
            strokeWidth={1}
            opacity={0.6}
          />
          {[
            [secX + cover, secY + cover],
            [secX + secW - cover, secY + cover],
            [secX + cover, secY + secH - cover],
            [secX + secW - cover, secY + secH - cover],
          ].map(([bx, by], i) => (
            <Circle key={`bar-${i}`} cx={bx} cy={by} r={3.5} fill={colors.brand} />
          ))}
        </G>
      )}

      {/* Cotes de section */}
      <SvgText x={secX + secW / 2} y={secY + secH + 20} fill={DIM} fontSize={11} textAnchor="middle">
        {isCirc ? `Ø ${data.D_mm ?? "—"} mm` : `${data.b_mm ?? "—"} × ${data.h_mm ?? "—"} mm`}
      </SvgText>
      <SvgText x={secX + secW / 2} y={secY + secH + 36} fill={DIM} fontSize={11} textAnchor="middle">
        {`As = ${data.As_cm2 ?? "—"} cm²  •  ${data.concrete_class ?? "—"}`}
      </SvgText>
    </G>
  );
}
