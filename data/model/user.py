import bcrypt
import logging
import json
import uuid
from flask_login import UserMixin

from peewee import JOIN, IntegrityError, fn
from uuid import uuid4
from datetime import datetime, timedelta

from data.database import (
    User,
    LoginService,
    FederatedLogin,
    RepositoryPermission,
    TeamMember,
    Team,
    Repository,
    RepositoryState,
    TupleSelector,
    TeamRole,
    Namespace,
    Visibility,
    EmailConfirmation,
    Role,
    db_for_update,
    random_string_generator,
    UserRegion,
    ImageStorageLocation,
    ServiceKeyApproval,
    OAuthApplication,
    RepositoryBuildTrigger,
    UserPromptKind,
    UserPrompt,
    UserPromptTypes,
    DeletedNamespace,
    RobotAccountMetadata,
    NamespaceGeoRestriction,
    RepoMirrorConfig,
    RobotAccountToken,
)
from data.readreplica import ReadOnlyModeException
from data.model import (
    DataModelException,
    InvalidPasswordException,
    InvalidRobotException,
    InvalidUsernameException,
    InvalidEmailAddressException,
    TooManyLoginAttemptsException,
    db_transaction,
    notification,
    config,
    repository,
    _basequery,
    gc,
)
from data.fields import Credential
from data.text import prefix_search
from util.names import format_robot_username, parse_robot_username
from util.validation import (
    validate_username,
    validate_email,
    validate_password,
    INVALID_PASSWORD_MESSAGE,
)
from util.backoff import exponential_backoff
from util.timedeltastring import convert_to_timedelta
from util.bytes import Bytes
from util.unicode import remove_unicode
from util.security.token import decode_public_private_token, encode_public_private_token


logger = logging.getLogger(__name__)


EXPONENTIAL_BACKOFF_SCALE = timedelta(seconds=1)


def hash_password(password, salt=None):
    salt = salt or bcrypt.gensalt()
    salt = Bytes.for_string_or_unicode(salt).as_encoded_str()
    return bcrypt.hashpw(password.encode("utf-8"), salt)


def create_user(
    username,
    password,
    email,
    auto_verify=False,
    email_required=True,
    prompts=tuple(),
    is_possible_abuser=False,
):
    """
    Creates a regular user, if allowed.
    """
    if not validate_password(password):
        raise InvalidPasswordException(INVALID_PASSWORD_MESSAGE)

    created = create_user_noverify(
        username,
        email,
        email_required=email_required,
        prompts=prompts,
        is_possible_abuser=is_possible_abuser,
    )
    created.password_hash = hash_password(password).decode("ascii")
    created.verified = auto_verify
    created.save()

    return created


def create_user_noverify(
    username, email, email_required=True, prompts=tuple(), is_possible_abuser=False
):
    if email_required:
        if not validate_email(email):
            raise InvalidEmailAddressException("Invalid email address: %s" % email)
    else:
        # If email addresses are not required and none was specified, then we just use a unique
        # ID to ensure that the database consistency check remains intact.
        email = email or str(uuid.uuid4())

    (username_valid, username_issue) = validate_username(username)
    if not username_valid:
        raise InvalidUsernameException("Invalid namespace %s: %s" % (username, username_issue))

    try:
        existing = User.get((User.username == username) | (User.email == email))
        logger.debug("Existing user with same username or email.")

        # A user already exists with either the same username or email
        if existing.username == username:
            assert not existing.robot

            msg = (
                "Username has already been taken by an organization and cannot be reused: %s"
                % username
            )
            if not existing.organization:
                msg = "Username has already been taken by user cannot be reused: %s" % username

            raise InvalidUsernameException(msg)

        raise InvalidEmailAddressException("Email has already been used: %s" % email)
    except User.DoesNotExist:
        # This is actually the happy path
        logger.debug("Email and username are unique!")

    # Create the user.
    try:
        default_expr_s = _convert_to_s(config.app_config["DEFAULT_TAG_EXPIRATION"])
        default_max_builds = config.app_config.get("DEFAULT_NAMESPACE_MAXIMUM_BUILD_COUNT")
        threat_max_builds = config.app_config.get("THREAT_NAMESPACE_MAXIMUM_BUILD_COUNT")

        if is_possible_abuser and threat_max_builds is not None:
            default_max_builds = threat_max_builds

        new_user = User.create(
            username=username,
            email=email,
            removed_tag_expiration_s=default_expr_s,
            maximum_queued_builds_count=default_max_builds,
        )
        for prompt in prompts:
            create_user_prompt(new_user, prompt)

        return new_user
    except Exception as ex:
        raise DataModelException(ex)


