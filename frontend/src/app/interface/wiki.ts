export interface JWikiPage {
  id: string;
  projectId: string;
  parentId: string | null;
  title: string;
  contentMd: string;
  renderedHtml: string;
  version: number;
  createdBy: string;
  updatedBy: string;
  createdAt: string;
  updatedAt: string;
}

export interface JWikiPageTreeItem {
  id: string;
  projectId: string;
  parentId: string | null;
  title: string;
  version: number;
  updatedAt: string;
  children: JWikiPageTreeItem[];
}

export interface JWikiPageRevision {
  id: string;
  pageId: string;
  projectId: string;
  parentId: string | null;
  version: number;
  title: string;
  contentMd: string;
  renderedHtml: string;
  createdBy: string;
  createdAt: string;
}

export interface JWikiPageAttachment {
  id: string;
  pageId: string;
  uploadedBy: string;
  fileName: string;
  mimeType: string | null;
  sizeBytes: number;
  storageKey: string;
  createdAt: string;
}
