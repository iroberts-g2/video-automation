import { Composition } from "remotion";
import type { ComponentType } from "react";
import { IntroBumper } from "./IntroBumper";
import { OutroBumper } from "./OutroBumper";
import { LowerThird } from "./LowerThird";
import { ClipOverlay, type ClipOverlayProps } from "./ClipOverlay";
import { ReviewerBadge, type ReviewerBadgeProps } from "./ReviewerBadge";
import {
  BUMPER_FPS,
  BUMPER_DURATION_FRAMES,
  INTRO_BUMPER_DURATION_FRAMES,
  LOWER_THIRD_FPS,
  LOWER_THIRD_DURATION_FRAMES,
} from "./theme";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyComp = ComponentType<any>;

const CLIP_OVERLAY_FPS = 25;

const DEFAULT_OVERLAY_EVENTS: ClipOverlayProps["events"] = [
  { startFrame: 0, durationFrames: 15, type: "reaction" },
  { startFrame: 30, durationFrames: 75, type: "rating", stars: 5, label: "G2 Review" },
];

const ALL_OVERLAYS_EVENTS: ClipOverlayProps["events"] = [
  { startFrame: 0,  durationFrames: 20, type: "reaction" },
  { startFrame: 5,  durationFrames: 80, type: "rating",    stars: 5, label: "G2 Review" },
  { startFrame: 10, durationFrames: 80, type: "callout",   text: "Easy to use" },
  { startFrame: 15, durationFrames: 80, type: "highlight", x: 800, y: 300, w: 400, h: 200 },
];

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="IntroBumper"
        component={IntroBumper as AnyComp}
        durationInFrames={INTRO_BUMPER_DURATION_FRAMES}
        fps={BUMPER_FPS}
        width={1920}
        height={1080}
        defaultProps={{ subtitle: "Customer Review", question: "What was AgencyHandy like to set up?", logoFile: "agency-handy.png", bgColor: "#000000", textColor: "#FFFFFF" }}
      />
      <Composition
        id="OutroBumper"
        component={OutroBumper as AnyComp}
        durationInFrames={BUMPER_DURATION_FRAMES}
        fps={BUMPER_FPS}
        width={1920}
        height={1080}
        defaultProps={{ subtitle: "A G2 Verified Review", logoFile: "g2-logo.svg", bgColor: "#000000", textColor: "#FFFFFF" }}
      />
      <Composition
        id="LowerThird"
        component={LowerThird as AnyComp}
        durationInFrames={LOWER_THIRD_DURATION_FRAMES}
        fps={LOWER_THIRD_FPS}
        width={1920}
        height={1080}
        defaultProps={{ name: "Jane Doe", title: "VP Engineering, Acme" }}
      />
      <Composition
        id="ReviewerBadge"
        component={ReviewerBadge as AnyComp}
        durationInFrames={100}
        fps={25}
        width={1920}
        height={1080}
        defaultProps={{ durationFrames: 100 }}
        calculateMetadata={({ props }) => ({
          durationInFrames: (props as unknown as ReviewerBadgeProps).durationFrames,
        })}
      />
      <Composition
        id="AllOverlays"
        component={ClipOverlay as AnyComp}
        durationInFrames={100}
        fps={CLIP_OVERLAY_FPS}
        width={1920}
        height={1080}
        defaultProps={{ events: ALL_OVERLAYS_EVENTS }}
      />
      <Composition
        id="ClipOverlay"
        component={ClipOverlay as AnyComp}
        durationInFrames={105}
        fps={CLIP_OVERLAY_FPS}
        width={1920}
        height={1080}
        defaultProps={{ events: DEFAULT_OVERLAY_EVENTS }}
        calculateMetadata={({ props }) => {
          const events = (props as unknown as ClipOverlayProps).events;
          const maxFrame = events.reduce(
            (max, e) => Math.max(max, e.startFrame + e.durationFrames),
            10,
          );
          return { durationInFrames: maxFrame };
        }}
      />
    </>
  );
};
