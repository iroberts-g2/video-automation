import React from "react";
import { useCurrentFrame, interpolate, Easing } from "remotion";
import { G2_RED } from "../theme";

interface ReactionProps {
  startFrame: number;
  durationFrames: number;
}

export const Reaction: React.FC<ReactionProps> = ({
  startFrame,
  durationFrames,
}) => {
  const frame = useCurrentFrame();
  const rel = frame - startFrame;

  if (rel < 0 || rel >= durationFrames) return null;

  const midpoint = durationFrames / 2;

  const flashIn = interpolate(rel, [0, midpoint * 0.4], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.quad),
  });

  const flashOut = interpolate(rel, [midpoint, durationFrames], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.in(Easing.cubic),
  });

  const opacity = flashIn * flashOut * 0.85;
  const borderW = Math.round(interpolate(opacity, [0, 0.85], [0, 10]));

  // Four individual border strips — no interior fill, no inset shadow
  const style = (edge: React.CSSProperties): React.CSSProperties => ({
    position: "absolute",
    backgroundColor: G2_RED,
    opacity,
    pointerEvents: "none",
    ...edge,
  });

  return (
    <>
      <div style={style({ top: 0, left: 0, right: 0, height: borderW })} />
      <div style={style({ bottom: 0, left: 0, right: 0, height: borderW })} />
      <div style={style({ top: 0, left: 0, bottom: 0, width: borderW })} />
      <div style={style({ top: 0, right: 0, bottom: 0, width: borderW })} />
    </>
  );
};
