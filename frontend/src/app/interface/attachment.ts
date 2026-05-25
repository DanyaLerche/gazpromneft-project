export interface JIssueAttachment {
  id: string;
  issueId: string;
  uploadedBy: string;
  fileName: string;
  mimeType: string | null;
  sizeBytes: number;
  storageKey: string;
  createdAt: string;
}