def increase_maximum_build_count(user, maximum_queued_builds_count):
    """
    Increases the maximum number of allowed builds on the namespace, if greater than that already
    present.
    """
    if (
        user.maximum_queued_builds_count is not None
        and maximum_queued_builds_count > user.maximum_queued_builds_count
    ):
        user.maximum_queued_builds_count = maximum_queued_builds_count
        user.save()


def is_username_unique(test_username):
    try:
        User.get((User.username == test_username))
        return False
    except User.DoesNotExist:
        return True


def change_password(user, new_password):
    if not validate_password(new_password):
        raise InvalidPasswordException(INVALID_PASSWORD_MESSAGE)

    pw_hash = hash_password(new_password)
    user.invalid_login_attempts = 0
    user.password_hash = pw_hash.decode("ascii")
    invalidate_all_sessions(user)

    # Remove any password required notifications for the user.
    notification.delete_notifications_by_kind(user, "password_required")


def get_default_user_prompts(features):
    prompts = set()
    if features.USER_METADATA:
        prompts.add(UserPromptTypes.ENTER_NAME)
        prompts.add(UserPromptTypes.ENTER_COMPANY)

    return prompts


def has_user_prompts(user):
    try:
        UserPrompt.select().where(UserPrompt.user == user).get()
        return True
    except UserPrompt.DoesNotExist:
        return False


def has_user_prompt(user, prompt_name):
    prompt_kind = UserPromptKind.get(name=prompt_name)

    try:
        UserPrompt.get(user=user, kind=prompt_kind)
        return True
    except UserPrompt.DoesNotExist:
        return False


def create_user_prompt(user, prompt_name):
    prompt_kind = UserPromptKind.get(name=prompt_name)
    return UserPrompt.create(user=user, kind=prompt_kind)


def remove_user_prompt(user, prompt_name):
    prompt_kind = UserPromptKind.get(name=prompt_name)
    UserPrompt.delete().where(UserPrompt.user == user, UserPrompt.kind == prompt_kind).execute()


def get_user_prompts(user):
    query = UserPrompt.select().where(UserPrompt.user == user).join(UserPromptKind)
    return [prompt.kind.name for prompt in query]


def change_username(user_id, new_username):
    (username_valid, username_issue) = validate_username(new_username)
    if not username_valid:
        raise InvalidUsernameException("Invalid username %s: %s" % (new_username, username_issue))

    with db_transaction():
        # Reload the user for update
        user = db_for_update(User.select().where(User.id == user_id)).get()

        # Rename the robots
        for robot in db_for_update(
            _list_entity_robots(user.username, include_metadata=False, include_token=False)
        ):
            _, robot_shortname = parse_robot_username(robot.username)
            new_robot_name = format_robot_username(new_username, robot_shortname)
            robot.username = new_robot_name
            robot.save()

        # Rename the user
        user.username = new_username
        user.save()

        # Remove any prompts for username.
        remove_user_prompt(user, "confirm_username")

        return user


def change_invoice_email_address(user, invoice_email_address):
    # Note: We null out the address if it is an empty string.
    user.invoice_email_address = invoice_email_address or None
    user.save()


def change_send_invoice_email(user, invoice_email):
    user.invoice_email = invoice_email
    user.save()


def _convert_to_s(timespan_string):
    """
    Returns the given timespan string (e.g. `2w` or `45s`) into seconds.
    """
    return convert_to_timedelta(timespan_string).total_seconds()


def change_user_tag_expiration(user, tag_expiration_s):
    """
    Changes the tag expiration on the given user/org.

    Note that the specified expiration must be within the configured TAG_EXPIRATION_OPTIONS or this
    method will raise a DataModelException.
    """
    allowed_options = [_convert_to_s(o) for o in config.app_config["TAG_EXPIRATION_OPTIONS"]]
    if tag_expiration_s not in allowed_options:
        raise DataModelException("Invalid tag expiration option")

    user.removed_tag_expiration_s = tag_expiration_s
    user.save()


def update_email(user, new_email, auto_verify=False):
    try:
        user.email = new_email
        user.verified = auto_verify
        user.save()
    except IntegrityError:
        raise DataModelException("E-mail address already used")


def update_enabled(user, set_enabled):
    user.enabled = set_enabled
    user.save()


def create_robot(robot_shortname, parent, description="", unstructured_metadata=None):
    (username_valid, username_issue) = validate_username(robot_shortname)
    if not username_valid:
        raise InvalidRobotException(
            "The name for the robot '%s' is invalid: %s" % (robot_shortname, username_issue)
        )

    username = format_robot_username(parent.username, robot_shortname)

    try:
        User.get(User.username == username)

        msg = "Existing robot with name: %s" % username
        logger.debug(msg)
        raise InvalidRobotException(msg)
    except User.DoesNotExist:
        pass

    service = LoginService.get(name="quayrobot")
    try:
        with db_transaction():
            created = User.create(username=username, email=str(uuid.uuid4()), robot=True)
            token = random_string_generator(length=64)()
            RobotAccountToken.create(robot_account=created, token=token, fully_migrated=True)
            FederatedLogin.create(
                user=created, service=service, service_ident="robot:%s" % created.id
            )
            RobotAccountMetadata.create(
                robot_account=created,
                description=description[0:255],
                unstructured_json=unstructured_metadata or {},
            )
            return created, token
    except Exception as ex:
        raise DataModelException(ex)


