import { Injectable } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivate, Router, UrlTree } from '@angular/router';
import { isAdminProjectRole } from '@trungk18/interface/role';
import { combineLatest, Observable, of } from 'rxjs';
import { filter, map, take } from 'rxjs/operators';
import { ProjectQuery } from './state/project/project.query';
import { ProjectService } from './state/project/project.service';

@Injectable({
  providedIn: 'root'
})
export class ProjectReportsGuard implements CanActivate {
  constructor(
    private _projectQuery: ProjectQuery,
    private _projectService: ProjectService,
    private _router: Router
  ) {}

  canActivate(route: ActivatedRouteSnapshot): Observable<boolean | UrlTree> {
    const projectId = this.getProjectId(route);
    if (!projectId) {
      return of(this._router.createUrlTree(['/projects']));
    }

    this._projectService.loadProjectIfNeeded(projectId);

    return combineLatest([
      this._projectQuery.project$,
      this._projectQuery.isLoading$,
      this._projectQuery.error$
    ]).pipe(
      filter(([project, loading, error]) => !loading && (!!error || project.id === projectId)),
      take(1),
      map(([project, _loading, error]) => {
        if (error || !project.id) {
          return this._router.createUrlTree(['/projects']);
        }

        return isAdminProjectRole(project.currentUserRole)
          ? true
          : this._router.createUrlTree(['/projects', projectId, 'board']);
      })
    );
  }

  private getProjectId(route: ActivatedRouteSnapshot): string | null {
    return (
      route.pathFromRoot
        .map((snapshot) => snapshot.paramMap.get('projectId'))
        .find((projectId): projectId is string => !!projectId) ?? null
    );
  }
}
