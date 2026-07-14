export interface ChatMessage {
  sender: "them" | "you";
  text: string;
}

export interface CookdShortProps {
  personName: string;
  messages: ChatMessage[];
  winningLine: string;
  strategyLabel: string;
  voiceoverAudio: string;
  // Dynamic hook fields
  hookStyle?: "roast" | "gap" | "outcome" | "strategy" | "bet";
}
