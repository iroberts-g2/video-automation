import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate, Easing } from "remotion";
import { G2_DARK, G2_WHITE, FONT_FAMILY } from "./theme";

const ACCENT_COLOR = "#7D00FF";

interface LowerThirdProps {
  name: string;
  title: string;
}

export const LowerThird: React.FC<LowerThirdProps> = ({ name, title }) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();

  // Bar slides up from bottom (0–12f)
  const barSlideIn = interpolate(frame, [0, 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  // Bar slides back down (75–100f)
  const barSlideOut = interpolate(frame, [75, 100], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.in(Easing.cubic),
  });

  const barProgress = barSlideIn * (1 - barSlideOut);

  // Red accent line sweeps in from left (4–16f)
  const accentIn = interpolate(frame, [4, 16], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.quad),
  });
  const accentOut = interpolate(frame, [75, 100], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.in(Easing.cubic),
  });
  const accentProgress = accentIn * (1 - accentOut);

  // Speaker name fades + slides in from left (8–22f)
  const nameIn = interpolate(frame, [8, 22], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const nameOut = interpolate(frame, [75, 100], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.in(Easing.cubic),
  });
  const nameOpacity = nameIn * (1 - nameOut);
  const nameX = interpolate(nameIn, [0, 1], [-60, 0]);

  // Title fades + slides in from left (14–28f)
  const titleIn = interpolate(frame, [14, 28], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const titleOut = interpolate(frame, [75, 100], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.in(Easing.cubic),
  });
  const titleOpacity = titleIn * (1 - titleOut);
  const titleX = interpolate(titleIn, [0, 1], [-60, 0]);

  const barH = height / 7;
  const barBottom = height / 20;
  const barY = height - barH - barBottom;
  const accentH = Math.max(4, height / 120);
  const slideOffset = (1 - barProgress) * (barH + barBottom + 20);

  return (
    <div
      style={{
        width,
        height,
        position: "relative",
        overflow: "hidden",
        // Black background — composited via blend=lighten in FFmpeg (black = transparent)
        backgroundColor: "#000000",
        fontFamily: FONT_FAMILY,
      }}
    >


      {/* Speaker name */}
      <div
        style={{
          position: "absolute",
          top: barY + barH * 0.18 + slideOffset,
          left: 30 + nameX,
          opacity: nameOpacity,
          color: G2_WHITE,
          fontSize: height / 22,
          fontWeight: 700,
          letterSpacing: "0.01em",
          whiteSpace: "nowrap",
        }}
      >
        {name}
      </div>

      {/* Speaker title */}
      <div
        style={{
          position: "absolute",
          top: barY + barH * 0.55 + slideOffset,
          left: 30 + titleX,
          opacity: titleOpacity,
          color: G2_WHITE,
          fontSize: height / 32,
          fontWeight: 500,
          letterSpacing: "0.02em",
          whiteSpace: "nowrap",
        }}
      >
        {title}
      </div>
    </div>
  );
};
