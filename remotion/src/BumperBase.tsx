import React from "react";
import {
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Easing,
  staticFile,
} from "remotion";
import { G2_RED, G2_WHITE, FONT_FAMILY } from "./theme";

export interface BumperProps {
  subtitle: string;
  question?: string;
  logoFile?: string;
  bgColor?: string;
  textColor?: string;
}

export const BumperBase: React.FC<BumperProps & { isIntro: boolean }> = ({
  subtitle,
  question,
  logoFile,
  bgColor,
  textColor,
  isIntro: _isIntro,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const ref = Math.min(width, height);

  // Logo slides up and fades in (5–18f)
  const logoSpring = spring({
    fps,
    frame: Math.max(0, frame - 5),
    config: { damping: 16, stiffness: 100, mass: 1 },
    durationInFrames: 13,
  });
  const logoY = interpolate(logoSpring, [0, 1], [50, 0]);
  const logoOpacity = interpolate(frame, [5, 16], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Typewriter: reveal characters from frame 20
  const TYPING_START = 20;
  const CHARS_PER_FRAME = 0.6;
  const charsToShow = question
    ? Math.min(question.length, Math.max(0, Math.floor((frame - TYPING_START) * CHARS_PER_FRAME)))
    : 0;
  const displayedText = question ? question.slice(0, charsToShow) : "";

  // Blinking cursor — blink every 8 frames, hide once typing is done
  const typingDone = question ? charsToShow >= question.length : true;
  const cursorVisible = !typingDone && Math.floor(frame / 6) % 2 === 0;

  // Outro: "G2" text slides up (8–25f) with spring
  const g2Spring = spring({
    fps,
    frame: Math.max(0, frame - 8),
    config: { damping: 14, stiffness: 120, mass: 1 },
    durationInFrames: 17,
  });
  const g2Y = interpolate(g2Spring, [0, 1], [80, 0]);
  const outroG2Opacity = interpolate(frame, [8, 16], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Subtitle fades in (18–38f)
  const subtitleOpacity = interpolate(frame, [18, 38], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Intro: holds then wipes down off screen (100–115f)
  // Outro: wipes up from below to reveal solid (0–15f)
  const wipeY = _isIntro
    ? interpolate(frame, [100, 115], [0, height], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: Easing.in(Easing.cubic),
      })
    : interpolate(frame, [0, 15], [height, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: Easing.out(Easing.cubic),
      });

  return (
    <div
      style={{
        width,
        height,
        backgroundColor: bgColor ?? "#000000",
        overflow: "hidden",
        position: "relative",
        fontFamily: FONT_FAMILY,
        transform: `translateY(${wipeY}px)`,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {_isIntro && question ? (
        <>
          {/* Logo */}
          {logoFile && (
            <img
              src={staticFile(logoFile)}
              style={{
                opacity: logoOpacity,
                transform: `translateY(${logoY}px)`,
                width: ref / 5,
                height: ref / 5,
                objectFit: "contain",
                marginBottom: ref / 20,
              }}
            />
          )}
          {/* Typewriter question */}
          <div
            style={{
              color: textColor ?? G2_WHITE,
              fontSize: ref / 10,
              fontWeight: 400,
              lineHeight: 1.25,
              textAlign: "center",
              padding: `0 ${width * 0.08}px`,
              minHeight: (ref / 10) * 1.25 * 2,
            }}
          >
            {displayedText}
            {cursorVisible && (
              <span style={{ opacity: 1, borderRight: `3px solid ${textColor ?? G2_WHITE}`, marginLeft: 2 }} />
            )}
          </div>
        </>
      ) : (
        <>
          {/* Outro: logo + message */}
          {logoFile && (
            <img
              src={staticFile(logoFile)}
              style={{
                opacity: outroG2Opacity,
                transform: `translateY(${g2Y}px)`,
                width: ref / 5,
                height: ref / 5,
                objectFit: "contain",
                marginBottom: ref / 20,
              }}
            />
          )}
          <div
            style={{
              opacity: subtitleOpacity,
              transform: `translateY(${g2Y}px)`,
              color: textColor ?? G2_WHITE,
              fontSize: ref / 10,
              fontWeight: 400,
              lineHeight: 1.35,
              textAlign: "center",
              whiteSpace: "pre-line",
              padding: `0 ${width * 0.08}px`,
            }}
          >
            {subtitle}
          </div>
        </>
      )}
    </div>
  );
};
