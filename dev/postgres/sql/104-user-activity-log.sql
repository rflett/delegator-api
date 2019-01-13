create type user_activity_action_type as enum('create_user', 'delete_user', 'edit_user', 'create_task', 'edit_task', 'delete_task');

create table user_activity_log
(
    id         serial not null
        constraint user_activity_log_pk
        primary key,
    org_id     integer,
    user_id    integer,
    action     user_activity_action_type,
    action_detail   varchar,
    created_at timestamp default now(),
    constraint auth_users_userid_id
        foreign key (user_id) references users (id),
    constraint auth_users_org_id
        foreign key (org_id) references organisations (id)
);
