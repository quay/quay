from data.database import (
    ImageStorage,
    ManifestBlob,
    NamespaceSize,
    Repository,
    RepositorySize,
    Tag,
    User,
)

# optimizations
# - If there's only one repo in a namespace don't count it twice
def run_total(namespace: int, repository: int):

    print(
        "catdebug",
        "namespace",
        namespace,
        "repository",
        repository,
        "====================================================",
    )

    if namespace is None:
        try:
            repo = (
                Repository.select(Repository.namespace_user_id)
                .where(Repository.id == repository)
                .get()
            )
            namespace = repo.namespace_user_id
        except Repository.DoesNotExist:
            # TODO: should not happen
            pass

    # namespace
    if namespace is not None:
        lifetime_start = 0
        try:
            namespace_summed_until = (
                NamespaceSize.select(NamespaceSize.summed_until_ms)
                .where(NamespaceSize.namespace_user_id == namespace)
                .get()
            )
            lifetime_start = namespace_summed_until.summed_until_ms
            NamespaceSize.update(namespace_user_id=namespace, running=True).where(
                NamespaceSize.namespace_user_id == namespace
            ).execute()
        except NamespaceSize.DoesNotExist:
            NamespaceSize.insert(
                namespace_user_id=namespace, size_bytes=0, summed_until_ms=0, running=True
            ).execute()

        tag_ids = (
            Tag.select(Tag.id, Tag.lifetime_start_ms)
            .join(Repository, on=(Tag.repository == Repository.id))
            .where(
                Repository.namespace_user_id == namespace, Tag.lifetime_start_ms > lifetime_start
            )
            .order_by(Tag.lifetime_start_ms.asc())
        )

        tags_found = False
        for tag in tag_ids:
            tags_found = True
            # print('catdebug','namespace sum','Found new tag id ',tag.id,' for repo ',repository,' in namespace ', namespace)

            blobs = (
                ImageStorage.select(ImageStorage.id, ImageStorage.image_size)
                .join(ManifestBlob, on=(ManifestBlob.blob_id == ImageStorage.id))
                .join(Tag, on=(Tag.manifest == ManifestBlob.manifest))
                .where(Tag.id == tag.id)
            )

            for blob in blobs:
                uncounted_blob = True
                try:
                    (
                        ManifestBlob.select(ManifestBlob.blob_id)
                        .join(Tag, on=(Tag.manifest == ManifestBlob.manifest))
                        .join(Repository, on=(Tag.repository == Repository.id))
                        .where(
                            ManifestBlob.blob_id == blob.id,
                            Repository.namespace_user_id == namespace,
                            Tag.lifetime_start_ms < tag.lifetime_start_ms,
                        )
                        .limit(1)
                        .get()
                    )
                    uncounted_blob = False
                except ManifestBlob.DoesNotExist:
                    pass

                if uncounted_blob:
                    total_size = 0
                    exists = False
                    try:
                        namespace_size = (
                            NamespaceSize.select()
                            .where(NamespaceSize.namespace_user_id == namespace)
                            .get()
                        )
                        total_size = namespace_size.size_bytes
                        exists = True
                    except NamespaceSize.DoesNotExist:
                        pass

                    if exists:
                        NamespaceSize.update(
                            size_bytes=total_size + blob.image_size,
                            summed_until_ms=tag.lifetime_start_ms,
                        ).where(NamespaceSize.namespace_user_id == namespace).execute()
                    else:
                        NamespaceSize.insert(
                            namespace_user_id=namespace,
                            size_bytes=total_size + blob.image_size,
                            summed_until_ms=tag.lifetime_start_ms,
                        ).execute()
        if not tags_found:
            print(
                "catdebug",
                "namespace sum",
                "No new tags for repo ",
                repository,
                " in namespace ",
                namespace,
            )
        NamespaceSize.update(running=False).where(
            NamespaceSize.namespace_user_id == namespace
        ).execute()

    # repository
    if repository is not None:
        lifetime_start = 0
        try:
            repository_summed_until = (
                RepositorySize.select(RepositorySize.summed_until_ms)
                .where(RepositorySize.repository_id == repository)
                .get()
            )
            lifetime_start = repository_summed_until.summed_until_ms
            RepositorySize.update(repository_id=repository, running=True).where(
                RepositorySize.repository == repository
            ).execute()
        except RepositorySize.DoesNotExist:
            RepositorySize.insert(
                repository_id=repository, size_bytes=0, summed_until_ms=0, running=True
            ).execute()

        if lifetime_start is None:
            lifetime_start = 0

        tag_ids = (
            Tag.select(Tag.id, Tag.lifetime_start_ms, Tag.name)
            .where(Tag.lifetime_start_ms > lifetime_start, Tag.repository == repository)
            .order_by(Tag.lifetime_start_ms.asc())
        )

        tags_found = False
        for tag in tag_ids:
            tags_found = True
            # print('catdebug','repository sum','Found new tag id ',tag.id,' for repo ',repository,' in namespace ', namespace)
            blobs = (
                ImageStorage.select(ImageStorage.id, ImageStorage.image_size)
                .join(ManifestBlob, on=(ManifestBlob.blob_id == ImageStorage.id))
                .join(Tag, on=(Tag.manifest == ManifestBlob.manifest))
                .where(Tag.id == tag.id)
            )

            for blob in blobs:
                uncounted_blob = True
                try:
                    (
                        ManifestBlob.select(ManifestBlob.blob_id)
                        .join(Tag, on=(Tag.manifest == ManifestBlob.manifest))
                        .where(
                            ManifestBlob.blob_id == blob.id,
                            ManifestBlob.repository == repository,
                            Tag.lifetime_start_ms < tag.lifetime_start_ms,
                        )
                        .limit(1)
                        .get()
                    )
                    uncounted_blob = False
                except ManifestBlob.DoesNotExist:
                    pass

                if uncounted_blob:
                    total_size = 0
                    exists = False
                    try:
                        repository_size = (
                            RepositorySize.select()
                            .where(RepositorySize.repository_id == repository)
                            .get()
                        )
                        total_size = repository_size.size_bytes
                        exists = True
                    except RepositorySize.DoesNotExist:
                        pass

                    if exists:
                        RepositorySize.update(
                            size_bytes=total_size + blob.image_size,
                            summed_until_ms=tag.lifetime_start_ms,
                        ).where(RepositorySize.repository == repository).execute()
                    else:
                        RepositorySize.insert(
                            repository_id=repository,
                            size_bytes=total_size + blob.image_size,
                            summed_until_ms=tag.lifetime_start_ms,
                        ).execute()
        if not tags_found:
            print(
                "catdebug",
                "repository sum",
                "No new tags for repo ",
                repository,
                " in namespace ",
                namespace,
            )
        RepositorySize.update(running=False).where(
            RepositorySize.repository == repository
        ).execute()


