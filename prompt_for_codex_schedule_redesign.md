# Промпт для Codex: редизайн страницы календаря `/schedule`

Работай только над страницей календаря `/schedule`, то есть `SchedulePageComponent`.  
Системная панель `/projects` и Kanban board уже переделаны, их сейчас не трогай.

Ты работаешь с Angular-проектом платформы управления проектами.

Нужно сделать полный редизайн страницы календаря так, чтобы она визуально совпадала со стилем новой системной панели: premium SaaS UI, светлый фон, фиолетовый акцент, мягкие карточки, современный layout.

Файлы, с которыми нужно работать в первую очередь:

- `frontend/src/app/schedule/schedule-page/schedule-page.component.html`
- `frontend/src/app/schedule/schedule-page/schedule-page.component.scss`
- `frontend/src/app/schedule/schedule-page/schedule-page.component.ts`
- `frontend/src/app/schedule/schedule.service.ts`
- `frontend/src/app/schedule/schedule.module.ts`
- `frontend/src/app/schedule/schedule-routing.module.ts`

Маршрут страницы:

- `/schedule`

Главная задача: полностью переработать UI/UX страницы календаря, сохранив всю текущую бизнес-логику.

---

## ВАЖНО

Не трогай без необходимости:

- `frontend/src/app/projects-page`
- `frontend/src/app/project/pages/board`
- Kanban board
- системную панель `/projects`
- backend
- API-контракты
- авторизацию
- профиль пользователя
- logout
- worklog API
- schedules API

Проект использует:

- Angular 15
- TypeScript
- SCSS
- ng-zorro-antd
- RxJS
- Reactive Forms
- date-fns

НЕ использовать:

- React
- shadcn/ui
- lucide-react
- Framer Motion
- переписывание приложения на другой стек

Можно использовать:

- Angular templates
- SCSS
- CSS transitions
- существующие `svg-icon` / `ng-zorro icons`
- существующий компонент `j-avatar`
- существующий `j-user-profile-popover`
- существующие сервисы авторизации и календаря

---

## Главная цель

Нужно превратить страницу `/schedule` в современный premium SaaS календарь, визуально связанный с новой системной панелью.

Календарь должен выглядеть как часть одного продукта:

- тот же фиолетовый SaaS-стиль;
- тот же визуальный язык, что у системной панели;
- похожий sidebar;
- похожий topbar;
- похожие карточки;
- похожие кнопки, бейджи, тени, скругления;
- ощущение цельного enterprise-продукта.

Интерфейс не должен выглядеть как старая админка или учебная HTML-страница.

Нужно получить ощущение: **“Это современная Платформа проектов с календарём задач и учётом фактических часов.”**

---

## Что уже есть в календаре

На странице `SchedulePageComponent` уже реализованы:

- недельный календарь;
- мини-календарь;
- выбор дня;
- переключение недель;
- переключение месяцев;
- переход к сегодняшнему дню;
- создание задачи двойным кликом по сетке;
- редактирование задачи;
- удаление задачи;
- плановые часы;
- фактические часы;
- списание факта через worklog;
- выбор задачи для worklog из `/for-me`;
- цвет задачи;
- loading state;
- error state;
- empty state;
- профиль пользователя;
- logout.

Нужно сохранить всю эту логику.

---

## Что обязательно сохранить

Сохранить:

- `ScheduleService`
- `listUserSchedules()`
- `listUserWorklogs()`
- `listWorklogIssueOptions()`
- `createSchedule()`
- `updateSchedule()`
- `deleteSchedule()`
- `createIssueWorklog()`
- `updateWorklog()`
- `deleteWorklog()`
- `authQuery.user$`
- `authQuery.userId$`
- `logout()`
- `j-avatar`
- `j-user-profile-popover`
- `editorForm`
- `showEditor`
- `save()`
- `confirmDelete()`
- `closeEditor()`
- `openFocusedDate()`
- `createTaskAtPosition()`
- `openExistingEvent()`
- `previousWeek()`
- `nextWeek()`
- `previousMonth()`
- `nextMonth()`
- `goToToday()`
- `selectMiniCalendarDay()`
- `focusDay()`
- `plannerDays`
- `miniCalendarDays`
- `totalPlannedHours`
- `totalActualHours`
- `totalSchedules`
- `currentTimeIndicator`
- `worklogIssueOptions`
- localStorage-сохранение локальных задач

