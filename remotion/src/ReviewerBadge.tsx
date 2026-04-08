import React from "react";
import { useCurrentFrame, useVideoConfig, spring } from "remotion";
import { G2_RED, FONT_FAMILY } from "./theme";

const BADGE_BG = "#FFD7D1";
const BADGE_TEXT = "#201F23";

export interface ReviewerBadgeProps {
  durationFrames: number;
}

export const ReviewerBadge: React.FC<ReviewerBadgeProps> = () => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  // Slide in from right (0–22f)
  const slideSpring = spring({
    fps,
    frame,
    config: { damping: 16, stiffness: 120, mass: 1 },
    durationInFrames: 22,
  });

  // Start off-screen right, slide to resting position
  const badgeW = width * 0.14;
  const slideX = (1 - slideSpring) * (badgeW + width * 0.03 + 20);

  const pad = width * 0.025;
  const fontSize = width * 0.011;
  const starSize = width * 0.015;
  const borderRadius = width * 0.011;
  const borderWidth = Math.max(3, width * 0.002);

  return (
    <div
      style={{
        width,
        height,
        position: "relative",
        overflow: "hidden",
        backgroundColor: "#00FF00",
        fontFamily: FONT_FAMILY,
      }}
    >
      <div
        style={{
          position: "absolute",
          top: pad,
          right: pad,
          transform: `translateX(${slideX}px)`,
          backgroundColor: BADGE_BG,
          border: `${borderWidth}px solid ${G2_RED}`,
          borderRadius,
          boxShadow: `0 0 0 2px ${G2_RED}`,
          padding: `${width * 0.008}px ${width * 0.01}px`,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: width * 0.004,
          minWidth: badgeW,
        }}
      >
        <div
          style={{
            color: BADGE_TEXT,
            fontWeight: 700,
            fontSize,
            lineHeight: 1.3,
            textAlign: "center",
            whiteSpace: "nowrap",
            textShadow: `0 0 2px ${BADGE_TEXT}`,
          }}
        >
          G2 Verified Reviewer
        </div>
        <div style={{ display: "flex", gap: width * 0.003 }}>
          {[...Array(5)].map((_, i) => (
            <span
              key={i}
              style={{
                color: G2_RED,
                fontSize: starSize,
                lineHeight: 1,
                textShadow: `0 0 2px ${G2_RED}`,
              }}
            >
              ★
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};
