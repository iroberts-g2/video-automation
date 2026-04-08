import React from "react";
import { useCurrentFrame, interpolate, Easing } from "remotion";
import { G2_RED, G2_WHITE, FONT_FAMILY } from "../theme";

interface CalloutProps {
  startFrame: number;
  durationFrames: number;
  text?: string;
}

export const Callout: React.FC<CalloutProps> = ({
  startFrame,
  durationFrames,
  text = "",
}) => {
  const frame = useCurrentFrame();
  const rel = frame - startFrame;

  if (rel < 0 || rel >= durationFrames) return null;

  const exitStart = durationFrames - 12;

  const slideIn = interpolate(rel, [0, 14], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  const slideOut = interpolate(rel, [exitStart, durationFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.in(Easing.cubic),
  });

  const progress = slideIn * (1 - slideOut);
  const translateX = interpolate(progress, [0, 1], [-220, 0]);
  const opacity = progress;

  const accentWidth = interpolate(rel, [4, 18], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.quad),
  }) * (1 - slideOut);

  return (
    <div
      style={{
        position: "absolute",
        left: 60,
        top: "40%",
        transform: `translateX(${translateX}px)`,
        opacity,
        fontFamily: FONT_FAMILY,
        pointerEvents: "none",
      }}
    >
      {/* Red accent line */}
      <div
        style={{
          width: `${accentWidth * 160}px`,
          height: 4,
          backgroundColor: G2_RED,
          marginBottom: 10,
          borderRadius: 2,
        }}
      />
      {/* Text card */}
      <div
        style={{
          backgroundColor: "rgba(26, 26, 46, 0.88)",
          borderLeft: `4px solid ${G2_RED}`,
          paddingTop: 14,
          paddingBottom: 14,
          paddingLeft: 20,
          paddingRight: 24,
          borderRadius: "0 6px 6px 0",
        }}
      >
        <span
          style={{
            color: G2_WHITE,
            fontSize: 36,
            fontWeight: 700,
            letterSpacing: "0.01em",
            whiteSpace: "nowrap",
          }}
        >
          {text}
        </span>
      </div>
    </div>
  );
};
