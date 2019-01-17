create table organisations
(
	id serial not null
		constraint organisations_pk
			primary key,
	name varchar not null,
	jwt_aud varchar not null,
	jwt_secret varchar not null
);

create unique index organisations_name_uindex
	on organisations (name);

create unique index organisations_jwt_aud_uindex
	on organisations (jwt_aud);

create unique index organisations_jwt_secret_uindex
	on organisations (jwt_secret);