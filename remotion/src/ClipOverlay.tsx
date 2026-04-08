import React from "react";
import { useVideoConfig } from "remotion";
import { Highlight } from "./overlays/Highlight";
import { Callout } from "./overlays/Callout";
import { Rating } from "./overlays/Rating";
import { Reaction } from "./overlays/Reaction";

export interface OverlayEvent {
  startFrame: number;
  durationFrames: number;
  type: "highlight" | "callout" | "rating" | "reaction";
  // highlight
  x?: number;
  y?: number;
  w?: number;
  h?: number;
  // callout / reaction
  text?: string;
  // rating
  stars?: number;
  label?: string;
}

export interface ClipOverlayProps {
  events: OverlayEvent[];
}

export const ClipOverlay: React.FC<ClipOverlayProps> = ({ events }) => {
  const { width, height } = useVideoConfig();

  return (
    <div
      style={{
        width,
        height,
        position: "relative",
        overflow: "hidden",
        backgroundColor: "transparent",
      }}
    >
      {events.map((event, i) => {
        switch (event.type) {
          case "highlight":
            return (
              <Highlight
                key={i}
                startFrame={event.startFrame}
                durationFrames={event.durationFrames}
                x={event.x}
                y={event.y}
                w={event.w}
                h={event.h}
              />
            );
          case "callout":
            return (
              <Callout
                key={i}
                startFrame={event.startFrame}
                durationFrames={event.durationFrames}
                text={event.text}
              />
            );
          case "rating":
            return (
              <Rating
                key={i}
                startFrame={event.startFrame}
                durationFrames={event.durationFrames}
                stars={event.stars}
                label={event.label}
              />
            );
          case "reaction":
            return (
              <Reaction
                key={i}
                startFrame={event.startFrame}
                durationFrames={event.durationFrames}
              />
            );
          default:
            return null;
        }
      })}
    </div>
  );
};
