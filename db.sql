create table conversations (
	id         serial        primary key,
	file_data  jsonb         null,
	file_name  varchar(64)   not null,
	file_path  varchar(255)  not null,
	date_time  timestamp     not null default current_timestamp
);

create or replace function public.load_conversation(
	p_file_data  conversations.file_data%type,
	p_file_name  conversations.file_name%type,
	p_file_path  conversations.file_path%type
) returns int
language plpgsql
security definer
as $$
declare
	v_conversation_id conversations.id%type;
begin
	insert into conversations(file_data, file_name, file_path)
		values (p_file_data, p_file_name, p_file_path)
	returning id into v_conversation_id;

	return v_conversation_id;
end;
$$;

create or replace function public.get_conversations(
) returns table (id         int,
				 file_data  jsonb,
				 file_name  varchar(64),
				 file_path  varchar(255),
				 date_time  timestamp)
language plpgsql
security definer
as $$
begin
	return query
		select c.id, c.file_data, c.file_name, c.file_path, c.date_time
        from conversations c;
end;
$$;

create or replace function public.get_single_conversation(
	p_conversation_id  conversations.id%type
) returns table (id         int,
			     file_data  jsonb,
			     file_name  varchar(64),
			     file_path  varchar(255),
			     date_time  timestamp)
language plpgsql
security definer
as $$
begin
	return query
		select * from
		public.get_conversations() c
		where c.id = p_conversation_id;
end;
$$;

create user audrec_conv_s with password 'service';
grant execute on function public.load_conversation       to audrec_conv_s;
grant execute on function public.get_conversations       to audrec_conv_s;
grant execute on function public.get_single_conversation to audrec_conv_s;