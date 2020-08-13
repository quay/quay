from collections import defaultdict

from datetime import datetime, timedelta

from auth.permissions import ReadRepositoryPermission
from data.database import Repository as RepositoryTable, RepositoryState
from data import model
from data.appr_model import (
    channel as channel_model,
    release as release_model,
    tag as apprtags_model,
)
from data.registry_model import registry_model
from data.registry_model.datatypes import RepositoryReference
from endpoints.appr.models_cnr import model as appr_model
from endpoints.api.repository_models_interface import (
    RepositoryDataInterface,
    RepositoryBaseElement,
    Repository,
    ApplicationRepository,
    ImageRepositoryRepository,
    Tag,
    Channel,
    Release,
    Count,
)

MAX_DAYS_IN_3_MONTHS = 92
REPOS_PER_PAGE = 100


def _create_channel(channel, releases_channels_map):
    releases_channels_map[channel.linked_tag.name].append(channel.name)
    return Channel(channel.name, channel.linked_tag.name, channel.linked_tag.lifetime_start)


class PreOCIModel(RepositoryDataInterface):
    """
    PreOCIModel implements the data model for the Repo Email using a database schema before it was
    changed to support the OCI specification.
    """

    def check_repository_usage(self, username, plan_found):
        private_repos = model.user.get_private_repo_count(username)
        if plan_found is None:
            repos_allowed = 0
        else:
            repos_allowed = plan_found["privateRepos"]

        user_or_org = model.user.get_namespace_user(username)
        if private_repos > repos_allowed:
            model.notification.create_unique_notification(
                "over_private_usage", user_or_org, {"namespace": username}
            )
        else:
            model.notification.delete_notifications_by_kind(user_or_org, "over_private_usage")

    def mark_repository_for_deletion(self, namespace_name, repository_name, repository_gc_queue):
        model.repository.mark_repository_for_deletion(
            namespace_name, repository_name, repository_gc_queue
        )
        user = model.user.get_namespace_user(namespace_name)
        return user.username

    def set_description(self, namespace_name, repository_name, description):
        repo = model.repository.get_repository(namespace_name, repository_name)
        model.repository.set_description(repo, description)

    def set_trust(self, namespace_name, repository_name, trust):
        repo = model.repository.get_repository(namespace_name, repository_name)
        model.repository.set_trust(repo, trust)

    def set_repository_visibility(self, namespace_name, repository_name, visibility):
        repo = model.repository.get_repository(namespace_name, repository_name)
        model.repository.set_repository_visibility(repo, visibility)

    def set_repository_state(self, namespace_name, repository_name, state):
        repo = model.repository.get_repository(namespace_name, repository_name)
        model.repository.set_repository_state(repo, state)

    def get_repo_list(
        self,
        starred,
        user,
        repo_kind,
        namespace,
        username,
        public,
        page_token,
        last_modified,
        popularity,
    ):
        next_page_token = None

        # Lookup the requested repositories (either starred or non-starred.)
        if starred:
            # Return the full list of repos starred by the current user that are still visible to them.
            def can_view_repo(repo):
                assert repo.state != RepositoryState.MARKED_FOR_DELETION
                can_view = ReadRepositoryPermission(repo.namespace_user.username, repo.name).can()
                return can_view or model.repository.is_repository_public(repo)

            unfiltered_repos = model.repository.get_user_starred_repositories(
                user, kind_filter=repo_kind
            )
            repos = [repo for repo in unfiltered_repos if can_view_repo(repo)]
        else:
            # Determine the starting offset for pagination. Note that we don't use the normal
            # model.modelutil.paginate method here, as that does not operate over UNION queries, which
            # get_visible_repositories will return if there is a logged-in user (for performance reasons).
            #
            # Also note the +1 on the limit, as paginate_query uses the extra result to determine whether
            # there is a next page.
            start_id = model.modelutil.pagination_start(page_token)
            repo_query = model.repository.get_visible_repositories(
                username=username,
                include_public=public,
                start_id=start_id,
                limit=REPOS_PER_PAGE + 1,
                kind_filter=repo_kind,
                namespace=namespace,
            )

            repos, next_page_token = model.modelutil.paginate_query(
                repo_query, limit=REPOS_PER_PAGE, sort_field_name="rid"
            )

        repos = list(repos)
        assert len(repos) <= REPOS_PER_PAGE

        # Collect the IDs of the repositories found for subsequent lookup of popularity
        # and/or last modified.
        last_modified_map = {}
        action_sum_map = {}
        if last_modified or popularity:
            repository_refs = [RepositoryReference.for_id(repo.rid) for repo in repos]
            repository_ids = [repo.rid for repo in repos]

            if last_modified:
                last_modified_map = (
                    registry_model.get_most_recent_tag_lifetime_start(repository_refs)
                    if repo_kind == "image"
                    else apprtags_model.get_most_recent_tag_lifetime_start(
                        repository_ids, appr_model.models_ref
                    )
                )

            if popularity:
                action_sum_map = model.log.get_repositories_action_sums(repository_ids)

        # Collect the IDs of the repositories that are starred for the user, so we can mark them
        # in the returned results.
        star_set = set()
        if username:
            starred_repos = model.repository.get_user_starred_repositories(user, repo_kind)
            star_set = {starred.id for starred in starred_repos}

        return (
            [
                RepositoryBaseElement(
                    repo.namespace_user.username,
                    repo.name,
                    repo.rid in star_set,
                    model.repository.is_repository_public(repo),
                    repo_kind,
                    repo.description,
                    repo.namespace_user.organization,
                    repo.namespace_user.removed_tag_expiration_s,
                    last_modified_map.get(repo.rid),
                    action_sum_map.get(repo.rid),
                    last_modified,
                    popularity,
                    username,
                    None,
                    repo.state,
                )
                for repo in repos
            ],
            next_page_token,
        )

    def repo_exists(self, namespace_name, repository_name):
        repo = model.repository.get_repository(namespace_name, repository_name)
        if repo is None:
            return False

        return True

    def create_repo(
        self,
        namespace_name,
        repository_name,
        owner,
        description,
        visibility="private",
        repo_kind="image",
    ):
        repo = model.repository.create_repository(
            namespace_name,
            repository_name,
            owner,
            visibility,
            repo_kind=repo_kind,
            description=description,
        )
        if repo is None:
            return None

        return Repository(namespace_name, repository_name)

    def get_repo(self, namespace_name, repository_name, user, include_tags=True, max_tags=500):
        repo = model.repository.get_repository(namespace_name, repository_name)
        if repo is None:
            return None

        is_starred = model.repository.repository_is_starred(user, repo) if user else False
        is_public = model.repository.is_repository_public(repo)
        kind_name = RepositoryTable.kind.get_name(repo.kind_id)
        base = RepositoryBaseElement(
            namespace_name,
            repository_name,
            is_starred,
            is_public,
            kind_name,
            repo.description,
            repo.namespace_user.organization,
            repo.namespace_user.removed_tag_expiration_s,
            None,
            None,
            False,
            False,
            False,
            repo.namespace_user.stripe_id is None,
            repo.state,
        )

        if base.kind_name == "application":
            channels = channel_model.get_repo_channels(repo, appr_model.models_ref)
            releases = release_model.get_release_objs(repo, appr_model.models_ref)
            releases_channels_map = defaultdict(list)
            return ApplicationRepository(
                base,
                [_create_channel(channel, releases_channels_map) for channel in channels],
                [
                    Release(release.name, release.lifetime_start, releases_channels_map)
                    for release in releases
                ],
                repo.state,
            )

        tags = None
        repo_ref = RepositoryReference.for_repo_obj(repo)
        if include_tags:
            tags, _ = registry_model.list_repository_tag_history(
                repo_ref, page=1, size=max_tags, active_tags_only=True
            )
            tags = [
                Tag(
                    tag.name,
                    tag.manifest.legacy_image_root_id,
                    tag.manifest_layers_size,
                    tag.lifetime_start_ts,
                    tag.manifest_digest,
                    tag.lifetime_end_ts,
                )
                for tag in tags
            ]

        start_date = datetime.now() - timedelta(days=MAX_DAYS_IN_3_MONTHS)
        counts = model.log.get_repository_action_counts(repo, start_date)

        assert repo.state is not None
        return ImageRepositoryRepository(
            base,
            tags,
            [Count(count.date, count.count) for count in counts],
            repo.badge_token,
            repo.trust_enabled,
            repo.state,
        )


pre_oci_model = PreOCIModel()
