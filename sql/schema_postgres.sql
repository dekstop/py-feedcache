
CREATE FUNCTION update_datemodified_column() RETURNS TRIGGER AS '
  begin 
    new.date_modified := now(); 
    RETURN new; 
  end;
' LANGUAGE plpgsql; 

-- =========
-- = feeds =
-- =========

CREATE TABLE semaphores (
  id            SERIAL PRIMARY KEY,
  date_created  TIMESTAMP NOT NULL DEFAULT now(),
  
  guid          VARCHAR(40) UNIQUE NOT NULL,
  shutdown_requested BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE batchimports (
  id            SERIAL PRIMARY KEY,
  date_modified TIMESTAMP DEFAULT now(),
  
  semaphore_id  INTEGER DEFAULT NULL,
  date_locked   TIMESTAMP DEFAULT NULL,

  url           VARCHAR(4096) UNIQUE NOT NULL,
  imported      BOOLEAN NOT NULL DEFAULT FALSE,

  date_added    TIMESTAMP NOT NULL DEFAULT now(),
  date_last_fetched TIMESTAMP,
  fail_count    INTEGER NOT NULL DEFAULT 0
);
CREATE TRIGGER batchimports_update_datemodified BEFORE UPDATE ON batchimports FOR EACH ROW EXECUTE PROCEDURE update_datemodified_column();

CREATE TABLE feeds (
  id            SERIAL PRIMARY KEY,
  date_modified TIMESTAMP DEFAULT now(),
  
  semaphore_id  INTEGER DEFAULT NULL,
  date_locked   TIMESTAMP DEFAULT NULL,

  active        BOOLEAN NOT NULL DEFAULT TRUE,
  url           VARCHAR(4096) UNIQUE NOT NULL,
  actual_url    VARCHAR(4096) NOT NULL,
  
  date_added    TIMESTAMP NOT NULL DEFAULT now(),
  date_last_fetched TIMESTAMP NOT NULL DEFAULT now(),
  fail_count    INTEGER NOT NULL DEFAULT 0,
  
  http_last_modified TIMESTAMP,
  http_etag     VARCHAR(2048),
  
  title         VARCHAR(4096) NOT NULL,
  description   VARCHAR(4096),
  link          VARCHAR(4096) NOT NULL,
  unique_id     VARCHAR(4096),
  ttl           INTEGER,
  date_updated  TIMESTAMP
);
CREATE TRIGGER feeds_update_datemodified BEFORE UPDATE ON feeds FOR EACH ROW EXECUTE PROCEDURE update_datemodified_column();

CREATE TABLE entries (
  id            SERIAL PRIMARY KEY,
  date_modified TIMESTAMP DEFAULT now(),
  
  feed_id       INTEGER NOT NULL,
  date_added    TIMESTAMP NOT NULL DEFAULT now(),
  unique_id     VARCHAR(4096) NOT NULL,
  title         VARCHAR(4096) NOT NULL,
  content       TEXT,
  summary       TEXT,
  link          VARCHAR(4096) NOT NULL,
  date_published TIMESTAMP,
  date_updated  TIMESTAMP,
  
  UNIQUE(feed_id, unique_id)
);
CREATE TRIGGER entries_update_datemodified BEFORE UPDATE ON entries FOR EACH ROW EXECUTE PROCEDURE update_datemodified_column();

-- ============
-- = messages =
-- ============
CREATE TABLE message_types (
  id            SERIAL PRIMARY KEY,
  date_modified TIMESTAMP DEFAULT now(),
  
  name          VARCHAR(1024) UNIQUE NOT NULL,
  description   VARCHAR(2048)
);
CREATE TRIGGER message_types_update_datemodified BEFORE UPDATE ON message_types FOR EACH ROW EXECUTE PROCEDURE update_datemodified_column();

INSERT INTO message_types(name, description) VALUES('FeedFetchError', 'Failed to request the feed document');
INSERT INTO message_types(name, description) VALUES('FeedParseError', 'Failed to parse the feed document');

CREATE TABLE messages (
  id            SERIAL PRIMARY KEY,
  date_modified TIMESTAMP DEFAULT now(),
  
  message_type_id INTEGER NOT NULL,
  message       VARCHAR(2048) NOT NULL,
  payload       TEXT
);
CREATE TRIGGER messages_lastmodified BEFORE UPDATE ON messages FOR EACH ROW EXECUTE PROCEDURE update_datemodified_column();

CREATE TABLE batchimports_messages (
  id            SERIAL PRIMARY KEY,
  date_modified TIMESTAMP DEFAULT now(),
  
  batchimport_id       INTEGER NOT NULL,
  message_id     INTEGER NOT NULL
);
CREATE TRIGGER batchimports_messages_update_datemodified BEFORE UPDATE ON batchimports_messages FOR EACH ROW EXECUTE PROCEDURE update_datemodified_column();

CREATE TABLE feeds_messages (
  id            SERIAL PRIMARY KEY,
  date_modified TIMESTAMP DEFAULT now(),
  
  feed_id       INTEGER NOT NULL,
  message_id     INTEGER NOT NULL
);
CREATE TRIGGER feeds_messages_update_datemodified BEFORE UPDATE ON feeds_messages FOR EACH ROW EXECUTE PROCEDURE update_datemodified_column();


-- ===========
-- = authors =
-- ===========
CREATE TABLE authors (
  id            SERIAL PRIMARY KEY,
  date_modified TIMESTAMP DEFAULT now(),
  
  name          VARCHAR(100) NOT NULL,
  email         VARCHAR(320),
  link          VARCHAR(4096),
  
  UNIQUE(name, email, link)
);
CREATE TRIGGER authors_update_datemodified BEFORE UPDATE ON authors FOR EACH ROW EXECUTE PROCEDURE update_datemodified_column();

CREATE TABLE feeds_authors (
  date_modified TIMESTAMP DEFAULT now(),
  
  feed_id       INTEGER NOT NULL,
  author_id     INTEGER NOT NULL,
  
  UNIQUE(feed_id, author_id)
);
CREATE TRIGGER feeds_authors_update_datemodified BEFORE UPDATE ON feeds_authors FOR EACH ROW EXECUTE PROCEDURE update_datemodified_column();

CREATE TABLE entries_authors (
  date_modified TIMESTAMP DEFAULT now(),
  
  entry_id      INTEGER NOT NULL,
  author_id     INTEGER NOT NULL,
  
  UNIQUE(entry_id, author_id)
);
CREATE TRIGGER entries_authors_update_datemodified BEFORE UPDATE ON entries_authors FOR EACH ROW EXECUTE PROCEDURE update_datemodified_column();

-- ==============
-- = categories =
-- ==============
CREATE TABLE categories (
  id            SERIAL PRIMARY KEY,
  date_modified TIMESTAMP DEFAULT now(),
  
  term          VARCHAR(1024) NOT NULL,
  scheme        VARCHAR(4096),
  label         VARCHAR(1024),
  
  UNIQUE(term, scheme, label)
);
CREATE TRIGGER categories_update_datemodified BEFORE UPDATE ON categories FOR EACH ROW EXECUTE PROCEDURE update_datemodified_column();

CREATE TABLE feeds_categories (
  date_modified TIMESTAMP DEFAULT now(),
  
  feed_id       INTEGER NOT NULL,
  category_id   INTEGER NOT NULL,
  
  UNIQUE(feed_id, category_id)
);
CREATE TRIGGER feeds_categories_update_datemodified BEFORE UPDATE ON feeds_categories FOR EACH ROW EXECUTE PROCEDURE update_datemodified_column();

CREATE TABLE entries_categories (
  date_modified TIMESTAMP DEFAULT now(),
  
  entry_id      INTEGER NOT NULL,
  category_id   INTEGER NOT NULL,
  
  UNIQUE(entry_id, category_id)
);
CREATE TRIGGER entries_categories_update_datemodified BEFORE UPDATE ON entries_categories FOR EACH ROW EXECUTE PROCEDURE update_datemodified_column();

-- =========
-- = users =
-- =========
CREATE TYPE usertypes AS ENUM('user', 'admin');
CREATE TABLE users(
  id            SERIAL PRIMARY KEY,
  date_modified TIMESTAMP DEFAULT now(),
  
  name          VARCHAR(100) UNIQUE NOT NULL,
  password      CHAR(16) NOT NULL,
  email         VARCHAR(320),
  type          usertypes NOT NULL DEFAULT 'user'
);
CREATE TRIGGER users_update_datemodified BEFORE UPDATE ON users FOR EACH ROW EXECUTE PROCEDURE update_datemodified_column();

CREATE TABLE feeds_users (
  date_modified TIMESTAMP DEFAULT now(),
  
  user_id       INTEGER NOT NULL,
  feed_id       INTEGER NOT NULL,
  
  UNIQUE (user_id, feed_id)
);
CREATE TRIGGER feeds_users_update_datemodified BEFORE UPDATE ON feeds_users FOR EACH ROW EXECUTE PROCEDURE update_datemodified_column();

-- ========
-- = tags =
-- ========
CREATE TABLE tags (
  id            SERIAL PRIMARY KEY,
  date_modified TIMESTAMP DEFAULT now(),
  
  name          VARCHAR(2048) UNIQUE NOT NULL
);
CREATE TRIGGER tags_update_datemodified BEFORE UPDATE ON tags FOR EACH ROW EXECUTE PROCEDURE update_datemodified_column();

CREATE TABLE feeds_tags (
  date_modified TIMESTAMP DEFAULT now(),
  
  user_id       INTEGER NOT NULL,
  feed_id       INTEGER NOT NULL,
  tag_id        INTEGER NOT NULL,
  
  UNIQUE(user_id, feed_id, tag_id)
);
CREATE TRIGGER feeds_tags_update_datemodified BEFORE UPDATE ON feeds_tags FOR EACH ROW EXECUTE PROCEDURE update_datemodified_column();

CREATE TABLE entries_tags (
  date_modified TIMESTAMP DEFAULT now(),
  
  user_id       INTEGER NOT NULL,
  entry_id      INTEGER NOT NULL,
  tag_id        INTEGER NOT NULL,
  
  UNIQUE(user_id, entry_id, tag_id)
);
CREATE TRIGGER entries_tags_update_datemodified BEFORE UPDATE ON entries_tags FOR EACH ROW EXECUTE PROCEDURE update_datemodified_column();

