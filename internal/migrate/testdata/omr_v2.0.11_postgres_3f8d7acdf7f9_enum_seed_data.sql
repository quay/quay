-- Enum/lookup table data from the same real `alembic upgrade 3f8d7acdf7f9`
-- run against PostgreSQL 16 documented in
-- omr_v2.0.11_postgres_3f8d7acdf7f9_schema.sql. `pg_dump --data-only` COPY
-- format, `\restrict`/`\unrestrict` pragma lines stripped.
--
-- All rows here matched the existing artifact-derived SQLite fixture's
-- enum seed rows (internal/dal/schema/sqlite/omr/3f8d7acdf7f9_seed_data.sql)
-- byte-for-byte, EXCEPT:
--
--   - mediatype ids 13-18: NOT stable across installations. See the
--     "IMPORTANT FINDING" note in omr_v2.0.11_postgres_3f8d7acdf7f9_schema.sql.
--   - imagestoragelocation: this fresh alembic-only run has exactly the 8
--     rows Alembic's base migration seeds; the SQLite fixture (extracted
--     from a real *running* installation) has a 9th "default" row added by
--     application runtime code (LocalStorage location auto-creation), not
--     by Alembic. Config-dependent, not a fixed baseline value.
--
-- PostgreSQL database dump
--


-- Dumped from database version 16.14 (Debian 16.14-1.pgdg13+1)
-- Dumped by pg_dump version 16.14 (Debian 16.14-1.pgdg13+1)

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
-- Data for Name: accesstokenkind; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.accesstokenkind (id, name) FROM stdin;
1	build-worker
2	pushpull-token
\.


--
-- Data for Name: apprblobplacementlocation; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.apprblobplacementlocation (id, name) FROM stdin;
1	local_eu
2	local_us
\.


--
-- Data for Name: apprtagkind; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.apprtagkind (id, name) FROM stdin;
1	tag
2	release
3	channel
\.


--
-- Data for Name: buildtriggerservice; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.buildtriggerservice (id, name) FROM stdin;
1	github
2	gitlab
3	bitbucket
4	custom-git
\.


--
-- Data for Name: disablereason; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.disablereason (id, name) FROM stdin;
1	user_toggled
2	successive_build_failures
3	successive_build_internal_errors
\.


--
-- Data for Name: externalnotificationevent; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.externalnotificationevent (id, name) FROM stdin;
1	build_failure
2	build_queued
3	build_start
4	build_success
5	repo_push
6	vulnerability_found
7	build_cancelled
8	repo_mirror_sync_started
9	repo_mirror_sync_success
10	repo_mirror_sync_failed
11	repo_image_expiry
\.


--
-- Data for Name: externalnotificationmethod; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.externalnotificationmethod (id, name) FROM stdin;
1	email
2	flowdock
3	hipchat
4	quay_notification
5	slack
6	webhook
\.


--
-- Data for Name: imagestoragelocation; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.imagestoragelocation (id, name) FROM stdin;
1	s3_us_east_1
2	s3_eu_west_1
3	s3_ap_southeast_1
4	s3_ap_southeast_2
5	s3_ap_northeast_1
6	s3_sa_east_1
7	local
8	s3_us_west_1
\.


--
-- Data for Name: imagestoragesignaturekind; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.imagestoragesignaturekind (id, name) FROM stdin;
1	gpg2
\.


--
-- Data for Name: imagestoragetransformation; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.imagestoragetransformation (id, name) FROM stdin;
1	squash
2	aci
\.


--
-- Data for Name: labelsourcetype; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.labelsourcetype (id, name, mutable) FROM stdin;
1	manifest	f
2	api	t
3	internal	f
\.


--
-- Data for Name: logentrykind; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.logentrykind (id, name) FROM stdin;
1	account_change_cc
2	account_change_password
3	account_change_plan
4	account_convert
5	add_repo_accesstoken
6	add_repo_notification
7	add_repo_permission
8	add_repo_webhook
9	build_dockerfile
10	change_repo_permission
11	change_repo_visibility
12	create_application
13	create_prototype_permission
14	create_repo
15	create_robot
16	create_tag
17	delete_application
18	delete_prototype_permission
19	delete_repo
20	delete_repo_accesstoken
21	delete_repo_notification
22	delete_repo_permission
23	delete_repo_trigger
24	delete_repo_webhook
25	delete_robot
26	delete_tag
27	manifest_label_add
28	manifest_label_delete
29	modify_prototype_permission
30	move_tag
31	org_add_team_member
32	org_create_team
33	org_delete_team
34	org_delete_team_member_invite
35	org_invite_team_member
36	org_remove_team_member
37	org_set_team_description
38	org_set_team_role
39	org_team_member_invite_accepted
40	org_team_member_invite_declined
41	pull_repo
42	push_repo
43	regenerate_robot_token
44	repo_verb
45	reset_application_client_secret
46	revert_tag
47	service_key_approve
48	service_key_create
49	service_key_delete
50	service_key_extend
51	service_key_modify
52	service_key_rotate
53	setup_repo_trigger
54	set_repo_description
55	take_ownership
56	update_application
57	change_repo_trust
58	reset_repo_notification
59	change_tag_expiration
60	create_app_specific_token
61	revoke_app_specific_token
62	toggle_repo_trigger
63	repo_mirror_enabled
64	repo_mirror_disabled
65	repo_mirror_config_changed
66	repo_mirror_sync_started
67	repo_mirror_sync_failed
68	repo_mirror_sync_success
69	repo_mirror_sync_now_requested
70	repo_mirror_sync_tag_success
71	repo_mirror_sync_tag_failed
72	repo_mirror_sync_test_success
73	repo_mirror_sync_test_failed
74	repo_mirror_sync_test_started
75	change_repo_state
76	create_proxy_cache_config
77	delete_proxy_cache_config
78	start_build_trigger
79	cancel_build
80	org_create
81	org_delete
82	org_change_email
83	org_change_invoicing
84	org_change_tag_expiration
85	org_change_name
86	user_create
87	user_delete
88	user_disable
89	user_enable
90	user_change_email
91	user_change_password
92	user_change_name
93	user_change_invoicing
94	user_change_tag_expiration
95	user_change_metadata
96	user_generate_client_key
97	login_success
98	logout_success
99	permanently_delete_tag
100	autoprune_tag_delete
101	create_namespace_autoprune_policy
102	update_namespace_autoprune_policy
103	delete_namespace_autoprune_policy
104	login_failure
105	push_repo_failed
106	pull_repo_failed
107	delete_tag_failed
108	create_repository_autoprune_policy
109	update_repository_autoprune_policy
110	delete_repository_autoprune_policy
111	enable_team_sync
112	disable_team_sync
113	oauth_token_assigned
114	oauth_token_revoked
\.