Не ломать:

- создание задач;
- редактирование задач;
- удаление задач;
- списание фактических часов;
- выбор задачи для worklog;
- валидацию формы;
- переходы между неделями;
- мини-календарь;
- профиль пользователя;
- logout.

---

## Визуальное направление

Страница календаря должна быть в стиле новой системной панели:

- светлый background: `#F6F7FB` / `#F8F7FC`;
- белые карточки;
- glass/panel aesthetics;
- мягкие тени;
- большие скругления;
- фиолетовый primary accent;
- аккуратные бейджи;
- современная типографика;
- много воздуха;
- premium SaaS dashboard feeling.

Цвета:

Primary:

- `#6C4CF1`
- `#7B61FF`
- `#8B5CF6`

Background:

- `#F6F7FB`
- `#F8F7FC`
- `#FFFFFF`

Text:

- `#111827`
- `#374151`
- `#6B7280`
- `#9CA3AF`

Success:

- `#22C55E`

Warning:

- `#F59E0B`

Danger:

- `#EF4444`

Info:

- `#3B82F6`

Borders:

- `rgba(15, 23, 42, 0.08)`

Border radius:

- cards: `20–28px`
- buttons: `12–16px`
- badges: `999px`

Тени:

- только мягкие;
- без тяжёлых чёрных shadow.

---

## Новый layout страницы

Сделать layout календаря похожим на layout системной панели.

Примерная структура:

```html
<div class="schedule-shell">
  <aside class="schedule-app-sidebar">...</aside>

  <div class="schedule-main">
    <header class="schedule-topbar">...</header>

    <main class="schedule-content">
      <section class="schedule-hero">...</section>
      <section class="schedule-stats">...</section>

      <section class="schedule-calendar-layout">
        <aside class="schedule-calendar-sidebar">...</aside>
        <section class="schedule-planner-card">...</section>
      </section>
    </main>
  </div>
</div>
```

Важно:

- сохранить текущие классы можно, но привести их к единой структуре;
- если проще — можно переиспользовать текущую структуру `.schedule-page`, но визуально перестроить её под shell/layout;
- не делать giant unreadable HTML;
- не ломать текущие Angular bindings.

---

## Sidebar

Сделать левый глобальный sidebar как на системной панели.

Он должен визуально совпадать с sidebar страницы `/projects`.

Внешний вид:

- ширина `260–280px`;
- высота `100vh`;
- fixed или sticky left;
- фиолетово-синий gradient;
- декоративные `radial-gradient` пятна;
- мягкое свечение;
- белый текст;
- rounded-right corners;
- premium look.

Структура:

Верх:

- логотип-иконка;
- название: **“ПЛАТФОРМА ПРОЕКТОВ”**;
- подпись: **“Project Workspace”**.

Навигация:

- Системная панель
- Мои задачи
- Проекты
- Календарь
- Дашборды
- Документы
- Отчёты
- Пользователи
- Настройки

Активный пункт:

- **“Календарь”**;
- светлая полупрозрачная плашка;
- rounded-xl;
- glow;
- иконка + текст.

Ссылки:

- Системная панель → `/projects`
- Проекты → `/projects`
- Календарь → `/schedule`
- Режим концентрации → `/focus`, если маршрут есть
- Остальные пункты можно сделать disabled-style, если маршрута нет

Важно:

