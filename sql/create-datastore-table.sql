create table datastore (
  rid       bigint not null auto_increment primary key
, ts        timestamp default current_timestamp not null
, env      varchar(256) character set utf8 not null
, projectid varchar(256) character set utf8 not null
, recordid  varchar(256) character set utf8 not null
, attrname  varchar(512) character set utf8 not null
, attrval   varchar(8192) character set utf8 not null 
);

