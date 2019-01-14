create table organisations
(
	id serial not null
		constraint organisations_pk
			primary key,
	name varchar not null
);

create unique index organisations_name_uindex
	on organisations (name);