def get_or_create_robot_metadata(robot):
    defaults = dict(description="", unstructured_json={})
    metadata, _ = RobotAccountMetadata.get_or_create(robot_account=robot, defaults=defaults)
    return metadata


def update_robot_metadata(robot, description="", unstructured_json=None):
    """
    Updates the description and user-specified unstructured metadata associated with a robot account
    to that specified.
    """
    metadata = get_or_create_robot_metadata(robot)
    metadata.description = description
    metadata.unstructured_json = unstructured_json or metadata.unstructured_json or {}
    metadata.save()


def retrieve_robot_token(robot):
    """
    Returns the decrypted token for the given robot.
    """
    token = RobotAccountToken.get(robot_account=robot).token.decrypt()
    return token


def get_robot_and_metadata(robot_shortname, parent):
    """
    Returns a tuple of the robot matching the given shortname, its token, and its metadata.
    """
    robot_username = format_robot_username(parent.username, robot_shortname)
    robot, metadata = lookup_robot_and_metadata(robot_username)
    token = retrieve_robot_token(robot)
    return robot, token, metadata


def lookup_robot(robot_username):
    try:
        robot_username.encode("ascii")
    except UnicodeEncodeError:
        raise InvalidRobotException("Could not find robot with specified username")

    try:
        return User.get(username=robot_username, robot=True)
    except User.DoesNotExist:
        raise InvalidRobotException("Could not find robot with specified username")


def lookup_robot_and_metadata(robot_username):
    robot = lookup_robot(robot_username)
    return robot, get_or_create_robot_metadata(robot)


def get_matching_robots(name_prefix, username, limit=10):
    admined_orgs = (
        _basequery.get_user_organizations(username)
        .switch(Team)
        .join(TeamRole)
        .where(TeamRole.name == "admin")
    )

    prefix_checks = False

    for org in admined_orgs:
        org_search = prefix_search(User.username, org.username + "+" + name_prefix)
        prefix_checks = prefix_checks | org_search

    user_search = prefix_search(User.username, username + "+" + name_prefix)
    prefix_checks = prefix_checks | user_search

    return User.select().where(prefix_checks).limit(limit)


def verify_robot(robot_username, password):
    try:
        password.encode("ascii")
    except UnicodeEncodeError:
        msg = "Could not find robot with username: %s and supplied password." % robot_username
        raise InvalidRobotException(msg)

    result = parse_robot_username(robot_username)
    if result is None:
        raise InvalidRobotException("%s is an invalid robot name" % robot_username)

    robot = lookup_robot(robot_username)
    assert robot.robot

    # Lookup the token for the robot.
    try:
        token_data = RobotAccountToken.get(robot_account=robot)
        if not token_data.token.matches(password):
            msg = "Could not find robot with username: %s and supplied password." % robot_username
            raise InvalidRobotException(msg)
    except RobotAccountToken.DoesNotExist:
        msg = "Could not find robot with username: %s and supplied password." % robot_username
        raise InvalidRobotException(msg)

    # Find the owner user and ensure it is not disabled.
    try:
        owner = User.get(User.username == result[0])
    except User.DoesNotExist:
        raise InvalidRobotException("Robot %s owner does not exist" % robot_username)

    if not owner.enabled:
        raise InvalidRobotException(
            "This user has been disabled. Please contact your administrator."
        )

    # Mark that the robot was accessed.
    _basequery.update_last_accessed(robot)

    return robot


def regenerate_robot_token(robot_shortname, parent):
    robot_username = format_robot_username(parent.username, robot_shortname)

    robot, metadata = lookup_robot_and_metadata(robot_username)
    password = random_string_generator(length=64)()
    robot.email = str(uuid4())
    robot.uuid = str(uuid4())

    service = LoginService.get(name="quayrobot")
    login = FederatedLogin.get(FederatedLogin.user == robot, FederatedLogin.service == service)
    login.service_ident = "robot:%s" % (robot.id)

    try:
        token_data = RobotAccountToken.get(robot_account=robot)
    except RobotAccountToken.DoesNotExist:
        token_data = RobotAccountToken.create(robot_account=robot)

    token_data.token = password

    with db_transaction():
        token_data.save()
        login.save()
        robot.save()

    return robot, password, metadata


