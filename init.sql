CREATE schema IF NOT EXISTS streaming_s;

CREATE TABLE IF NOT EXISTS streaming_s.justwatch_tb (
	id SERIAL PRIMARY KEY,
	provedor VARCHAR(50) NOT NULL,
	categoria VARCHAR(20) NOT NULL,
	titulo VARCHAR(200),
	ano INTEGER,
	duracao VARCHAR(50),
	duracao_minutos INTEGER,
	imdb_score FLOAT,
	imdb_count INTEGER,
	classificacao VARCHAR(20),
	sinopse TEXT,
	url VARCHAR(500),
	extract_timestamp TIMESTAMP without time zone 
);

CREATE TABLE IF NOT EXISTS streaming_s.provider_tb (
	provedor_id CHAR(3) PRIMARY KEY,
	provedor VARCHAR(50) NOT NULL UNIQUE,
	mensalidade numeric
);

INSERT INTO
	streaming_s.provider_tb (provedor_id, provedor, mensalidade)
VALUES
	('dnp', 'disney-plus', 27.99),
	('nfx', 'netflix', 20.90),
	('prv', 'amazon-prime-video', 19.90),
	('mxx', 'max', 29.90),
	('pmp', 'paramount-plus', 18.90),
	('atp', 'apple-tv-plus', 21.90),
	('gop', 'globoplay', 22.90);