- sidebar должен быть похож на sidebar системной панели;
- активным пунктом должен быть именно **“Календарь”**;
- не делать отдельный старый header **“Платформа проектов”** сверху, если он дублирует новый sidebar.

---

## Topbar

Сделать topbar календаря в стиле системной панели.

Структура:

Слева:

- breadcrumbs: **“Главная / Календарь”**
- подпись: **“Личное планирование задач и фактических часов”**

Центр:

- можно добавить визуальное поле поиска;
- placeholder: **“Поиск по задачам, датам и списаниям...”**
- если безопасно, можно сделать простой client-side filter по названию/комментарию задач;
- если это рискованно, оставить поле как UI-элемент без сложной логики.

Справа:

- кнопка **“+ Новая задача”**
  - вызывает `openFocusedDate()`
- кнопка **“Сегодня”**
  - вызывает `goToToday()`
- круглая кнопка уведомлений
- круглая кнопка помощи
- профиль пользователя:
  - avatar
  - имя
  - email/роль
  - popover через `j-user-profile-popover`
- logout можно оставить внутри профиля или отдельной компактной кнопкой

Важно:

- сохранить `authQuery.user$`;
- сохранить `logout()`;
- сохранить `j-avatar`;
- сохранить `nz-popover`;
- не ломать профиль пользователя.

---

## Hero-блок календаря

Под topbar сделать красивый hero-блок.

Содержимое:

- маленький eyebrow: **“Личное планирование”**
- большой заголовок: **“Календарь задач”**
- подзаголовок: **“Планируйте рабочую неделю, фиксируйте фактические часы и связывайте списания с задачами проекта.”**
- справа компактный блок:
  - текущая неделя: `weekLabel`
  - период: `visiblePeriodLabel`
  - `timezoneLabel`

Визуально:

- white/glass card;
- мягкий фиолетовый gradient;
- декоративные blurred circles;
- большие отступы;
- современная типографика.

---

## KPI-карточки календаря

Сделать 4 KPI-карточки под hero.

Использовать уже существующие данные:

### 1. Выбран день

- значение: `focusedDateLabel`
- описание: **“Активная дата планирования”**
- фиолетовый акцент

### 2. Задач за неделю

- значение: `totalSchedules`
- описание: **“Плановые блоки в календаре”**
- синий/фиолетовый акцент

### 3. Плановые часы

- значение: `formatHours(totalPlannedHours)`
- описание: **“Запланированная нагрузка”**
- зелёный или фиолетовый акцент

### 4. Фактические часы

- значение: `formatHours(totalActualHours)`
- описание: **“Списано по worklog”**
- оранжевый/amber акцент

Стиль:

- white cards;
- rounded-2xl;
- soft shadow;
- subtle border;
- icon bubble;
- hover lift;
- transition `160–220ms`;
- карточки должны совпадать со стилем KPI на системной панели.

---

## Основная структура календаря

Ниже KPI сделать основной блок календаря.

Layout:

- слева вспомогательная панель;
- справа большая карточка календарной сетки.

Пример:

```html
<section class="schedule-calendar-layout">
  <aside class="schedule-calendar-sidebar">
    mini calendar
    legend
    day summary
    quick actions
  </aside>

  <section class="schedule-planner-card">
    week toolbar
    calendar grid
  </section>
</section>
```

Desktop:

- sidebar календаря `320–360px`;
- календарная сетка занимает всё остальное пространство.

Tablet:

- sidebar сверху или в две колонки;
- календарь ниже.

Mobile:

- всё в одну колонку;
- календарная сетка получает horizontal scroll, если нужно.

---

## Левая панель календаря

Переделать текущую левую панель в набор красивых карточек.

Секции:

### 1. Mini calendar

- сохранить `miniCalendarDays`;
- сохранить `previousMonth()`;
- сохранить `nextMonth()`;
- сохранить `selectMiniCalendarDay(day)`;
- визуально сделать календарь компактным, белым, с фиолетовым активным днём;
- today выделять кольцом/точкой;
- focused day выделять filled purple;
- дни выбранной недели подсвечивать soft purple background.

