import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { JWikiPage, JWikiPageAttachment, JWikiPageRevision, JWikiPageTreeItem } from '@trungk18/interface/wiki';
import { Observable, throwError } from 'rxjs';
import { map, switchMap } from 'rxjs/operators';
import { environment } from 'src/environments/environment';

interface ApiWikiPage {
  id: string;
  project_id: string;
  parent_id: string | null;
  title: string;
  content_md: string;
  rendered_html: string;
  version: number;
  created_by: string;
  updated_by: string;
  created_at: string;
  updated_at: string;
}

interface ApiWikiPageTreeItem {
  id: string;
  project_id: string;
  parent_id: string | null;
  title: string;
  version: number;
  updated_at: string;
  children: ApiWikiPageTreeItem[];
}

interface ApiWikiPageRevision {
  id: string;
  page_id: string;
  project_id: string;
  parent_id: string | null;
  version: number;
  title: string;
  content_md: string;
  rendered_html: string;
  created_by: string;
  created_at: string;
}

interface ApiWikiPageAttachment {
  id: string;
  page_id: string;
  uploaded_by: string;
  file_name: string;
  mime_type: string | null;
  size_bytes: number;
  storage_key: string;
  created_at: string;
}

interface ApiWikiPageResponse {
  page: ApiWikiPage;
}

interface ApiWikiPageTreeResponse {
  items: ApiWikiPageTreeItem[];
}

interface ApiWikiPageRevisionListResponse {
  items: ApiWikiPageRevision[];
}

interface ApiWikiPageAttachmentListResponse {
  items: ApiWikiPageAttachment[];
}

interface ApiWikiPageAttachmentResponse {
  attachment: ApiWikiPageAttachment;
}

interface ApiWikiRenderResponse {
  rendered_html: string;
}

interface ApiPrepareUpload {
  storage_key: string;
  upload_url: string;
  headers: Record<string, string>;
  fields: Record<string, string>;
  method: 'POST';
  expires_in: number;
}

interface ApiPrepareWikiAttachmentResponse {
  upload: ApiPrepareUpload;
}

interface ApiCreateWikiPageRequest {
  title: string;
  content_md: string;
  parent_id?: string | null;
}

interface ApiUpdateWikiPageRequest {
  title?: string;
  content_md?: string;
  parent_id?: string | null;
}

interface ApiCreateWikiAttachmentRequest {
  storage_key: string;
  file_name: string;
  mime_type: string;
  size_bytes: number;
}

interface ApiWikiAttachmentDownloadResponse {
  download_url: string;
}

export interface CreateWikiPagePayload {
  title: string;
  contentMd: string;
  parentId?: string | null;
}

export interface UpdateWikiPagePayload {
  title?: string;
  contentMd?: string;
  parentId?: string | null;
}

@Injectable({
  providedIn: 'root'
})
export class WikiService {
  private readonly baseUrl = environment.apiUrl;

  constructor(private _http: HttpClient) {}

  listPages(projectId: string): Observable<JWikiPageTreeItem[]> {
    return this._http
      .get<ApiWikiPageTreeResponse>(`${this.baseUrl}/projects/${projectId}/wiki/pages`)
      .pipe(map((response) => response.items.map((item) => this.mapTreeItem(item))));
  }

  getPage(projectId: string, pageId: string): Observable<JWikiPage> {
    return this._http
      .get<ApiWikiPageResponse>(`${this.baseUrl}/projects/${projectId}/wiki/pages/${pageId}`)
      .pipe(map((response) => this.mapPage(response.page)));
  }

  createPage(projectId: string, payload: CreateWikiPagePayload): Observable<JWikiPage> {
    const body: ApiCreateWikiPageRequest = {
      title: payload.title.trim(),
      content_md: payload.contentMd,
      ...(payload.parentId !== undefined ? { parent_id: payload.parentId } : {})
    };
    return this._http
      .post<ApiWikiPageResponse>(`${this.baseUrl}/projects/${projectId}/wiki/pages`, body)
      .pipe(map((response) => this.mapPage(response.page)));
  }

  updatePage(projectId: string, pageId: string, payload: UpdateWikiPagePayload): Observable<JWikiPage> {
    const body: ApiUpdateWikiPageRequest = {};
    if (payload.title !== undefined) {
      body.title = payload.title.trim();
    }
    if (payload.contentMd !== undefined) {
      body.content_md = payload.contentMd;
    }
    if (payload.parentId !== undefined) {
      body.parent_id = payload.parentId;
    }

    return this._http
      .patch<ApiWikiPageResponse>(`${this.baseUrl}/projects/${projectId}/wiki/pages/${pageId}`, body)
      .pipe(map((response) => this.mapPage(response.page)));
  }

  deletePage(projectId: string, pageId: string): Observable<void> {
    return this._http
      .delete<void>(`${this.baseUrl}/projects/${projectId}/wiki/pages/${pageId}`)
      .pipe(map(() => void 0));
  }

  listRevisions(projectId: string, pageId: string): Observable<JWikiPageRevision[]> {
    return this._http
      .get<ApiWikiPageRevisionListResponse>(
        `${this.baseUrl}/projects/${projectId}/wiki/pages/${pageId}/revisions`
      )
      .pipe(map((response) => response.items.map((item) => this.mapRevision(item))));
  }

