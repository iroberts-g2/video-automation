import React from "react";
import { BumperBase, BumperProps } from "./BumperBase";

export const IntroBumper: React.FC<BumperProps> = (props) => (
  <BumperBase {...props} isIntro={true} />
);
