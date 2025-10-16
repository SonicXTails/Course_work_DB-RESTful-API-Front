--
-- PostgreSQL database dump
--

-- Dumped from database version 16.0
-- Dumped by pg_dump version 16.0

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: hstore; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS hstore WITH SCHEMA public;


--
-- Name: EXTENSION hstore; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION hstore IS 'data type for storing sets of (key, value) pairs';


--
-- Name: audit_row(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.audit_row() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE rec_id text;
BEGIN
  -- Универсально вынимаем PK: сначала id, если нет — VIN (для core_car)
  rec_id := COALESCE(
              (to_jsonb(NEW)->>'id'),
              (to_jsonb(OLD)->>'id'),
              (to_jsonb(NEW)->>'VIN'),
              (to_jsonb(OLD)->>'VIN')
           );

  INSERT INTO core_auditlog(user_id, action, table_name, record_id, old_data, new_data, action_time)
  VALUES (NULL, TG_OP, TG_TABLE_NAME, rec_id, to_jsonb(OLD), to_jsonb(NEW), now());
  RETURN COALESCE(NEW, OLD);
END; $$;


ALTER FUNCTION public.audit_row() OWNER TO postgres;

--
-- Name: sp_bulk_reprice(integer, numeric); Type: PROCEDURE; Schema: public; Owner: postgres
--

CREATE PROCEDURE public.sp_bulk_reprice(IN p_make_id integer, IN p_percent numeric)
    LANGUAGE plpgsql
    AS $$
BEGIN
  UPDATE core_car
  SET price = ROUND(price * (1 + p_percent/100.0), 2)
  WHERE make_id = p_make_id AND status IN ('available','reserved');
END;
$$;


ALTER PROCEDURE public.sp_bulk_reprice(IN p_make_id integer, IN p_percent numeric) OWNER TO postgres;

--
-- Name: sp_cancel_reservation(integer, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.sp_cancel_reservation(p_order_id integer, p_reason text DEFAULT NULL::text) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE v_car_vin VARCHAR;
BEGIN
SELECT car_id INTO v_car_vin FROM core_order WHERE id = p_order_id FOR UPDATE;
IF NOT FOUND THEN RAISE EXCEPTION 'ORDER_NOT_FOUND' USING HINT='Заказ не найден'; END IF;


PERFORM 1 FROM core_order WHERE id = p_order_id AND status = 'pending';
IF NOT FOUND THEN RAISE EXCEPTION 'ORDER_INVALID_STATE' USING HINT='Отменять можно только pending'; END IF;


UPDATE core_order SET status='cancelled' WHERE id = p_order_id;
UPDATE core_car SET status='available' WHERE "VIN" = v_car_vin;
END; $$;


ALTER FUNCTION public.sp_cancel_reservation(p_order_id integer, p_reason text) OWNER TO postgres;

--
-- Name: sp_complete_sale(integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.sp_complete_sale(p_order_id integer) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE v_tx_id INT; v_car_vin VARCHAR; v_amount NUMERIC;
BEGIN
  SELECT car_id, total_amount INTO v_car_vin, v_amount FROM core_order WHERE id=p_order_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'ORDER_NOT_FOUND'; END IF;

  PERFORM 1 FROM core_order WHERE id=p_order_id AND status='pending';
  IF NOT FOUND THEN RAISE EXCEPTION 'ORDER_INVALID_STATE' USING HINT='Продажа возможна только из pending'; END IF;

  INSERT INTO core_transaction(order_id, amount, transaction_date, status)
  VALUES(p_order_id, v_amount, now(), 'completed')
  RETURNING id INTO v_tx_id;

  UPDATE core_order SET status='paid' WHERE id=p_order_id;
  UPDATE core_car   SET status='sold' WHERE "VIN"=v_car_vin;

  RETURN v_tx_id;
END;
$$;


ALTER FUNCTION public.sp_complete_sale(p_order_id integer) OWNER TO postgres;

--
-- Name: sp_reserve_car(integer, character varying); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.sp_reserve_car(p_user_id integer, p_car_vin character varying) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE v_order_id INT; v_price NUMERIC;
BEGIN
  PERFORM 1 FROM core_car WHERE "VIN"=p_car_vin AND status='available' FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'CAR_NOT_AVAILABLE' USING HINT='Авто недоступно'; END IF;

  SELECT price INTO v_price FROM core_car WHERE "VIN"=p_car_vin;
  INSERT INTO core_order(buyer_id, car_id, status, order_date, total_amount)
  VALUES(p_user_id, p_car_vin, 'pending', now(), v_price)
  RETURNING id INTO v_order_id;

  UPDATE core_car SET status='reserved' WHERE "VIN"=p_car_vin;
  RETURN v_order_id;
END;
$$;


ALTER FUNCTION public.sp_reserve_car(p_user_id integer, p_car_vin character varying) OWNER TO postgres;

--
-- Name: trg_validate_tx(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.trg_validate_tx() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE v_order_status TEXT;
BEGIN
  SELECT status INTO v_order_status FROM core_order WHERE id = NEW.order_id;
  IF v_order_status <> 'pending' THEN
    RAISE EXCEPTION 'ORDER_INVALID_STATE' USING HINT='Транзакцию можно создать только из pending';
  END IF;
  RETURN NEW;
END; $$;


ALTER FUNCTION public.trg_validate_tx() OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: accounts_userpreference; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.accounts_userpreference (
    id bigint NOT NULL,
    theme character varying(10) NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    user_id bigint NOT NULL
);


ALTER TABLE public.accounts_userpreference OWNER TO postgres;

--
-- Name: accounts_userpreference_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.accounts_userpreference ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.accounts_userpreference_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_group; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.auth_group (
    id integer NOT NULL,
    name character varying(150) NOT NULL
);


ALTER TABLE public.auth_group OWNER TO postgres;

--
-- Name: auth_group_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.auth_group ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_group_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_group_permissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.auth_group_permissions (
    id bigint NOT NULL,
    group_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.auth_group_permissions OWNER TO postgres;

--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.auth_group_permissions ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_group_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_permission; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.auth_permission (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    content_type_id integer NOT NULL,
    codename character varying(100) NOT NULL
);


ALTER TABLE public.auth_permission OWNER TO postgres;

--
-- Name: auth_permission_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.auth_permission ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_permission_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: authtoken_token; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.authtoken_token (
    key character varying(40) NOT NULL,
    created timestamp with time zone NOT NULL,
    user_id bigint NOT NULL
);


ALTER TABLE public.authtoken_token OWNER TO postgres;

--
-- Name: core_auditlog; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.core_auditlog (
    id bigint NOT NULL,
    action character varying(100) NOT NULL,
    table_name character varying(50) NOT NULL,
    record_id character varying(255),
    old_data jsonb,
    new_data jsonb,
    action_time timestamp with time zone NOT NULL,
    user_id bigint,
    actor_label character varying(150)
);


ALTER TABLE public.core_auditlog OWNER TO postgres;

--
-- Name: core_auditlog_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.core_auditlog ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.core_auditlog_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_backupconfig; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.core_backupconfig (
    id smallint NOT NULL,
    last_run_at timestamp with time zone,
    CONSTRAINT core_backupconfig_id_check CHECK ((id >= 0))
);


ALTER TABLE public.core_backupconfig OWNER TO postgres;

--
-- Name: core_backupfile; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.core_backupfile (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    method character varying(16) NOT NULL,
    status character varying(16) NOT NULL,
    file_path character varying(512) NOT NULL,
    file_size bigint NOT NULL,
    checksum_sha256 character varying(64) NOT NULL,
    log text NOT NULL,
    created_by_id bigint
);


ALTER TABLE public.core_backupfile OWNER TO postgres;

--
-- Name: core_backupfile_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.core_backupfile ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.core_backupfile_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_car; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.core_car (
    "VIN" character varying(17) NOT NULL,
    year integer NOT NULL,
    price numeric(12,2) NOT NULL,
    status character varying(20) NOT NULL,
    description text NOT NULL,
    created_at timestamp with time zone NOT NULL,
    seller_id bigint,
    make_id bigint NOT NULL,
    model_id bigint NOT NULL
);


ALTER TABLE public.core_car OWNER TO postgres;

--
-- Name: core_carimage; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.core_carimage (
    id bigint NOT NULL,
    image character varying(100) NOT NULL,
    car_id character varying(17) NOT NULL
);


ALTER TABLE public.core_carimage OWNER TO postgres;

--
-- Name: core_carimage_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.core_carimage ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.core_carimage_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_favorite; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.core_favorite (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    car_id character varying(17) NOT NULL,
    user_id bigint NOT NULL
);


ALTER TABLE public.core_favorite OWNER TO postgres;

--
-- Name: core_favorite_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.core_favorite ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.core_favorite_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_make; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.core_make (
    id bigint NOT NULL,
    name character varying(50) NOT NULL
);


ALTER TABLE public.core_make OWNER TO postgres;

--
-- Name: core_make_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.core_make ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.core_make_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_model; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.core_model (
    id bigint NOT NULL,
    name character varying(50) NOT NULL,
    make_id bigint NOT NULL
);


ALTER TABLE public.core_model OWNER TO postgres;

--
-- Name: core_model_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.core_model ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.core_model_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_order; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.core_order (
    id bigint NOT NULL,
    order_date timestamp with time zone NOT NULL,
    status character varying(20) NOT NULL,
    total_amount numeric(12,2) NOT NULL,
    buyer_id bigint,
    car_id character varying(17) NOT NULL
);


ALTER TABLE public.core_order OWNER TO postgres;

--
-- Name: core_order_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.core_order ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.core_order_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_review; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.core_review (
    id bigint NOT NULL,
    rating smallint NOT NULL,
    comment text,
    created_at timestamp with time zone NOT NULL,
    author_id bigint NOT NULL,
    target_id bigint NOT NULL,
    CONSTRAINT core_review_rating_check CHECK ((rating >= 0))
);


ALTER TABLE public.core_review OWNER TO postgres;

--
-- Name: core_review_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.core_review ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.core_review_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_role; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.core_role (
    id bigint NOT NULL,
    name character varying(50) NOT NULL
);


ALTER TABLE public.core_role OWNER TO postgres;

--
-- Name: core_role_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.core_role ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.core_role_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_transaction; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.core_transaction (
    id bigint NOT NULL,
    amount numeric(12,2) NOT NULL,
    transaction_date timestamp with time zone NOT NULL,
    status character varying(20) NOT NULL,
    order_id bigint NOT NULL
);


ALTER TABLE public.core_transaction OWNER TO postgres;

--
-- Name: core_transaction_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.core_transaction ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.core_transaction_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_user; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.core_user (
    id bigint NOT NULL,
    password character varying(128) NOT NULL,
    last_login timestamp with time zone,
    is_superuser boolean NOT NULL,
    username character varying(150) NOT NULL,
    first_name character varying(150) NOT NULL,
    last_name character varying(150) NOT NULL,
    email character varying(254) NOT NULL,
    is_staff boolean NOT NULL,
    is_active boolean NOT NULL,
    date_joined timestamp with time zone NOT NULL
);


ALTER TABLE public.core_user OWNER TO postgres;

--
-- Name: core_user_groups; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.core_user_groups (
    id bigint NOT NULL,
    user_id bigint NOT NULL,
    group_id integer NOT NULL
);


ALTER TABLE public.core_user_groups OWNER TO postgres;

--
-- Name: core_user_groups_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.core_user_groups ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.core_user_groups_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_user_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.core_user ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.core_user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_user_user_permissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.core_user_user_permissions (
    id bigint NOT NULL,
    user_id bigint NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.core_user_user_permissions OWNER TO postgres;

--
-- Name: core_user_user_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.core_user_user_permissions ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.core_user_user_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_userprofile; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.core_userprofile (
    id bigint NOT NULL,
    phone_masked character varying(32) NOT NULL,
    user_id bigint NOT NULL
);


ALTER TABLE public.core_userprofile OWNER TO postgres;

--
-- Name: core_userprofile_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.core_userprofile ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.core_userprofile_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_userrole; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.core_userrole (
    id bigint NOT NULL,
    role_id bigint NOT NULL,
    user_id bigint NOT NULL
);


ALTER TABLE public.core_userrole OWNER TO postgres;

--
-- Name: core_userrole_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.core_userrole ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.core_userrole_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_usersettings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.core_usersettings (
    id bigint NOT NULL,
    theme character varying(10) NOT NULL,
    date_format character varying(12) NOT NULL,
    number_format character varying(12) NOT NULL,
    page_size smallint NOT NULL,
    saved_filters jsonb NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    user_id bigint NOT NULL,
    CONSTRAINT core_usersettings_page_size_check CHECK ((page_size >= 0)),
    CONSTRAINT usersettings_page_size_range CHECK (((page_size >= 5) AND (page_size <= 200)))
);


ALTER TABLE public.core_usersettings OWNER TO postgres;

--
-- Name: core_usersettings_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.core_usersettings ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.core_usersettings_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: django_admin_log; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.django_admin_log (
    id integer NOT NULL,
    action_time timestamp with time zone NOT NULL,
    object_id text,
    object_repr character varying(200) NOT NULL,
    action_flag smallint NOT NULL,
    change_message text NOT NULL,
    content_type_id integer,
    user_id bigint NOT NULL,
    CONSTRAINT django_admin_log_action_flag_check CHECK ((action_flag >= 0))
);


ALTER TABLE public.django_admin_log OWNER TO postgres;

--
-- Name: django_admin_log_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.django_admin_log ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.django_admin_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: django_content_type; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.django_content_type (
    id integer NOT NULL,
    app_label character varying(100) NOT NULL,
    model character varying(100) NOT NULL
);


ALTER TABLE public.django_content_type OWNER TO postgres;

--
-- Name: django_content_type_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.django_content_type ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.django_content_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: django_migrations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.django_migrations (
    id bigint NOT NULL,
    app character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    applied timestamp with time zone NOT NULL
);


ALTER TABLE public.django_migrations OWNER TO postgres;

--
-- Name: django_migrations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.django_migrations ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.django_migrations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: django_session; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.django_session (
    session_key character varying(40) NOT NULL,
    session_data text NOT NULL,
    expire_date timestamp with time zone NOT NULL
);


ALTER TABLE public.django_session OWNER TO postgres;

--
-- Name: vw_active_listings; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.vw_active_listings AS
 SELECT c."VIN" AS vin,
    m.name AS make,
    md.name AS model,
    c.price,
    c.year,
    c.status,
    c.created_at
   FROM ((public.core_car c
     JOIN public.core_make m ON ((m.id = c.make_id)))
     JOIN public.core_model md ON ((md.id = c.model_id)))
  WHERE ((c.status)::text = 'available'::text);


ALTER VIEW public.vw_active_listings OWNER TO postgres;

--
-- Name: vw_sales_by_make_month; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.vw_sales_by_make_month AS
 SELECT m.name AS make,
    date_trunc('month'::text, t.transaction_date) AS month,
    count(*) AS deals,
    sum(t.amount) AS revenue
   FROM (((public.core_transaction t
     JOIN public.core_order o ON ((o.id = t.order_id)))
     JOIN public.core_car c ON (((c."VIN")::text = (o.car_id)::text)))
     JOIN public.core_make m ON ((m.id = c.make_id)))
  WHERE ((t.status)::text = 'completed'::text)
  GROUP BY m.name, (date_trunc('month'::text, t.transaction_date));


ALTER VIEW public.vw_sales_by_make_month OWNER TO postgres;

--
-- Name: vw_user_activity; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.vw_user_activity AS
 SELECT u.id AS user_id,
    u.username,
    count(DISTINCT o.id) AS orders_cnt,
    count(DISTINCT t.id) AS tx_cnt
   FROM ((public.core_user u
     LEFT JOIN public.core_order o ON ((o.buyer_id = u.id)))
     LEFT JOIN public.core_transaction t ON (((t.order_id = o.id) AND ((t.status)::text = 'completed'::text))))
  GROUP BY u.id, u.username;


ALTER VIEW public.vw_user_activity OWNER TO postgres;

--
-- Name: accounts_userpreference accounts_userpreference_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounts_userpreference
    ADD CONSTRAINT accounts_userpreference_pkey PRIMARY KEY (id);


--
-- Name: accounts_userpreference accounts_userpreference_user_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounts_userpreference
    ADD CONSTRAINT accounts_userpreference_user_id_key UNIQUE (user_id);


--
-- Name: auth_group auth_group_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_name_key UNIQUE (name);


--
-- Name: auth_group_permissions auth_group_permissions_group_id_permission_id_0cd325b0_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_permission_id_0cd325b0_uniq UNIQUE (group_id, permission_id);


--
-- Name: auth_group_permissions auth_group_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_pkey PRIMARY KEY (id);


--
-- Name: auth_group auth_group_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_pkey PRIMARY KEY (id);


--
-- Name: auth_permission auth_permission_content_type_id_codename_01ab375a_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_codename_01ab375a_uniq UNIQUE (content_type_id, codename);


--
-- Name: auth_permission auth_permission_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_pkey PRIMARY KEY (id);


--
-- Name: authtoken_token authtoken_token_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.authtoken_token
    ADD CONSTRAINT authtoken_token_pkey PRIMARY KEY (key);


--
-- Name: authtoken_token authtoken_token_user_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.authtoken_token
    ADD CONSTRAINT authtoken_token_user_id_key UNIQUE (user_id);


--
-- Name: core_auditlog core_auditlog_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_auditlog
    ADD CONSTRAINT core_auditlog_pkey PRIMARY KEY (id);


--
-- Name: core_backupconfig core_backupconfig_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_backupconfig
    ADD CONSTRAINT core_backupconfig_pkey PRIMARY KEY (id);


--
-- Name: core_backupfile core_backupfile_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_backupfile
    ADD CONSTRAINT core_backupfile_pkey PRIMARY KEY (id);


--
-- Name: core_car core_car_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_car
    ADD CONSTRAINT core_car_pkey PRIMARY KEY ("VIN");


--
-- Name: core_carimage core_carimage_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_carimage
    ADD CONSTRAINT core_carimage_pkey PRIMARY KEY (id);


--
-- Name: core_favorite core_favorite_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_favorite
    ADD CONSTRAINT core_favorite_pkey PRIMARY KEY (id);


--
-- Name: core_favorite core_favorite_user_id_car_id_b55edcd4_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_favorite
    ADD CONSTRAINT core_favorite_user_id_car_id_b55edcd4_uniq UNIQUE (user_id, car_id);


--
-- Name: core_make core_make_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_make
    ADD CONSTRAINT core_make_name_key UNIQUE (name);


--
-- Name: core_make core_make_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_make
    ADD CONSTRAINT core_make_pkey PRIMARY KEY (id);


--
-- Name: core_model core_model_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_model
    ADD CONSTRAINT core_model_pkey PRIMARY KEY (id);


--
-- Name: core_order core_order_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_order
    ADD CONSTRAINT core_order_pkey PRIMARY KEY (id);


--
-- Name: core_review core_review_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_review
    ADD CONSTRAINT core_review_pkey PRIMARY KEY (id);


--
-- Name: core_role core_role_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_role
    ADD CONSTRAINT core_role_name_key UNIQUE (name);


--
-- Name: core_role core_role_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_role
    ADD CONSTRAINT core_role_pkey PRIMARY KEY (id);


--
-- Name: core_transaction core_transaction_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_transaction
    ADD CONSTRAINT core_transaction_pkey PRIMARY KEY (id);


--
-- Name: core_user_groups core_user_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_user_groups
    ADD CONSTRAINT core_user_groups_pkey PRIMARY KEY (id);


--
-- Name: core_user_groups core_user_groups_user_id_group_id_c82fcad1_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_user_groups
    ADD CONSTRAINT core_user_groups_user_id_group_id_c82fcad1_uniq UNIQUE (user_id, group_id);


--
-- Name: core_user core_user_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_user
    ADD CONSTRAINT core_user_pkey PRIMARY KEY (id);


--
-- Name: core_user_user_permissions core_user_user_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_user_user_permissions
    ADD CONSTRAINT core_user_user_permissions_pkey PRIMARY KEY (id);


--
-- Name: core_user_user_permissions core_user_user_permissions_user_id_permission_id_73ea0daa_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_user_user_permissions
    ADD CONSTRAINT core_user_user_permissions_user_id_permission_id_73ea0daa_uniq UNIQUE (user_id, permission_id);


--
-- Name: core_user core_user_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_user
    ADD CONSTRAINT core_user_username_key UNIQUE (username);


--
-- Name: core_userprofile core_userprofile_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_userprofile
    ADD CONSTRAINT core_userprofile_pkey PRIMARY KEY (id);


--
-- Name: core_userprofile core_userprofile_user_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_userprofile
    ADD CONSTRAINT core_userprofile_user_id_key UNIQUE (user_id);


--
-- Name: core_userrole core_userrole_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_userrole
    ADD CONSTRAINT core_userrole_pkey PRIMARY KEY (id);


--
-- Name: core_usersettings core_usersettings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_usersettings
    ADD CONSTRAINT core_usersettings_pkey PRIMARY KEY (id);


--
-- Name: core_usersettings core_usersettings_user_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_usersettings
    ADD CONSTRAINT core_usersettings_user_id_key UNIQUE (user_id);


--
-- Name: django_admin_log django_admin_log_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_pkey PRIMARY KEY (id);


--
-- Name: django_content_type django_content_type_app_label_model_76bd3d3b_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_app_label_model_76bd3d3b_uniq UNIQUE (app_label, model);


--
-- Name: django_content_type django_content_type_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_pkey PRIMARY KEY (id);


--
-- Name: django_migrations django_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_migrations
    ADD CONSTRAINT django_migrations_pkey PRIMARY KEY (id);


--
-- Name: django_session django_session_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_session
    ADD CONSTRAINT django_session_pkey PRIMARY KEY (session_key);


--
-- Name: core_model uniq_model_per_make; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_model
    ADD CONSTRAINT uniq_model_per_make UNIQUE (make_id, name);


--
-- Name: core_review unique_review_per_user; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_review
    ADD CONSTRAINT unique_review_per_user UNIQUE (author_id, target_id);


--
-- Name: auth_group_name_a6ea08ec_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_group_name_a6ea08ec_like ON public.auth_group USING btree (name varchar_pattern_ops);


--
-- Name: auth_group_permissions_group_id_b120cbf9; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_group_permissions_group_id_b120cbf9 ON public.auth_group_permissions USING btree (group_id);


--
-- Name: auth_group_permissions_permission_id_84c5c92e; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_group_permissions_permission_id_84c5c92e ON public.auth_group_permissions USING btree (permission_id);


--
-- Name: auth_permission_content_type_id_2f476e4b; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_permission_content_type_id_2f476e4b ON public.auth_permission USING btree (content_type_id);


--
-- Name: authtoken_token_key_10f0b77e_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX authtoken_token_key_10f0b77e_like ON public.authtoken_token USING btree (key varchar_pattern_ops);


--
-- Name: core_auditl_action__d5c966_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_auditl_action__d5c966_idx ON public.core_auditlog USING btree (action_time DESC);


--
-- Name: core_auditl_action_d9fb24_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_auditl_action_d9fb24_idx ON public.core_auditlog USING btree (action);


--
-- Name: core_auditl_table_n_4a8950_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_auditl_table_n_4a8950_idx ON public.core_auditlog USING btree (table_name);


--
-- Name: core_auditlog_action_time_f504adae; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_auditlog_action_time_f504adae ON public.core_auditlog USING btree (action_time);


--
-- Name: core_auditlog_record_id_56d91507; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_auditlog_record_id_56d91507 ON public.core_auditlog USING btree (record_id);


--
-- Name: core_auditlog_record_id_56d91507_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_auditlog_record_id_56d91507_like ON public.core_auditlog USING btree (record_id varchar_pattern_ops);


--
-- Name: core_auditlog_user_id_3797aaab; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_auditlog_user_id_3797aaab ON public.core_auditlog USING btree (user_id);


--
-- Name: core_backupfile_created_by_id_17b1fe59; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_backupfile_created_by_id_17b1fe59 ON public.core_backupfile USING btree (created_by_id);


--
-- Name: core_car_VIN_59031950_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_car_VIN_59031950_like" ON public.core_car USING btree ("VIN" varchar_pattern_ops);


--
-- Name: core_car_make_id_dad62edd; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_car_make_id_dad62edd ON public.core_car USING btree (make_id);


--
-- Name: core_car_model_id_ab210b11; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_car_model_id_ab210b11 ON public.core_car USING btree (model_id);


--
-- Name: core_car_seller_id_f28e3cc5; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_car_seller_id_f28e3cc5 ON public.core_car USING btree (seller_id);


--
-- Name: core_carimage_car_id_980997b9; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_carimage_car_id_980997b9 ON public.core_carimage USING btree (car_id);


--
-- Name: core_carimage_car_id_980997b9_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_carimage_car_id_980997b9_like ON public.core_carimage USING btree (car_id varchar_pattern_ops);


--
-- Name: core_favori_car_id_1ad79f_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_favori_car_id_1ad79f_idx ON public.core_favorite USING btree (car_id);


--
-- Name: core_favori_user_id_cbe902_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_favori_user_id_cbe902_idx ON public.core_favorite USING btree (user_id);


--
-- Name: core_favorite_car_id_887f1ad0; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_favorite_car_id_887f1ad0 ON public.core_favorite USING btree (car_id);


--
-- Name: core_favorite_car_id_887f1ad0_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_favorite_car_id_887f1ad0_like ON public.core_favorite USING btree (car_id varchar_pattern_ops);


--
-- Name: core_favorite_user_id_6e3cf6dd; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_favorite_user_id_6e3cf6dd ON public.core_favorite USING btree (user_id);


--
-- Name: core_make_name_07f7e019_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_make_name_07f7e019_like ON public.core_make USING btree (name varchar_pattern_ops);


--
-- Name: core_model_make_id_dafc45de; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_model_make_id_dafc45de ON public.core_model USING btree (make_id);


--
-- Name: core_order_buyer_id_75e0ab1b; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_order_buyer_id_75e0ab1b ON public.core_order USING btree (buyer_id);


--
-- Name: core_order_car_id_5e0a257c; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_order_car_id_5e0a257c ON public.core_order USING btree (car_id);


--
-- Name: core_order_car_id_5e0a257c_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_order_car_id_5e0a257c_like ON public.core_order USING btree (car_id varchar_pattern_ops);


--
-- Name: core_review_author_id_b9ff1c35; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_review_author_id_b9ff1c35 ON public.core_review USING btree (author_id);


--
-- Name: core_review_target_id_f0d3fb81; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_review_target_id_f0d3fb81 ON public.core_review USING btree (target_id);


--
-- Name: core_role_name_ca4cd9c7_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_role_name_ca4cd9c7_like ON public.core_role USING btree (name varchar_pattern_ops);


--
-- Name: core_transaction_order_id_e41a6bc5; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_transaction_order_id_e41a6bc5 ON public.core_transaction USING btree (order_id);


--
-- Name: core_user_groups_group_id_fe8c697f; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_user_groups_group_id_fe8c697f ON public.core_user_groups USING btree (group_id);


--
-- Name: core_user_groups_user_id_70b4d9b8; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_user_groups_user_id_70b4d9b8 ON public.core_user_groups USING btree (user_id);


--
-- Name: core_user_user_permissions_permission_id_35ccf601; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_user_user_permissions_permission_id_35ccf601 ON public.core_user_user_permissions USING btree (permission_id);


--
-- Name: core_user_user_permissions_user_id_085123d3; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_user_user_permissions_user_id_085123d3 ON public.core_user_user_permissions USING btree (user_id);


--
-- Name: core_user_username_36e4f7f7_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_user_username_36e4f7f7_like ON public.core_user USING btree (username varchar_pattern_ops);


--
-- Name: core_userrole_role_id_8272b20d; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_userrole_role_id_8272b20d ON public.core_userrole USING btree (role_id);


--
-- Name: core_userrole_user_id_aca63c51; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX core_userrole_user_id_aca63c51 ON public.core_userrole USING btree (user_id);


--
-- Name: django_admin_log_content_type_id_c4bce8eb; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX django_admin_log_content_type_id_c4bce8eb ON public.django_admin_log USING btree (content_type_id);


--
-- Name: django_admin_log_user_id_c564eba6; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX django_admin_log_user_id_c564eba6 ON public.django_admin_log USING btree (user_id);


--
-- Name: django_session_expire_date_a5c62663; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX django_session_expire_date_a5c62663 ON public.django_session USING btree (expire_date);


--
-- Name: django_session_session_key_c0390e0f_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX django_session_session_key_c0390e0f_like ON public.django_session USING btree (session_key varchar_pattern_ops);


--
-- Name: core_car audit_cars; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER audit_cars AFTER INSERT OR DELETE OR UPDATE ON public.core_car FOR EACH ROW EXECUTE FUNCTION public.audit_row();


--
-- Name: core_order audit_orders; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER audit_orders AFTER INSERT OR DELETE OR UPDATE ON public.core_order FOR EACH ROW EXECUTE FUNCTION public.audit_row();


--
-- Name: core_transaction audit_tx; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER audit_tx AFTER INSERT OR DELETE OR UPDATE ON public.core_transaction FOR EACH ROW EXECUTE FUNCTION public.audit_row();


--
-- Name: core_transaction validate_tx; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER validate_tx BEFORE INSERT ON public.core_transaction FOR EACH ROW EXECUTE FUNCTION public.trg_validate_tx();


--
-- Name: accounts_userpreference accounts_userpreference_user_id_110cffd7_fk_core_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounts_userpreference
    ADD CONSTRAINT accounts_userpreference_user_id_110cffd7_fk_core_user_id FOREIGN KEY (user_id) REFERENCES public.core_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_group_permissions auth_group_permissio_permission_id_84c5c92e_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissio_permission_id_84c5c92e_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_group_permissions auth_group_permissions_group_id_b120cbf9_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_b120cbf9_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_permission auth_permission_content_type_id_2f476e4b_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_2f476e4b_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: authtoken_token authtoken_token_user_id_35299eff_fk_core_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.authtoken_token
    ADD CONSTRAINT authtoken_token_user_id_35299eff_fk_core_user_id FOREIGN KEY (user_id) REFERENCES public.core_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_auditlog core_auditlog_user_id_3797aaab_fk_core_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_auditlog
    ADD CONSTRAINT core_auditlog_user_id_3797aaab_fk_core_user_id FOREIGN KEY (user_id) REFERENCES public.core_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_backupfile core_backupfile_created_by_id_17b1fe59_fk_core_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_backupfile
    ADD CONSTRAINT core_backupfile_created_by_id_17b1fe59_fk_core_user_id FOREIGN KEY (created_by_id) REFERENCES public.core_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_car core_car_make_id_dad62edd_fk_core_make_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_car
    ADD CONSTRAINT core_car_make_id_dad62edd_fk_core_make_id FOREIGN KEY (make_id) REFERENCES public.core_make(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_car core_car_model_id_ab210b11_fk_core_model_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_car
    ADD CONSTRAINT core_car_model_id_ab210b11_fk_core_model_id FOREIGN KEY (model_id) REFERENCES public.core_model(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_car core_car_seller_id_f28e3cc5_fk_core_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_car
    ADD CONSTRAINT core_car_seller_id_f28e3cc5_fk_core_user_id FOREIGN KEY (seller_id) REFERENCES public.core_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_carimage core_carimage_car_id_980997b9_fk_core_car_VIN; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_carimage
    ADD CONSTRAINT "core_carimage_car_id_980997b9_fk_core_car_VIN" FOREIGN KEY (car_id) REFERENCES public.core_car("VIN") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_favorite core_favorite_car_id_887f1ad0_fk_core_car_VIN; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_favorite
    ADD CONSTRAINT "core_favorite_car_id_887f1ad0_fk_core_car_VIN" FOREIGN KEY (car_id) REFERENCES public.core_car("VIN") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_favorite core_favorite_user_id_6e3cf6dd_fk_core_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_favorite
    ADD CONSTRAINT core_favorite_user_id_6e3cf6dd_fk_core_user_id FOREIGN KEY (user_id) REFERENCES public.core_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_model core_model_make_id_dafc45de_fk_core_make_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_model
    ADD CONSTRAINT core_model_make_id_dafc45de_fk_core_make_id FOREIGN KEY (make_id) REFERENCES public.core_make(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_order core_order_buyer_id_75e0ab1b_fk_core_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_order
    ADD CONSTRAINT core_order_buyer_id_75e0ab1b_fk_core_user_id FOREIGN KEY (buyer_id) REFERENCES public.core_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_order core_order_car_id_5e0a257c_fk_core_car_VIN; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_order
    ADD CONSTRAINT "core_order_car_id_5e0a257c_fk_core_car_VIN" FOREIGN KEY (car_id) REFERENCES public.core_car("VIN") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_review core_review_author_id_b9ff1c35_fk_core_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_review
    ADD CONSTRAINT core_review_author_id_b9ff1c35_fk_core_user_id FOREIGN KEY (author_id) REFERENCES public.core_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_review core_review_target_id_f0d3fb81_fk_core_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_review
    ADD CONSTRAINT core_review_target_id_f0d3fb81_fk_core_user_id FOREIGN KEY (target_id) REFERENCES public.core_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_transaction core_transaction_order_id_e41a6bc5_fk_core_order_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_transaction
    ADD CONSTRAINT core_transaction_order_id_e41a6bc5_fk_core_order_id FOREIGN KEY (order_id) REFERENCES public.core_order(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_user_groups core_user_groups_group_id_fe8c697f_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_user_groups
    ADD CONSTRAINT core_user_groups_group_id_fe8c697f_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_user_groups core_user_groups_user_id_70b4d9b8_fk_core_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_user_groups
    ADD CONSTRAINT core_user_groups_user_id_70b4d9b8_fk_core_user_id FOREIGN KEY (user_id) REFERENCES public.core_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_user_user_permissions core_user_user_permi_permission_id_35ccf601_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_user_user_permissions
    ADD CONSTRAINT core_user_user_permi_permission_id_35ccf601_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_user_user_permissions core_user_user_permissions_user_id_085123d3_fk_core_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_user_user_permissions
    ADD CONSTRAINT core_user_user_permissions_user_id_085123d3_fk_core_user_id FOREIGN KEY (user_id) REFERENCES public.core_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_userprofile core_userprofile_user_id_5141ad90_fk_core_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_userprofile
    ADD CONSTRAINT core_userprofile_user_id_5141ad90_fk_core_user_id FOREIGN KEY (user_id) REFERENCES public.core_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_userrole core_userrole_role_id_8272b20d_fk_core_role_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_userrole
    ADD CONSTRAINT core_userrole_role_id_8272b20d_fk_core_role_id FOREIGN KEY (role_id) REFERENCES public.core_role(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_userrole core_userrole_user_id_aca63c51_fk_core_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_userrole
    ADD CONSTRAINT core_userrole_user_id_aca63c51_fk_core_user_id FOREIGN KEY (user_id) REFERENCES public.core_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_usersettings core_usersettings_user_id_116dd0d3_fk_core_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_usersettings
    ADD CONSTRAINT core_usersettings_user_id_116dd0d3_fk_core_user_id FOREIGN KEY (user_id) REFERENCES public.core_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_admin_log django_admin_log_content_type_id_c4bce8eb_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_content_type_id_c4bce8eb_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_admin_log django_admin_log_user_id_c564eba6_fk_core_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_user_id_c564eba6_fk_core_user_id FOREIGN KEY (user_id) REFERENCES public.core_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- PostgreSQL database dump complete
--

