export interface TranscriptMessage {
  sender: "them" | "you";
  text: string;
}

export interface VideoCandidate {
  id: string;
  personName: string;
  detectedApp: string;
  strategyLabel: string;
  winningLine: string;
  coachReasoning: string;
  theirLastMessage: string;
  transcript: TranscriptMessage[];
  hookStyle: string;
  viralScore: number;
  priority: string;
  createdAt: string;
}

export interface RenderedVideo {
  id: string;
  interactionId: string | null;
  personName: string;
  winningLine: string;
  strategyLabel: string;
  hookStyle: string;
  viralScore: number;
  fileSizeBytes: number;
  status: string;
  errorMessage: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface PaginatedResponse {
  videos: RenderedVideo[];
  count: number;
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export interface RenderedFilters {
  search: string;
  status: string;
  hookStyle: string;
  strategyLabel: string;
  minScore: string;
  maxScore: string;
}

export interface CandidateFilters {
  search: string;
  hookType: string;
  priority: string;
  minScore: string;
  maxScore: string;
}

export interface CandidatePaginatedResponse {
  candidates: VideoCandidate[];
  count: number;
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  score_buckets: {
    high: number;
    medium: number;
  };
}
