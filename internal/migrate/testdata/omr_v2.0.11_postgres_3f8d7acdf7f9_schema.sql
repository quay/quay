-- Compact OMR v2.0.11 PostgreSQL table inventory at Alembic revision
-- 3f8d7acdf7f9. It was derived from a real PostgreSQL 16 schema created by
-- running Quay's `alembic upgrade 3f8d7acdf7f9`, then captured with
-- `pg_dump --schema-only --no-owner --no-privileges`.
--
-- This fixture intentionally retains only the 97 CREATE TABLE definitions.
-- The production compatibility contract observes relation kind, column order,
-- column name, PostgreSQL type, and nullability. Sequences, defaults, indexes,
-- constraints, ownership, and dump session settings do not affect that contract
-- or the row-copy behavior exercised by the integration test.
--
-- Source versions: PostgreSQL 16.14, Python 3.12.13, Alembic 1.13.1, and the
-- repository's immutable migration chain through 3f8d7acdf7f9. The table set
-- and column inventory were verified against the artifact-derived SQLite OMR
-- fixture at internal/dal/schema/sqlite/omr/3f8d7acdf7f9_schema.sql.
--
-- IMPORTANT FINDING: mediatype IDs 13-18 are not stable across installations
-- because their migrations iterate Python sets. imagestoragelocation can also
-- gain a config-dependent `default` row at runtime. The converter must copy
-- lookup rows from each source rather than assume baseline IDs; the companion
-- enum_seed_data fixture exercises those rows.

CREATE TABLE public.accesstoken (
    id integer NOT NULL,
    friendly_name character varying(255),
    repository_id integer NOT NULL,
    created timestamp without time zone NOT NULL,
    role_id integer NOT NULL,
    temporary boolean NOT NULL,
    kind_id integer,
    token_code character varying(255) NOT NULL,
    token_name character varying(255) NOT NULL
);

CREATE TABLE public.accesstokenkind (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);

CREATE TABLE public.apprblob (
    id integer NOT NULL,
    digest character varying(255) NOT NULL,
    media_type_id integer NOT NULL,
    size bigint NOT NULL,
    uncompressed_size bigint
);

CREATE TABLE public.apprblobplacement (
    id integer NOT NULL,
    blob_id integer NOT NULL,
    location_id integer NOT NULL
);

CREATE TABLE public.apprblobplacementlocation (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);

CREATE TABLE public.apprmanifest (
    id integer NOT NULL,
    digest character varying(255) NOT NULL,
    media_type_id integer NOT NULL,
    manifest_json text NOT NULL
);

CREATE TABLE public.apprmanifestblob (
    id integer NOT NULL,
    manifest_id integer NOT NULL,
    blob_id integer NOT NULL
);

CREATE TABLE public.apprmanifestlist (
    id integer NOT NULL,
    digest character varying(255) NOT NULL,
    manifest_list_json text NOT NULL,
    schema_version character varying(255) NOT NULL,
    media_type_id integer NOT NULL
);

CREATE TABLE public.apprmanifestlistmanifest (
    id integer NOT NULL,
    manifest_list_id integer NOT NULL,
    manifest_id integer NOT NULL,
    operating_system character varying(255),
    architecture character varying(255),
    platform_json text,
    media_type_id integer NOT NULL
);

CREATE TABLE public.apprtag (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    repository_id integer NOT NULL,
    manifest_list_id integer,
    lifetime_start bigint NOT NULL,
    lifetime_end bigint,
    hidden boolean NOT NULL,
    reverted boolean NOT NULL,
    protected boolean NOT NULL,
    tag_kind_id integer NOT NULL,
    linked_tag_id integer
);

CREATE TABLE public.apprtagkind (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);

CREATE TABLE public.appspecificauthtoken (
    id integer NOT NULL,
    user_id integer NOT NULL,
    uuid character varying(36) NOT NULL,
    title character varying(255) NOT NULL,
    created timestamp without time zone NOT NULL,
    expiration timestamp without time zone,
    last_accessed timestamp without time zone,
    token_name character varying(255) NOT NULL,
    token_secret character varying(255) NOT NULL
);