  restoreRevision(projectId: string, pageId: string, version: number): Observable<JWikiPage> {
    return this._http
      .post<ApiWikiPageResponse>(`${this.baseUrl}/projects/${projectId}/wiki/pages/${pageId}/restore`, {
        version
      })
      .pipe(map((response) => this.mapPage(response.page)));
  }

  renderContent(projectId: string, contentMd: string): Observable<string> {
    return this._http
      .post<ApiWikiRenderResponse>(`${this.baseUrl}/projects/${projectId}/wiki/render`, {
        content_md: contentMd
      })
      .pipe(map((response) => response.rendered_html));
  }

  listAttachments(projectId: string, pageId: string): Observable<JWikiPageAttachment[]> {
    return this._http
      .get<ApiWikiPageAttachmentListResponse>(
        `${this.baseUrl}/projects/${projectId}/wiki/pages/${pageId}/attachments`
      )
      .pipe(map((response) => response.items.map((item) => this.mapAttachment(item))));
  }

  prepareAttachmentUpload(projectId: string, pageId: string, file: File): Observable<ApiPrepareUpload> {
    return this._http
      .post<ApiPrepareWikiAttachmentResponse>(
        `${this.baseUrl}/projects/${projectId}/wiki/pages/${pageId}/attachments/prepare`,
        {
          file_name: file.name,
          mime_type: file.type || 'application/octet-stream',
          size_bytes: file.size
        }
      )
      .pipe(map((response) => response.upload));
  }

  uploadAttachmentToStorage(upload: ApiPrepareUpload, file: File): Observable<void> {
    if (upload.method !== 'POST') {
      return throwError(new Error(`Unsupported upload method: ${upload.method}`));
    }

    const formData = new FormData();
    Object.entries(upload.fields ?? {}).forEach(([key, value]) => {
      formData.append(key, value);
    });
    formData.append('file', file, file.name);
    const headers = new HttpHeaders(upload.headers ?? {});
    return this._http.post(upload.upload_url, formData, { headers }).pipe(map(() => void 0));
  }

  createAttachment(projectId: string, pageId: string, file: File, storageKey: string): Observable<JWikiPageAttachment> {
    const body: ApiCreateWikiAttachmentRequest = {
      storage_key: storageKey,
      file_name: file.name,
      mime_type: file.type || 'application/octet-stream',
      size_bytes: file.size
    };
    return this._http
      .post<ApiWikiPageAttachmentResponse>(
        `${this.baseUrl}/projects/${projectId}/wiki/pages/${pageId}/attachments`,
        body
      )
      .pipe(map((response) => this.mapAttachment(response.attachment)));
  }

  uploadAttachment(projectId: string, pageId: string, file: File): Observable<JWikiPageAttachment> {
    return this.prepareAttachmentUpload(projectId, pageId, file).pipe(
      switchMap((upload) =>
        this.uploadAttachmentToStorage(upload, file).pipe(
          switchMap(() => this.createAttachment(projectId, pageId, file, upload.storage_key))
        )
      )
    );
  }

  getAttachmentDownloadUrl(attachmentId: string): Observable<string> {
    return this._http
      .get<ApiWikiAttachmentDownloadResponse>(`${this.baseUrl}/wiki/attachments/${attachmentId}/download`)
      .pipe(map((response) => response.download_url));
  }

  deleteAttachment(attachmentId: string): Observable<void> {
    return this._http
      .delete<void>(`${this.baseUrl}/wiki/attachments/${attachmentId}`)
      .pipe(map(() => void 0));
  }

  private mapPage(page: ApiWikiPage): JWikiPage {
    return {
      id: page.id,
      projectId: page.project_id,
      parentId: page.parent_id,
      title: page.title,
      contentMd: page.content_md,
      renderedHtml: page.rendered_html,
      version: page.version,
      createdBy: page.created_by,
      updatedBy: page.updated_by,
      createdAt: page.created_at,
      updatedAt: page.updated_at
    };
  }

  private mapTreeItem(item: ApiWikiPageTreeItem): JWikiPageTreeItem {
    return {
      id: item.id,
      projectId: item.project_id,
      parentId: item.parent_id,
      title: item.title,
      version: item.version,
      updatedAt: item.updated_at,
      children: (item.children ?? []).map((child) => this.mapTreeItem(child))
    };
  }

  private mapRevision(item: ApiWikiPageRevision): JWikiPageRevision {
    return {
      id: item.id,
      pageId: item.page_id,
      projectId: item.project_id,
      parentId: item.parent_id,
      version: item.version,
      title: item.title,
      contentMd: item.content_md,
      renderedHtml: item.rendered_html,
      createdBy: item.created_by,
      createdAt: item.created_at
    };
  }

  private mapAttachment(item: ApiWikiPageAttachment): JWikiPageAttachment {
    return {
      id: item.id,
      pageId: item.page_id,
      uploadedBy: item.uploaded_by,
      fileName: item.file_name,
      mimeType: item.mime_type,
      sizeBytes: item.size_bytes,
      storageKey: item.storage_key,
      createdAt: item.created_at
    };
  }
}
