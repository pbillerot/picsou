/*
 Tables SQLITE
 */
CREATE TABLE "ptf" (
	"ptf_id"	TEXT NOT NULL,
	"ptf_name"	TEXT DEFAULT '',
	"ptf_enabled"	INTEGER DEFAULT 0,
	"ptf_top"	INTEGER DEFAULT 0,
	"ptf_gain"	NUMERIC DEFAULT 0,
	"ptf_note"	TEXT DEFAULT '',
	"ptf_quote"	REAL DEFAULT 0,
	"ptf_seuil_achat"	REAL DEFAULT 0,
	"ptf_seuil_vente"	REAL DEFAULT 0,
	"ptf_isin"	TEXT DEFAULT 0,
	"ptf_rem"	TEXT DEFAULT '',
	"ptf_trend"	TEXT DEFAULT '',
	PRIMARY KEY("ptf_id")
);

CREATE TABLE "quotes" (
	"id"	TEXT,
	"name"	TEXT,
	"date"	TEXT,
	"open"	REAL,
	"high"	REAL,
	"low"	REAL,
	"close"	REAL,
	"close1"	REAL,
	"adjclose"	REAL,
	"volume"	INTEGER
);

CREATE TABLE "orders" (
	"orders_id"	INTEGER NOT NULL,
	"orders_name"	TEXT DEFAULT '',
	"orders_ptf_id"	INTEGER DEFAULT 0,
	"orders_order"	TEXT DEFAULT '',
	"orders_time"	TEXT DEFAULT '',
	"orders_quote"	REAL DEFAULT 0,
	"orders_quantity"	INTEGER DEFAULT 0,
	"orders_buy"	REAL DEFAULT 0,
	"orders_sell"	REAL DEFAULT 0,
	"orders_cost_price"	REAL DEFAULT 0,
	"orders_cost"	REAL DEFAULT 0,
	"orders_debit"	REAL DEFAULT 0,
	"orders_credit"	REAL DEFAULT 0,
	"orders_gain"	REAL DEFAULT 0,
	"orders_gainp"	REAL DEFAULT 0,
	"orders_sell_time"	TEXT DEFAULT '',
	"orders_sell_cost"	REAL DEFAULT 0,
	"orders_sell_gain"	REAL DEFAULT 0,
	"orders_sell_gainp"	REAL DEFAULT 0,
	"orders_rem"	TEXT DEFAULT '',
	PRIMARY KEY("orders_id" AUTOINCREMENT)
);