--
-- Data for Name: loginservice; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.loginservice (id, name) FROM stdin;
1	github
2	quayrobot
3	ldap
4	google
5	keystone
6	dex
7	jwtauthn
8	oidc
\.


--
-- Data for Name: mediatype; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.mediatype (id, name) FROM stdin;
1	text/plain
2	application/json
3	text/markdown
4	application/vnd.cnr.blob.v0.tar+gzip
5	application/vnd.cnr.package-manifest.helm.v0.json
6	application/vnd.cnr.package-manifest.kpm.v0.json
7	application/vnd.cnr.package-manifest.docker-compose.v0.json
8	application/vnd.cnr.package.kpm.v0.tar+gzip
9	application/vnd.cnr.package.helm.v0.tar+gzip
10	application/vnd.cnr.package.docker-compose.v0.tar+gzip
11	application/vnd.cnr.manifests.v0.json
12	application/vnd.cnr.manifest.list.v0.json
13	application/vnd.docker.distribution.manifest.v1+json
14	application/vnd.docker.distribution.manifest.v1+prettyjws
15	application/vnd.docker.distribution.manifest.v2+json
16	application/vnd.docker.distribution.manifest.list.v2+json
17	application/vnd.oci.image.index.v1+json
18	application/vnd.oci.image.manifest.v1+json
\.


--
-- Data for Name: notificationkind; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.notificationkind (id, name) FROM stdin;
1	build_failure
2	build_queued
3	build_start
4	build_success
5	expiring_license
6	maintenance
7	org_team_invite
8	over_private_usage
9	password_required
10	repo_push
11	service_key_submitted
12	vulnerability_found
13	build_cancelled
14	repo_mirror_sync_started
15	repo_mirror_sync_success
16	repo_mirror_sync_failed
17	quota_warning
18	quota_error
19	assigned_authorization
\.


--
-- Data for Name: quotatype; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.quotatype (id, name) FROM stdin;
1	Warning
2	Reject
\.


--
-- Data for Name: repositorykind; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.repositorykind (id, name) FROM stdin;
1	image
2	application
\.


--
-- Data for Name: role; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.role (id, name) FROM stdin;
1	admin
2	write
3	read
\.


--
-- Data for Name: tagkind; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tagkind (id, name) FROM stdin;
1	tag
\.


--
-- Data for Name: teamrole; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.teamrole (id, name) FROM stdin;
1	admin
2	creator
3	member
\.


--
-- Data for Name: userpromptkind; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.userpromptkind (id, name) FROM stdin;
1	confirm_username
2	enter_name
3	enter_company
\.


--
-- Data for Name: visibility; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.visibility (id, name) FROM stdin;
1	public
2	private
\.


--
-- Name: accesstokenkind_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.accesstokenkind_id_seq', 2, true);


--
-- Name: apprblobplacementlocation_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.apprblobplacementlocation_id_seq', 3, false);


--
-- Name: apprtagkind_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.apprtagkind_id_seq', 4, false);


--
-- Name: buildtriggerservice_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.buildtriggerservice_id_seq', 4, true);


--
-- Name: disablereason_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.disablereason_id_seq', 1, false);


--
-- Name: externalnotificationevent_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.externalnotificationevent_id_seq', 11, true);


--
-- Name: externalnotificationmethod_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.externalnotificationmethod_id_seq', 6, true);


--
-- Name: imagestoragelocation_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.imagestoragelocation_id_seq', 8, true);


--
-- Name: imagestoragesignaturekind_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.imagestoragesignaturekind_id_seq', 1, true);


--
-- Name: imagestoragetransformation_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.imagestoragetransformation_id_seq', 2, true);


--
-- Name: labelsourcetype_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.labelsourcetype_id_seq', 3, true);


--
-- Name: logentrykind_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.logentrykind_id_seq', 114, true);


--
-- Name: loginservice_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.loginservice_id_seq', 8, true);


--
-- Name: mediatype_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.mediatype_id_seq', 18, true);


--
-- Name: notificationkind_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.notificationkind_id_seq', 19, true);


--
-- Name: quotatype_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.quotatype_id_seq', 2, true);


--
-- Name: repositorykind_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.repositorykind_id_seq', 1, false);


--
-- Name: role_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.role_id_seq', 3, true);


--
-- Name: tagkind_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.tagkind_id_seq', 1, true);


--
-- Name: teamrole_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.teamrole_id_seq', 3, true);


--
-- Name: userpromptkind_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.userpromptkind_id_seq', 3, true);


--
-- Name: visibility_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.visibility_id_seq', 2, true);


--
-- PostgreSQL database dump complete
--
