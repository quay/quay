import React from "react";
import RepositoriesList from "src/routes/RepositoriesList/RepositoriesList";

export function NpmPackagesList() {
  return (
    <>
      <RepositoriesList
        organizationName={null}
        repoKind={"npm"}
        title={"NPM Packages"}
      />
    </>
  );
}
