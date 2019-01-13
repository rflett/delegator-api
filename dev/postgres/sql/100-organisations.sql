create table organisations
(
	id serial not null,
	name int not null
);

create unique index organisations_id_uindex
	on organisations (id);

alter table organisations
	add constraint organisations_pk
		primary key (id);

