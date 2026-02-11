--
-- PostgreSQL database dump
--

-- Dumped from database version 14.2 (Debian 14.2-1.pgdg110+1)
-- Dumped by pg_dump version 14.2 (Debian 14.2-1.pgdg110+1)

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

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: histo; Type: TABLE; Schema: public; Owner: beedule
--

CREATE TABLE public.histo (
    id character varying(20) NOT NULL,
    date character varying(10) NOT NULL,
    open numeric NOT NULL,
    high numeric NOT NULL,
    low numeric NOT NULL,
    close numeric NOT NULL,
    adjclose numeric NOT NULL,
    volume integer NOT NULL
);


ALTER TABLE public.histo OWNER TO beedule;

--
-- Name: events; Type: TABLE; Schema: public; Owner: beedule
--

CREATE TABLE public.events (
    events_id integer NOT NULL,
    events_ptf_id character varying(20) DEFAULT ''::character varying,
    events_datetime character varying(30) DEFAULT ''::character varying,
    events_quote numeric DEFAULT '0'::numeric,
    events_rsi numeric DEFAULT '0'::numeric
);


ALTER TABLE public.events OWNER TO beedule;

CREATE TABLE public.orders (
    orders_id integer NOT NULL,
    orders_ptf_id character varying(20) DEFAULT ''::character varying,
    orders_order character varying(20) DEFAULT ''::character varying,
    orders_time character varying(30) DEFAULT ''::character varying,
    orders_quote numeric DEFAULT '0'::numeric,
    orders_quantity smallint DEFAULT '0'::smallint,
    orders_buy numeric DEFAULT '0'::numeric,
    orders_sell numeric DEFAULT '0'::numeric,
    orders_cost_price numeric DEFAULT '0'::numeric,
    orders_cost numeric DEFAULT '0'::numeric,
    orders_debit numeric DEFAULT '0'::numeric,
    orders_credit numeric DEFAULT '0'::numeric,
    orders_gain numeric DEFAULT '0'::numeric,
    orders_gainp numeric DEFAULT '0'::numeric,
    orders_sell_time character varying(30) DEFAULT ''::character varying,
    orders_sell_cost numeric DEFAULT '0'::numeric,
    orders_sell_gain numeric DEFAULT '0'::numeric,
    orders_sell_gainp numeric DEFAULT '0'::numeric,
    orders_rem character varying(200) DEFAULT ''::character varying,
    orders_simulation smallint DEFAULT '0'::smallint NOT NULL
);


ALTER TABLE public.orders OWNER TO beedule;

--
-- Name: orders_orders_id_seq; Type: SEQUENCE; Schema: public; Owner: beedule
--

ALTER TABLE public.orders ALTER COLUMN orders_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.orders_orders_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: ptf; Type: TABLE; Schema: public; Owner: beedule
--

CREATE TABLE public.ptf (
    ptf_id character varying(20) NOT NULL,
    ptf_name character varying(50) DEFAULT ''::character varying,
    ptf_enabled smallint DEFAULT '0'::smallint,
    ptf_top smallint DEFAULT '0'::smallint,
    ptf_gain numeric DEFAULT 0,
    ptf_quote numeric DEFAULT '0'::numeric,
    ptf_isin character varying(30) DEFAULT 0,
    ptf_rem character varying(200) DEFAULT ''::character varying,
    ptf_candle0 character varying(20) DEFAULT ''''''::character varying,
    ptf_candle1 character varying(20) DEFAULT ''''''::character varying,
    ptf_candle2 character varying(20) DEFAULT ''''''::character varying,
    ptf_rsi smallint DEFAULT '0'::smallint,
    ptf_trend numeric DEFAULT '0'::numeric NOT NULL
);


ALTER TABLE public.ptf OWNER TO beedule;

--
-- Name: quotes; Type: TABLE; Schema: public; Owner: beedule
--

CREATE TABLE public.quotes (
    id character varying(20),
    date character varying(10),
    open real,
    high real,
    low real,
    close real,
    adjclose real,
    volume integer
);


ALTER TABLE public.quotes OWNER TO beedule;
