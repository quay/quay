package postgres

type columnKind int

const (
	kindInt64 columnKind = iota
	kindText
	kindBool
	kindTimestamp
)

func (k columnKind) String() string {
	switch k {
	case kindInt64:
		return "int64"
	case kindText:
		return "text"
	case kindBool:
		return "bool"
	case kindTimestamp:
		return "timestamp"
	default:
		return "unknown"
	}
}

const (
	tableVisibility     = "visibility"
	tableRepositoryKind = "repositorykind"
	tableMediaType      = "mediatype"
	tableTagKind        = "tagkind"
	tableUser           = "user"
	tableRepository     = "repository"
	tableManifest       = "manifest"
	tableTag            = "tag"
	columnName          = "name"
)

type postgresColumn struct {
	name string
	kind columnKind
}

type postgresTable struct {
	name                 string
	columns              []postgresColumn
	replacesBaselineSeed bool
}

// Lookup IDs can differ between OMR installations, so lookup rows replace
// the intermediate's static seed data instead of relying on fixed IDs.
var approvedPostgresTables = []postgresTable{
	{
		name: tableVisibility, replacesBaselineSeed: true,
		columns: []postgresColumn{{name: "id", kind: kindInt64}, {name: columnName, kind: kindText}},
	},
	{
		name: tableRepositoryKind, replacesBaselineSeed: true,
		columns: []postgresColumn{{name: "id", kind: kindInt64}, {name: columnName, kind: kindText}},
	},
	{
		name: tableMediaType, replacesBaselineSeed: true,
		columns: []postgresColumn{{name: "id", kind: kindInt64}, {name: columnName, kind: kindText}},
	},
	{
		name: tableTagKind, replacesBaselineSeed: true,
		columns: []postgresColumn{{name: "id", kind: kindInt64}, {name: columnName, kind: kindText}},
	},
	{
		name: tableUser,
		columns: []postgresColumn{
			{name: "id", kind: kindInt64},
			{name: "uuid", kind: kindText},
			{name: "username", kind: kindText},
			{name: "password_hash", kind: kindText},
			{name: "email", kind: kindText},
			{name: "verified", kind: kindBool},
			{name: "stripe_id", kind: kindText},
			{name: "organization", kind: kindBool},
			{name: "robot", kind: kindBool},
			{name: "invoice_email", kind: kindBool},
			{name: "invalid_login_attempts", kind: kindInt64},
			{name: "last_invalid_login", kind: kindTimestamp},
			{name: "removed_tag_expiration_s", kind: kindInt64},
			{name: "enabled", kind: kindBool},
			{name: "invoice_email_address", kind: kindText},
			{name: "company", kind: kindText},
			{name: "family_name", kind: kindText},
			{name: "given_name", kind: kindText},
			{name: "location", kind: kindText},
			{name: "maximum_queued_builds_count", kind: kindInt64},
			{name: "creation_date", kind: kindTimestamp},
			{name: "last_accessed", kind: kindTimestamp},
		},
	},
	{
		name: tableRepository,
		columns: []postgresColumn{
			{name: "id", kind: kindInt64},
			{name: "namespace_user_id", kind: kindInt64},
			{name: columnName, kind: kindText},
			{name: "visibility_id", kind: kindInt64},
			{name: "description", kind: kindText},
			{name: "badge_token", kind: kindText},
			{name: "kind_id", kind: kindInt64},
			{name: "trust_enabled", kind: kindBool},
			{name: "state", kind: kindInt64},
		},
	},
	{
		name: tableManifest,
		columns: []postgresColumn{
			{name: "id", kind: kindInt64},
			{name: "repository_id", kind: kindInt64},
			{name: "digest", kind: kindText},
			{name: "media_type_id", kind: kindInt64},
			{name: "manifest_bytes", kind: kindText},
			{name: "config_media_type", kind: kindText},
			{name: "layers_compressed_size", kind: kindInt64},
			{name: "subject", kind: kindText},
			{name: "subject_backfilled", kind: kindBool},
			{name: "artifact_type", kind: kindText},
			{name: "artifact_type_backfilled", kind: kindBool},
		},
	},
	{
		name: tableTag,
		columns: []postgresColumn{
			{name: "id", kind: kindInt64},
			{name: columnName, kind: kindText},
			{name: "repository_id", kind: kindInt64},
			{name: "manifest_id", kind: kindInt64},
			{name: "lifetime_start_ms", kind: kindInt64},
			{name: "lifetime_end_ms", kind: kindInt64},
			{name: "hidden", kind: kindBool},
			{name: "reversion", kind: kindBool},
			{name: "tag_kind_id", kind: kindInt64},
			{name: "linked_tag_id", kind: kindInt64},
		},
	},
}
