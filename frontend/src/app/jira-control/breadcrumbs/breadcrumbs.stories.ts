import { Meta, Story } from '@storybook/angular';
import { BreadcrumbsComponent } from './breadcrumbs.component';

export default {
  title: 'Компоненты/Breadcrumbs',
  component: BreadcrumbsComponent
} as Meta;

const Template: Story<BreadcrumbsComponent> = (args: BreadcrumbsComponent) => ({
  component: BreadcrumbsComponent,
  props: args
});

export const Default: Story<BreadcrumbsComponent> = Template.bind({});
Default.args = {
  items: ['Проекты', 'Angular Jira Clone', 'Канбан-доска']
};
