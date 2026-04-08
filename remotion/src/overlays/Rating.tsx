import React from "react";
import { useCurrentFrame, interpolate, Easing } from "remotion";
import { G2_RED, G2_WHITE, FONT_FAMILY } from "../theme";

interface RatingProps {
  startFrame: number;
  durationFrames: number;
  stars?: number;
  label?: string;
}

const STAR = "★";

export const Rating: React.FC<RatingProps> = ({
  startFrame,
  durationFrames,
  stars = 5,
  label = "G2 Review",
}) => {
  const frame = useCurrentFrame();
  const rel = frame - startFrame;

  if (rel < 0 || rel >= durationFrames) return null;

  const cardH = 110;
  const bottomGap = 60;
  const exitStart = durationFrames - 15;

  const slideIn = interpolate(rel, [0, 15], [0, 1], {
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
  const translateY = interpolate(progress, [0, 1], [cardH + bottomGap + 20, 0]);

  return (
    <div
      style={{
        position: "absolute",
        left: 60,
        bottom: bottomGap,
        transform: `translateY(${translateY}px)`,
        opacity: progress,
        fontFamily: FONT_FAMILY,
        pointerEvents: "none",
        display: "flex",
        alignItems: "center",
        backgroundColor: "rgba(26, 26, 46, 0.92)",
        borderRadius: 10,
        borderTop: `4px solid ${G2_RED}`,
        paddingTop: 18,
        paddingBottom: 18,
        paddingLeft: 24,
        paddingRight: 30,
        gap: 16,
      }}
    >
      {/* G2 badge */}
      <div
        style={{
          width: 60,
          height: 60,
          borderRadius: "50%",
          backgroundColor: G2_RED,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
        }}
      >
        <span
          style={{
            color: G2_WHITE,
            fontSize: 26,
            fontWeight: 900,
            letterSpacing: "-0.02em",
          }}
        >
          G2
        </span>
      </div>

      {/* Stars + label */}
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <div style={{ display: "flex", gap: 3 }}>
          {Array.from({ length: 5 }).map((_, i) => (
            <span
              key={i}
              style={{
                color: i < stars ? G2_RED : "rgba(255,255,255,0.25)",
                fontSize: 28,
                lineHeight: 1,
              }}
            >
              {STAR}
            </span>
          ))}
        </div>
        <span
          style={{
            color: G2_WHITE,
            fontSize: 22,
            fontWeight: 600,
            letterSpacing: "0.01em",
          }}
        >
          {label}
        </span>
      </div>
    </div>
  );
};
