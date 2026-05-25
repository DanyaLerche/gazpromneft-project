export class SideBarLink {
  constructor(
    public name: string,
    public icon: string,
    public url?: string,
    public requiresProjectAdmin = false,
    public requiresNewEmployeeMode = false
  ) {}
}
