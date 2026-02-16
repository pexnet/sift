import type {
  KeywordStream,
  KeywordStreamCreateRequest,
  KeywordStreamUpdateRequest,
} from "../types/contracts";
import { apiClient } from "./client";

const STREAMS_ENDPOINT = "/api/v1/streams";

export async function getStreams(): Promise<KeywordStream[]> {
  return apiClient.get<KeywordStream[]>(STREAMS_ENDPOINT);
}

export async function createStream(payload: KeywordStreamCreateRequest): Promise<KeywordStream> {
  return apiClient.post<KeywordStreamCreateRequest, KeywordStream>(STREAMS_ENDPOINT, payload);
}

export async function updateStream(streamId: string, payload: KeywordStreamUpdateRequest): Promise<KeywordStream> {
  return apiClient.patch<KeywordStreamUpdateRequest, KeywordStream>(`${STREAMS_ENDPOINT}/${streamId}`, payload);
}

export async function deleteStream(streamId: string): Promise<void> {
  await apiClient.request<null>(`${STREAMS_ENDPOINT}/${streamId}`, { method: "DELETE" });
}

export async function runStreamBackfill(streamId: string): Promise<void> {
  await apiClient.post<Record<string, never>, unknown>(`${STREAMS_ENDPOINT}/${streamId}/backfill`, {});
}
