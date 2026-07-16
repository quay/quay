-- revision: 6715e4719375
-- down_revision: b30800b1d271

CREATE TABLE namespacenotification (
	id INTEGER NOT NULL,
	uuid VARCHAR(255) NOT NULL,
	namespace_id INTEGER NOT NULL,
	event_id INTEGER NOT NULL,
	method_id INTEGER NOT NULL,
	title VARCHAR(255),
	config_json TEXT NOT NULL,
	event_config_json TEXT DEFAULT '{}' NOT NULL,
	number_of_failures INTEGER DEFAULT '0' NOT NULL,
	last_ran_ms BIGINT,
	CONSTRAINT pk_namespacenotification PRIMARY KEY (id),
	CONSTRAINT fk_namespacenotification_namespace_id FOREIGN KEY(namespace_id) REFERENCES user (id),
	CONSTRAINT fk_namespacenotification_event_id FOREIGN KEY(event_id) REFERENCES externalnotificationevent (id),
	CONSTRAINT fk_namespacenotification_method_id FOREIGN KEY(method_id) REFERENCES externalnotificationmethod (id)
);

CREATE INDEX namespacenotification_uuid ON namespacenotification (uuid);
CREATE INDEX namespacenotification_namespace_id ON namespacenotification (namespace_id);

CREATE TABLE quotanotificationstate (
	id INTEGER NOT NULL,
	namespace_id INTEGER NOT NULL,
	threshold_percent INTEGER NOT NULL,
	last_notified_at DATETIME,
	cleared BOOLEAN DEFAULT '1' NOT NULL,
	CONSTRAINT pk_quotanotificationstate PRIMARY KEY (id),
	CONSTRAINT fk_quotanotificationstate_namespace_id FOREIGN KEY(namespace_id) REFERENCES user (id)
);

CREATE INDEX quotanotificationstate_namespace_id
ON quotanotificationstate (namespace_id);

CREATE UNIQUE INDEX quotanotificationstate_namespace_threshold
ON quotanotificationstate (namespace_id, threshold_percent);

INSERT OR IGNORE INTO externalnotificationevent (name) VALUES ('quota_warning');
INSERT OR IGNORE INTO externalnotificationevent (name) VALUES ('quota_error');