CREATE TABLE public.autoprunetaskstatus (
    id integer NOT NULL,
    namespace_id integer NOT NULL,
    last_ran_ms bigint,
    status text
);

CREATE TABLE public.blobupload (
    id integer NOT NULL,
    repository_id integer NOT NULL,
    uuid character varying(255) NOT NULL,
    byte_count bigint NOT NULL,
    sha_state text,
    location_id integer NOT NULL,
    storage_metadata text,
    chunk_count integer DEFAULT 0 NOT NULL,
    uncompressed_byte_count bigint,
    created timestamp without time zone DEFAULT '2026-08-12 19:12:10'::timestamp without time zone NOT NULL,
    piece_sha_state text,
    piece_hashes text
);

CREATE TABLE public.buildtriggerservice (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);

CREATE TABLE public.deletednamespace (
    id integer NOT NULL,
    namespace_id integer NOT NULL,
    marked timestamp without time zone NOT NULL,
    original_username character varying(255) NOT NULL,
    original_email character varying(255) NOT NULL,
    queue_id character varying(255)
);

CREATE TABLE public.deletedrepository (
    id integer NOT NULL,
    repository_id integer NOT NULL,
    marked timestamp without time zone NOT NULL,
    original_name character varying(255) NOT NULL,
    queue_id character varying(255)
);

CREATE TABLE public.disablereason (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);

CREATE TABLE public.emailconfirmation (
    id integer NOT NULL,
    code character varying(255) NOT NULL,
    user_id integer NOT NULL,
    pw_reset boolean NOT NULL,
    new_email character varying(255),
    email_confirm boolean NOT NULL,
    created timestamp without time zone NOT NULL,
    verification_code character varying(255)
);

CREATE TABLE public.externalnotificationevent (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);

CREATE TABLE public.externalnotificationmethod (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);

CREATE TABLE public.federatedlogin (
    id integer NOT NULL,
    user_id integer NOT NULL,
    service_id integer NOT NULL,
    service_ident character varying(255) NOT NULL,
    metadata_json text NOT NULL
);

CREATE TABLE public.imagestorage (
    id integer NOT NULL,
    uuid character varying(255) NOT NULL,
    image_size bigint,
    uncompressed_size bigint,
    uploading boolean,
    cas_path boolean DEFAULT false NOT NULL,
    content_checksum character varying(255)
);

CREATE TABLE public.imagestoragelocation (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);

CREATE TABLE public.imagestorageplacement (
    id integer NOT NULL,
    storage_id integer NOT NULL,
    location_id integer NOT NULL
);

CREATE TABLE public.imagestoragesignature (
    id integer NOT NULL,
    storage_id integer NOT NULL,
    kind_id integer NOT NULL,
    signature text,
    uploading boolean
);

CREATE TABLE public.imagestoragesignaturekind (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);

CREATE TABLE public.imagestoragetransformation (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);

CREATE TABLE public.label (
    id integer NOT NULL,
    uuid character varying(255) NOT NULL,
    key character varying(255) NOT NULL,
    value text NOT NULL,
    media_type_id integer NOT NULL,
    source_type_id integer NOT NULL
);

CREATE TABLE public.labelsourcetype (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    mutable boolean NOT NULL
);

CREATE TABLE public.logentry (
    id bigint NOT NULL,
    kind_id integer NOT NULL,
    account_id integer NOT NULL,
    performer_id integer,
    repository_id integer,
    datetime timestamp without time zone NOT NULL,
    ip character varying(255),
    metadata_json text NOT NULL
);

CREATE TABLE public.logentry2 (
    id integer NOT NULL,
    kind_id integer NOT NULL,
    account_id integer NOT NULL,
    performer_id integer,
    repository_id integer,
    datetime timestamp without time zone NOT NULL,
    ip character varying(255),
    metadata_json text NOT NULL
);

