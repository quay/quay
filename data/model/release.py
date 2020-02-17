from data.database import QuayRelease, QuayRegion, QuayService


def set_region_release(service_name, region_name, version):
    service, _ = QuayService.get_or_create(name=service_name)
    region, _ = QuayRegion.get_or_create(name=region_name)

    return QuayRelease.get_or_create(service=service, version=version, region=region)


def get_recent_releases(service_name, region_name):
    return (
        QuayRelease.select(QuayRelease)
        .join(QuayService)
        .switch(QuayRelease)
        .join(QuayRegion)
        .where(
            QuayService.name == service_name,
            QuayRegion.name == region_name,
            QuayRelease.reverted == False,
        )
        .order_by(QuayRelease.created.desc())
    )
