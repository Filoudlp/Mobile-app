// CAD-style dark blueprint grid background.
// Rendered as a static SVG behind a Schema component.

import React from "react";
import Svg, { Line, Rect } from "react-native-svg";

import { colors } from "../theme";

type Props = {
  width: number;
  height: number;
};

export function BlueprintGrid({ width, height }: Props) {
  const minor = 16;
  const major = 80;

  const vMinor: number[] = [];
  const hMinor: number[] = [];
  const vMajor: number[] = [];
  const hMajor: number[] = [];

  for (let x = 0; x <= width; x += minor) {
    if (x % major === 0) vMajor.push(x);
    else vMinor.push(x);
  }
  for (let y = 0; y <= height; y += minor) {
    if (y % major === 0) hMajor.push(y);
    else hMinor.push(y);
  }

  return (
    <Svg
      width={width}
      height={height}
      style={{ position: "absolute", top: 0, left: 0 }}
    >
      <Rect x={0} y={0} width={width} height={height} fill={colors.surface} />
      {vMinor.map((x) => (
        <Line
          key={`vmin-${x}`}
          x1={x}
          y1={0}
          x2={x}
          y2={height}
          stroke={colors.divider}
          strokeWidth={0.5}
          opacity={0.5}
        />
      ))}
      {hMinor.map((y) => (
        <Line
          key={`hmin-${y}`}
          x1={0}
          y1={y}
          x2={width}
          y2={y}
          stroke={colors.divider}
          strokeWidth={0.5}
          opacity={0.5}
        />
      ))}
      {vMajor.map((x) => (
        <Line
          key={`vmaj-${x}`}
          x1={x}
          y1={0}
          x2={x}
          y2={height}
          stroke={colors.border}
          strokeWidth={0.8}
          opacity={0.9}
        />
      ))}
      {hMajor.map((y) => (
        <Line
          key={`hmaj-${y}`}
          x1={0}
          y1={y}
          x2={width}
          y2={y}
          stroke={colors.border}
          strokeWidth={0.8}
          opacity={0.9}
        />
      ))}
    </Svg>
  );
}
