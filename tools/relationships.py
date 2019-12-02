from data.database import User, Repository, TeamMember


def fix_ident(ident):
    return str(ident).translate(None, "-/.")


with open("outfile.dot", "w") as outfile:
    outfile.write("digraph relationships {\n")

    for repo in Repository.select():
        ns = fix_ident(repo.namespace_user.username)
        outfile.write("%s_%s -> %s\n" % (ns, fix_ident(repo.name), ns))

    teams_in_orgs = set()

    for member in TeamMember.select():
        if "+" in member.user.username:
            continue

        org_name = fix_ident(member.team.organization.username)

        team_to_org = (member.team.name, member.team.organization.username)
        if not team_to_org in teams_in_orgs:
            teams_in_orgs.add(team_to_org)
            outfile.write("%s_%s -> %s\n" % (org_name, fix_ident(member.team.name), org_name))

        team_name = fix_ident(member.team.name)

        outfile.write("%s -> %s_%s\n" % (fix_ident(member.user.username), org_name, team_name))
        outfile.write("%s_%s [shape=box]\n" % (org_name, team_name))

    for user in User.select():
        if "+" in user.username:
            continue

        if user.organization:
            outfile.write("%s [shape=circle]\n" % fix_ident(user.username))
        else:
            outfile.write("%s [shape=triangle]\n" % fix_ident(user.username))

    outfile.write("}")
