import RepositoriesList from "src/routes/RepositoriesList/RepositoriesList";

export default function NpmPlugin() {
  return (
    <div>
      <h1>NpmPlugin</h1>
      <RepositoriesList organizationName={null} />
    </div>
  );
}
