import React from "react";
import { useCurrentFrame, interpolate, Easing } from "remotion";
import { G2_RED } from "../theme";

interface HighlightProps {
  startFrame: number;
  durationFrames: number;
  x?: number;
  y?: number;
  w?: number;
  h?: number;
}

export const Highlight: React.FC<HighlightProps> = ({
  startFrame,
  durationFrames,
  x = 480,
  y = 270,
  w = 960,
  h = 540,
}) => {
  const frame = useCurrentFrame();
  const rel = frame - startFrame;

  if (rel < 0 || rel >= durationFrames) return null;

  const exitStart = durationFrames - 10;

  const scaleIn = interpolate(rel, [0, 10], [0.6, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  const opacityIn = interpolate(rel, [0, 8], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const opacityOut = interpolate(rel, [exitStart, durationFrames], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.in(Easing.cubic),
  });

  // Subtle pulse after entry
  const pulse = rel > 10
    ? 1 + Math.sin((rel / 10) * Math.PI) * 0.025
    : scaleIn;

  const scale = rel > 10 ? pulse : scaleIn;
  const opacity = opacityIn * opacityOut;

  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width: w,
        height: h,
        transform: `scale(${scale})`,
        transformOrigin: "center center",
        opacity,
        border: `5px solid ${G2_RED}`,
        borderRadius: 10,
        boxShadow: `0 0 24px ${G2_RED}99, inset 0 0 24px ${G2_RED}22`,
        pointerEvents: "none",
      }}
    />
  );
};
