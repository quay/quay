from app import get_app_url, avatar
from data import model
from util.names import parse_robot_username
from jinja2 import Environment, FileSystemLoader


def icon_path(icon_name):
    return "%s/static/img/icons/%s.png" % (get_app_url(), icon_name)


def icon_image(icon_name):
    return '<img src="%s" alt="%s">' % (icon_path(icon_name), icon_name)


def team_reference(teamname):
    avatar_html = avatar.get_mail_html(teamname, teamname, 24, "team")
    return "<span>%s <b>%s</b></span>" % (avatar_html, teamname)


def user_reference(username):
    user = model.user.get_namespace_user(username)
    if not user:
        return username

    if user.robot:
        parts = parse_robot_username(username)
        user = model.user.get_namespace_user(parts[0])

        return """<span><img src="%s" alt="Robot"> <b>%s</b></span>""" % (
            icon_path("wrench"),
            username,
        )

    avatar_html = avatar.get_mail_html(
        user.username, user.email, 24, "org" if user.organization else "user"
    )

    return """
  <span>
  %s
  <b>%s</b>
  </span>""" % (
        avatar_html,
        username,
    )


def repository_tag_reference(repository_path_and_tag):
    (repository_path, tag) = repository_path_and_tag
    (namespace, repository) = repository_path.split("/")
    owner = model.user.get_namespace_user(namespace)
    if not owner:
        return tag

    return """<a href="%s/repository/%s/%s?tag=%s&tab=tags">%s</a>""" % (
        get_app_url(),
        namespace,
        repository,
        tag,
        tag,
    )


def repository_reference(pair):
    if isinstance(pair, tuple):
        (namespace, repository) = pair
    else:
        pair = pair.split("/")
        namespace = pair[0]
        repository = pair[1]

    owner = model.user.get_namespace_user(namespace)
    if not owner:
        return "%s/%s" % (namespace, repository)

    avatar_html = avatar.get_mail_html(
        owner.username, owner.email, 16, "org" if owner.organization else "user"
    )

    return """
  <span style="white-space: nowrap;">
  %s
  <a href="%s/repository/%s/%s">%s/%s</a>
  </span>
  """ % (
        avatar_html,
        get_app_url(),
        namespace,
        repository,
        namespace,
        repository,
    )


def admin_reference(username):
    user = model.user.get_user_or_org(username)
    if not user:
        return "account settings"

    if user.organization:
        return """
    <a href="%s/organization/%s?tab=settings">organization's admin setting</a>
    """ % (
            get_app_url(),
            username,
        )
    else:
        return """
    <a href="%s/user/">account settings</a>
    """ % (
            get_app_url()
        )


def get_template_env(searchpath):
    template_loader = FileSystemLoader(searchpath=searchpath)
    template_env = Environment(loader=template_loader)
    add_filters(template_env)
    return template_env


def add_filters(template_env):
    template_env.filters["icon_image"] = icon_image
    template_env.filters["team_reference"] = team_reference
    template_env.filters["user_reference"] = user_reference
    template_env.filters["admin_reference"] = admin_reference
    template_env.filters["repository_reference"] = repository_reference
    template_env.filters["repository_tag_reference"] = repository_tag_reference
