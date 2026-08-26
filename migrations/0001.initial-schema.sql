-- Справочник городов. code уникален (первичный ключ),
-- position задаёт порядок выдачи в /api/cities.
CREATE TABLE cities (
    code text PRIMARY KEY,
    name text NOT NULL,
    country text,
    position integer NOT NULL
);

-- Справочник авиакомпаний.
CREATE TABLE airlines (
    code text PRIMARY KEY,
    name text NOT NULL
);

-- Рейсы. id — строковый идентификатор, попадает в URL.
-- Цену держим целым числом в рублях (не money/numeric).
-- Время — timestamptz, отдаём в UTC.
CREATE TABLE flights (
    id text PRIMARY KEY,
    flight_number text NOT NULL,
    airline_code text NOT NULL REFERENCES airlines (code),
    origin_code text NOT NULL REFERENCES cities (code),
    destination_code text NOT NULL REFERENCES cities (code),
    departure_at timestamptz NOT NULL,
    arrival_at timestamptz NOT NULL,
    duration_minutes integer NOT NULL,
    price_amount integer NOT NULL,
    currency text NOT NULL DEFAULT 'RUB',
    seats_available integer NOT NULL,
    CONSTRAINT flights_distinct_cities CHECK (origin_code <> destination_code)
);

-- Поиск идёт по городам вылета/прилёта и дате вылета.
CREATE INDEX flights_search_idx
    ON flights (origin_code, destination_code, departure_at);

-- Брони. totalPrice сохраняем в самой брони: цена рейса со временем
-- меняется, а в брони должна остаться та, по которой купили.
CREATE TABLE bookings (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code text NOT NULL UNIQUE,
    status text NOT NULL DEFAULT 'confirmed',
    flight_id text NOT NULL REFERENCES flights (id),
    contact_email text NOT NULL,
    contact_phone text NOT NULL,
    total_price_amount integer NOT NULL,
    currency text NOT NULL DEFAULT 'RUB',
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT bookings_status_check CHECK (status IN ('confirmed', 'cancelled'))
);

-- Пассажиры существуют только внутри своей брони.
CREATE TABLE passengers (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    booking_id bigint NOT NULL REFERENCES bookings (id) ON DELETE CASCADE,
    first_name text NOT NULL,
    last_name text NOT NULL,
    date_of_birth date NOT NULL,
    document_number text NOT NULL
);

CREATE INDEX passengers_booking_idx ON passengers (booking_id);

-- Просмотр брони — по коду и фамилии (без учёта регистра).
CREATE INDEX passengers_last_name_idx ON passengers (lower(last_name));
