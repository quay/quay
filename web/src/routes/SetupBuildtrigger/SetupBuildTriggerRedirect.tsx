import {useEffect} from 'react';
import {useLocation, useNavigate} from 'react-router-dom';

export default function SetupBuildTriggerRedirect() {
  const navigate = useNavigate();
  const location = useLocation();
  useEffect(() => {
    const splitPath = location.pathname.split('/trigger/');
    if (splitPath.length < 2) {
      // Never reached since the routing rule will always contain "/trigger/"
      return;
    }
    const repoDetailsPath = splitPath[0];
    const triggerUuid = splitPath[1];
    const newPath = repoDetailsPath + '?tab=builds&setupTrigger=' + triggerUuid;
    navigate(newPath);
  });
  return <>You will now be redirected</>;
}
