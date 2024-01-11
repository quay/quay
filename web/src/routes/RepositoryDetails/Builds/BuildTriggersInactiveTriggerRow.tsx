import {Td, Tr} from '@patternfly/react-table';
import {AlertVariant} from 'src/atoms/AlertState';
import Conditional from 'src/components/empty/Conditional';
import {useAlerts} from 'src/hooks/UseAlerts';
import {useDeleteBuildTrigger} from 'src/hooks/UseBuildTriggers';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';

export default function InactiveTrigger(props: InactiveTriggerProps) {
  const config = useQuayConfig();
  const {addAlert} = useAlerts();
  const {deleteTrigger} = useDeleteBuildTrigger(
    props.org,
    props.repo,
    props.trigger_uuid,
    {
      onSuccess: () => {
        addAlert({
          variant: AlertVariant.Success,
          title: 'Successfully deleted trigger',
        });
      },
      onError: (error) => {
        addAlert({
          variant: AlertVariant.Failure,
          title: 'Failed to delete trigger',
        });
      },
    },
  );
  return (
    <Tr>
      <Td colSpan={7}>
        This build trigger has not had its setup completed.
        <Conditional if={config?.config?.REGISTRY_STATE !== 'readonly'}>
          <a onClick={() => deleteTrigger()}> Delete Trigger</a>
        </Conditional>
      </Td>
    </Tr>
  );
}

interface InactiveTriggerProps {
  org: string;
  repo: string;
  trigger_uuid: string;
}
