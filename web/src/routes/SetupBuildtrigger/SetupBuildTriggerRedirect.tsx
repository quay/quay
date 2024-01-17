import {useEffect} from 'react';
import {useLocation, useNavigate} from 'react-router-dom';

export default function SetupBuildTriggerRedirect() {
  const navigate = useNavigate();
  const location = useLocation();
  useEffect(() => {
    const splitBy = '/trigger/';
    const lastIndexOfTrigger = location.pathname.lastIndexOf(splitBy);
    if (lastIndexOfTrigger === -1) {
      // Never reached since the routing rule will always contain "/trigger/"
      return;
    }
    const repoDetailsPath = location.pathname.substring(0, lastIndexOfTrigger);
    const triggerUuid = location.pathname.substring(
      lastIndexOfTrigger + splitBy.length,
      location.pathname.length,
    );
    const newPath = repoDetailsPath + '?tab=builds&setupTrigger=' + triggerUuid;
    navigate(newPath);
  });
  return <>You will now be redirected</>;
}