CREATE TABLE public.logentry3 (
    id bigint NOT NULL,
    kind_id integer NOT NULL,
    account_id integer NOT NULL,
    performer_id integer,
    repository_id integer,
    datetime timestamp without time zone NOT NULL,
    ip character varying(255),
    metadata_json text NOT NULL
);

CREATE TABLE public.logentrykind (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);

CREATE TABLE public.loginservice (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);

CREATE TABLE public.manifest (
    id integer NOT NULL,
    repository_id integer NOT NULL,
    digest character varying(255) NOT NULL,
    media_type_id integer NOT NULL,
    manifest_bytes text NOT NULL,
    config_media_type character varying(255),
    layers_compressed_size bigint,
    subject character varying(255),
    subject_backfilled boolean,
    artifact_type character varying(255),
    artifact_type_backfilled boolean
);

CREATE TABLE public.manifestblob (
    id integer NOT NULL,
    repository_id integer NOT NULL,
    manifest_id integer NOT NULL,
    blob_id integer NOT NULL
);

CREATE TABLE public.manifestchild (
    id integer NOT NULL,
    repository_id integer NOT NULL,
    manifest_id integer NOT NULL,
    child_manifest_id integer NOT NULL
);

CREATE TABLE public.manifestlabel (
    id integer NOT NULL,
    repository_id integer NOT NULL,
    manifest_id integer NOT NULL,
    label_id integer NOT NULL
);

CREATE TABLE public.manifestsecuritystatus (
    id integer NOT NULL,
    manifest_id integer NOT NULL,
    repository_id integer NOT NULL,
    index_status integer NOT NULL,
    error_json text NOT NULL,
    last_indexed timestamp without time zone NOT NULL,
    indexer_hash character varying(128) NOT NULL,
    indexer_version integer NOT NULL,
    metadata_json text NOT NULL
);

CREATE TABLE public.mediatype (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);

CREATE TABLE public.messages (
    id integer NOT NULL,
    content text NOT NULL,
    uuid character varying(36) DEFAULT ''::character varying NOT NULL,
    media_type_id integer DEFAULT 1 NOT NULL,
    severity character varying(255) DEFAULT 'info'::character varying NOT NULL
);

CREATE TABLE public.namespaceautoprunepolicy (
    id integer NOT NULL,
    uuid character varying(36) NOT NULL,
    namespace_id integer NOT NULL,
    policy text NOT NULL
);

CREATE TABLE public.namespacegeorestriction (
    id integer NOT NULL,
    namespace_id integer NOT NULL,
    added timestamp without time zone NOT NULL,
    description character varying(255) NOT NULL,
    unstructured_json text NOT NULL,
    restricted_region_iso_code character varying(255) NOT NULL
);

CREATE TABLE public.notification (
    id integer NOT NULL,
    uuid character varying(255) NOT NULL,
    kind_id integer NOT NULL,
    target_id integer NOT NULL,
    metadata_json text NOT NULL,
    created timestamp without time zone NOT NULL,
    dismissed boolean NOT NULL,
    lookup_path character varying(255)
);

CREATE TABLE public.notificationkind (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);

CREATE TABLE public.oauthaccesstoken (
    id integer NOT NULL,
    uuid character varying(255) NOT NULL,
    application_id integer NOT NULL,
    authorized_user_id integer NOT NULL,
    scope character varying(255) NOT NULL,
    token_type character varying(255) NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    data text NOT NULL,
    token_code character varying(255) NOT NULL,
    token_name character varying(255) NOT NULL
);

CREATE TABLE public.oauthapplication (
    id integer NOT NULL,
    client_id character varying(255) NOT NULL,
    redirect_uri character varying(255) NOT NULL,
    application_uri character varying(255) NOT NULL,
    organization_id integer NOT NULL,
    name character varying(255) NOT NULL,
    description text NOT NULL,
    gravatar_email character varying(255),
    secure_client_secret character varying(255),
    fully_migrated boolean DEFAULT false NOT NULL
);

CREATE TABLE public.oauthassignedtoken (
    id integer NOT NULL,
    uuid character varying(255) NOT NULL,
    assigned_user_id integer NOT NULL,
    application_id integer NOT NULL,
    redirect_uri character varying(255),
    scope character varying(255) NOT NULL,
    response_type character varying(255)
);