# Attempt #2 recalculate sum each time
# Takes a very long time to run each time
# def total_namespace(namespace: int):
#     # Total namespace
#     derived_ns = (
#         ImageStorage.select(ImageStorage.image_size)
#         .join(ManifestBlob, on=(ImageStorage.id==ManifestBlob.blob))
#         .join(Repository, on=(Repository.id==ManifestBlob.repository))
#         .where(Repository.namespace_user_id==namespace)
#         .group_by(ImageStorage.id)
#     )

#     ns_total = ImageStorage.select(fn.Sum(derived_ns.c.image_size)).from_(derived_ns).scalar()
#     exists = True
#     try:
#         NamespaceSize.select().where(NamespaceSize.namespace_user_id==namespace).get()
#     except NamespaceSize.DoesNotExist:
#         exists = False

#     if ns_total is None:
#         ns_total = 0

#     if exists:
#         NamespaceSize.update(size_bytes=ns_total).where(NamespaceSize.namespace_user_id==namespace).execute()
#     else:
#         NamespaceSize.insert(namespace_user_id=namespace,size_bytes=ns_total).execute()

# def total_repository(repository: int):
#     # TODO: error handling on repo not found
#     repo = Repository.select().where(Repository.id==repository).get()
#     namespace = repo.namespace_user_id
#     total_namespace(namespace)