### 2. Легенда

- **“Плановые блоки”**
- **“Фактические списания”**
- цветные точки/плашки;
- объяснение разницы между планом и фактом.

### 3. Quick actions

- кнопка **“Новая задача”**
  - вызывает `openFocusedDate()`
- кнопка **“Сегодня”**
  - вызывает `goToToday()`

### 4. Подсказка

- краткий текст: **“Двойной клик по сетке создаёт задачу на выбранное время.”**

Стиль:

- каждая секция как white card;
- rounded-2xl;
- soft shadow;
- не использовать тяжёлые рамки;
- много воздуха.

---

## Toolbar недели

Перед календарной сеткой сделать современную панель управления неделей.

Содержимое:

Слева:

- кнопка предыдущей недели `previousWeek()`
- кнопка следующей недели `nextWeek()`
- кнопка **“Сегодня”** `goToToday()`

Центр:

- `weekLabel`
- `visiblePeriodLabel`

Справа:

- `timezoneLabel` chip
- `totalSchedules` chip
- planned hours chip
- actual hours chip

Стиль:

- white/glass panel;
- rounded-2xl;
- мягкая тень;
- chip-бейджи;
- фиолетовый primary для ключевых значений.

---

## Календарная сетка

Полностью переработать внешний вид сетки, но сохранить текущую логику.

Сохранить:

- `plannerDays`
- `timeSlots`
- `trackByDay`
- `trackByTask`
- `trackByEvent`
- `trackByActualEvent`
- `formatTimeSlot(hour)`
- `getDayTitle(day)`
- `focusDay(day)`
- `createTaskAtPosition($event, day)`
- `onPlannerDayKeydown($event, day)`
- `openExistingEvent($event, day, plannerEvent.task)`
- `currentTimeIndicator`

Визуально сделать:

- большая white-card вокруг сетки;
- внутри сетки мягкий background;
- time column аккуратная и muted;
- day headers в виде карточек;
- today выделять фиолетовым border/glow;
- focused day выделять soft purple background;
- weekends подсвечивать очень мягким оттенком;
- строки времени с тонкими линиями `rgba(15, 23, 42, 0.06)`;
- не использовать резкие borders.

Day header:

- `weekdayLabel`;
- `dayNumber`;
- `summaryLabel`;
- если today — маленький badge **“Сегодня”**;
- если focused — subtle purple border.

Empty day state:

- вместо грубого текста сделать мягкую подсказку:
  **“Двойной клик — новая задача”**
- показывать только при hover или очень ненавязчиво.

---

## Карточки событий в календаре

Переделать `.schedule-event`.

Плановая задача:

- white/purple card или цветная карточка с мягким background;
- rounded-xl;
- subtle shadow;
- left accent border;
- `timeLabel` сверху;
- `hours` справа;
- title/comment крупнее;
- hover lift;
- cursor pointer;
- transition `160–200ms`.

Фактическое списание:

- отдельный стиль `.schedule-event--actual`;
- бейдж **“Факт”**;
- более насыщенный зелёный/синий/фиолетовый акцент;
- показывать `issueTitle`;
- показывать `hoursLabel`;
- визуально отличать от планового блока, но не ломать общую стилистику.

Нулевые часы:

- `.schedule-event--zero`;
- сделать muted style;
- пунктирный border или сниженная opacity;
- не скрывать.

Важно:

- не менять алгоритм позиционирования карточек;
- сохранить `[ngStyle]="plannerEvent.style"`;
- сохранить `[ngStyle]="actualEvent.style"`;
- не ломать высоту, top, left, width.

---

## Current time indicator

Сохранить `currentTimeIndicator`.

Визуально:

