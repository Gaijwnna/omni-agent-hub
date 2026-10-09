-- Initial PostgreSQL schema. Generated from app/db.py; do not run against an already initialised database.

BEGIN;


CREATE TABLE abuse_reports (
	id VARCHAR(36) NOT NULL, 
	url TEXT NOT NULL, 
	description TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
)

;


CREATE TABLE accounts (
	id VARCHAR(36) NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	plan VARCHAR(20) NOT NULL, 
	stripe_customer VARCHAR(200), 
	subscription VARCHAR(200), 
	PRIMARY KEY (id), 
	UNIQUE (stripe_customer), 
	UNIQUE (subscription)
)

;


CREATE TABLE alert_events (
	id VARCHAR(36) NOT NULL, 
	source VARCHAR(100) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	payload JSON NOT NULL, 
	PRIMARY KEY (id)
)

;

CREATE INDEX ix_alert_events_source ON alert_events (source);


CREATE TABLE alert_subscriptions (
	id VARCHAR(36) NOT NULL, 
	owner VARCHAR(100) NOT NULL, 
	source VARCHAR(100) NOT NULL, 
	webhook TEXT, 
	secret_cipher TEXT, 
	active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
)

;

CREATE INDEX ix_alert_subscriptions_owner ON alert_subscriptions (owner);


CREATE TABLE benchmark_runs (
	id VARCHAR(36) NOT NULL, 
	owner VARCHAR(100) NOT NULL, 
	agent VARCHAR(200) NOT NULL, 
	agent_version VARCHAR(100) NOT NULL, 
	suite VARCHAR(40) NOT NULL, 
	seed INTEGER NOT NULL, 
	private BOOLEAN NOT NULL, 
	verified BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	result JSON, 
	state JSON NOT NULL, 
	PRIMARY KEY (id)
)

;

CREATE INDEX ix_benchmark_runs_owner ON benchmark_runs (owner);


CREATE TABLE billing_events (
	id VARCHAR(200) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
)

;


CREATE TABLE directory_entries (
	id VARCHAR(36) NOT NULL, 
	owner VARCHAR(100) NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	url TEXT NOT NULL, 
	description TEXT NOT NULL, 
	approved BOOLEAN NOT NULL, 
	sponsored BOOLEAN NOT NULL, 
	PRIMARY KEY (id)
)

;


CREATE TABLE feed_snapshots (
	id VARCHAR(100) NOT NULL, 
	fetched_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	payload JSON NOT NULL, 
	PRIMARY KEY (id)
)

;


CREATE TABLE index_notifications (
	id VARCHAR(64) NOT NULL, 
	url TEXT NOT NULL, 
	attempts INTEGER NOT NULL, 
	next_attempt TIMESTAMP WITH TIME ZONE NOT NULL, 
	accepted BOOLEAN NOT NULL, 
	last_status INTEGER, 
	PRIMARY KEY (id)
)

;


CREATE TABLE public_scores (
	domain VARCHAR(253) NOT NULL, 
	payload JSON NOT NULL, 
	html TEXT NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (domain)
)

;


CREATE TABLE scans (
	id VARCHAR(36) NOT NULL, 
	owner VARCHAR(100) NOT NULL, 
	url TEXT NOT NULL, 
	public BOOLEAN NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	priority INTEGER NOT NULL, 
	attempts INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE, 
	report JSON, 
	error TEXT, 
	PRIMARY KEY (id)
)

;

CREATE INDEX ix_scans_public ON scans (public);

CREATE INDEX ix_scans_owner ON scans (owner);

CREATE INDEX ix_scans_status ON scans (status);


CREATE TABLE api_keys (
	digest VARCHAR(64) NOT NULL, 
	account_id VARCHAR(36) NOT NULL, 
	prefix VARCHAR(16) NOT NULL, 
	revoked BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (digest), 
	FOREIGN KEY(account_id) REFERENCES accounts (id)
)

;

CREATE INDEX ix_api_keys_account_id ON api_keys (account_id);


CREATE TABLE certifications (
	domain VARCHAR(253) NOT NULL, 
	account_id VARCHAR(36) NOT NULL, 
	scan_id VARCHAR(36) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	verified_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	verification_method VARCHAR(40) NOT NULL, 
	PRIMARY KEY (domain), 
	FOREIGN KEY(account_id) REFERENCES accounts (id), 
	FOREIGN KEY(scan_id) REFERENCES scans (id)
)

;


CREATE TABLE webhook_deliveries (
	id VARCHAR(36) NOT NULL, 
	event_id VARCHAR(36) NOT NULL, 
	subscription_id VARCHAR(36) NOT NULL, 
	attempts INTEGER NOT NULL, 
	next_attempt TIMESTAMP WITH TIME ZONE NOT NULL, 
	delivered BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (event_id, subscription_id), 
	FOREIGN KEY(event_id) REFERENCES alert_events (id), 
	FOREIGN KEY(subscription_id) REFERENCES alert_subscriptions (id)
)

;

COMMIT;