def delete_robot(robot_username):
    try:
        robot = User.get(username=robot_username, robot=True)
        robot.delete_instance(recursive=True, delete_nullable=True)

    except User.DoesNotExist:
        raise InvalidRobotException("Could not find robot with username: %s" % robot_username)

    except IntegrityError:
        DataModelException("Could not delete robot with username: %s" % robot_username)


def list_namespace_robots(namespace):
    """
    Returns all the robots found under the given namespace.
    """
    return _list_entity_robots(namespace)


def _list_entity_robots(entity_name, include_metadata=True, include_token=True):
    """
    Return the list of robots for the specified entity.

    This MUST return a query, not a materialized list so that callers can use db_for_update.
    """
    if include_metadata or include_token:
        query = (
            User.select(User, RobotAccountToken, RobotAccountMetadata)
            .join(RobotAccountMetadata, JOIN.LEFT_OUTER)
            .switch(User)
            .join(RobotAccountToken)
            .where(User.robot == True, User.username ** (entity_name + "+%"))
        )
    else:
        query = User.select(User).where(User.robot == True, User.username ** (entity_name + "+%"))

    return query


def list_entity_robot_permission_teams(entity_name, limit=None, include_permissions=False):
    query = _list_entity_robots(entity_name)

    fields = [
        User.username,
        User.creation_date,
        User.last_accessed,
        RobotAccountToken.token,
        RobotAccountMetadata.description,
        RobotAccountMetadata.unstructured_json,
    ]
    if include_permissions:
        query = (
            query.join(
                RepositoryPermission,
                JOIN.LEFT_OUTER,
                on=(RepositoryPermission.user == RobotAccountToken.robot_account),
            )
            .join(Repository, JOIN.LEFT_OUTER)
            .switch(User)
            .join(TeamMember, JOIN.LEFT_OUTER)
            .join(Team, JOIN.LEFT_OUTER)
        )

        fields.append(Repository.name)
        fields.append(Team.name)

    query = query.limit(limit).order_by(User.last_accessed.desc())
    return TupleSelector(query, fields)


def update_user_metadata(user, metadata=None):
    """
    Updates the metadata associated with the user, including his/her name and company.
    """
    metadata = metadata if metadata is not None else {}

    with db_transaction():
        if "given_name" in metadata:
            user.given_name = metadata["given_name"]

        if "family_name" in metadata:
            user.family_name = metadata["family_name"]

        if "company" in metadata:
            user.company = metadata["company"]

        if "location" in metadata:
            user.location = metadata["location"]

        user.save()

        # Remove any prompts associated with the user's metadata being needed.
        remove_user_prompt(user, UserPromptTypes.ENTER_NAME)
        remove_user_prompt(user, UserPromptTypes.ENTER_COMPANY)


def _get_login_service(service_id):
    try:
        return LoginService.get(LoginService.name == service_id)
    except LoginService.DoesNotExist:
        return LoginService.create(name=service_id)


def create_federated_user(
    username,
    email,
    service_id,
    service_ident,
    set_password_notification,
    metadata={},
    email_required=True,
    confirm_username=True,
    prompts=tuple(),
):
    prompts = set(prompts)

    if confirm_username:
        prompts.add(UserPromptTypes.CONFIRM_USERNAME)

    new_user = create_user_noverify(username, email, email_required=email_required, prompts=prompts)
    new_user.verified = True
    new_user.save()

    FederatedLogin.create(
        user=new_user,
        service=_get_login_service(service_id),
        service_ident=service_ident,
        metadata_json=json.dumps(metadata),
    )

    if set_password_notification:
        notification.create_notification("password_required", new_user)

    return new_user


def attach_federated_login(user, service_id, service_ident, metadata=None):
    service = _get_login_service(service_id)
    FederatedLogin.create(
        user=user,
        service=service,
        service_ident=service_ident,
        metadata_json=json.dumps(metadata or {}),
    )
    return user


def verify_federated_login(service_id, service_ident):
    try:
        found = (
            FederatedLogin.select(FederatedLogin, User)
            .join(LoginService)
            .switch(FederatedLogin)
            .join(User)
            .where(FederatedLogin.service_ident == service_ident, LoginService.name == service_id)
            .get()
        )

        # Mark that the user was accessed.
        _basequery.update_last_accessed(found.user)

        return found.user
    except FederatedLogin.DoesNotExist:
        return None


def list_federated_logins(user):
    selected = FederatedLogin.select(
        FederatedLogin.service_ident, LoginService.name, FederatedLogin.metadata_json
    )
    joined = selected.join(LoginService)
    return joined.where(LoginService.name != "quayrobot", FederatedLogin.user == user)


def lookup_federated_login(user, service_name):
    try:
        return list_federated_logins(user).where(LoginService.name == service_name).get()
    except FederatedLogin.DoesNotExist:
        return None


