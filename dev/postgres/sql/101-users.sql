create type role_type as enum('admin', 'manager', 'user');

create table users
(
	id serial not null
		constraint users_pk
			primary key,
	org_id int not null,
	username varchar not null,
	email varchar not null,
	first_name varchar not null,
	last_name varchar not null,
	password varchar not null,
	role role_type not null,
	created_at timestamp default NOW(),
	constraint users_orgs_org_id
		foreign key (org_id) references organisations (id)
);

create unique index users_email_uindex
	on users (email);

create unique index users_username_uindex
	on users (username);

