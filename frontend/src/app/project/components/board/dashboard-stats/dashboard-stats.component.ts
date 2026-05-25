import { Component } from '@angular/core';
import { ProjectQuery } from '@trungk18/project/state/project/project.query';
import { combineLatest } from 'rxjs';
import { map } from 'rxjs/operators';

interface DashboardStatCard {
  title: string;
  value: string;
  description: string;
  icon: string;
  tone: 'primary' | 'success' | 'warning' | 'danger';
}

@Component({
  selector: 'dashboard-stats',
  templateUrl: './dashboard-stats.component.html',
  styleUrls: ['./dashboard-stats.component.scss']
})
export class DashboardStatsComponent {
  private readonly shortDateFormatter = new Intl.DateTimeFormat('ru-RU', {
    day: 'numeric',
    month: 'long'
  });

  readonly cards$ = combineLatest([
    this.projectQuery.project$,
    this.projectQuery.issues$,
    this.projectQuery.users$
  ]).pipe(
    map(([project, issues, users]) => {
      const totalIssues = issues.length;
      const doneIssues = issues.filter((issue) => issue.statusCategory === 'done' || !!issue.resolvedAt).length;
      const progress = totalIssues ? Math.round((doneIssues / totalIssues) * 100) : 0;
      const openTasks = issues.filter((issue) => !issue.resolvedAt).length;
      const dueDates = issues
        .filter((issue) => !!issue.dueDate)
        .map((issue) => new Date(issue.dueDate as string))
        .filter((date) => Number.isFinite(date.getTime()));
      const nearestDeadline = dueDates.length
        ? this.shortDateFormatter.format(new Date(Math.min(...dueDates.map((date) => date.getTime()))))
        : 'Без срока';

      const cards: DashboardStatCard[] = [
        {
          title: 'Прогресс проекта',
          value: `${progress}%`,
          description: `${doneIssues} из ${totalIssues} задач выполнено`,
          icon: 'board',
          tone: 'primary'
        },
        {
          title: 'Открытые задачи',
          value: String(openTasks),
          description: openTasks ? 'Требуют внимания' : 'Все под контролем',
          icon: 'task',
          tone: openTasks > 0 ? 'warning' : 'success'
        },
        {
          title: 'Участники команды',
          value: String(users.length),
          description: project?.name ? `Участники проекта ${project.name}` : 'Участники рабочего пространства',
          icon: 'star',
          tone: 'success'
        },
        {
          title: 'Ближайший дедлайн',
          value: nearestDeadline,
          description: 'Ближайший срок по задачам',
          icon: 'report',
          tone: dueDates.length ? 'danger' : 'primary'
        }
      ];

      return cards;
    })
  );

  constructor(public projectQuery: ProjectQuery) {}
}