def create_confirm_email_code(user, new_email=None):
    if new_email:
        if not validate_email(new_email):
            raise InvalidEmailAddressException("Invalid email address: %s" % new_email)

    verification_code, unhashed = Credential.generate()
    code = EmailConfirmation.create(
        user=user, email_confirm=True, new_email=new_email, verification_code=verification_code
    )
    return encode_public_private_token(code.code, unhashed)


def confirm_user_email(token):
    result = decode_public_private_token(token)
    if not result:
        raise DataModelException("Invalid email confirmation code")

    try:
        code = EmailConfirmation.get(
            EmailConfirmation.code == result.public_code, EmailConfirmation.email_confirm == True
        )
    except EmailConfirmation.DoesNotExist:
        raise DataModelException("Invalid email confirmation code")

    if result.private_token and not code.verification_code.matches(result.private_token):
        raise DataModelException("Invalid email confirmation code")

    user = code.user
    user.verified = True

    old_email = None
    new_email = code.new_email
    if new_email and new_email != old_email:
        if find_user_by_email(new_email):
            raise DataModelException("E-mail address already used")

        old_email = user.email
        user.email = new_email

    with db_transaction():
        user.save()
        code.delete_instance()

    return user, new_email, old_email


def create_reset_password_email_code(email):
    try:
        user = User.get(User.email == email)
    except User.DoesNotExist:
        raise InvalidEmailAddressException("Email address was not found")

    if user.organization:
        raise InvalidEmailAddressException("Organizations can not have passwords")

    verification_code, unhashed = Credential.generate()
    code = EmailConfirmation.create(user=user, pw_reset=True, verification_code=verification_code)
    return encode_public_private_token(code.code, unhashed)


def validate_reset_code(token):
    result = decode_public_private_token(token)
    if not result:
        return None

    # Find the reset code.
    try:
        code = EmailConfirmation.get(
            EmailConfirmation.code == result.public_code, EmailConfirmation.pw_reset == True
        )
    except EmailConfirmation.DoesNotExist:
        return None

    if result.private_token and not code.verification_code.matches(result.private_token):
        return None

    # Make sure the code is not expired.
    max_lifetime_duration = convert_to_timedelta(config.app_config["USER_RECOVERY_TOKEN_LIFETIME"])
    if code.created + max_lifetime_duration < datetime.now():
        code.delete_instance()
        return None

    # Verify the user and return the code.
    user = code.user

    with db_transaction():
        if not user.verified:
            user.verified = True
            user.save()

        code.delete_instance()

    return user


def find_user_by_email(email):
    try:
        return User.get(User.email == email)
    except User.DoesNotExist:
        return None


def get_nonrobot_user(username):
    try:
        return User.get(User.username == username, User.organization == False, User.robot == False)
    except User.DoesNotExist:
        return None


def get_user(username):
    try:
        return User.get(User.username == username, User.organization == False)
    except User.DoesNotExist:
        return None


def get_namespace_user(username):
    try:
        return User.get(User.username == username)
    except User.DoesNotExist:
        return None


def get_user_or_org(username):
    try:
        return User.get(User.username == username, User.robot == False)
    except User.DoesNotExist:
        return None


def get_user_by_id(user_db_id):
    try:
        return User.get(User.id == user_db_id, User.organization == False)
    except User.DoesNotExist:
        return None


def get_user_map_by_ids(namespace_ids):
    id_user = {namespace_id: None for namespace_id in namespace_ids}
    users = User.select().where(User.id << namespace_ids, User.organization == False)
    for user in users:
        id_user[user.id] = user

    return id_user


def get_namespace_user_by_user_id(namespace_user_db_id):
    try:
        return User.get(User.id == namespace_user_db_id, User.robot == False)
    except User.DoesNotExist:
        raise InvalidUsernameException("User with id does not exist: %s" % namespace_user_db_id)


def get_namespace_by_user_id(namespace_user_db_id):
    try:
        return User.get(User.id == namespace_user_db_id, User.robot == False).username
    except User.DoesNotExist:
        raise InvalidUsernameException("User with id does not exist: %s" % namespace_user_db_id)


def get_user_by_uuid(user_uuid):
    try:
        return User.get(User.uuid == user_uuid, User.organization == False)
    except User.DoesNotExist:
        return None


def get_user_or_org_by_customer_id(customer_id):
    try:
        return User.get(User.stripe_id == customer_id)
    except User.DoesNotExist:
        return None


def invalidate_all_sessions(user):
    """
    Invalidates all existing user sessions by rotating the user's UUID.
    """
    if not user:
        return

    user.uuid = str(uuid4())
    user.save()


def get_matching_user_namespaces(namespace_prefix, username, limit=10):
    namespace_user = get_namespace_user(username)
    namespace_user_id = namespace_user.id if namespace_user is not None else None

    namespace_search = prefix_search(Namespace.username, namespace_prefix)
    base_query = (
        Namespace.select()
        .distinct()
        .join(Repository, on=(Repository.namespace_user == Namespace.id))
        .join(RepositoryPermission, JOIN.LEFT_OUTER)
        .where(namespace_search)
    )

    return _basequery.filter_to_repos_for_user(base_query, namespace_user_id).limit(limit)