- тонкая фиолетовая линия;
- маленькая точка слева;
- subtle glow;
- не перекрывать карточки слишком агрессивно.

---

## Loading / Error / Empty states

Обновить состояния в стиле системной панели.

Loading:

- skeleton card;
- skeleton calendar grid;
- shimmer animation;
- текст **“Загружаю календарь”**.

Error:

- большая white error-card;
- мягкий danger accent;
- текст ошибки;
- кнопка **“Повторить”** вызывает `retryLoad()`.

Empty:

- если задач нет:
  - **“На эту неделю пока нет задач”**
  - **“Дважды кликните по сетке или нажмите Новая задача.”**
- добавить декоративную иконку/круг;
- кнопка **“Создать задачу”** вызывает `openFocusedDate()`.

---

## Модалка создания/редактирования задачи

Сохранить текущую модалку и всю логику формы.

Сохранить:

- `showEditor`
- `selectedTask`
- `selectedDateLabel`
- `editorForm`
- `startTime`
- `plannedHours`
- `actualIssueId`
- `actualHours`
- `color`
- `comment`
- `save()`
- `confirmDelete()`
- `closeEditor()`
- `onBackdropClick()`
- `toggleColorDropdown()`
- `selectTaskColor()`
- `modalErrorMessage`
- validation errors
- `selectedMaxPlannedHours`
- `startTimeControlInvalid`
- `plannedHoursControlInvalid`
- `plannedHoursErrorMessage`

Визуально обновить модалку:

- затемнение background;
- glass/white dialog;
- rounded-2xl / 28px;
- soft shadow;
- заголовок:
  - **“Новая задача”** или **“Редактирование задачи”**
- крупная дата `selectedDateLabel`;
- поля modern input/select/textarea;
- labels аккуратные;
- hints muted;
- errors danger-style;
- primary button фиолетовый gradient;
- danger button для удаления;
- close button как круглая иконка.

Форма должна выглядеть как premium SaaS modal.

---

## Color picker

Сохранить текущий color picker:

- `taskColorOptions`
- `showColorDropdown`
- `selectedTaskColor`
- `toggleColorDropdown()`
- `selectTaskColor()`

Визуально улучшить:

- trigger как modern button;
- swatch;
- dropdown как floating card;
- выбранный цвет с галочкой;
- hover states;
- rounded-xl;
- soft shadow.

---

## Worklog section

Поле **“Списать фактические часы”** должно выглядеть понятно.

Сохранить:

- `actualIssueId`
- `actualHours`
- `worklogIssueOptions`
- `isLoadingIssueOptions`
- `listWorklogIssueOptions()`

UX:

- select должен быть современным;
- placeholder **“Не списывать”**;
- если issue options загружаются — показать loading hint;
- hint: **“Выберите задачу и укажите фактические часы, чтобы записать worklog.”**
- `actualHours = 0` означает без списания факта.

Не ломать создание/обновление worklog.

---

## Responsive behavior

Desktop:

- глобальный sidebar слева;
- topbar сверху;
- hero;
- 4 KPI cards в ряд;
- слева mini-calendar/sidebar;
- справа недельная сетка.

Tablet:

- sidebar можно сделать уже;
- KPI 2x2;
- mini-calendar и planner в две строки;
- calendar grid может иметь horizontal scroll.

Mobile:

- глобальный sidebar скрывается или становится compact top navigation;
- topbar переносится;
- KPI cards в одну колонку;
- mini-calendar сверху;
- calendar grid с horizontal scroll;
- modal занимает почти всю ширину;
- ничего не должно вылезать за экран.

Важно:

- страница не должна ломаться на маленьких экранах;
- если календарная сетка широкая, horizontal scroll допустим только внутри календарной карточки, а не на всей странице.

---

## Accessibility

Добавить/сохранить:

- `aria-label` у кнопок;
- `focus-visible` состояния;
- keyboard navigation для дней;
- contrast для текста;
- disabled states;
- pointer cursor только там, где элемент кликабельный.

