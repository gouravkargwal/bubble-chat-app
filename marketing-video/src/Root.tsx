import { Composition } from "remotion";
import { CookdChatShortVideo } from "./Composition";
import { CookdShortProps } from "./types";

// 🧠 DYNAMIC MATH ENGINE: Calculates exact video length based on payload size
export const calculateVideoDuration = (props: CookdShortProps) => {
  const analyzeStartFrame = 30 + props.messages.length * 45; // 1.5s per message
  const revealStartFrame = analyzeStartFrame + 60; // 2s analyzing tension
  const typingDuration = props.winningLine.length * 3; // 3 frames per character typed
  const outroStartFrame = revealStartFrame + typingDuration + 90; // Wait 3s after typing
  const totalDuration = outroStartFrame + 120; // Hold the final Google Play screen for 4s

  return totalDuration;
};

export const RemotionRoot: React.FC = () => {
  const samplePreviewProps: CookdShortProps = {
    personName: "Anvi",
    messages: [
      { sender: "them", text: "hey." },
      { sender: "you", text: "hey what is up" },
    ],
    winningLine: "bet those heels made for a clumsy entrance",
    strategyLabel: "FRAME CONTROL",
    voiceoverAudio: "",
  };

  return (
    <>
      <Composition
        id="CookdChatShort"
        component={CookdChatShortVideo}
        // Instead of hardcoding 540, the video now mathematically sizes itself!
        durationInFrames={calculateVideoDuration(samplePreviewProps)}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={samplePreviewProps}
      />
    </>
  );
};