def get_matching_users(
    username_prefix, robot_namespace=None, organization=None, limit=20, exact_matches_only=False
):
    # Lookup the exact match first. This ensures that the exact match is not cut off by the list
    # limit.
    updated_limit = limit
    exact_match = list(
        _get_matching_users(
            username_prefix, robot_namespace, organization, limit=1, exact_matches_only=True
        )
    )
    if exact_match:
        updated_limit -= 1
        yield exact_match[0]

    # Perform the remainder of the lookup.
    if updated_limit:
        for result in _get_matching_users(
            username_prefix, robot_namespace, organization, updated_limit, exact_matches_only
        ):
            if exact_match and result.username == exact_match[0].username:
                continue

            yield result


def _get_matching_users(
    username_prefix, robot_namespace=None, organization=None, limit=20, exact_matches_only=False
):
    user_search = prefix_search(User.username, username_prefix)
    if exact_matches_only:
        user_search = User.username == username_prefix

    direct_user_query = user_search & (User.organization == False) & (User.robot == False)

    if robot_namespace:
        robot_prefix = format_robot_username(robot_namespace, username_prefix)
        robot_search = prefix_search(User.username, robot_prefix)
        direct_user_query = (robot_search & (User.robot == True)) | direct_user_query

    query = (
        User.select(User.id, User.username, User.email, User.robot)
        .group_by(User.id, User.username, User.email, User.robot)
        .where(direct_user_query)
    )

    if organization:
        query = (
            query.select(User.id, User.username, User.email, User.robot, fn.Sum(Team.id))
            .join(TeamMember, JOIN.LEFT_OUTER)
            .join(
                Team,
                JOIN.LEFT_OUTER,
                on=((Team.id == TeamMember.team) & (Team.organization == organization)),
            )
            .order_by(User.robot.desc())
        )

    class MatchingUserResult(object):
        def __init__(self, *args):
            self.id = args[0]
            self.username = args[1]
            self.email = args[2]
            self.robot = args[3]

            if organization:
                self.is_org_member = args[3] != None
            else:
                self.is_org_member = None

    return (MatchingUserResult(*args) for args in query.tuples().limit(limit))


def verify_user(username_or_email, password):
    """
    Verifies that the given username/email + password pair is valid.

    If the username or e-mail address is invalid, returns None. If the password specified does not
    match for the given user, either returns None or raises TooManyLoginAttemptsException if there
    have been too many invalid login attempts. Returns the user object if the login was valid.
    """

    # Make sure we didn't get any unicode for the username.
    try:
        username_or_email.encode("ascii")
    except UnicodeEncodeError:
        return None

    # Fetch the user with the matching username or e-mail address.
    try:
        fetched = User.get((User.username == username_or_email) | (User.email == username_or_email))
    except User.DoesNotExist:
        return None

    # If the user has any invalid login attempts, check to see if we are within the exponential
    # backoff window for the user. If so, we raise an exception indicating that the user cannot
    # login.
    now = datetime.utcnow()
    if fetched.invalid_login_attempts > 0:
        can_retry_at = exponential_backoff(
            fetched.invalid_login_attempts, EXPONENTIAL_BACKOFF_SCALE, fetched.last_invalid_login
        )

        if can_retry_at > now:
            retry_after = can_retry_at - now
            raise TooManyLoginAttemptsException(
                "Too many login attempts.", retry_after.total_seconds()
            )

    # Hash the given password and compare it to the specified password.
    if (
        fetched.password_hash
        and hash_password(password, fetched.password_hash).decode("ascii") == fetched.password_hash
    ):
        # If the user previously had any invalid login attempts, clear them out now.
        if fetched.invalid_login_attempts > 0:
            try:
                (User.update(invalid_login_attempts=0).where(User.id == fetched.id).execute())

                # Mark that the user was accessed.
                _basequery.update_last_accessed(fetched)
            except ReadOnlyModeException:
                pass

        # Return the valid user.
        return fetched

    # Otherwise, update the user's invalid login attempts.
    try:
        (
            User.update(
                invalid_login_attempts=User.invalid_login_attempts + 1, last_invalid_login=now
            )
            .where(User.id == fetched.id)
            .execute()
        )
    except ReadOnlyModeException:
        pass

    # We weren't able to authorize the user
    return None


def get_all_repo_users(namespace_name, repository_name):
    return (
        RepositoryPermission.select(User, Role, RepositoryPermission)
        .join(User)
        .switch(RepositoryPermission)
        .join(Role)
        .switch(RepositoryPermission)
        .join(Repository)
        .join(Namespace, on=(Repository.namespace_user == Namespace.id))
        .where(Namespace.username == namespace_name, Repository.name == repository_name)
    )