Не ломать:

- `onPlannerDayKeydown()`
- `tabindex="0"`
- `role="button"`

---

## Архитектура

Если HTML становится слишком большим, можно аккуратно вынести части в компоненты внутри:

- `frontend/src/app/schedule/components/`

Возможные компоненты:

- `ScheduleAppSidebarComponent`
- `ScheduleTopbarComponent`
- `ScheduleHeroComponent`
- `ScheduleStatsComponent`
- `ScheduleMiniCalendarComponent`
- `ScheduleWeekToolbarComponent`
- `SchedulePlannerGridComponent`
- `ScheduleEditorModalComponent`

Но не делать чрезмерную декомпозицию, если это повышает риск поломки.

Если выносишь компоненты:

- правильно объявить их в `ScheduleModule`;
- передать данные через `@Input`;
- события через `@Output`;
- сохранить типизацию;
- не ломать tests/build.

Если безопаснее — оставить всё в `SchedulePageComponent`, но привести HTML/SCSS к аккуратной структуре.

---

## Что нельзя делать

Нельзя:

- переписывать календарь с нуля;
- переписывать проект на React;
- использовать shadcn/ui;
- использовать lucide-react;
- использовать Framer Motion;
- ломать API;
- менять backend без необходимости;
- удалять текущую бизнес-логику;
- ломать создание задач;
- ломать редактирование задач;
- ломать удаление задач;
- ломать worklog;
- ломать mini-calendar;
- ломать недельную сетку;
- ломать профиль пользователя;
- ломать logout;
- трогать Kanban board;
- трогать системную панель `/projects`;
- оставлять старый стиль рядом с новым;
- делать календарь визуально не связанным с системной панелью.

---

## Что нужно сделать по шагам

Шаг 1. Проанализировать текущие файлы `SchedulePageComponent` и `ScheduleService`.

Шаг 2. Понять текущую структуру данных:

- `plannerDays`
- `miniCalendarDays`
- `plannedEvents`
- `actualEvents`
- `worklogIssueOptions`
- `editorForm`

Шаг 3. Не меняя API и бизнес-логику, перестроить layout страницы.

Шаг 4. Добавить sidebar в стиле системной панели, активный пункт — **“Календарь”**.

Шаг 5. Переделать topbar.

Шаг 6. Добавить hero-блок календаря.

Шаг 7. Переделать KPI-карточки.

Шаг 8. Переделать левую календарную панель:

- mini-calendar
- легенда
- quick actions
- подсказка

Шаг 9. Переделать toolbar недели.

Шаг 10. Переделать недельную календарную сетку.

Шаг 11. Переделать карточки плановых задач.

Шаг 12. Переделать карточки фактических списаний.

Шаг 13. Переделать loading/error/empty states.

Шаг 14. Переделать модалку создания/редактирования задачи.

Шаг 15. Переделать color picker.

Шаг 16. Сделать responsive polishing.

Шаг 17. Проверить сборку и отсутствие ошибок.

---

## Ожидаемый результат

После работы страница `/schedule` должна выглядеть как современный календарь внутри premium SaaS платформы:

- слева фиолетовый sidebar в стиле системной панели;
- активный пункт **“Календарь”**;
- сверху topbar с профилем и быстрыми действиями;
- hero **“Календарь задач”**;
- 4 KPI-карточки:
  - выбран день;
  - задач за неделю;
  - плановые часы;
  - фактические часы;
- слева mini-calendar и действия;
- справа большая недельная сетка;
- красивые карточки плановых задач;
- отдельный стиль для фактических списаний;
- современная модалка создания/редактирования;
- responsive layout;
- единая фиолетовая дизайн-система;
- UI визуально совпадает с новой системной панелью.

Финальное ощущение: это не старая страница расписания, а современный календарь задач в составе **“Платформы проектов”**.
