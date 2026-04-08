import React from "react";
import { BumperBase } from "./BumperBase";

interface OutroBumperProps {
  subtitle: string;
}

export const OutroBumper: React.FC<OutroBumperProps> = (props) => (
  <BumperBase {...props} isIntro={false} />
);
