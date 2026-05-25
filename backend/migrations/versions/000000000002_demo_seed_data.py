"""Демонстрационные данные для канбан-доски в стиле Jira.

- демо-пользователь
- демо-проект
- базовые статусы (колонки)
- несколько демо-задач
"""

from typing import Sequence, Union

from alembic import op


revision: str = "000000000002"
down_revision: Union[str, None] = "000000000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
SET search_path = tracker, public;

-- Фиксированные UUID, чтобы демо-данные были воспроизводимыми
DO $$
DECLARE
  v_user_id uuid := '11111111-1111-1111-1111-111111111111';
  v_user2_id uuid := '11111111-1111-1111-1111-222222222222';
  v_user3_id uuid := '11111111-1111-1111-1111-333333333333';
  v_project_id uuid := '22222222-2222-2222-2222-222222222222';
  v_status_backlog uuid := '33333333-3333-3333-3333-333333333333';
  v_status_selected uuid := '44444444-4444-4444-4444-444444444444';
  v_status_inprogress uuid := '55555555-5555-5555-5555-555555555555';
  v_status_done uuid := '66666666-6666-6666-6666-666666666666';
  v_crit_low uuid;
  v_crit_medium uuid;
  v_crit_high uuid;
BEGIN
  -- Демо-пользователи
  INSERT INTO users (id, email, full_name, is_active)
  VALUES (v_user_id, 'demo.user@example.com', 'Demo User', true)
  ON CONFLICT (email) DO NOTHING;

  INSERT INTO users (id, email, full_name, is_active)
  VALUES (v_user2_id, 'dev.one@example.com', 'Разработчик Один', true)
  ON CONFLICT (email) DO NOTHING;

  INSERT INTO users (id, email, full_name, is_active)
  VALUES (v_user3_id, 'qa.one@example.com', 'Тестировщик Один', true)
  ON CONFLICT (email) DO NOTHING;

  -- Демо-проект
  INSERT INTO projects (id, key, name, created_by)
  VALUES (v_project_id, 'DEMO', 'Demo Project', v_user_id)
  ON CONFLICT (key) DO NOTHING;

  -- Связь пользователей с проектом
  INSERT INTO project_users (project_id, user_id, role)
  VALUES (v_project_id, v_user_id, 'project_admin')
  ON CONFLICT (project_id, user_id) DO NOTHING;

  INSERT INTO project_users (project_id, user_id, role)
  VALUES (v_project_id, v_user2_id, 'project_member')
  ON CONFLICT (project_id, user_id) DO NOTHING;

  INSERT INTO project_users (project_id, user_id, role)
  VALUES (v_project_id, v_user3_id, 'project_member')
  ON CONFLICT (project_id, user_id) DO NOTHING;

  -- Критичности (если ещё не существуют)
  INSERT INTO criticalities (id, name, level)
  VALUES
    ('77777777-7777-7777-7777-777777777777', 'Low', 1),
    ('88888888-8888-8888-8888-888888888888', 'Medium', 2),
    ('99999999-9999-9999-9999-999999999999', 'High', 3)
  ON CONFLICT (name) DO NOTHING;

  -- Гарантируем, что переменные v_crit_* соответствуют фактическим ID в таблице
  SELECT id INTO v_crit_low FROM criticalities WHERE name = 'Low';
  SELECT id INTO v_crit_medium FROM criticalities WHERE name = 'Medium';
  SELECT id INTO v_crit_high FROM criticalities WHERE name = 'High';

  -- Базовые колонки канбан-доски
  INSERT INTO statuses (id, project_id, name, category, sort_order)
  VALUES
    (v_status_backlog,   v_project_id, 'Бэклог',                    'todo',         10),
    (v_status_selected,  v_project_id, 'Отобрано для разработки',   'todo',         20),
    (v_status_inprogress,v_project_id, 'В работе',                  'in_progress',  30),
    (v_status_done,      v_project_id, 'Готово',                    'done',         40)
  ON CONFLICT (project_id, name) DO NOTHING;

  -- Демо-задачи во всех колонках
  INSERT INTO issues (
    project_id, key, type,
    title, description,
    criticality_id, status_id,
    author_id, assignee_id
  )
  VALUES
    -- Бэклог
    (
      v_project_id, 'DEMO-1', 'task',
      'Настроить проект', 'Создать базовый проект и репозиторий.',
      v_crit_medium, v_status_backlog,
      v_user_id, v_user2_id
    ),
    (
      v_project_id, 'DEMO-2', 'task',
      'Описать процессы', 'Собрать базовое описание процессов для проекта.',
      v_crit_low, v_status_backlog,
      v_user_id, v_user3_id
    ),
    -- Отобрано для разработки
    (
      v_project_id, 'DEMO-3', 'task',
      'Перенести демо-данные', 'Подготовить демонстрационные задачи для канбан-доски.',
      v_crit_low, v_status_selected,
      v_user_id, v_user2_id
    ),
    -- В работе
    (
      v_project_id, 'DEMO-4', 'task',
      'Поднять dev-среду', 'Запустить docker-compose и проверить healthcheck.',
      v_crit_high, v_status_inprogress,
      v_user_id, v_user2_id
    ),
    (
      v_project_id, 'DEMO-5', 'task',
      'Настроить мониторинг', 'Добавить базовые метрики и алерты.',
      v_crit_medium, v_status_inprogress,
      v_user_id, v_user2_id
    ),
    (
      v_project_id, 'DEMO-6', 'task',
      'Подготовить тест-кейсы', 'Составить чек-лист и базовые сценарии для регресса.',
      v_crit_medium, v_status_inprogress,
      v_user_id, v_user3_id
    ),
    -- Готово
    (
      v_project_id, 'DEMO-7', 'task',
      'Показать канбан-доску', 'Провести демонстрацию.',
      v_crit_medium, v_status_done,
      v_user_id, v_user_id
    ),
    (
      v_project_id, 'DEMO-8', 'task',
      'Настроить права доступа', 'Проверить роли project_admin и project_member.',
      v_crit_high, v_status_done,
      v_user_id, v_user_id
    ),
    (
      v_project_id, 'DEMO-9', 'task',
      'Актуализировать README', 'Обновить документацию по запуску проекта.',
      v_crit_low, v_status_done,
      v_user_id, v_user3_id
    )
  ON CONFLICT (project_id, key) DO NOTHING;
END;
$$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
SET search_path = tracker, public;

DO $$
DECLARE
  v_user_id uuid := '11111111-1111-1111-1111-111111111111';
  v_project_id uuid := '22222222-2222-2222-2222-222222222222';
BEGIN
  -- Удаляем демо-задачи
  DELETE FROM issues
  WHERE project_id = v_project_id
    AND key LIKE 'DEMO-%';

  -- Удаляем статусы, относящиеся к демо-проекту
  DELETE FROM statuses
  WHERE project_id = v_project_id;

  -- Отвязываем пользователя от проекта
  DELETE FROM project_users
  WHERE project_id = v_project_id
    AND user_id = v_user_id;

  -- Удаляем проект
  DELETE FROM projects
  WHERE id = v_project_id
    AND key = 'DEMO';

  -- Удаляем демо-пользователя (по email для надёжности)
  DELETE FROM users
  WHERE id = v_user_id
    AND email = 'demo.user@example.com';

  -- Опционально удаляем критичности, если с ними больше нет задач
  DELETE FROM criticalities
  WHERE name IN ('Low', 'Medium', 'High')
    AND id NOT IN (SELECT DISTINCT criticality_id FROM issues WHERE criticality_id IS NOT NULL);
END;
$$;
        """
    )

