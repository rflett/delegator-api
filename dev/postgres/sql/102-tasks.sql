create type status_type as enum('ready', 'todo', 'inprogress', 'paused', 'finished');


create table tasks
(
	id serial
		constraint tasks_pk
			primary key,
	org_id int,
	created_by int,
	title varchar,
	description varchar,
	status status_type,
	assignee int,
	finished_by int,
	created_at timestamp,
	finished_at timestamp,
	constraint tasks_users_assignee_id
		foreign key (assignee) references users (id),
	constraint tasks_users_finishedby_id
		foreign key (finished_by) references users (id),
	constraint tasks_users_createdby_id
		foreign key (created_by) references users (id)
);