def get_all_repo_users_transitive_via_teams(namespace_name, repository_name):
    return (
        User.select()
        .distinct()
        .join(TeamMember)
        .join(Team)
        .join(RepositoryPermission)
        .join(Repository)
        .join(Namespace, on=(Repository.namespace_user == Namespace.id))
        .where(Namespace.username == namespace_name, Repository.name == repository_name)
    )


def get_all_repo_users_transitive(namespace_name, repository_name):
    # Load the users found via teams and directly via permissions.
    via_teams = get_all_repo_users_transitive_via_teams(namespace_name, repository_name)
    directly = [perm.user for perm in get_all_repo_users(namespace_name, repository_name)]

    # Filter duplicates.
    user_set = set()

    def check_add(u):
        if u.username in user_set:
            return False

        user_set.add(u.username)
        return True

    return [user for user in list(directly) + list(via_teams) if check_add(user)]


def get_private_repo_count(username):
    return (
        Repository.select()
        .join(Visibility)
        .switch(Repository)
        .join(Namespace, on=(Repository.namespace_user == Namespace.id))
        .where(Namespace.username == username, Visibility.name == "private")
        .where(Repository.state != RepositoryState.MARKED_FOR_DELETION)
        .count()
    )


def get_active_users(disabled=True, deleted=False):
    query = User.select().where(User.organization == False, User.robot == False)

    if not disabled:
        query = query.where(User.enabled == True)
    else:
        # NOTE: Deleted users are already disabled, so we don't need this extra check.
        if not deleted:
            query = query.where(User.id.not_in(DeletedNamespace.select(DeletedNamespace.namespace)))

    return query


def get_active_user_count():
    return get_active_users().count()


def get_estimated_robot_count():
    return _basequery.estimated_row_count(RobotAccountToken)


def detach_external_login(user, service_name):
    try:
        service = LoginService.get(name=service_name)
    except LoginService.DoesNotExist:
        return

    FederatedLogin.delete().where(
        FederatedLogin.user == user, FederatedLogin.service == service
    ).execute()


def get_solely_admined_organizations(user_obj):
    """
    Returns the organizations admined solely by the given user.
    """
    orgs = (
        User.select()
        .where(User.organization == True)
        .join(Team)
        .join(TeamRole)
        .where(TeamRole.name == "admin")
        .switch(Team)
        .join(TeamMember)
        .where(TeamMember.user == user_obj)
        .distinct()
    )

    # Filter to organizations where the user is the sole admin.
    solely_admined = []
    for org in orgs:
        admin_user_count = (
            TeamMember.select()
            .join(Team)
            .join(TeamRole)
            .where(Team.organization == org, TeamRole.name == "admin")
            .switch(TeamMember)
            .join(User)
            .where(User.robot == False)
            .distinct()
            .count()
        )

        if admin_user_count == 1:
            solely_admined.append(org)

    return solely_admined


def mark_namespace_for_deletion(user, queues, namespace_gc_queue, force=False):
    """
    Marks a namespace (as referenced by the given user) for deletion.

    A queue item will be added to delete the namespace's repositories and storage, while the
    namespace itself will be renamed, disabled, and delinked from other tables.
    """
    if not user.enabled:
        return None

    if not force and not user.organization:
        # Ensure that the user is not the sole admin for any organizations. If so, then the user
        # cannot be deleted before those organizations are deleted or reassigned.
        organizations = get_solely_admined_organizations(user)
        if len(organizations) > 0:
            message = (
                "Cannot delete %s as you are the only admin for organizations: " % user.username
            )
            for index, org in enumerate(organizations):
                if index > 0:
                    message = message + ", "

                message = message + org.username

            raise DataModelException(message)

    # Delete all queue items for the user.
    for queue in queues:
        queue.delete_namespaced_items(user.username)

    # Delete non-repository related items. This operation is very quick, so we can do so here.
    _delete_user_linked_data(user)

    with db_transaction():
        original_username = user.username
        user = db_for_update(User.select().where(User.id == user.id)).get()

        # Mark the namespace as deleted and ready for GC.
        try:
            marker = DeletedNamespace.create(
                namespace=user, original_username=original_username, original_email=user.email
            )
        except IntegrityError:
            return

        # Disable the namespace itself, and replace its various unique fields with UUIDs.
        user.enabled = False
        user.username = str(uuid4())
        user.email = str(uuid4())
        user.save()

    # Add a queueitem to delete the namespace.
    marker.queue_id = namespace_gc_queue.put(
        [str(user.id)],
        json.dumps(
            {
                "marker_id": marker.id,
                "original_username": original_username,
            }
        ),
    )
    marker.save()
    return marker.id


