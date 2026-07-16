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
  keyDetail?: string;
  transcript: TranscriptMessage[];
  hookStyle: string;
  viralScore: number;
  priority: string;
  createdAt: string;
  isOpener?: boolean;
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

export interface TrendingTrack {
  youtubeId: string;
  title: string;
  channelName: string;
  viewCount: number;
  durationSeconds: number | null;
}

export interface PublishedVideo {
  id: string;
  renderedVideoId: string;
  platform: string;
  platformPostId: string | null;
  platformUrl: string | null;
  audioTrackTitle: string | null;
  caption: string | null;
  status: string;
  errorMessage: string | null;
  viewCount: number;
  likeCount: number;
  commentCount: number;
  createdAt: string;
}

export interface PublishResult {
  platform: string;
  status: string;
  platformPostId: string | null;
  platformUrl: string | null;
  error: string | null;
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