CREATE TABLE public.oauthauthorizationcode (
    id integer NOT NULL,
    application_id integer NOT NULL,
    scope character varying(255) NOT NULL,
    data text NOT NULL,
    code_credential character varying(255) NOT NULL,
    code_name character varying(255) NOT NULL
);

CREATE TABLE public.organizationrhskus (
    id integer NOT NULL,
    subscription_id integer NOT NULL,
    org_id integer NOT NULL,
    user_id integer NOT NULL,
    quantity integer
);

CREATE TABLE public.permissionprototype (
    id integer NOT NULL,
    org_id integer NOT NULL,
    uuid character varying(255) NOT NULL,
    activating_user_id integer,
    delegate_user_id integer,
    delegate_team_id integer,
    role_id integer NOT NULL
);

CREATE TABLE public.proxycacheconfig (
    id integer NOT NULL,
    organization_id integer NOT NULL,
    creation_date timestamp without time zone NOT NULL,
    upstream_registry character varying(2048) NOT NULL,
    upstream_registry_username character varying(4096),
    upstream_registry_password character varying(4096),
    expiration_s integer DEFAULT 86400,
    insecure boolean DEFAULT false NOT NULL
);

CREATE TABLE public.quayregion (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);

CREATE TABLE public.quayrelease (
    id integer NOT NULL,
    service_id integer NOT NULL,
    version character varying(255) NOT NULL,
    region_id integer NOT NULL,
    reverted boolean NOT NULL,
    created timestamp without time zone NOT NULL
);

CREATE TABLE public.quayservice (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);

CREATE TABLE public.queueitem (
    id integer NOT NULL,
    queue_name character varying(1024) NOT NULL,
    body text NOT NULL,
    available_after timestamp without time zone NOT NULL,
    available boolean NOT NULL,
    processing_expires timestamp without time zone,
    retries_remaining integer NOT NULL,
    state_id character varying(255) DEFAULT ''::character varying NOT NULL
);

CREATE TABLE public.quotalimits (
    id integer NOT NULL,
    quota_id integer NOT NULL,
    quota_type_id integer NOT NULL,
    percent_of_limit integer NOT NULL
);

CREATE TABLE public.quotanamespacesize (
    id integer NOT NULL,
    namespace_user_id integer NOT NULL,
    size_bytes bigint DEFAULT '0'::bigint NOT NULL,
    backfill_start_ms bigint,
    backfill_complete boolean DEFAULT false NOT NULL
);

CREATE TABLE public.quotaregistrysize (
    id integer NOT NULL,
    size_bytes bigint DEFAULT '0'::bigint NOT NULL,
    running boolean DEFAULT false NOT NULL,
    queued boolean DEFAULT false NOT NULL,
    completed_ms bigint
);

CREATE TABLE public.quotarepositorysize (
    id integer NOT NULL,
    repository_id integer NOT NULL,
    size_bytes bigint DEFAULT '0'::bigint NOT NULL,
    backfill_start_ms bigint,
    backfill_complete boolean DEFAULT false NOT NULL
);

CREATE TABLE public.quotatype (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);

CREATE TABLE public.redhatsubscriptions (
    id integer NOT NULL,
    user_id integer NOT NULL,
    account_number integer NOT NULL
);

CREATE TABLE public.repomirrorconfig (
    id integer NOT NULL,
    repository_id integer NOT NULL,
    creation_date timestamp without time zone NOT NULL,
    is_enabled boolean NOT NULL,
    mirror_type integer NOT NULL,
    internal_robot_id integer NOT NULL,
    external_registry_username character varying(4096),
    external_registry_password character varying(4096),
    external_registry_config text NOT NULL,
    sync_interval integer DEFAULT 60 NOT NULL,
    sync_start_date timestamp without time zone,
    sync_expiration_date timestamp without time zone,
    sync_retries_remaining integer DEFAULT 3 NOT NULL,
    sync_status integer NOT NULL,
    sync_transaction_id character varying(36),
    root_rule_id integer NOT NULL,
    external_reference text NOT NULL
);