def delete_namespace_via_marker(marker_id, queues):
    """
    Deletes a namespace referenced by the given DeletedNamespace marker ID.
    """
    try:
        marker = DeletedNamespace.get(id=marker_id)
    except DeletedNamespace.DoesNotExist:
        return True

    return delete_user(marker.namespace, queues)


def delete_user(user, queues):
    """
    Deletes a user/organization/robot.

    Should *not* be called by any user-facing API. Instead, mark_namespace_for_deletion should be
    used, and the queue should call this method.

    Returns True on success and False otherwise.
    """
    # Ensure the user is disabled before beginning the deletion process.
    if user.enabled:
        user.enabled = False
        user.save()

    # Delete all queue items for the user.
    for queue in queues:
        queue.delete_namespaced_items(user.username)

    # Delete any repositories under the user's namespace.
    while True:
        is_progressing = False
        repositories = list(Repository.select().where(Repository.namespace_user == user))
        if not repositories:
            break

        for repo in repositories:
            if gc.purge_repository(repo, force=True):
                is_progressing = True

        if not is_progressing:
            return False

    # Delete non-repository related items.
    _delete_user_linked_data(user)

    # Delete the user itself.
    try:
        user.delete_instance(recursive=True, delete_nullable=True)
        return True
    except IntegrityError:
        return False


def _delete_user_linked_data(user):
    if user.organization:
        # Delete the organization's teams.
        with db_transaction():
            for team in Team.select().where(Team.organization == user):
                team.delete_instance(recursive=True)

        # Delete any OAuth approvals and tokens associated with the user.
        with db_transaction():
            for app in OAuthApplication.select().where(OAuthApplication.organization == user):
                app.delete_instance(recursive=True)
    else:
        # Remove the user from any teams in which they are a member.
        TeamMember.delete().where(TeamMember.user == user).execute()

    # Delete any repository buildtriggers where the user is the connected user.
    with db_transaction():
        triggers = RepositoryBuildTrigger.select().where(
            RepositoryBuildTrigger.connected_user == user
        )
        for trigger in triggers:
            trigger.delete_instance(recursive=True, delete_nullable=False)

    # Delete any mirrors with robots owned by this user.
    with db_transaction():
        robots = list(list_namespace_robots(user.username))
        RepoMirrorConfig.delete().where(RepoMirrorConfig.internal_robot << robots).execute()

    # Delete any robots owned by this user.
    with db_transaction():
        robots = list(list_namespace_robots(user.username))
        for robot in robots:
            robot.delete_instance(recursive=True, delete_nullable=True)

    # Null out any service key approvals. We technically lose information here, but its better than
    # falling and only occurs if a superuser is being deleted.
    ServiceKeyApproval.update(approver=None).where(ServiceKeyApproval.approver == user).execute()

    # Delete any federated user links.
    FederatedLogin.delete().where(FederatedLogin.user == user).execute()


def get_pull_credentials(robotname):
    """
    Returns the pull credentials for a robot with the given name.
    """
    try:
        robot = lookup_robot(robotname)
    except InvalidRobotException:
        return None

    token = retrieve_robot_token(robot)

    return {
        "username": robot.username,
        "password": token,
        "registry": "%s://%s/v1/"
        % (config.app_config["PREFERRED_URL_SCHEME"], config.app_config["SERVER_HOSTNAME"]),
    }


def get_region_locations(user):
    """
    Returns the locations defined as preferred storage for the given user.
    """
    query = (
        UserRegion.select(UserRegion, ImageStorageLocation)
        .join(ImageStorageLocation)
        .where(UserRegion.user == user)
    )
    return set([region.location.name for region in query])


def get_federated_logins(user_ids, service_name):
    """
    Returns all federated logins for the given user ids under the given external service.
    """
    if not user_ids:
        return []

    return (
        FederatedLogin.select()
        .join(User)
        .switch(FederatedLogin)
        .join(LoginService)
        .where(FederatedLogin.user << user_ids, LoginService.name == service_name)
    )


def list_namespace_geo_restrictions(namespace_name):
    """
    Returns all of the defined geographic restrictions for the given namespace.
    """
    return NamespaceGeoRestriction.select().join(User).where(User.username == namespace_name)


def get_minimum_user_id():
    return User.select(fn.Min(User.id)).tuples().get()[0]


class LoginWrappedDBUser(UserMixin):
    def __init__(self, user_uuid, db_user=None):
        self._uuid = user_uuid
        self._db_user = db_user

    def db_user(self):
        if not self._db_user:
            self._db_user = get_user_by_uuid(self._uuid)
        return self._db_user

    @property
    def is_authenticated(self):
        return self.db_user() is not None

    @property
    def is_active(self):
        return self.db_user() and self.db_user().verified

    def get_id(self):
        return str(self._uuid)
