import { Composition } from "remotion";
import { CookdChatShortVideo } from "./Composition";
import { ProfileCardVideo, calcProfileCardDuration } from "./ProfileCard";
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
  const sampleChatProps: CookdShortProps = {
    personName: "Anvi",
    messages: [
      { sender: "them", text: "hey." },
      { sender: "you", text: "hey what is up" },
    ],
    winningLine: "bet those heels made for a clumsy entrance",
    strategyLabel: "FRAME CONTROL",
    voiceoverAudio: "",
  };

  const sampleOpenerProps: CookdShortProps = {
    personName: "Anupama",
    messages: [
      {
        sender: "them",
        text: "She is a grounded, mindfulness-focused individual who values substance and adventure over superficiality.",
      },
    ],
    winningLine: "adventure over glam or just nice hotel lobbies?",
    strategyLabel: "FRAME CONTROL",
    voiceoverAudio: "",
    isOpener: true,
    keyDetail: "Adventure than Glam",
  };

  return (
    <>
      <Composition
        id="CookdChatShort"
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        component={CookdChatShortVideo as any}
        durationInFrames={calculateVideoDuration(sampleChatProps)}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={sampleChatProps}
      />
      <Composition
        id="CookdProfileCard"
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        component={ProfileCardVideo as any}
        durationInFrames={calcProfileCardDuration(
          sampleOpenerProps.winningLine
        )}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={sampleOpenerProps}
      />
    </>
  );
};
