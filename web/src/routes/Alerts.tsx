import { Alert, AlertActionCloseButton, AlertGroup } from "@patternfly/react-core";
import { useRecoilState } from "recoil";
import { AlertVariant, alertState } from "src/atoms/AlertState";


export default function Alerts(){
    const [alerts, setAlerts] = useRecoilState(alertState);
    return (
    <AlertGroup isToast isLiveRegion>
        {alerts.map(alert=><Alert
            isExpandable={alert.message != null}
            variant={alert.variant}
            title={alert.title}
            timeout={alert.variant === AlertVariant.Success}
            actionClose={
            <AlertActionCloseButton
                onClose={()=>{setAlerts(prev=>prev.filter(a=>a.key!==alert.key))}}
            />
            }
            key={alert.key}
        >
            {alert.message}
        </Alert>)}
    </AlertGroup>
    )
}
