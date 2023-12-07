import {
  ActionGroup,
  Button,
  Checkbox,
  Form,
  FormGroup,
  Spinner,
  Title,
} from '@patternfly/react-core';
import {useEffect, useState} from 'react';
import {AlertVariant} from 'src/atoms/AlertState';
import RequestError from 'src/components/errors/RequestError';
import {useAlerts} from 'src/hooks/UseAlerts';
import {
  useRepositoryPolicy,
  useUpdateRepositoryPolicy,
} from 'src/hooks/UseRepositoryPolicy';
import {isNullOrUndefined} from 'src/libs/utils';

export default function Policies(props: PoliciesProps) {
  const {addAlert} = useAlerts();
  const [blockUnsignedImagesEnabled, setBlockUnsignedImagesEnabled] =
    useState<boolean>(false);
  const {policy, isLoading, isSuccess, error, dataUpdatedAt} =
    useRepositoryPolicy(props.org, props.repo);
  const {updatePolicy} = useUpdateRepositoryPolicy(props.org, props.repo, {
    onSuccess: () => {
      addAlert({
        title: 'Successfully updated policy',
        variant: AlertVariant.Success,
      });
    },
    onError: (error) => {
      addAlert({
        title: 'Could not update policy',
        variant: AlertVariant.Failure,
        message: error.toString(),
      });
    },
  });

  useEffect(() => {
    if (isSuccess) {
      setBlockUnsignedImagesEnabled(
        isNullOrUndefined(policy.blockUnsignedImages)
          ? false
          : policy.blockUnsignedImages,
      );
    }
  }, [isSuccess, dataUpdatedAt]);

  if (isLoading) {
    return <Spinner />;
  }

  if (!isNullOrUndefined(error)) {
    return <RequestError message={error.toString()} />;
  }

  const update = () => {
    const updatedPolcy = {
      blockUnsignedImages: blockUnsignedImagesEnabled,
    };
    updatePolicy(updatedPolcy);
  };

  return (
    <>
      <Title headingLevel="h2">Repository Policies</Title>
      <div style={{paddingBottom: '2em'}} />
      <Form>
        <FormGroup
          label="Block pull of unsigned images"
          isStack
          fieldId="block-pull-of-unsigned-images"
          hasNoPaddingTop
          role="group"
        >
          <Checkbox
            isChecked={blockUnsignedImagesEnabled}
            onChange={(_, ischecked) =>
              setBlockUnsignedImagesEnabled(ischecked)
            }
            label="enabled"
            id="block-pull-of-unsigned-images-checkbox"
          />
        </FormGroup>
        <ActionGroup>
          <Button variant="primary" onClick={update}>
            Submit
          </Button>
          <Button variant="link">Cancel</Button>
        </ActionGroup>
      </Form>
    </>
  );
}

interface PoliciesProps {
  org: string;
  repo: string;
}