#     # Total repository
#     derived_repo = (
#         ImageStorage.select(ImageStorage.image_size)
#         .join(ManifestBlob, on=(ImageStorage.id==ManifestBlob.blob))
#         .where(ManifestBlob.repository==repository)
#         .group_by(ImageStorage.id)
#     )

#     repo_total = ImageStorage.select(fn.Sum(derived_repo.c.image_size)).from_(derived_repo).scalar()
#     exists = True
#     try:
#         RepositorySize.select().where(RepositorySize.repository_id==repository).get()
#     except RepositorySize.DoesNotExist:
#         exists = False

#     if repo_total is None:
#         repo_total = 0

#     if exists:
#         RepositorySize.update(size_bytes=repo_total).where(RepositorySize.repository_id==repository).execute()
#     else:
#         RepositorySize.insert(repository_id=repository, size_bytes=repo_total).execute()

# Attempt #1 loop through imagestorage table and bucket sums
# doesn't account for manifest created in repository that has already existing blobs - since it doens't pick up on blobs that already exist
# it doesn't re-run and get the total
# def run_total(batch_size: int):
#     # # # print("quaydebug","=================================================================================")
#     # # # print("quaydebug","starting to run total...")

#     # get start index
#     index = 0
#     quotaIndex = None
#     try:
#         quotaIndex = QuotaIndex.select().get()
#         index = quotaIndex.start_index
#     except QuotaIndex.DoesNotExist:
#         pass

#     # Get blob id and size via start index and batch size
#     last_blob = None
#     for blob in ImageStorage.select().where(ImageStorage.id >= index).order_by(ImageStorage.id, ImageStorage.id.asc()).limit(batch_size):
#         # # # print("quaydebug","blob",blob)
#         namespaces = []
#         repos = []
#         # For each blob get the namespace and repository id's that they belong too
#         for ns_repository in Repository.select(Repository.id,Repository.namespace_user).join(ManifestBlob, on=(ManifestBlob.repository==Repository.id)).where(ManifestBlob.blob==blob):
#             namespaces.append(ns_repository.namespace_user)
#             repos.append(ns_repository.id)


#         # Get the current size of the namespace and repository, 0 if they don't exist
#         # Add the new sum and write it back out
#         for ns in set(namespaces):
#             # # # print("quaydebug","ns",ns)
#             currentSize = 0
#             exists = True
#             try:
#                 nsSizeEntry = NamespaceSize.select().where(NamespaceSize.namespace_user_id==ns).get()
#                 currentSize = nsSizeEntry.size_bytes
#             except NamespaceSize.DoesNotExist:
#                 exists = False

#             if exists:
#                 NamespaceSize.update(size_bytes=currentSize+blob.image_size).where(NamespaceSize.namespace_user_id==ns).execute()
#             else:
#                 NamespaceSize.insert(namespace_user_id=ns,size_bytes=currentSize+blob.image_size).execute()


#         for repo in set(repos):
#             # # # print("quaydebug","repo",repo)
#             currentSize = 0
#             exists = True
#             try:
#                 repoSizeEntry = RepositorySize.select().where(RepositorySize.repository==repo).get()
#                 currentSize = repoSizeEntry.size_bytes
#             except RepositorySize.DoesNotExist:
#                 exists = False

#             if exists:
#                 RepositorySize.update(size_bytes=currentSize+blob.image_size).where(RepositorySize.repository==repo).execute()
#             else:
#                 RepositorySize.insert(repository=repo,size_bytes=currentSize+blob.image_size).execute()

#         last_blob = blob

#     # increment start index
#     # # # print("quaydebug","new start index",last_blob.id+1)
#     if last_blob is not None:
#         if quotaIndex is not None:
#             quotaIndex.start_index = last_blob.id+1
#             quotaIndex.save()
#         else:
#             QuotaIndex.insert(start_index=last_blob.id+1).execute()
#     else:
#         # # print("No blobs found")
#     # # # print("quaydebug","=================================================================================")
