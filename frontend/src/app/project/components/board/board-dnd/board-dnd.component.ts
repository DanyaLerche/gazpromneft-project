import { Component } from '@angular/core';
import { UntilDestroy } from '@ngneat/until-destroy';
import { ProjectQuery } from '@trungk18/project/state/project/project.query';
@UntilDestroy()
@Component({
  selector: 'kanban-board',
  templateUrl: './board-dnd.component.html',
  styleUrls: ['./board-dnd.component.scss']
})
export class BoardDndComponent {
  constructor(public projectQuery: ProjectQuery) {}
}
