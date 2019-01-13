create type task_activity_action_type as enum('edit_attr');

create table task_activity_log
(
    id         serial not null
        constraint task_activity_log_pk
        primary key,
    org_id     integer,
    task_id    integer,
    action     task_activity_action_type,
    action_detail   varchar,
    created_at timestamp default now(),
    constraint auth_tasks_taskid_id
        foreign key (task_id) references tasks (id),
    constraint auth_tasks_org_id
        foreign key (org_id) references organisations (id)
);
