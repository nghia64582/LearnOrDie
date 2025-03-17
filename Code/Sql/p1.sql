CREATE TABLE users (
	users_id int not null primary key,
    banned ENUM('yes', 'no') NOT NULL DEFAULT 'no',
    role ENUM('client', 'driver', 'partner') NOT NULL DEFAULT 'client'
);

CREATE TABLE trips (
	id int not null primary key,
    client_id int not null,
    driver_id int not null,
    city_id int not null,
    status ENUM('completed', 'cancelled_by_driver', 'cancelled_by_client') not null default 'completed',
    request_at varchar(10),
    foreign key (client_id) references users(users_id),
    foreign key (driver_id) references users(users_id)
);


INSERT INTO users VALUES 
(1 , 'no'     , 'client'),
(2 , 'yes'    , 'client'),
(3 , 'no'     , 'client'),
(4 , 'no'     , 'client'),
(10, 'no'     , 'driver'),
(11, 'no'     , 'driver'),
(12, 'no'     , 'driver'),
(13, 'no'     , 'driver');

INSERT INTO trips VALUES
(1  , 1, 10, 1 , 'completed'           ,'2013-10-01'),
(2  , 2, 11, 1 , 'cancelled_by_driver' ,'2013-10-01'),
(3  , 3, 12, 6 , 'completed'           ,'2013-10-01'),
(4  , 4, 13, 6 , 'cancelled_by_client' ,'2013-10-01'),
(5  , 1, 10, 1 , 'completed'           ,'2013-10-02'),
(6  , 2, 11, 6 , 'completed'           ,'2013-10-02'),
(7  , 3, 12, 6 , 'completed'           ,'2013-10-02'),
(8  , 2, 12, 12, 'completed'           ,'2013-10-03'),
(9  , 3, 10, 12, 'completed'           ,'2013-10-03'),
(10 , 4, 13, 12, 'cancelled_by_driver' ,'2013-10-03');