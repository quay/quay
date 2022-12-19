import {useEffect, useState} from 'react';
import {
  getLabels,
  LabelsResponse,
  Label as ImageLabel,
} from 'src/resources/TagResource';
import {Label, Skeleton} from '@patternfly/react-core';
import './Labels.css';

export default function Labels(props: LabelsProps) {
  const [labels, setLabels] = useState<ImageLabel[]>([]);
  const [err, setErr] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    (async () => {
      try {
        const labelsResp: LabelsResponse = await getLabels(
          props.org,
          props.repo,
          props.digest,
        );
        setLabels(labelsResp.labels);
      } catch (error: any) {
        console.error('Unable to get labels: ', error);
        setErr(true);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (err) {
    return <>Unable to get labels</>;
  }

  if (loading) {
    return <Skeleton width="100%" />;
  }

  if (labels != null && labels.length === 0) {
    return <>No labels found</>;
  }

  return (
    <>
      {labels.map((label: ImageLabel) => (
        <>
          <Label key={label.key} className="label">
            <span className="label-content">
              {label.key} = {label.value}
            </span>
          </Label>{' '}
        </>
      ))}
    </>
  );
}

interface LabelsProps {
  org: string;
  repo: string;
  digest: string;
}