CREATE TABLE public.repomirrorrule (
    id integer NOT NULL,
    uuid character varying(36) NOT NULL,
    repository_id integer NOT NULL,
    creation_date timestamp without time zone NOT NULL,
    rule_type integer NOT NULL,
    rule_value text NOT NULL,
    left_child_id integer,
    right_child_id integer
);

CREATE TABLE public.repository (
    id integer NOT NULL,
    namespace_user_id integer,
    name character varying(255) NOT NULL,
    visibility_id integer NOT NULL,
    description text,
    badge_token character varying(255) NOT NULL,
    kind_id integer DEFAULT 1 NOT NULL,
    trust_enabled boolean DEFAULT false NOT NULL,
    state integer DEFAULT 0 NOT NULL
);

CREATE TABLE public.repositoryactioncount (
    id integer NOT NULL,
    repository_id integer NOT NULL,
    count integer NOT NULL,
    date date NOT NULL
);

CREATE TABLE public.repositoryauthorizedemail (
    id integer NOT NULL,
    repository_id integer NOT NULL,
    email character varying(255) NOT NULL,
    code character varying(255) NOT NULL,
    confirmed boolean NOT NULL
);

CREATE TABLE public.repositoryautoprunepolicy (
    id integer NOT NULL,
    uuid character varying(36) NOT NULL,
    repository_id integer NOT NULL,
    namespace_id integer NOT NULL,
    policy text NOT NULL
);

CREATE TABLE public.repositorybuild (
    id integer NOT NULL,
    uuid character varying(255) NOT NULL,
    repository_id integer NOT NULL,
    access_token_id integer NOT NULL,
    resource_key character varying(255),
    job_config text NOT NULL,
    phase character varying(255) NOT NULL,
    started timestamp without time zone NOT NULL,
    display_name character varying(255) NOT NULL,
    trigger_id integer,
    pull_robot_id integer,
    logs_archived boolean DEFAULT false NOT NULL,
    queue_id character varying(255)
);

CREATE TABLE public.repositorybuildtrigger (
    id integer NOT NULL,
    uuid character varying(255) NOT NULL,
    service_id integer NOT NULL,
    repository_id integer NOT NULL,
    connected_user_id integer NOT NULL,
    config text NOT NULL,
    write_token_id integer,
    pull_robot_id integer,
    disabled_reason_id integer,
    enabled boolean DEFAULT true NOT NULL,
    successive_failure_count integer DEFAULT 0 NOT NULL,
    successive_internal_error_count integer DEFAULT 0 NOT NULL,
    disabled_datetime timestamp without time zone,
    secure_auth_token character varying(255),
    secure_private_key text,
    fully_migrated boolean DEFAULT false NOT NULL
);

CREATE TABLE public.repositorykind (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);

CREATE TABLE public.repositorynotification (
    id integer NOT NULL,
    uuid character varying(255) NOT NULL,
    repository_id integer NOT NULL,
    event_id integer NOT NULL,
    method_id integer NOT NULL,
    title character varying(255),
    config_json text NOT NULL,
    event_config_json text NOT NULL,
    number_of_failures integer DEFAULT 0 NOT NULL,
    last_ran_ms bigint
);

CREATE TABLE public.repositorypermission (
    id integer NOT NULL,
    team_id integer,
    user_id integer,
    repository_id integer NOT NULL,
    role_id integer NOT NULL
);

CREATE TABLE public.repositorysearchscore (
    id integer NOT NULL,
    repository_id integer NOT NULL,
    score bigint NOT NULL,
    last_updated timestamp without time zone
);

CREATE TABLE public.robotaccountmetadata (
    id integer NOT NULL,
    robot_account_id integer NOT NULL,
    description character varying(255) NOT NULL,
    unstructured_json text NOT NULL
);

