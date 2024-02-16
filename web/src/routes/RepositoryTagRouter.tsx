import TagDetails from 'src/routes/TagDetails/TagDetails';
import RepositoryDetails from 'src/routes/RepositoryDetails/RepositoryDetails';
import {useLocation} from 'react-router-dom';
import Build from './Build/Build';

export default function RepositoryTagRouter() {
  const location = useLocation();
  const pathParts = location.pathname.split('/').slice(3);
  if (pathParts.length > 2 && pathParts[pathParts.length - 2] === 'tag') {
    return <TagDetails />;
  } else if (
    pathParts.length > 2 &&
    pathParts[pathParts.length - 2] === 'build'
  ) {
    return <Build />;
  } else {
    return <RepositoryDetails />;
  }
}
