begin;
create table awardings (
	id serial primary key,
	value integer not null,
	house text not null
);
commit;