CREATE TABLE public.robotaccounttoken (
    id integer NOT NULL,
    robot_account_id integer NOT NULL,
    token character varying(255) NOT NULL,
    fully_migrated boolean DEFAULT false NOT NULL
);

CREATE TABLE public.role (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);

CREATE TABLE public.servicekey (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    kid character varying(255) NOT NULL,
    service character varying(255) NOT NULL,
    jwk text NOT NULL,
    metadata text NOT NULL,
    created_date timestamp without time zone NOT NULL,
    expiration_date timestamp without time zone,
    rotation_duration integer,
    approval_id integer
);

CREATE TABLE public.servicekeyapproval (
    id integer NOT NULL,
    approver_id integer,
    approval_type character varying(255) NOT NULL,
    approved_date timestamp without time zone NOT NULL,
    notes text NOT NULL
);

CREATE TABLE public.star (
    id integer NOT NULL,
    user_id integer NOT NULL,
    repository_id integer NOT NULL,
    created timestamp without time zone NOT NULL
);

CREATE TABLE public.tag (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    repository_id integer NOT NULL,
    manifest_id integer,
    lifetime_start_ms bigint NOT NULL,
    lifetime_end_ms bigint,
    hidden boolean DEFAULT false NOT NULL,
    reversion boolean DEFAULT false NOT NULL,
    tag_kind_id integer NOT NULL,
    linked_tag_id integer
);

CREATE TABLE public.tagkind (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);

CREATE TABLE public.tagnotificationsuccess (
    id integer NOT NULL,
    notification_id integer NOT NULL,
    tag_id integer NOT NULL,
    method_id integer NOT NULL
);

CREATE TABLE public.team (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    organization_id integer NOT NULL,
    role_id integer NOT NULL,
    description text NOT NULL
);

CREATE TABLE public.teammember (
    id integer NOT NULL,
    user_id integer NOT NULL,
    team_id integer NOT NULL
);

CREATE TABLE public.teammemberinvite (
    id integer NOT NULL,
    user_id integer,
    email character varying(255),
    team_id integer NOT NULL,
    inviter_id integer NOT NULL,
    invite_token character varying(255) NOT NULL
);

CREATE TABLE public.teamrole (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);

CREATE TABLE public.teamsync (
    id integer NOT NULL,
    team_id integer NOT NULL,
    transaction_id character varying(255) NOT NULL,
    last_updated timestamp without time zone,
    service_id integer NOT NULL,
    config text NOT NULL
);

CREATE TABLE public.uploadedblob (
    id bigint NOT NULL,
    repository_id integer NOT NULL,
    blob_id integer NOT NULL,
    uploaded_at timestamp without time zone NOT NULL,
    expires_at timestamp without time zone NOT NULL
);

CREATE TABLE public."user" (
    id integer NOT NULL,
    uuid character varying(36),
    username character varying(255) NOT NULL,
    password_hash character varying(255),
    email character varying(255) NOT NULL,
    verified boolean NOT NULL,
    stripe_id character varying(255),
    organization boolean NOT NULL,
    robot boolean NOT NULL,
    invoice_email boolean NOT NULL,
    invalid_login_attempts integer DEFAULT 0 NOT NULL,
    last_invalid_login timestamp without time zone NOT NULL,
    removed_tag_expiration_s bigint DEFAULT 1209600 NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    invoice_email_address character varying(255),
    company character varying(255),
    family_name character varying(255),
    given_name character varying(255),
    location character varying(255),
    maximum_queued_builds_count integer,
    creation_date timestamp without time zone,
    last_accessed timestamp without time zone
);

CREATE TABLE public.userorganizationquota (
    id integer NOT NULL,
    namespace_id integer NOT NULL,
    limit_bytes bigint NOT NULL
);

CREATE TABLE public.userprompt (
    id integer NOT NULL,
    user_id integer NOT NULL,
    kind_id integer NOT NULL
);

CREATE TABLE public.userpromptkind (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);

CREATE TABLE public.userregion (
    id integer NOT NULL,
    user_id integer NOT NULL,
    location_id integer NOT NULL
);

CREATE TABLE public.visibility (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);
