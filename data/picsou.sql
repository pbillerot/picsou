-- Adminer 4.8.1 PostgreSQL 14.2 (Debian 14.2-1.pgdg110+1) dump

DROP TABLE IF EXISTS "histo";
CREATE TABLE "public"."histo" (
    "id" character varying(20) NOT NULL,
    "name" character varying(50) NOT NULL,
    "date" character varying(10) NOT NULL,
    "open" numeric NOT NULL,
    "high" numeric NOT NULL,
    "low" numeric NOT NULL,
    "close" numeric NOT NULL,
    "adjclose" numeric NOT NULL,
    "volume" integer NOT NULL
) WITH (oids = false);


DROP TABLE IF EXISTS "orders";
CREATE TABLE "public"."orders" (
    "orders_id" integer NOT NULL,
    "orders_ptf_id" character varying(20) DEFAULT '',
    "orders_order" character varying(20) DEFAULT '',
    "orders_time" character varying(30) DEFAULT '',
    "orders_quote" numeric DEFAULT '0',
    "orders_quantity" smallint DEFAULT '0',
    "orders_buy" numeric DEFAULT '0',
    "orders_sell" numeric DEFAULT '0',
    "orders_cost_price" numeric DEFAULT '0',
    "orders_cost" numeric DEFAULT '0',
    "orders_debit" numeric DEFAULT '0',
    "orders_credit" numeric DEFAULT '0',
    "orders_gain" numeric DEFAULT '0',
    "orders_gainp" numeric DEFAULT '0',
    "orders_sell_time" character varying(30) DEFAULT '',
    "orders_sell_cost" numeric DEFAULT '0',
    "orders_sell_gain" numeric DEFAULT '0',
    "orders_sell_gainp" numeric DEFAULT '0',
    "orders_rem" character varying(200) DEFAULT '',
    CONSTRAINT "orders_orders_id" PRIMARY KEY ("orders_id")
) WITH (oids = false);


DROP TABLE IF EXISTS "ptf";
CREATE TABLE "public"."ptf" (
    "ptf_id" character varying(20) NOT NULL,
    "ptf_name" character varying(50) DEFAULT '',
    "ptf_enabled" smallint DEFAULT '0',
    "ptf_top" smallint DEFAULT '0',
    "ptf_gain" numeric DEFAULT '0',
    "ptf_quote" numeric DEFAULT '0',
    "ptf_isin" character varying(30) DEFAULT '0',
    "ptf_rem" character varying(200) DEFAULT '',
    "ptf_candle0" character varying(20) DEFAULT '''''',
    "ptf_candle1" character varying(20) DEFAULT '''''',
    "ptf_candle2" character varying(20) DEFAULT '''''',
    "ptf_rsi" smallint DEFAULT '0',
    CONSTRAINT "ptf_pkey" PRIMARY KEY ("ptf_id")
) WITH (oids = false);


DROP TABLE IF EXISTS "quotes";
CREATE TABLE "public"."quotes" (
    "id" character varying(20),
    "date" character varying(10),
    "open" numeric,
    "high" numeric,
    "low" numeric,
    "close" numeric,
    "adjclose" numeric,
    "volume" integer,
    "close1" numeric,
    "candle" character varying(30) DEFAULT ''
) WITH (oids = false);


-- 2023-07-13 14:22:14.395188+02